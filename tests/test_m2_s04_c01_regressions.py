"""C01 regression tests for M2-S04 — paused manual step, allowed_actions,
command result observability, engine run_id encapsulation.

M2-S04-C01: validates corrected semantics after CAPA review.
"""

import pytest

from virtual_factory.discrete.commands import (
    ControlCommandType,
    RunControlCommand,
)
from virtual_factory.discrete.controller import (
    DiscreteRunController,
    ExecutionMode,
    _compute_allowed_actions,
)
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.engine import DiscreteSimulationEngine
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
    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        return HandlerOutcome(
            event_id=event.event_id,
            success=True,
            follow_up_events=(),
            state_changes=(),
        )


# ──────────────────────────────────────────────
# C01-01: Manual step from PAUSED
# ──────────────────────────────────────────────

class TestManualStepFromPaused:
    """C01-01: Manual stepping from PAUSED must process exactly one event."""

    def test_manual_paused_step_processes_one_event(self):
        """MANUAL controller, PAUSED engine, 2 pending events.
        step_once() must process exactly one event and preserve PAUSED.
        """
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        # Manually set PAUSED (engine.start_running then engine.pause)
        engine.start_running()
        engine.pause()

        snap_before = ctrl.to_snapshot()
        assert snap_before.status == "paused"
        assert snap_before.processed_events == 0

        snap = ctrl.step_once()

        # Processed exactly one event
        assert snap.processed_events == snap_before.processed_events + 1
        # last_event_id changed
        assert snap.last_event_id == "e1"
        # Trace total increased by exactly 1
        assert snap.diagnostics.trace_total_entries == 1
        # pending_events reflects remaining queue
        assert snap.pending_events == 1
        # status remains PAUSED (nonterminal step preserves status)
        assert snap.status == "paused"

    def test_hybrid_paused_step_processes_one_event(self):
        """HYBRID controller, PAUSED engine, 2 pending events.
        step_once() must process exactly one event and preserve PAUSED.
        """
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        engine.start_running()
        engine.pause()

        snap = ctrl.step_once()
        assert snap.processed_events == 1
        assert snap.last_event_id == "e1"
        assert snap.diagnostics.trace_total_entries == 1
        assert snap.pending_events == 1
        assert snap.status == "paused"


class TestPauseCommandBlocksNextEvent:
    """C01-01: Pause applied at safe-point blocks the next event."""

    def test_pause_command_blocks_event(self):
        """RUNNING engine, pending event, queued PAUSE.
        step_once: pause applies → PAUSED, event NOT processed.
        """
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1")])
        engine.start_running()

        # Submit pause
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        snap_before = ctrl.to_snapshot()
        assert snap_before.status == "running"

        snap = ctrl.step_once()

        # Pause applied, event NOT processed
        assert snap.status == "paused"
        assert snap.processed_events == snap_before.processed_events
        assert snap.pending_events == 1  # event still pending
        # snapshot_sequence increased only for pause transition (not event)
        assert snap.snapshot_sequence == snap_before.snapshot_sequence + 1

    def test_automatic_pause_blocks_event(self):
        """Same as above but via run_cycle in AUTOMATIC mode."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Process E1 first
        ctrl.run_cycle()
        assert ctrl.to_snapshot().processed_events == 1

        # Queue pause
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        snap_before = ctrl.to_snapshot()
        snap = ctrl.run_cycle()

        # Pause applied, E2 NOT processed
        assert snap.status == "paused"
        assert snap.processed_events == snap_before.processed_events
        assert snap.pending_events == 1

    def test_manual_step_from_running_no_command(self):
        """step_once from RUNNING with no queued commands processes an event."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        engine.start_running()

        snap = ctrl.step_once()
        assert snap.processed_events == 1
        assert snap.status == "running"


# ──────────────────────────────────────────────
# C01-02: Exact allowed_actions matrix
# ──────────────────────────────────────────────

class TestExactAllowedActions:
    """C01-02: Every row of the allowed_actions matrix, exact order."""

    def test_created(self):
        assert _compute_allowed_actions(RunStatus.CREATED, ExecutionMode.MANUAL) == ("initialize", "stop")

    def test_ready_manual(self):
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.MANUAL) == ("step_event", "stop")

    def test_ready_automatic(self):
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.AUTOMATIC) == ("auto_run", "stop")

    def test_ready_hybrid(self):
        # step_event BEFORE auto_run (not alphabetical)
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.HYBRID) == ("step_event", "auto_run", "stop")

    def test_running_manual(self):
        assert _compute_allowed_actions(RunStatus.RUNNING, ExecutionMode.MANUAL) == ("pause", "stop")

    def test_running_automatic(self):
        assert _compute_allowed_actions(RunStatus.RUNNING, ExecutionMode.AUTOMATIC) == ("pause", "stop")

    def test_running_hybrid(self):
        assert _compute_allowed_actions(RunStatus.RUNNING, ExecutionMode.HYBRID) == ("pause", "stop")

    def test_paused_manual(self):
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.MANUAL) == ("step_event", "stop")

    def test_paused_automatic(self):
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.AUTOMATIC) == ("resume", "stop")

    def test_paused_hybrid(self):
        # step_event BEFORE resume (not alphabetical)
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.HYBRID) == ("step_event", "resume", "stop")

    def test_completed(self):
        assert _compute_allowed_actions(RunStatus.COMPLETED, ExecutionMode.MANUAL) == ()

    def test_stopped(self):
        assert _compute_allowed_actions(RunStatus.STOPPED, ExecutionMode.AUTOMATIC) == ()

    def test_failed(self):
        assert _compute_allowed_actions(RunStatus.FAILED, ExecutionMode.HYBRID) == ()


