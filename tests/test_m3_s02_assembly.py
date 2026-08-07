"""VF-DM-M3-S02 — Vertical Assembly Runtime tests.

Scenario A: Source→Buffer→Processor→QualityGate(PASS)→Sink
Scenario B: Source→Buffer→Processor→QualityGate(REWORK)→Processor→QualityGate(PASS)→Sink
"""

import pytest
from virtual_factory.assembly.primitives import (
    Source, Buffer, Processor, QualityGate, Sink,
)
from virtual_factory.assembly.quality import QualityDisposition
from virtual_factory.assembly.runtime import AssemblyRuntimeState, RuntimeStateError
from virtual_factory.assembly.topology import AssemblyTopology
from virtual_factory.assembly.wip import WipId, WipState, WipStatus
from virtual_factory.assembly.handlers import (
    make_source_handler,
    make_buffer_handler,
    make_processor_handler,
    make_process_complete_handler,
    make_quality_gate_handler,
    make_sink_handler,
)
from virtual_factory.discrete.engine import DiscreteSimulationEngine
from virtual_factory.discrete.handler_registry import HandlerRegistry
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.run_service import DiscreteRunService
from virtual_factory.discrete.events import ScheduledEvent


def _evt(event_id, simulation_time_s=0.0, event_type="", target_id="", causation_id=None):
    return ScheduledEvent(
        event_id=event_id, simulation_time_s=simulation_time_s,
        event_type=event_type, target_id=target_id, causation_id=causation_id,
    )


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def _rc(**kw):
    defaults = {"run_id": "m3s02", "model_id": "assembly-vslice"}
    defaults.update(kw)
    return RunContext(**defaults)


def _build_normal_flow_topology() -> tuple[AssemblyTopology, AssemblyRuntimeState, list[int]]:
    """Build topology: Source→Buffer→Processor→QualityGate→Sink."""
    topo = AssemblyTopology()
    for p in [
        Source(primitive_id="source-1"),
        Buffer(primitive_id="buffer-1", capacity=10),
        Processor(primitive_id="processor-1", processing_time_s=0.5),
        QualityGate(primitive_id="quality-1"),
        Sink(primitive_id="sink-1"),
    ]:
        topo.add_primitive(p)

    topo.add_edge("source-1", "buffer-1")
    topo.add_edge("buffer-1", "processor-1")
    topo.add_edge("processor-1", "quality-1")
    topo.add_edge("quality-1", "sink-1", QualityDisposition.PASS.value)

    state = AssemblyRuntimeState()
    return topo, state, [0]


def _build_rework_topology() -> tuple[AssemblyTopology, AssemblyRuntimeState, list[int]]:
    """Build topology with rework loop: QualityGate→REWORK→Processor."""
    topo = AssemblyTopology()
    for p in [
        Source(primitive_id="source-1"),
        Buffer(primitive_id="buffer-1", capacity=10),
        Processor(primitive_id="processor-1", processing_time_s=0.5),
        QualityGate(primitive_id="quality-1"),
        Sink(primitive_id="sink-1"),
    ]:
        topo.add_primitive(p)

    topo.add_edge("source-1", "buffer-1")
    topo.add_edge("buffer-1", "processor-1")
    topo.add_edge("processor-1", "quality-1")
    topo.add_edge("quality-1", "sink-1", QualityDisposition.PASS.value)
    topo.add_edge("quality-1", "processor-1", QualityDisposition.REWORK.value)

    state = AssemblyRuntimeState()
    return topo, state, [0]


def _build_registry(topo, state, wip_counter, dispositions=None):
    """Build HandlerRegistry for the vertical flow."""
    reg = HandlerRegistry()
    reg.register("WIP_CREATED", make_source_handler(state, topo, wip_counter))
    reg.register("WIP_QUEUED", make_buffer_handler(state, topo))
    reg.register("PROCESS_START", make_processor_handler(state, topo))
    reg.register("PROCESS_COMPLETE", make_process_complete_handler(state, topo))
    reg.register("QUALITY_CHECK", make_quality_gate_handler(state, topo, dispositions))
    reg.register("WIP_COMPLETED", make_sink_handler(state))
    return reg


