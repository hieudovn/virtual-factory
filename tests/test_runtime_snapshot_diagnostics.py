"""Tests for RuntimeSnapshot v1.1 + engine trace integration — M2-S03."""

import pytest

from virtual_factory.discrete.snapshot import RuntimeSnapshot, RuntimeSnapshotError
from virtual_factory.discrete.trace import EventTraceEntry, RuntimeDiagnostics
from virtual_factory.discrete.engine import DiscreteSimulationEngine
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.handler_registry import HandlerRegistry
from virtual_factory.discrete.run_context import RunContext


def _rc(**kw):
    d = {"run_id": "r1", "model_id": "m1"}
    d.update(kw)
    return RunContext(**d)

def _evt(eid, simulation_time_s=0.0, event_type="test", **kw):
    return ScheduledEvent(event_id=eid, simulation_time_s=simulation_time_s, event_type=event_type, **kw)

def _ok(event):
    return HandlerOutcome(event_id=event.event_id, success=True, follow_up_events=(), state_changes=("ok",))

def _snap(**kw):
    d = dict(run_id="r1", model_id="m1", model_version=None, scenario_id=None, scenario_version=None,
             status="created", simulation_time_s=0.0, stop_reason=None, failure_error=None,
             processed_events=0, pending_events=0, last_event_id=None, snapshot_sequence=0)
    d.update(kw)
    return RuntimeSnapshot(**d)

def _tr(**kw):
    d = dict(trace_sequence=1, event_id="e1", event_type="t", target_id="", simulation_time_s=0.0,
             priority=0, scheduler_sequence=1, correlation_id=None, causation_id=None,
             result="committed", error_code=None, error_detail=None, state_changes=(),
             requested_follow_up_events=0, scheduled_follow_up_events=0,
             processed_events_after=1, pending_events_after=0)
    d.update(kw)
    return EventTraceEntry(**d)


class TestRuntimeSnapshotV11:
    def test_schema_1_2_0(self): assert _snap().schema_version == "1.2.0"
    def test_old_keyword_ok(self):
        s = RuntimeSnapshot(run_id="r1", model_id="m1", status="created", simulation_time_s=0.0,
                            processed_events=0, pending_events=0, snapshot_sequence=0,
                            stop_reason=None, failure_error=None, last_event_id=None,
                            model_version=None, scenario_id=None, scenario_version=None)
        assert s.status == "created"
    def test_old_positional_ok(self):
        s = RuntimeSnapshot("r1", "m1", None, None, None, "created", 0.0, None, None, 0, 0, None, 0)
        assert s.schema_version == "1.2.0"
    def test_new_fields_defaults(self):
        s = _snap()
        assert s.recent_events == ()
        assert isinstance(s.diagnostics, RuntimeDiagnostics)
    def test_recent_events_content(self):
        s = _snap(recent_events=(_tr(),))
        assert len(s.recent_events) == 1
    def test_invalid_status(self):
        with pytest.raises(RuntimeSnapshotError, match="status"): _snap(status="bad")
    def test_negative_time(self):
        with pytest.raises(RuntimeSnapshotError, match="simulation_time_s"): _snap(simulation_time_s=-1.0)
    def test_negative_counter(self):
        with pytest.raises(RuntimeSnapshotError, match="processed_events"): _snap(processed_events=-1)
    def test_bool_counter(self):
        with pytest.raises(RuntimeSnapshotError, match="processed_events"): _snap(processed_events=True)
    def test_recent_must_be_tuple(self):
        with pytest.raises(RuntimeSnapshotError, match="recent_events"): _snap(recent_events=[])
    def test_invalid_recent_element(self):
        with pytest.raises(RuntimeSnapshotError, match="recent_events"): _snap(recent_events=("x",))


class TestEngineTraceCommitted:
    def test_committed_trace(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.result == "committed" and t.event_id == "e1"
    def test_trace_metadata(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("e1", simulation_time_s=2.0, event_type="mt", target_id="T1", priority=3, correlation_id="c1", causation_id="c0")])
        e.step_event(); t = e.to_snapshot().recent_events[0]
        assert t.event_type == "mt" and t.target_id == "T1" and t.correlation_id == "c1"


