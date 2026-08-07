"""VF-DM-M4-S02 — SimulationDefinition + Validation tests."""

import pytest
from virtual_factory.assembly.definition import (
    SimulationDefinition, PrimitiveDef, EdgeDef,
    validate_definition, build_topology_from_definition, ValidationError,
)
from virtual_factory.assembly.definition_io import (
    load_definition_from_dict, load_definition_from_yaml,
)
from virtual_factory.discrete.run_service import DiscreteRunService
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.assembly.handlers import (
    make_source_handler, make_buffer_handler, make_processor_handler,
    make_process_complete_handler, make_quality_gate_handler, make_sink_handler,
)
from virtual_factory.assembly.runtime import AssemblyRuntimeState
from virtual_factory.assembly.quality import QualityDisposition
from virtual_factory.discrete.handler_registry import HandlerRegistry


# ═══════════════════════════════════════
# Validator tests
# ═══════════════════════════════════════

class TestValidator:
    def test_valid_definition_passes(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[
                PrimitiveDef(id="s", type="source"),
                PrimitiveDef(id="b", type="buffer", capacity=5),
                PrimitiveDef(id="p", type="processor"),
                PrimitiveDef(id="q", type="quality_gate"),
                PrimitiveDef(id="sk", type="sink"),
            ],
            edges=[
                EdgeDef(from_id="s", to="b"),
                EdgeDef(from_id="b", to="p"),
                EdgeDef(from_id="p", to="q"),
                EdgeDef(from_id="q", to="sk", disposition="pass"),
            ],
        )
        result = validate_definition(defn)
        assert result.valid

    def test_duplicate_id_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[
                PrimitiveDef(id="s", type="source"),
                PrimitiveDef(id="s", type="source"),
            ],
            edges=[],
        )
        result = validate_definition(defn)
        assert not result.valid
        assert any("duplicate" in e for e in result.errors)

    def test_unknown_type_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[PrimitiveDef(id="x", type="nonexistent")],
            edges=[],
        )
        assert not validate_definition(defn).valid

    def test_invalid_buffer_capacity_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[PrimitiveDef(id="b", type="buffer", capacity=0)],
            edges=[],
        )
        assert not validate_definition(defn).valid

    def test_invalid_processing_time_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[PrimitiveDef(id="p", type="processor", processing_time_s=-1)],
            edges=[],
        )
        assert not validate_definition(defn).valid

    def test_missing_edge_target_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[PrimitiveDef(id="s", type="source")],
            edges=[EdgeDef(from_id="s", to="nonexistent")],
        )
        assert not validate_definition(defn).valid

    def test_source_without_outgoing_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[PrimitiveDef(id="s", type="source")],
            edges=[],
        )
        assert not validate_definition(defn).valid

    def test_quality_gate_missing_pass_fails(self):
        defn = SimulationDefinition(
            model_id="test",
            primitives=[
                PrimitiveDef(id="q", type="quality_gate"),
                PrimitiveDef(id="sk", type="sink"),
            ],
            edges=[
                EdgeDef(from_id="q", to="sk", disposition="rework"),
            ],
        )
        assert not validate_definition(defn).valid


# ═══════════════════════════════════════
# Loader + builder tests
# ═══════════════════════════════════════

class TestLoaderAndBuilder:
    def test_load_from_dict(self):
        data = {
            "model": {"id": "demo"},
            "primitives": [
                {"id": "src", "type": "source"},
                {"id": "buf", "type": "buffer", "capacity": 5},
                {"id": "proc", "type": "processor"},
                {"id": "qg", "type": "quality_gate"},
                {"id": "snk", "type": "sink"},
            ],
            "edges": [
                {"from": "src", "to": "buf"},
                {"from": "buf", "to": "proc"},
                {"from": "proc", "to": "qg"},
                {"from": "qg", "to": "snk", "disposition": "pass"},
            ],
        }
        defn = load_definition_from_dict(data)
        assert defn.model_id == "demo"
        assert len(defn.primitives) == 5
        assert len(defn.edges) == 4

    def test_build_topology_from_definition(self):
        data = {
            "model": {"id": "demo"},
            "primitives": [
                {"id": "src", "type": "source"},
                {"id": "buf", "type": "buffer", "capacity": 5},
                {"id": "proc", "type": "processor"},
                {"id": "qg", "type": "quality_gate"},
                {"id": "snk", "type": "sink"},
            ],
            "edges": [
                {"from": "src", "to": "buf"},
                {"from": "buf", "to": "proc"},
                {"from": "proc", "to": "qg"},
                {"from": "qg", "to": "snk", "disposition": "pass"},
            ],
        }
        defn = load_definition_from_dict(data)
        topo = build_topology_from_definition(defn)
        assert len(topo.primitives) == 5
        assert topo.next_primitive("src") == "buf"

    def test_load_from_yaml(self):
        defn = load_definition_from_yaml("configs/plants/generic_demo.yaml")
        assert defn.model_id == "generic-demo"
        assert len(defn.primitives) == 6
        assert len(defn.edges) == 5

    def test_generic_demo_runs(self):
        """Load generic demo YAML, build topology, run to completion."""
        defn = load_definition_from_yaml("configs/plants/generic_demo.yaml")
        topo = build_topology_from_definition(defn)

        state = AssemblyRuntimeState()
        wc = [0]
        reg = HandlerRegistry()
        reg.register("WIP_CREATED", make_source_handler(state, topo, wc))
        reg.register("WIP_QUEUED", make_buffer_handler(state, topo))
        reg.register("PROCESS_START", make_processor_handler(state, topo))
        reg.register("PROCESS_COMPLETE", make_process_complete_handler(state, topo))
        reg.register("QUALITY_CHECK", make_quality_gate_handler(state, topo,
            {"wip-0001": [QualityDisposition.PASS]}))
        reg.register("WIP_COMPLETED", make_sink_handler(state))

        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="demo", model_id="generic-demo"), reg,
                       initial_events=[
            ScheduledEvent(event_id="wip-0001-create", simulation_time_s=0,
                           event_type="WIP_CREATED", target_id="source-1"),
        ])
        for _ in range(100):
            if svc.snapshot.status in ("completed", "stopped", "failed"):
                break
            svc.step_once()

        assert svc.snapshot.status == "completed"
