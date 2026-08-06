"""Tests for DiscreteSimulationEngine — M2-S01 lifecycle."""

import pytest

from virtual_factory.discrete.dispatcher import (
    EventDispatcherProtocol,
    HandlerOutcome,
    HandlerOutcomeError,
)
from virtual_factory.discrete.engine import (
    DiscreteSimulationEngine,
    DiscreteSimulationEngineError,
)
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.state import RunStatus


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _rc(**kw):
    defaults = {"run_id": "run-001", "model_id": "tipa_final_assembly_v1"}
    defaults.update(kw)
    return RunContext(**defaults)


def _evt(event_id, simulation_time_s=0.0, event_type="test", **kw):
    return ScheduledEvent(
        event_id=event_id,
        simulation_time_s=simulation_time_s,
        event_type=event_type,
        **kw,
    )


class StubDispatcher:
    """Returns success with no follow-ups for every event."""

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        return HandlerOutcome(
            event_id=event.event_id,
            success=True,
            follow_up_events=(),
            state_changes=(),
        )


class FailingDispatcher:
    """Always returns failure."""

    def __init__(self, error_code="test_failure", error_detail=None):
        self.error_code = error_code
        self.error_detail = error_detail

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        return HandlerOutcome(
            event_id=event.event_id,
            success=False,
            follow_up_events=(),
            state_changes=(),
            error_code=self.error_code,
            error_detail=self.error_detail,
        )


# ──────────────────────────────────────────────
# Construction
# ──────────────────────────────────────────────