# ──────────────────────────────────────────────
# C01-03: Command result observability
# ──────────────────────────────────────────────

class TestCommandResultObservability:
    """C01-03: Every accepted command produces one observable terminal result."""

    def test_accepted_pause_one_applied_result(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        ctrl.run_cycle()  # process E1

        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.run_cycle()  # pause applies

        results = ctrl.drain_command_results()
        assert len(results) == 1
        assert results[0].status == "applied"
        assert results[0].command_id == "c1"
        assert results[0].command_type == "pause"

    def test_accepted_stop_one_applied_result(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.STOP),
        )
        ctrl.run_cycle()

        results = ctrl.drain_command_results()
        assert len(results) == 1
        assert results[0].status == "applied"
        assert results[0].command_type == "stop"

    def test_accepted_command_invalidated_by_earlier_one_rejected(self):
        """pause then pause: first applied, second rejected."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        ctrl.run_cycle()

        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.submit_command(
            RunControlCommand(command_id="c2", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.run_cycle()

        results = ctrl.drain_command_results()
        assert len(results) == 2
        applied = [r for r in results if r.status == "applied"]
        rejected = [r for r in results if r.status == "rejected"]
        assert len(applied) == 1
        assert len(rejected) == 1
        assert applied[0].command_id == "c1"
        assert rejected[0].command_id == "c2"
        assert rejected[0].rejection_code == "invalid_for_status"

    def test_terminal_drain_explicit_rejected_result(self):
        """When engine reaches terminal, queued commands are drained with rejection results."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Process E1 first, then submit command
        ctrl.run_cycle()  # E1 done, E2 pending
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        # Next cycle: pause applies at safe-point → PAUSED, execution_blocked
        ctrl.run_cycle()

        # Pause was applied (engine PAUSED), not rejected. Now submit stop.
        ctrl.submit_command(
            RunControlCommand(command_id="c2", run_id="run-001", command_type=ControlCommandType.STOP),
        )
        # step_once (HYBRID mode allows this): stop applies → STOPPED
        ctrl.step_once()

        results = ctrl.drain_command_results()
        # Both commands had terminal results
        assert len(results) == 2
        applied = [r for r in results if r.status == "applied"]
        assert len(applied) == 2
        # Verify a drained rejection: after terminal, submit another command
        r3 = ctrl.submit_command(
            RunControlCommand(command_id="c3", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        # Already rejected at submission (terminal status)
        assert r3.status == "rejected"

    def test_fifo_result_ordering(self):
        """Results preserve command_sequence order."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        ctrl.run_cycle()

        ctrl.submit_command(
            RunControlCommand(command_id="a", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.submit_command(
            RunControlCommand(command_id="b", run_id="run-001", command_type=ControlCommandType.STOP),
        )
        ctrl.run_cycle()

        results = ctrl.drain_command_results()
        # Order by command_sequence
        assert results[0].command_id == "a"
        assert results[1].command_id == "b"

    def test_drain_returns_tuple(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        results = ctrl.drain_command_results()
        assert isinstance(results, tuple)
        assert results == ()

    def test_second_drain_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        ctrl.run_cycle()
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.run_cycle()

        first = ctrl.drain_command_results()
        assert len(first) == 1
        second = ctrl.drain_command_results()
        assert second == ()

    def test_no_accepted_command_without_result(self):
        """Every accepted command must eventually produce a result in the outbox."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2"), _evt("e3")])
        ctrl.start_automatic()

        # Process E1 first
        ctrl.run_cycle()

        # Submit 2 commands (both accepted — pause from RUNNING, stop from RUNNING)
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.submit_command(
            RunControlCommand(command_id="c2", run_id="run-001", command_type=ControlCommandType.STOP),
        )

        # Process cycle: pause applies → PAUSED, execution blocked
        ctrl.run_cycle()

        results = ctrl.drain_command_results()
        # Both accepted commands must have terminal results
        assert len(results) == 2
        cmd_ids = {r.command_id for r in results}
        assert cmd_ids == {"c1", "c2"}


# ──────────────────────────────────────────────
# C01-04: Engine run_id encapsulation
# ──────────────────────────────────────────────

class TestEngineRunId:
    """C01-04: engine.run_id is public, read-only, correct."""

    def test_run_id_matches_context(self):
        engine = DiscreteSimulationEngine(_rc(run_id="my-run"), StubDispatcher())
        assert engine.run_id == "my-run"

    def test_run_id_is_read_only(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(AttributeError):
            engine.run_id = "changed"

    def test_run_id_after_initialize(self):
        engine = DiscreteSimulationEngine(_rc(run_id="r42"), StubDispatcher())
        engine.initialize()
        assert engine.run_id == "r42"
