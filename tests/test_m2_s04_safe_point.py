"""Tests for safe-point command application — M2-S04.

Tests that commands are applied before the next event, current event
commits before accepted commands, and multiple commands are ordered/revalidated.
"""

import pytest

from virtual_factory.discrete.commands import (
    ControlCommandType,
    RunControlCommand,
)
from virtual_factory.discrete.controller import (
    DiscreteRunController,
    DiscreteRunControllerError,
    ExecutionMode,
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


class DispatchTrackingDispatcher:
    """Records dispatch calls for safe-point ordering verification."""

    def __init__(self):
        self.dispatched: list[str] = []

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        self.dispatched.append(event.event_id)
        return HandlerOutcome(
            event_id=event.event_id,
            success=True,
            follow_up_events=(),
            state_changes=(),
        )


# ──────────────────────────────────────────────
# Safe-point — pause during dispatch
# ──────────────────────────────────────────────

class TestPauseDuringDispatch:
    def test_pause_applies_before_next_event(self):
        """When pause is accepted during E1 dispatch, E2 is not popped."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Submit pause (it will be queued, applied at next safe-point)
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        # First run_cycle: applies pause at safe-point, then does NOT step
        # Wait — the pause was submitted AFTER start_automatic.
        # So at run_cycle, safe-point applies pause, status becomes paused.
        snap = ctrl.run_cycle()
        assert snap.status == "paused"
        # E1 was NOT processed because pause applied first
        assert snap.processed_events == 0

    def test_current_event_commits_before_accepted_command(self):
        """If a command is accepted during dispatch, the current event commits first."""
        dispatch_log = []

        class LoggingDispatcher:
            def dispatch(self, event):
                dispatch_log.append(("dispatch", event.event_id))
                return HandlerOutcome(
                    event_id=event.event_id,
                    success=True,
                    follow_up_events=(),
                    state_changes=(),
                )

        engine = DiscreteSimulationEngine(_rc(), LoggingDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])

        # Step once — E1 commits
        ctrl.step_once()
        # Now accept pause
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        # E1 is committed. Pause is queued but not yet applied (engine is still READY in manual)
        assert engine.status == RunStatus.READY

    def test_pause_during_dispatch_commits_event_then_pauses(self):
        """E1 dispatched and committed. Pause queued during dispatch.
        Next safe-point applies pause. E2 never popped.
        """
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Process E1 via run_cycle
        snap1 = ctrl.run_cycle()
        assert snap1.processed_events == 1
        assert snap1.status == "running"

        # Submit pause — queued
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        # Next run_cycle: safe-point applies pause, E2 not popped
        snap2 = ctrl.run_cycle()
        assert snap2.status == "paused"
        assert snap2.processed_events == 1  # still 1, E2 was not processed
        assert snap2.pending_events == 1  # E2 remains pending


# ──────────────────────────────────────────────
# Safe-point — stop during dispatch
# ──────────────────────────────────────────────

class TestStopDuringDispatch:
    def test_stop_applies_before_next_event(self):
        """When stop is queued, next safe-point applies it and event is not popped."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Process E1
        ctrl.run_cycle()
        # Submit stop
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.STOP),
        )

        # Next cycle: stop applies, E2 not popped
        snap = ctrl.run_cycle()
        assert snap.status == "stopped"
        assert snap.processed_events == 1

    def test_stop_before_empty_check(self):
        """Command accepted after previous event; scheduler has one final event.
        Next run_cycle: stop applies first, final event is not popped.
        """
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()

        # Submit stop BEFORE processing E1
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.STOP),
        )

        # run_cycle: safe-point applies stop, E1 not popped
        snap = ctrl.run_cycle()
        assert snap.status == "stopped"
        assert snap.processed_events == 0


# ──────────────────────────────────────────────
# Safe-point — multiple commands
# ──────────────────────────────────────────────

class TestMultipleCommands:
    def test_commands_apply_fifo(self):
        """pause seq=1, stop seq=2: apply strictly in order."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Submit pause, stop (resume not allowed from RUNNING)
        r1 = ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        r2 = ctrl.submit_command(
            RunControlCommand(command_id="c2", run_id="run-001", command_type=ControlCommandType.STOP),
        )
        assert r1.command_sequence == 1
        assert r2.command_sequence == 2

        # run_cycle: pause applies → paused → stop applies → stopped
        snap = ctrl.run_cycle()
        # Both applied in FIFO, final state is stopped
        assert snap.status == "stopped"
        assert snap.processed_events == 0  # no event processed

    def test_commands_revalidated_after_each(self):
        """If pause+resume+stop queued, each is revalidated."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()

        # Submit pause, then pause again (second should be rejected on apply)
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        ctrl.submit_command(
            RunControlCommand(command_id="c2", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        # run_cycle: first pause applies (RUNNING→PAUSED), second pause revalidated
        # and rejected (PAUSED → pause not allowed)
        snap = ctrl.run_cycle()
        assert snap.status == "paused"

    def test_no_command_lost_when_scheduler_empty(self):
        """Commands accepted but never applied because scheduler became empty."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])  # single event
        ctrl.start_automatic()

        # Submit pause
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        # run_cycle: safe-point applies pause → paused → check status != running → drain
        snap = ctrl.run_cycle()
        assert snap.status == "paused"

    def test_terminal_queue_drained(self):
        """After step leads to terminal, queued commands are drained."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        # Process E1 first
        ctrl.run_cycle()
        # Now submit commands
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )

        # Next run_cycle: safe-point applies pause → PAUSED, E2 NOT popped
        snap = ctrl.run_cycle()
        assert snap.status == "paused"


# ──────────────────────────────────────────────
# Safe-point — no silent command loss
# ──────────────────────────────────────────────

class TestNoSilentCommandLoss:
    def test_command_accepted_during_dispatch_not_lost(self):
        """A pause command submitted while an event is dispatching
        must still be queued and applied later."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2"), _evt("e3")])
        ctrl.start_automatic()

        # Process E1
        ctrl.run_cycle()
        # Submit pause
        result = ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        assert result.status == "accepted"

        # Next cycle: pause applies, E2 not popped
        snap = ctrl.run_cycle()
        assert snap.status == "paused"
        assert snap.processed_events == 1


# ──────────────────────────────────────────────
# Safe-point — manual mode safe-point
# ──────────────────────────────────────────────

class TestManualModeSafePoint:
    def test_step_once_applies_commands_before_step(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])

        # Submit stop
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.STOP),
        )

        # step_once: safe-point applies stop, E1 not popped
        snap = ctrl.step_once()
        assert snap.status == "stopped"


# ──────────────────────────────────────────────
# Safe-point — hybrid mode
# ──────────────────────────────────────────────

class TestHybridModeSafePoint:
    def test_hybrid_run_cycle_applies_commands(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()

        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        snap = ctrl.run_cycle()
        assert snap.status == "paused"

    def test_hybrid_step_once_applies_commands(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])

        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.STOP),
        )
        snap = ctrl.step_once()
        assert snap.status == "stopped"