class TestEngineConstruction:
    def test_created_status_and_zero_counters(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        assert engine.status == RunStatus.CREATED
        snap = engine.to_snapshot()
        assert snap.status == "created"
        assert snap.processed_events == 0
        assert snap.pending_events == 0
        assert snap.snapshot_sequence == 0

    def test_invalid_run_context_rejected(self):
        with pytest.raises(DiscreteSimulationEngineError, match="RunContext"):
            DiscreteSimulationEngine("not-a-context", StubDispatcher())

    def test_non_conforming_dispatcher_rejected(self):
        with pytest.raises(DiscreteSimulationEngineError, match="EventDispatcherProtocol"):
            DiscreteSimulationEngine(_rc(), "not-a-dispatcher")


# ──────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────

class TestEngineInitialize:
    def test_empty_initialize(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        snap = engine.initialize()
        assert engine.status == RunStatus.READY
        assert snap.status == "ready"
        assert snap.snapshot_sequence == 1

    def test_ordered_initial_events_scheduled(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        events = [
            _evt("e1", simulation_time_s=1.0),
            _evt("e2", simulation_time_s=0.5),
        ]
        snap = engine.initialize(initial_events=events)
        assert snap.pending_events == 2

    def test_pre_sequenced_event_rejected_atomically(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        bad = [_evt("e1", sequence=5)]
        with pytest.raises(DiscreteSimulationEngineError, match="sequence=None"):
            engine.initialize(initial_events=bad)
        assert engine.status == RunStatus.CREATED

    def test_duplicate_bootstrap_ids_rejected_atomically(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        events = [_evt("dup"), _evt("dup")]
        with pytest.raises(DiscreteSimulationEngineError, match="dup"):
            engine.initialize(initial_events=events)
        assert engine.status == RunStatus.CREATED

    def test_invalid_element_rejected_atomically(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="ScheduledEvent"):
            engine.initialize(initial_events=["not-an-event"])
        assert engine.status == RunStatus.CREATED

    def test_initialize_twice_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        with pytest.raises(DiscreteSimulationEngineError, match="CREATED"):
            engine.initialize()


# ──────────────────────────────────────────────
# Step
# ──────────────────────────────────────────────

class TestEngineStep:
    def test_empty_scheduler_completes(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()  # no events
        snap = engine.step_event()
        assert snap.status == "completed"
        assert snap.stop_reason == "scheduler_empty"

    def test_event_time_synchronized_from_scheduler(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1", simulation_time_s=5.0)])
        snap = engine.step_event()
        assert snap.simulation_time_s == 5.0

    def test_successful_outcome_commits_counters(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.processed_events == 1
        assert snap.pending_events == 0

    def test_final_event_advances_sequence_twice(self):
        """Event commit + completion each advance snapshot_sequence."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        # snapshot_sequence after init=1, after event=2, after completion=3
        assert snap.snapshot_sequence == 3
        assert snap.status == "completed"

    def test_follow_ups_scheduled_and_ordered(self):
        class FollowUpDispatcher:
            def dispatch(self, event):
                return HandlerOutcome(
                    event_id=event.event_id,
                    success=True,
                    follow_up_events=(
                        _evt("f1", simulation_time_s=10.0, priority=5),
                        _evt("f2", simulation_time_s=10.0, priority=1),
                    ),
                    state_changes=(),
                )

        engine = DiscreteSimulationEngine(_rc(), FollowUpDispatcher())
        engine.initialize(initial_events=[_evt("boot")])
        engine.step_event()  # dispatches boot, schedules f1, f2
        snap = engine.to_snapshot()
        assert snap.pending_events == 2

    def test_dispatcher_exception_fails(self):
        class ExplodingDispatcher:
            def dispatch(self, event):
                raise RuntimeError("boom")

        engine = DiscreteSimulationEngine(_rc(), ExplodingDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "dispatcher_exception"

    def test_unsuccessful_outcome_fails(self):
        engine = DiscreteSimulationEngine(_rc(), FailingDispatcher("bad"))
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "bad"
        assert snap.processed_events == 0  # not committed

    def test_outcome_event_id_mismatch_fails(self):
        class MismatchDispatcher:
            def dispatch(self, event):
                return HandlerOutcome(
                    event_id="wrong-id",
                    success=True,
                    follow_up_events=(),
                    state_changes=(),
                )

        engine = DiscreteSimulationEngine(_rc(), MismatchDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert "mismatch" in snap.failure_error

    def test_step_before_initialize_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="READY"):
            engine.step_event()

    def test_step_after_terminal_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        engine.step_event()  # completes
        with pytest.raises(DiscreteSimulationEngineError, match="READY"):
            engine.step_event()


# ──────────────────────────────────────────────
# Stop
# ──────────────────────────────────────────────

class TestEngineStop:
    def test_stop_from_created(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        snap = engine.stop("user terminated")
        assert snap.status == "stopped"
        assert snap.stop_reason == "user terminated"

    def test_stop_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        snap = engine.stop("done")
        assert snap.status == "stopped"

    def test_stop_reason_must_be_non_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="non-empty"):
            engine.stop("")

    def test_stop_after_terminal_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        engine.step_event()  # completes
        with pytest.raises(DiscreteSimulationEngineError, match="terminal"):
            engine.stop("try")


# ──────────────────────────────────────────────
# Snapshot
# ──────────────────────────────────────────────

class TestEngineSnapshot:
    def test_snapshot_identity_from_run_context(self):
        ctx = _rc(run_id="my-run", model_id="m1", model_version="2.0")
        engine = DiscreteSimulationEngine(ctx, StubDispatcher())
        snap = engine.to_snapshot()
        assert snap.run_id == "my-run"
        assert snap.model_id == "m1"
        assert snap.model_version == "2.0"

    def test_public_api_no_mutable_state(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        assert not hasattr(engine, "state")


# ──────────────────────────────────────────────
# Determinism
# ──────────────────────────────────────────────

class TestEngineDeterminism:
    def test_identical_inputs_produce_identical_snapshots(self):
        ctx = _rc(run_id="det-run")

        def build_and_run():
            engine = DiscreteSimulationEngine(ctx, StubDispatcher())
            engine.initialize(initial_events=[
                _evt("a", simulation_time_s=1.0),
                _evt("b", simulation_time_s=2.0),
            ])
            snaps = []
            while True:
                snap = engine.step_event()
                snaps.append(snap)
                if snap.status in ("completed", "failed", "stopped"):
                    break
            return tuple(
                (s.status, s.simulation_time_s, s.processed_events,
                 s.pending_events, s.snapshot_sequence)
                for s in snaps
            )

        result1 = build_and_run()
        result2 = build_and_run()
        assert result1 == result2

# --- M2-S01-C01: Failure-state + contract hardening tests ---

class TestFailureStateConsistency:
    """Failure transitions synchronize pending_events from scheduler."""

    def test_dispatcher_exception_syncs_pending(self):
        class ExplodingDispatcher:
            def dispatch(self, event):
                raise RuntimeError("boom")
        engine = DiscreteSimulationEngine(_rc(), ExplodingDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.processed_events == 0
        assert snap.pending_events == 0

    def test_unsuccessful_outcome_with_remaining_events(self):
        engine = DiscreteSimulationEngine(_rc(), FailingDispatcher("bad"))
        engine.initialize(initial_events=[_evt("e1"), _evt("e2")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.processed_events == 0
        assert snap.pending_events == 1

    def test_follow_up_scheduling_partial_failure(self):
        call_count = [0]
        class PartialFailDispatcher:
            def dispatch(self, event):
                call_count[0] += 1
                if call_count[0] == 1:
                    return HandlerOutcome(
                        event_id=event.event_id, success=True,
                        follow_up_events=(
                            _evt("ok", simulation_time_s=1.0),
                            _evt("ok", simulation_time_s=1.0),  # duplicate!
                        ),
                        state_changes=(),
                    )
                return HandlerOutcome(
                    event_id=event.event_id, success=True,
                    follow_up_events=(), state_changes=(),
                )
        engine = DiscreteSimulationEngine(_rc(), PartialFailDispatcher())
        engine.initialize(initial_events=[_evt("boot")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "schedule_error"
        assert snap.processed_events == 0
        assert snap.pending_events == 1

    def test_invalid_dispatcher_return_type_syncs(self):
        class BadReturnDispatcher:
            def dispatch(self, event):
                return "not-an-outcome"
        engine = DiscreteSimulationEngine(_rc(), BadReturnDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "invalid_outcome"
        assert snap.pending_events == 0


class TestAtomicInitializeState:
    """After failed initialize, engine stays CREATED with zero counters."""

    def test_sequence_rejected_atomically_preserves_state(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError):
            engine.initialize(initial_events=[_evt("e1", sequence=5)])
        assert engine.status == RunStatus.CREATED
        snap = engine.to_snapshot()
        assert snap.snapshot_sequence == 0
        assert snap.pending_events == 0
        assert snap.processed_events == 0

    def test_duplicate_ids_rejected_atomically_preserves_state(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError):
            engine.initialize(initial_events=[_evt("dup"), _evt("dup")])
        snap = engine.to_snapshot()
        assert snap.snapshot_sequence == 0
        assert snap.pending_events == 0


class TestFollowUpOrdering:
    """Same-time follow-ups execute by time -> priority -> scheduler sequence."""

    def test_recording_dispatcher_ordering(self):
        dispatched = []
        class RecordingDispatcher:
            def dispatch(self, event):
                dispatched.append(event.event_id)
                return HandlerOutcome(
                    event_id=event.event_id, success=True,
                    follow_up_events=(), state_changes=(),
                )
        engine = DiscreteSimulationEngine(_rc(), RecordingDispatcher())
        engine.initialize(initial_events=[
            _evt("a", simulation_time_s=1.0, priority=3),
            _evt("b", simulation_time_s=1.0, priority=1),
            _evt("c", simulation_time_s=0.0),
        ])
        # pop all until complete
        while True:
            snap = engine.step_event()
            if snap.status != "ready":
                break
        assert dispatched == ["c", "b", "a"]


class TestHandlerOutcomeValidation:
    """HandlerOutcome rejects invalid input."""

    def test_blank_event_id_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="event_id"):
            HandlerOutcome(event_id="", success=True, follow_up_events=(), state_changes=())

    def test_non_bool_success_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="success"):
            HandlerOutcome(event_id="e1", success="yes", follow_up_events=(), state_changes=())

    def test_list_not_tuple_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="follow_up_events"):
            HandlerOutcome(event_id="e1", success=True, follow_up_events=[], state_changes=())

    def test_blank_error_code_on_failure_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="error_code"):
            HandlerOutcome(event_id="e1", success=False, follow_up_events=(), state_changes=(), error_code="")

    def test_non_string_error_detail_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="error_detail"):
            HandlerOutcome(event_id="e1", success=False, follow_up_events=(), state_changes=(), error_code="fail", error_detail=42)

    def test_non_string_state_change_rejected(self):
        with pytest.raises(HandlerOutcomeError, match="state_changes"):
            HandlerOutcome(event_id="e1", success=True, follow_up_events=(), state_changes=(1, 2))


class TestStopReasonValidation:
    """stop() rejects non-string and whitespace-only reasons."""

    def test_non_string_reason_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="non-empty"):
            engine.stop(123)

    def test_whitespace_only_reason_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="non-empty"):
            engine.stop("   ")


# ──────────────────────────────────────────────
# M2-S04: Engine transitions — RUNNING / PAUSED
# ──────────────────────────────────────────────

class TestEngineTransitions:
    """READY → RUNNING, RUNNING → PAUSED, PAUSED → RUNNING."""

    def test_start_running_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        assert engine.status == RunStatus.READY
        snap = engine.start_running()
        assert engine.status == RunStatus.RUNNING
        assert snap.status == "running"

    def test_start_running_increments_snapshot_sequence(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        seq_before = engine.to_snapshot().snapshot_sequence
        engine.start_running()
        seq_after = engine.to_snapshot().snapshot_sequence
        assert seq_after == seq_before + 1

    def test_start_running_no_trace(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        engine.start_running()
        snap = engine.to_snapshot()
        # No trace entry created for transition
        assert len(snap.recent_events) == 0

    def test_start_running_preserves_time_and_counters(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1", simulation_time_s=5.0)])
        snap_before = engine.to_snapshot()
        engine.start_running()
        snap_after = engine.to_snapshot()
        assert snap_after.simulation_time_s == snap_before.simulation_time_s
        assert snap_after.processed_events == snap_before.processed_events
        assert snap_after.pending_events == snap_before.pending_events

    def test_start_running_not_from_ready_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="READY"):
            engine.start_running()

    def test_pause_from_running(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        snap = engine.pause()
        assert engine.status == RunStatus.PAUSED
        assert snap.status == "paused"

    def test_pause_increments_snapshot_sequence(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        seq_before = engine.to_snapshot().snapshot_sequence
        engine.pause()
        seq_after = engine.to_snapshot().snapshot_sequence
        assert seq_after == seq_before + 1

    def test_pause_no_trace(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        snap = engine.to_snapshot()
        assert len(snap.recent_events) == 0

    def test_pause_not_from_running_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        with pytest.raises(DiscreteSimulationEngineError, match="RUNNING"):
            engine.pause()

    def test_resume_from_paused(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        snap = engine.resume()
        assert engine.status == RunStatus.RUNNING
        assert snap.status == "running"

    def test_resume_increments_snapshot_sequence(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        seq_before = engine.to_snapshot().snapshot_sequence
        engine.resume()
        seq_after = engine.to_snapshot().snapshot_sequence
        assert seq_after == seq_before + 1

    def test_resume_no_trace(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        engine.resume()
        snap = engine.to_snapshot()
        assert len(snap.recent_events) == 0

    def test_resume_not_from_paused_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        with pytest.raises(DiscreteSimulationEngineError, match="PAUSED"):
            engine.resume()

    def test_invalid_transition_atomic(self):
        """Invalid transition must not mutate state."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        snap_before = engine.to_snapshot()
        with pytest.raises(DiscreteSimulationEngineError):
            engine.pause()  # not RUNNING
        snap_after = engine.to_snapshot()
        assert snap_after.status == snap_before.status
        assert snap_after.snapshot_sequence == snap_before.snapshot_sequence


# ──────────────────────────────────────────────
# M2-S04: Step from active states
# ──────────────────────────────────────────────

class TestStepFromActiveStates:
    def test_step_from_running(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1"), _evt("e2")])
        engine.start_running()
        snap = engine.step_event()
        assert snap.processed_events == 1
        # Status preserved after non-terminal step
        assert snap.status == "running"

    def test_step_from_paused(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1"), _evt("e2")])
        engine.start_running()
        engine.pause()
        snap = engine.step_event()
        assert snap.processed_events == 1
        # Status preserved after non-terminal step
        assert snap.status == "paused"

    def test_step_from_ready_preserves_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1"), _evt("e2")])
        snap = engine.step_event()
        assert snap.processed_events == 1
        assert snap.status == "ready"

    def test_step_from_running_completes_when_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        snap = engine.step_event()
        assert snap.status == "completed"

    def test_step_from_paused_completes_when_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        snap = engine.step_event()
        assert snap.status == "completed"

    def test_step_from_running_failure_to_failed(self):
        engine = DiscreteSimulationEngine(_rc(), FailingDispatcher("bad"))
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        snap = engine.step_event()
        assert snap.status == "failed"

    def test_step_not_from_active_state_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteSimulationEngineError, match="READY"):
            engine.step_event()


# ──────────────────────────────────────────────
# M2-S04: Stop from RUNNING / PAUSED
# ──────────────────────────────────────────────

class TestStopFromActiveStates:
    def test_stop_from_running(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        snap = engine.stop("user stopped")
        assert snap.status == "stopped"
        assert snap.stop_reason == "user stopped"

    def test_stop_from_paused(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize(initial_events=[_evt("e1")])
        engine.start_running()
        engine.pause()
        snap = engine.stop("user stopped")
        assert snap.status == "stopped"

    def test_stop_from_terminal_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        engine.initialize()
        engine.step_event()  # completes
        with pytest.raises(DiscreteSimulationEngineError, match="terminal"):
            engine.stop("try")

    def test_stop_from_failed_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), FailingDispatcher("bad"))
        engine.initialize(initial_events=[_evt("e1")])
        engine.step_event()  # fails
        with pytest.raises(DiscreteSimulationEngineError, match="terminal"):
            engine.stop("try")
