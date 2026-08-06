"""Tests for DiscreteRunController, ExecutionMode, ControllerPacingPolicy — M2-S04."""

import math
import pytest

from virtual_factory.discrete.commands import (
    ControlCommandResult,
    ControlCommandType,
    RunControlCommand,
)
from virtual_factory.discrete.controller import (
    ControllerPacingPolicy,
    ControllerPacingPolicyError,
    DiscreteRunController,
    DiscreteRunControllerError,
    ExecutionMode,
    _compute_allowed_actions,
)
from virtual_factory.discrete.dispatcher import HandlerOutcome
from virtual_factory.discrete.engine import (
    DiscreteSimulationEngine,
    DiscreteSimulationEngineError,
)
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.snapshot import RuntimeSnapshot, RuntimeSnapshotError
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


class FailingDispatcher:
    def __init__(self, error_code="test_failure"):
        self.error_code = error_code

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        return HandlerOutcome(
            event_id=event.event_id,
            success=False,
            follow_up_events=(),
            state_changes=(),
            error_code=self.error_code,
        )


# ──────────────────────────────────────────────
# ExecutionMode
# ──────────────────────────────────────────────

class TestExecutionMode:
    def test_values(self):
        assert ExecutionMode.MANUAL.value == "manual"
        assert ExecutionMode.AUTOMATIC.value == "automatic"
        assert ExecutionMode.HYBRID.value == "hybrid"

    def test_is_str_enum(self):
        assert isinstance(ExecutionMode.MANUAL, str)


# ──────────────────────────────────────────────
# ControllerPacingPolicy
# ──────────────────────────────────────────────

class TestControllerPacingPolicy:
    def test_defaults(self):
        p = ControllerPacingPolicy()
        assert p.speed_factor == 1.0
        assert p.max_events_per_second == 1000
        assert p.snapshot_broadcast_max_hz == 10

    def test_custom_values(self):
        p = ControllerPacingPolicy(speed_factor=2.0, max_events_per_second=500, snapshot_broadcast_max_hz=5)
        assert p.speed_factor == 2.0
        assert p.max_events_per_second == 500
        assert p.snapshot_broadcast_max_hz == 5

    def test_bool_speed_factor_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="speed_factor"):
            ControllerPacingPolicy(speed_factor=True)

    def test_nan_speed_factor_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="speed_factor"):
            ControllerPacingPolicy(speed_factor=math.nan)

    def test_inf_speed_factor_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="speed_factor"):
            ControllerPacingPolicy(speed_factor=math.inf)

    def test_zero_speed_factor_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="speed_factor"):
            ControllerPacingPolicy(speed_factor=0.0)

    def test_negative_speed_factor_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="speed_factor"):
            ControllerPacingPolicy(speed_factor=-1.0)

    def test_bool_max_eps_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="max_events_per_second"):
            ControllerPacingPolicy(max_events_per_second=True)

    def test_zero_max_eps_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="max_events_per_second"):
            ControllerPacingPolicy(max_events_per_second=0)

    def test_bool_snapshot_hz_rejected(self):
        with pytest.raises(ControllerPacingPolicyError, match="snapshot_broadcast_max_hz"):
            ControllerPacingPolicy(snapshot_broadcast_max_hz=True)

    def test_frozen(self):
        p = ControllerPacingPolicy()
        with pytest.raises(Exception):
            p.speed_factor = 2.0


# ──────────────────────────────────────────────
# DiscreteRunController — construction
# ──────────────────────────────────────────────

