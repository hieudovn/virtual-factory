"""C01 correction tests for M2-S03."""
import pytest
from virtual_factory.discrete.snapshot import RuntimeSnapshot, RuntimeSnapshotError
from virtual_factory.discrete.trace import EventTraceEntry, RuntimeDiagnostics
from virtual_factory.discrete.engine import DiscreteSimulationEngine
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.handler_registry import HandlerRegistry
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.scheduler import FutureEventSchedulerError

def _rc(**kw): d={"run_id":"r1","model_id":"m1"};d.update(kw);return RunContext(**d)
def _evt(eid,simulation_time_s=0.0,event_type="test",**kw):
    return ScheduledEvent(event_id=eid,simulation_time_s=simulation_time_s,event_type=event_type,**kw)
def _ok(e):return HandlerOutcome(event_id=e.event_id,success=True,follow_up_events=(),state_changes=("ok",))
def _snap(**kw):
    d=dict(run_id="r1",model_id="m1",model_version=None,scenario_id=None,scenario_version=None,
           status="created",simulation_time_s=0.0,stop_reason=None,failure_error=None,
           processed_events=0,pending_events=0,last_event_id=None,snapshot_sequence=0)
    d.update(kw);return RuntimeSnapshot(**d)
def _tr(**kw):
    d=dict(trace_sequence=1,event_id="e1",event_type="t",target_id="",simulation_time_s=0.0,
           priority=0,scheduler_sequence=1,correlation_id=None,causation_id=None,
           result="committed",error_code=None,error_detail=None,state_changes=(),
           requested_follow_up_events=0,scheduled_follow_up_events=0,
           processed_events_after=1,pending_events_after=0)
    d.update(kw);return EventTraceEntry(**d)

class TestC01Positional:
    def test_legacy_13_args_explicit_schema(self):
        s = RuntimeSnapshot("r1","m1",None,None,None,"created",0.0,None,None,0,0,None,0,"1.0.0")
        assert s.schema_version == "1.0.0"
        assert s.recent_events == ()
        assert isinstance(s.diagnostics, RuntimeDiagnostics)

    def test_legacy_13_args_default_schema(self):
        s = RuntimeSnapshot("r1","m1",None,None,None,"created",0.0,None,None,0,0,None,0)
        assert s.schema_version == "1.1.0"

    def test_schema_version_non_empty_rejected(self):
        with pytest.raises(RuntimeSnapshotError, match="schema_version"):
            _snap(schema_version="")

    def test_schema_version_non_string_rejected(self):
        with pytest.raises(RuntimeSnapshotError, match="schema_version"):
            _snap(schema_version=123)

    def test_diagnostics_wrong_type_rejected(self):
        with pytest.raises(RuntimeSnapshotError, match="diagnostics"):
            _snap(diagnostics="bad")


class TestC01NoTrace:
    def test_scheduler_pop_failure_no_trace(self, monkeypatch):
        e = DiscreteSimulationEngine(_rc(), HandlerRegistry(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")])
        def _fail():
            raise FutureEventSchedulerError("injected")
        monkeypatch.setattr(e._scheduler, "pop_next", _fail)
        snap = e.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "scheduler_pop_error"
        assert snap.recent_events == ()
        assert snap.diagnostics.trace_total_entries == 0
        assert snap.diagnostics.trace_size == 0

    def test_stop_after_trace_preserves_entries(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("a"), _evt("b")])
        e.step_event()
        total = e.to_snapshot().diagnostics.trace_total_entries
        e.stop("done")
        snap = e.to_snapshot()
        assert snap.diagnostics.trace_total_entries == total
        assert len(snap.recent_events) == 1


class TestC01Payload:
    def test_payload_not_in_trace(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        secret = {"secret_marker": "MUST_NOT_APPEAR_IN_TRACE", "nested": {"value": 123}}
        evt = ScheduledEvent(event_id="e1", simulation_time_s=0.0, event_type="test", payload=secret)
        e.initialize(initial_events=[evt]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert not hasattr(t, "payload")
        diag_repr = repr(e.to_snapshot().diagnostics)
        assert "MUST_NOT_APPEAR_IN_TRACE" not in diag_repr


class TestC01Determinism:
    def test_full_equality(self):
        def run():
            r = HandlerRegistry(); r.register("test", _ok)
            e = DiscreteSimulationEngine(RunContext(run_id="det", model_id="m1"), r, trace_capacity=3)
            e.initialize(initial_events=[_evt("a", simulation_time_s=1.0), _evt("b", simulation_time_s=2.0)])
            snaps = []
            while True:
                s = e.step_event(); snaps.append(s)
                if s.status in ("completed", "failed", "stopped"): break
            return tuple(snaps)
        assert run() == run()


class TestC01Sequence:
    def test_independent(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("only")])
        assert e.to_snapshot().snapshot_sequence == 1
        snap = e.step_event()
        assert snap.snapshot_sequence == 3
        assert snap.diagnostics.trace_total_entries == 1
        assert snap.recent_events[0].trace_sequence == 1

    def test_monotonic(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=10)
        N = 5; e.initialize(initial_events=[_evt(f"e{i}") for i in range(N)])
        for _ in range(N): e.step_event()
        seqs = [t.trace_sequence for t in e.to_snapshot().recent_events]
        assert seqs == list(range(1, N + 1))


class TestC01Minor:
    def test_buffer_string_capacity_rejected(self):
        from virtual_factory.discrete.trace import EventTraceBuffer, EventTraceBufferError
        with pytest.raises(EventTraceBufferError, match="capacity"):
            EventTraceBuffer(capacity="10")