def _run_to_completion(svc, max_steps=50):
    """Step service to completion."""
    for _ in range(max_steps):
        snap = svc.snapshot
        if snap.status in ("completed", "stopped", "failed"):
            break
        svc.step_once()
    return svc.snapshot


# ═══════════════════════════════════════════
# Scenario A — Normal flow
# ═══════════════════════════════════════════

class TestScenarioANormalFlow:
    """Normal: Source→Buffer→Processor→QualityGate(PASS)→Sink."""

    def test_completes_with_correct_location(self):
        topo, state, wc = _build_normal_flow_topology()
        reg = _build_registry(topo, state, wc, {"wip-0001": QualityDisposition.PASS})

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        final = _run_to_completion(svc)
        assert final.status == "completed"

        ws = state.get_wip(WipId("wip-0001"))
        assert ws is not None
        assert ws.status == WipStatus.COMPLETED
        assert ws.location == "sink-1"

    def test_simulation_time_reflects_processing(self):
        topo, state, wc = _build_normal_flow_topology()
        reg = _build_registry(topo, state, wc, {"wip-0001": QualityDisposition.PASS})

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        final = _run_to_completion(svc)
        # Processing delay 0.5s should advance simulation time
        assert final.simulation_time_s >= 0.5

    def test_pending_events_zero_at_completion(self):
        topo, state, wc = _build_normal_flow_topology()
        reg = _build_registry(topo, state, wc, {"wip-0001": QualityDisposition.PASS})

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        final = _run_to_completion(svc)
        assert final.pending_events == 0

    def test_trace_has_correct_event_types(self):
        topo, state, wc = _build_normal_flow_topology()
        reg = _build_registry(topo, state, wc, {"wip-0001": QualityDisposition.PASS})

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        _run_to_completion(svc)
        trace_types = [t.event_type for t in svc.snapshot.recent_events]
        assert "WIP_CREATED" in trace_types
        assert "WIP_QUEUED" in trace_types
        assert "PROCESS_START" in trace_types
        assert "PROCESS_COMPLETE" in trace_types
        assert "QUALITY_CHECK" in trace_types
        assert "WIP_COMPLETED" in trace_types

    def test_buffer_empty_at_end(self):
        topo, state, wc = _build_normal_flow_topology()
        reg = _build_registry(topo, state, wc, {"wip-0001": QualityDisposition.PASS})

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        _run_to_completion(svc)
        assert state.buffer_size("buffer-1") == 0


# ═══════════════════════════════════════════
# Scenario B — Rework flow
# ═══════════════════════════════════════════