class TestControllerConstruction:
    def test_default_mode_is_manual(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        assert ctrl.mode == ExecutionMode.MANUAL

    def test_explicit_mode(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        assert ctrl.mode == ExecutionMode.AUTOMATIC

    def test_invalid_engine_rejected(self):
        with pytest.raises(DiscreteRunControllerError, match="engine"):
            DiscreteRunController("not-an-engine")

    def test_invalid_mode_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        with pytest.raises(DiscreteRunControllerError, match="mode"):
            DiscreteRunController(engine, mode="auto")


# ──────────────────────────────────────────────
# allowed_actions projection
# ──────────────────────────────────────────────

class TestAllowedActions:
    def test_created(self):
        assert _compute_allowed_actions(RunStatus.CREATED, ExecutionMode.MANUAL) == ("initialize", "stop")

    def test_ready_manual(self):
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.MANUAL) == ("step_event", "stop")

    def test_ready_automatic(self):
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.AUTOMATIC) == ("auto_run", "stop")

    def test_ready_hybrid(self):
        assert _compute_allowed_actions(RunStatus.READY, ExecutionMode.HYBRID) == ("auto_run", "step_event", "stop")

    def test_running(self):
        for mode in ExecutionMode:
            assert _compute_allowed_actions(RunStatus.RUNNING, mode) == ("pause", "stop")

    def test_paused_manual(self):
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.MANUAL) == ("step_event", "stop")

    def test_paused_automatic(self):
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.AUTOMATIC) == ("resume", "stop")

    def test_paused_hybrid(self):
        assert _compute_allowed_actions(RunStatus.PAUSED, ExecutionMode.HYBRID) == ("resume", "step_event", "stop")

    def test_terminal_empty(self):
        for status in (RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.FAILED):
            for mode in ExecutionMode:
                assert _compute_allowed_actions(status, mode) == ()

    def test_result_is_tuple(self):
        actions = _compute_allowed_actions(RunStatus.READY, ExecutionMode.HYBRID)
        assert isinstance(actions, tuple)
        # Check sorted order
        assert actions == tuple(sorted(actions))


# ──────────────────────────────────────────────
# Controller snapshot
# ──────────────────────────────────────────────