class TestEngineTraceFailures:
    def test_unknown_handler(self):
        e = DiscreteSimulationEngine(_rc(), HandlerRegistry(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.result == "failed" and t.error_code == "no_handler"
    def test_handler_exception(self):
        def broken(e):
            raise RuntimeError("crash")
        r = HandlerRegistry(); r.register("test", broken)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.result == "failed" and t.error_code == "handler_error"
    def test_dispatcher_exception(self):
        class X:
            def dispatch(self, e): raise RuntimeError("boom")
        e = DiscreteSimulationEngine(_rc(), X(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.result == "failed" and t.error_code == "dispatcher_exception"
    def test_invalid_outcome(self):
        class X:
            def dispatch(self, e): return "bad"
        e = DiscreteSimulationEngine(_rc(), X(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.error_code == "invalid_outcome"
    def test_id_mismatch(self):
        class X:
            def dispatch(self, e): return HandlerOutcome(event_id="wrong", success=True, follow_up_events=(), state_changes=())
        e = DiscreteSimulationEngine(_rc(), X(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.error_code == "outcome_event_id_mismatch"
    def test_unsuccessful(self):
        class X:
            def dispatch(self, e): return HandlerOutcome(event_id=e.event_id, success=False, follow_up_events=(), state_changes=(), error_code="bad")
        e = DiscreteSimulationEngine(_rc(), X(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        t = e.to_snapshot().recent_events[0]
        assert t.error_code == "bad"


class TestEngineScheduleFailure:
    def test_partial(self):
        r = HandlerRegistry()
        def h(e): return HandlerOutcome(event_id=e.event_id, success=True, follow_up_events=(_evt("ok"), _evt("ok")), state_changes=("m",))
        r.register("boot", h)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=5)
        e.initialize(initial_events=[_evt("boot", event_type="boot")])
        s = e.step_event()
        assert s.status == "failed"
        t = s.recent_events[0]
        assert t.error_code == "schedule_error" and t.requested_follow_up_events == 2 and t.scheduled_follow_up_events == 1 and t.processed_events_after == 0


class TestEngineNoTrace:
    def test_no_trace_init(self):
        e = DiscreteSimulationEngine(_rc(), HandlerRegistry(), trace_capacity=5)
        e.initialize()
        assert e.to_snapshot().recent_events == ()
    def test_no_trace_stop(self):
        e = DiscreteSimulationEngine(_rc(), HandlerRegistry(), trace_capacity=5)
        e.stop("d")
        assert e.to_snapshot().recent_events == ()
    def test_no_trace_empty(self):
        e = DiscreteSimulationEngine(_rc(), HandlerRegistry(), trace_capacity=5)
        e.initialize(); e.step_event()
        assert e.to_snapshot().recent_events == ()


class TestEngineTraceEviction:
    def test_eviction(self):
        r = HandlerRegistry(); r.register("test", _ok)
        e = DiscreteSimulationEngine(_rc(), r, trace_capacity=3)
        e.initialize(initial_events=[_evt(f"e{i}") for i in range(10)])
        for _ in range(10): e.step_event()
        d = e.to_snapshot().diagnostics
        assert d.trace_capacity == 3 and d.trace_size == 3 and d.trace_total_entries == 10 and d.trace_dropped_entries == 7


class TestEngineTraceDeterminism:
    def test_deterministic(self):
        def run():
            r = HandlerRegistry(); r.register("test", _ok)
            e = DiscreteSimulationEngine(RunContext(run_id="det", model_id="m1"), r, trace_capacity=5)
            e.initialize(initial_events=[_evt("a"), _evt("b")])
            out = []
            while True:
                s = e.step_event(); out.append(s)
                if s.status in ("completed", "failed", "stopped"): break
            return tuple((s.status, s.snapshot_sequence, tuple((x.trace_sequence, x.event_id, x.result) for x in s.recent_events), (s.diagnostics.trace_capacity, s.diagnostics.trace_size, s.diagnostics.trace_total_entries, s.diagnostics.trace_dropped_entries)) for s in out)
        assert run() == run()


class TestSnapshotDiagnostics:
    def test_failure_detail(self):
        class X:
            def dispatch(self, e): return HandlerOutcome(event_id=e.event_id, success=False, follow_up_events=(), state_changes=(), error_code="bad", error_detail="wrong")
        e = DiscreteSimulationEngine(_rc(), X(), trace_capacity=5)
        e.initialize(initial_events=[_evt("e1")]); e.step_event()
        assert e.to_snapshot().diagnostics.failure_detail == "wrong"
