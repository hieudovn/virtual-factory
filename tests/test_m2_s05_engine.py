"""M2-S05 tests — determinism, max-events, no-progress, replay metadata."""

import pytest
from virtual_factory.discrete.engine import DiscreteSimulationEngine, DiscreteSimulationEngineError
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.snapshot import RuntimeSnapshot
from virtual_factory.discrete.state import RunStatus


def _rc(**kw):
    d = {"run_id": "run-001", "model_id": "m1"}
    d.update(kw)
    return RunContext(**d)


def _evt(event_id, simulation_time_s=0.0, event_type="test", **kw):
    return ScheduledEvent(event_id=event_id, simulation_time_s=simulation_time_s, event_type=event_type, **kw)


class StubDispatcher:
    def __init__(self, follow_ups=()):
        self.follow_ups = follow_ups
    def dispatch(self, event):
        return HandlerOutcome(event_id=event.event_id, success=True, follow_up_events=self.follow_ups, state_changes=())


class TestDeterminism:
    """M2-S05-A: Two equivalent runs with same seed produce same results."""

    def test_same_seed_same_result(self):
        e1 = DiscreteSimulationEngine(_rc(random_seed=42), StubDispatcher(), trace_capacity=32)
        e1.initialize([_evt("e1", 1.0)])
        e1.step_event()
        s1 = e1.to_snapshot()

        e2 = DiscreteSimulationEngine(_rc(random_seed=42), StubDispatcher(), trace_capacity=32)
        e2.initialize([_evt("e1", 1.0)])
        e2.step_event()
        s2 = e2.to_snapshot()

        assert s1.processed_events == s2.processed_events
        assert s1.simulation_time_s == s2.simulation_time_s
        assert s1.status == s2.status

    def test_different_seed_different_random(self):
        e1 = DiscreteSimulationEngine(_rc(random_seed=1), StubDispatcher())
        e2 = DiscreteSimulationEngine(_rc(random_seed=99999), StubDispatcher())
        # Different seeds produce different RNG states
        assert e1.run_random.randint(0, 10**9) != e2.run_random.randint(0, 10**9)

    def test_run_random_is_deterministic(self):
        e = DiscreteSimulationEngine(_rc(random_seed=123), StubDispatcher())
        r1 = [e.run_random.random() for _ in range(5)]
        # Reset with same seed
        import random
        r2 = random.Random(123)
        assert r1 == [r2.random() for _ in range(5)]

    def test_seed_preserved_in_snapshot(self):
        e = DiscreteSimulationEngine(_rc(random_seed=77), StubDispatcher())
        snap = e.to_snapshot()
        assert snap.diagnostics.random_seed == 77


class TestMaxEvents:
    """M2-S05-B: max_processed_events safety limit."""

    def test_max_events_stops_run(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=3)
        e.initialize([_evt("e1", 1.0), _evt("e2", 2.0), _evt("e3", 3.0), _evt("e4", 4.0)])
        for _ in range(3):
            e.step_event()
        # 4th step should trigger guard
        snap = e.step_event()
        assert snap.status == "stopped"
        assert "max_processed_events" in snap.stop_reason

    def test_under_limit_continues_normally(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=10)
        e.initialize([_evt("e1", 1.0)])
        snap = e.step_event()
        assert snap.status not in ("stopped", "failed")
        assert snap.processed_events == 1

    def test_no_limit_continues(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=None)
        e.initialize([_evt("e1", 1.0)])
        snap = e.step_event()
        assert snap.processed_events == 1

    def test_invalid_max_events_rejected(self):
        with pytest.raises(DiscreteSimulationEngineError):
            DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=0)
        with pytest.raises(DiscreteSimulationEngineError):
            DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=-5)
        with pytest.raises(DiscreteSimulationEngineError):
            DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=True)

    def test_max_events_in_snapshot(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=500)
        assert e.to_snapshot().diagnostics.max_processed_events_limit == 500


class TestNoProgress:
    """M2-S05-C: No-progress detection for same-time event churn."""

    def test_same_time_churn_stops(self):
        # Multiple events at same simulation time — churn detected
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=3)
        events = [_evt(f"e{i}", 0.0) for i in range(10)]
        e.initialize(events)
        snap = None
        for _ in range(10):
            if e.status.value in ("stopped", "completed", "failed"):
                break
            snap = e.step_event()
        assert snap is not None
        assert snap.status == "stopped"
        assert "no_progress" in snap.stop_reason

    def test_legitimate_same_time_batch_ok(self):
        # Small same-time batch under limit
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=10)
        e.initialize([_evt("e1", 0.0), _evt("e2", 0.0)])
        e.step_event()
        snap = e.step_event()
        assert snap.status not in ("stopped", "failed")

    def test_time_advancement_resets_counter(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=3)
        e.initialize([_evt("e1", 1.0), _evt("e2", 1.0), _evt("e3", 2.0), _evt("e4", 2.0)])
        e.step_event()  # e1 at 1.0
        e.step_event()  # e2 at 1.0 — same_time_count=1
        e.step_event()  # e3 at 2.0 — resets counter
        snap = e.step_event()  # e4 at 2.0 — counter restarts
        assert snap.status not in ("stopped", "failed")

    def test_invalid_max_same_time_rejected(self):
        with pytest.raises(DiscreteSimulationEngineError):
            DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=0)
        with pytest.raises(DiscreteSimulationEngineError):
            DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=-1)

    def test_same_time_limit_in_snapshot(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_same_time_events=50)
        assert e.to_snapshot().diagnostics.same_time_event_limit == 50


class TestReplayMetadata:
    """M2-S05-D: Replay metadata in snapshot diagnostics."""

    def test_snapshot_contains_replay_metadata(self):
        e = DiscreteSimulationEngine(
            _rc(random_seed=42, run_id="replay-001"),
            StubDispatcher(),
            max_processed_events=1000,
            max_same_time_events=50,
        )
        e.initialize([_evt("e1", 1.0)])
        snap = e.to_snapshot()
        assert snap.run_id == "replay-001"
        assert snap.diagnostics.random_seed == 42
        assert snap.diagnostics.max_processed_events_limit == 1000
        assert snap.diagnostics.same_time_event_limit == 50
        assert snap.simulation_time_s == 0.0  # Not yet stepped

    def test_after_run_metadata_reflects_state(self):
        e = DiscreteSimulationEngine(
            _rc(random_seed=7),
            StubDispatcher(),
            max_processed_events=5,
        )
        e.initialize([_evt("e1", 1.0), _evt("e2", 2.0)])
        e.step_event()
        snap = e.step_event()
        assert snap.processed_events == 2
        assert snap.diagnostics.random_seed == 7
        assert snap.status in ("completed", "running")

    def test_guarded_stop_preserves_trace(self):
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=2, trace_capacity=10)
        e.initialize([_evt("e1", 1.0), _evt("e2", 2.0), _evt("e3", 3.0)])
        e.step_event()
        e.step_event()
        snap = e.step_event()
        assert snap.status == "stopped"
        assert len(snap.recent_events) >= 2  # Trace preserved

    def test_normal_behavior_preserved(self):
        """Existing controller/trace/snapshot behavior unchanged."""
        e = DiscreteSimulationEngine(_rc(), StubDispatcher(), max_processed_events=100)
        e.initialize([_evt("e1", 1.0)])
        snap = e.step_event()
        assert snap.status in ("completed", "running", "ready")
        assert snap.processed_events == 1
        assert snap.snapshot_sequence >= 1