class TestControllerSnapshot:
    def test_created_snapshot_has_allowed_actions(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        snap = ctrl.to_snapshot()
        assert snap.allowed_actions == ("initialize", "stop")
        assert snap.schema_version == "1.2.0"

    def test_ready_manual_snapshot(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        ctrl.initialize()
        snap = ctrl.to_snapshot()
        assert snap.allowed_actions == ("step_event", "stop")
        assert snap.status == "ready"

    def test_allowed_actions_is_tuple(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        snap = ctrl.to_snapshot()
        assert isinstance(snap.allowed_actions, tuple)
        # Verify immutability via frozendataclass
        with pytest.raises(Exception):
            snap.allowed_actions = ("x",)

    def test_engine_snapshot_has_empty_allowed_actions(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        snap = engine.to_snapshot()
        assert snap.allowed_actions == ()


# ──────────────────────────────────────────────
# Controller initialize
# ──────────────────────────────────────────────

class TestControllerInitialize:
    def test_initialize_transitions_to_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        snap = ctrl.initialize()
        assert snap.status == "ready"

    def test_initialize_with_events(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        snap = ctrl.initialize(initial_events=[_evt("e1")])
        assert snap.pending_events == 1


# ──────────────────────────────────────────────
# Controller submit_command
# ──────────────────────────────────────────────

class TestControllerSubmitCommand:
    def test_accept_pause_when_running(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()  # READY → RUNNING
        result = ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        assert result.status == "accepted"
        assert result.command_sequence == 1

    def test_reject_pause_when_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine)
        ctrl.initialize()  # READY
        result = ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        assert result.status == "rejected"
        assert result.rejection_code == "invalid_for_status"

    def test_acceptance_does_not_mutate_snapshot_sequence(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()
        seq_before = ctrl.to_snapshot().snapshot_sequence
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        seq_after = ctrl.to_snapshot().snapshot_sequence
        assert seq_after == seq_before

    def test_wrong_run_id_rejected(self):
        engine = DiscreteSimulationEngine(_rc(run_id="run-001"), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()
        result = ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-002", command_type=ControlCommandType.PAUSE),
        )
        assert result.status == "rejected"
        assert result.rejection_code == "run_id_mismatch"


# ──────────────────────────────────────────────
# Manual mode
# ──────────────────────────────────────────────

class TestManualMode:
    def test_step_once_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1")])
        snap = ctrl.step_once()
        assert snap.processed_events == 1

    def test_step_once_preserves_ready_after_non_terminal(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        snap = ctrl.step_once()
        assert snap.status == "ready"
        assert snap.processed_events == 1
        assert snap.pending_events == 1

    def test_step_completes_when_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1")])
        snap = ctrl.step_once()
        assert snap.status == "completed"

    def test_automatic_start_rejected_in_manual(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize()
        with pytest.raises(DiscreteRunControllerError, match="MANUAL"):
            ctrl.start_automatic()

    def test_step_from_paused_in_manual(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        # Manually start running then pause
        engine.start_running()
        engine.pause()
        # Now PAUSED in MANUAL mode — step allowed
        snap = ctrl.step_once()
        assert snap.status == "paused"

    def test_step_not_allowed_in_automatic_mode(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize()
        with pytest.raises(DiscreteRunControllerError, match="AUTOMATIC"):
            ctrl.step_once()


# ──────────────────────────────────────────────
# Automatic mode
# ──────────────────────────────────────────────

class TestAutomaticMode:
    def test_start_automatic_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        snap = ctrl.start_automatic()
        assert snap.status == "running"

    def test_start_automatic_from_paused(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()
        engine.pause()
        snap = ctrl.start_automatic()
        assert snap.status == "running"

    def test_start_automatic_from_running_rejected(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()
        with pytest.raises(DiscreteRunControllerError, match="ready or paused"):
            ctrl.start_automatic()

    def test_run_cycle_processes_one_event(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        snap = ctrl.run_cycle()
        assert snap.processed_events == 1
        assert snap.pending_events == 1
        assert snap.status == "running"

    def test_run_cycle_completes_when_empty(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1")])
        ctrl.start_automatic()
        snap = ctrl.run_cycle()
        assert snap.status == "completed"

    def test_run_cycle_not_allowed_in_manual(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.MANUAL)
        ctrl.initialize()
        with pytest.raises(DiscreteRunControllerError, match="AUTOMATIC or HYBRID"):
            ctrl.run_cycle()

    def test_run_cycle_drains_on_terminal(self):
        """When a step leads to terminal, queued commands are drained."""
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.AUTOMATIC)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        # Process E1 first, then submit pause between cycles
        ctrl.run_cycle()  # processes E1, status stays RUNNING
        ctrl.submit_command(
            RunControlCommand(command_id="c1", run_id="run-001", command_type=ControlCommandType.PAUSE),
        )
        # Next run_cycle: safe-point applies pause → PAUSED → drain because not RUNNING
        snap = ctrl.run_cycle()
        assert snap.status == "paused"
        # Pause applied, E2 remains pending


# ──────────────────────────────────────────────
# Hybrid mode
# ──────────────────────────────────────────────

class TestHybridMode:
    def test_manual_step_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1")])
        snap = ctrl.step_once()
        assert snap.processed_events == 1

    def test_automatic_start_from_ready(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1")])
        snap = ctrl.start_automatic()
        assert snap.status == "running"

    def test_run_cycle_in_hybrid(self):
        engine = DiscreteSimulationEngine(_rc(), StubDispatcher())
        ctrl = DiscreteRunController(engine, mode=ExecutionMode.HYBRID)
        ctrl.initialize(initial_events=[_evt("e1"), _evt("e2")])
        ctrl.start_automatic()
        snap = ctrl.run_cycle()
        assert snap.processed_events == 1


# ──────────────────────────────────────────────
# Controller snapshot compatibility
# ──────────────────────────────────────────────

class TestSnapshotCompatibility:
    def test_legacy_14_positional_still_works(self):
        """Exact 14-arg positional constructor from spec must still work."""
        s = RuntimeSnapshot(
            "r1", "m1", None, None, None,
            "created", 0.0, None, None,
            0, 0, None, 0,
            "1.0.0",
        )
        assert s.run_id == "r1"
        assert s.schema_version == "1.0.0"
        assert s.allowed_actions == ()

    def test_schema_version_position_preserved(self):
        """schema_version remains at field index 13 (0-based)."""
        s = RuntimeSnapshot(
            "r1", "m1", None, None, None,
            "created", 0.0, None, None,
            0, 0, None, 0,
            "1.0.0",
        )
        assert s.schema_version == "1.0.0"

    def test_allowed_actions_tuple_validation(self):
        with pytest.raises(RuntimeSnapshotError, match="allowed_actions"):
            RuntimeSnapshot(
                run_id="r1", model_id="m1",
                model_version=None, scenario_id=None, scenario_version=None,
                status="created", simulation_time_s=0.0,
                stop_reason=None, failure_error=None,
                processed_events=0, pending_events=0,
                last_event_id=None, snapshot_sequence=0,
                allowed_actions=["a", "b"],  # list not tuple
            )

    def test_allowed_actions_non_str_element_rejected(self):
        with pytest.raises(RuntimeSnapshotError, match="allowed_actions"):
            RuntimeSnapshot(
                run_id="r1", model_id="m1",
                model_version=None, scenario_id=None, scenario_version=None,
                status="created", simulation_time_s=0.0,
                stop_reason=None, failure_error=None,
                processed_events=0, pending_events=0,
                last_event_id=None, snapshot_sequence=0,
                allowed_actions=(1, 2),
            )