class TestScenarioBRework:
    """REWORK: Source→Buffer→Processor→QualityGate(REWORK)→Processor→QualityGate(PASS)→Sink."""

    def test_rework_eventually_completes(self):
        topo, state, wc = _build_rework_topology()
        # First quality check: REWORK, second: PASS
        dispositions = {"wip-0001": QualityDisposition.REWORK}
        reg = _build_registry(topo, state, wc, dispositions)

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        # First pass through quality gate fails with REWORK
        # The handler routes back to processor-1
        # On the second pass, disposition_map no longer has wip-0001 → defaults to PASS
        final = _run_to_completion(svc)
        assert final.status == "completed"

        ws = state.get_wip(WipId("wip-0001"))
        assert ws is not None
        assert ws.status == WipStatus.COMPLETED
        assert ws.location == "sink-1"

    def test_same_wip_id_retained(self):
        topo, state, wc = _build_rework_topology()
        dispositions = {"wip-0001": QualityDisposition.REWORK}
        reg = _build_registry(topo, state, wc, dispositions)

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        _run_to_completion(svc)
        ws = state.get_wip(WipId("wip-0001"))
        assert ws is not None

    def test_rework_observable_in_trace(self):
        topo, state, wc = _build_rework_topology()
        dispositions = {"wip-0001": QualityDisposition.REWORK}
        reg = _build_registry(topo, state, wc, dispositions)

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        _run_to_completion(svc)
        trace = svc.snapshot.recent_events
        state_changes = [sc for t in trace for sc in t.state_changes]

        # Should see rework state change
        rework_changes = [sc for sc in state_changes if "rework" in sc.lower()]
        assert len(rework_changes) >= 1

    def test_rework_doubles_processor_events(self):
        """Processor is visited twice: initial + after rework."""
        topo, state, wc = _build_rework_topology()
        dispositions = {"wip-0001": QualityDisposition.REWORK}
        reg = _build_registry(topo, state, wc, dispositions)

        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", simulation_time_s=0.0,
                 event_type="WIP_CREATED", target_id="source-1"),
        ])

        _run_to_completion(svc)
        trace = svc.snapshot.recent_events
        process_starts = [t for t in trace if t.event_type == "PROCESS_START"]
        assert len(process_starts) == 2  # initial + rework


# ═══════════════════════════════════════════
# Buffer capacity proof
# ═══════════════════════════════════════════

class TestBufferCapacity:
    """Buffer enforces capacity — no silent WIP loss."""

    def test_buffer_full_rejects(self):
        topo = AssemblyTopology()
        buf = Buffer(primitive_id="buf-1", capacity=1)
        topo.add_primitive(buf)
        topo.add_primitive(Processor(primitive_id="proc-1"))
        topo.add_edge("buf-1", "proc-1")

        state = AssemblyRuntimeState()
        state.ensure_buffer(buf)
        w1 = WipId("w-1")
        state.buffer_enqueue("buf-1", w1, 1)

        with pytest.raises(RuntimeStateError, match="full"):
            state.buffer_enqueue("buf-1", WipId("w-2"), 1)

    def test_buffer_dequeue_from_empty_raises(self):
        state = AssemblyRuntimeState()
        state.ensure_buffer(Buffer(primitive_id="buf-1"))
        with pytest.raises(RuntimeStateError, match="empty"):
            state.buffer_dequeue("buf-1")


# ═══════════════════════════════════════════
# Runtime state integrity
# ═══════════════════════════════════════════

class TestRuntimeState:
    """AssemblyRuntimeState basic invariants."""

    def test_add_and_get_wip(self):
        state = AssemblyRuntimeState()
        ws = WipState(wip_id=WipId("w-1"))
        state.add_wip(ws)
        assert state.get_wip(WipId("w-1")) is ws
        assert state.wip_count == 1

    def test_duplicate_wip_rejected(self):
        state = AssemblyRuntimeState()
        state.add_wip(WipState(wip_id=WipId("w-1")))
        with pytest.raises(RuntimeStateError, match="already registered"):
            state.add_wip(WipState(wip_id=WipId("w-1")))


# ═══════════════════════════════════════════
# Topology
# ═══════════════════════════════════════════

class TestTopology:
    """Topology connectivity invariants."""

    def test_edge_routing(self):
        topo = AssemblyTopology()
        topo.add_primitive(Source(primitive_id="s"))
        topo.add_primitive(Buffer(primitive_id="b"))
        topo.add_edge("s", "b")
        assert topo.next_primitive("s") == "b"

    def test_disposition_edge(self):
        topo = AssemblyTopology()
        topo.add_primitive(QualityGate(primitive_id="qg"))
        topo.add_primitive(Sink(primitive_id="sk"))
        topo.add_primitive(Processor(primitive_id="p"))
        topo.add_edge("qg", "sk", "pass")
        topo.add_edge("qg", "p", "rework")
        assert topo.next_primitive("qg", "pass") == "sk"
        assert topo.next_primitive("qg", "rework") == "p"
        assert topo.next_primitive("qg", "scrap") is None
