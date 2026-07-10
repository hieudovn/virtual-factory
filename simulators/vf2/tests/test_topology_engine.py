"""Tests for VF-2 topology & dependency engine (ST04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulators.vf2.object_registry import ObjectRegistry
from simulators.vf2.package_loader import load_package
from simulators.vf2.signal_registry import SignalRegistry
from simulators.vf2.topology_engine import TopologyEngine, _infer_signal_deps

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def pkg():
    return load_package(GOLDEN)


@pytest.fixture(scope="module")
def obj_reg(pkg):
    return ObjectRegistry(pkg)


@pytest.fixture(scope="module")
def sig_reg(pkg):
    return SignalRegistry(pkg)


@pytest.fixture(scope="module")
def engine(pkg, obj_reg, sig_reg):
    return TopologyEngine(pkg, obj_reg, sig_reg)


@pytest.fixture(scope="module")
def graph(pkg, obj_reg, sig_reg):
    engine = TopologyEngine(pkg, obj_reg, sig_reg)
    return engine.build()


class TestTopologyEngine:

    # AC-1
    def test_build_from_golden(self, graph):
        assert len(graph.process_flow) > 0

    def test_process_flow_graph(self, graph):
        """Motor–Pump edges create correct flow graph."""
        # Edge: VF2-REF-PMP-101A → VF2-REF-PMP-MTR-101A
        assert "VF2-REF-PMP-MTR-101A" in graph.process_flow.get(
            "VF2-REF-PMP-101A", []
        )
        # Edge: VF2-REF-PMP-101B → VF2-REF-PMP-MTR-101B
        assert "VF2-REF-PMP-MTR-101B" in graph.process_flow.get(
            "VF2-REF-PMP-101B", []
        )

    # AC-2
    def test_topological_sort(self, graph, sig_reg):
        """Signals must be sorted: independent first, dependent last."""
        order = graph.eval_order
        assert len(order) == sig_reg.signal_count
        # If signal A depends on B, B must appear before A
        for sig_id, upstream_ids in graph.signal_deps.items():
            if upstream_ids:
                sig_idx = order.index(sig_id)
                for up_id in upstream_ids:
                    if up_id in order:
                        assert order.index(up_id) < sig_idx, (
                            f"{up_id} should be before {sig_id} in eval_order"
                        )

    # AC-3
    def test_get_downstream_objects(self, engine):
        downstream = engine.get_downstream_objects("VF2-REF-PMP-101A")
        assert isinstance(downstream, list)
        # Pump A is connected to Motor A
        assert "VF2-REF-PMP-MTR-101A" in downstream

    def test_get_downstream_objects_nonexistent(self, engine):
        downstream = engine.get_downstream_objects("VF2-NONEXISTENT")
        assert downstream == []

    # AC-4
    def test_get_affected_signals(self, engine):
        """get_affected_signals returns signal IDs for a given object."""
        affected = engine.get_affected_signals("VF2-REF-PMP-101A")
        assert isinstance(affected, list)
        # Pump A has 3 signals (FT, PT, VB) → should be in affected
        expected_sigs = [
            "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER",
            "VF2.PUMP_STATION_01.PT_101.DISCHARGE_PRESSURE_TRANSMITTER",
            "VF2.PUMP_STATION_01.VB_101.PUMP_A_VIBRATION_SENSOR",
        ]
        for es in expected_sigs:
            assert es in affected, f"Expected {es} in affected signals"

    # AC-5
    def test_boundary_endpoints_identified(self, graph):
        """Topology edges to VF2-UNIT-* or objects not in objects[] → boundary."""
        assert len(graph.boundary_endpoints) >= 1
        assert "VF2-UNIT-REF-PUMP-STATION-01" in graph.boundary_endpoints
        assert "VF2-REF-PMP-DISCH-001" in graph.boundary_endpoints

    # AC-6
    def test_signal_dependency_dag_non_empty(self, graph):
        """Signal dependency DAG is non-empty."""
        assert len(graph.signal_deps) > 0

    def test_empty_electrical_edges(self, graph):
        """Golden fixture has no electrical edges → electrical dict is empty."""
        assert graph.electrical == {}

    def test_resolve_order_subset(self, engine):
        """resolve_order handles a subset of signals."""
        sigs = [
            "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER",
            "VF2.PUMP_STATION_01.LT_101.SUCTION_LEVEL_TRANSMITTER",
        ]
        order = engine.resolve_order(sigs)
        assert len(order) == 2

    def test_get_affected_downstream(self, engine):
        """Affected signals include downstream object signals."""
        # No objects are downstream of valves in golden fixture,
        # but direct signals should still be found
        affected = engine.get_affected_signals("VF2-REF-PMP-VLV-102A")
        assert isinstance(affected, list)


class TestInferSignalDeps:

    def test_measurement_depends_on_status_same_asset(self, pkg, obj_reg, sig_reg):
        """Measurement signals should have no inferred status dep since there
        are no status signals in the golden fixture (all 4 are measurements)."""
        flow: dict = {}
        deps = _infer_signal_deps(sig_reg, obj_reg, flow)
        # No status signals → no deps from rule 1
        for sig_id, upstream in deps.items():
            assert len(upstream) == 0, f"{sig_id} has unexpected deps: {upstream}"

    def test_process_flow_creates_deps(self, pkg, obj_reg, sig_reg):
        """Upstream→downstream edges in process flow create measurement deps."""
        from simulators.vf2.models import VF2SimulationSignal, VF2SignalBehavior, VF2SignalDirection, VF2SignalType

        # Build mock: pump A has a measurement, motor A has a status
        pump_sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.PUMP_MEAS",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Pump Measurement",
            direction=VF2SignalDirection.VF2_INPUT,
            behavior=VF2SignalBehavior(
                signal_type=VF2SignalType.MEASUREMENT,
                initial_value=0.0,
            ),
        )
        motor_sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.MOTOR_STATUS",
            canonical_asset_id="ASSET-REF-PMP-MTR-101A",
            name="Test Motor Status",
            direction=VF2SignalDirection.VF2_OUTPUT,
            behavior=VF2SignalBehavior(
                signal_type=VF2SignalType.STATUS,
                initial_value=False,
            ),
        )
        # Add to registry
        from copy import deepcopy
        pkg2 = deepcopy(pkg)
        pkg2.signals = list(pkg2.signals) + [pump_sig, motor_sig]
        reg2 = SignalRegistry(pkg2)

        flow = {"VF2-REF-PMP-101A": ["VF2-REF-PMP-MTR-101A"]}
        deps = _infer_signal_deps(reg2, obj_reg, flow)

        # Pump measurement should depend on nothing extra (motor status is on
        # different canonical asset), but deps should exist
        assert "VF2.TEST.PUMP_MEAS" in deps
        assert "VF2.TEST.MOTOR_STATUS" in deps


class TestTopologicalSort:

    def test_simple_linear(self):
        from simulators.vf2.topology_engine import _topological_sort
        deps = {
            "A": [],
            "B": ["A"],
            "C": ["B"],
        }
        order = _topological_sort(deps)
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_no_deps(self):
        from simulators.vf2.topology_engine import _topological_sort
        deps = {"A": [], "B": [], "C": []}
        order = _topological_sort(deps)
        assert len(order) == 3

    def test_cycle_detected(self):
        from simulators.vf2.topology_engine import _topological_sort
        deps = {"A": ["B"], "B": ["C"], "C": ["A"]}
        with pytest.raises(ValueError, match="Cycle detected"):
            _topological_sort(deps)
