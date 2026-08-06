"""M2-S04-C02 result capacity guarantee tests.

Validates:
- result_outbox_capacity parameter validation
- Default capacity equals command_queue_capacity
- Capacity exhaustion enforcement (no silent eviction)
- Drain releases capacity
- pending_command_count / pending_result_count / result_outbox_capacity
- Monotonic command sequences
- No duplicate or missing terminal results
- Terminal drain preserves all results
"""

import pytest

from virtual_factory.discrete.commands import (
    ControlCommandResult,
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


def _cmd(command_id, run_id="run-001", command_type=ControlCommandType.PAUSE):
    return RunControlCommand(
        command_id=command_id,
        run_id=run_id,
        command_type=command_type,
    )


def _make_running_controller(
    result_outbox_capacity=None,
    command_queue_capacity=None,
    mode=ExecutionMode.MANUAL,
):
    """Create an initialized, running controller ready for command submission.

    If ``command_queue_capacity`` is None, defaults to
    ``result_outbox_capacity`` (or 1024 if neither is set).
    """
    if command_queue_capacity is None:
        command_queue_capacity = result_outbox_capacity if result_outbox_capacity is not None else 1024
    engine = DiscreteSimulationEngine(
        _rc(), StubDispatcher(), trace_capacity=32,
    )
    ctrl = DiscreteRunController(
        engine,
        mode=mode,
        command_queue_capacity=command_queue_capacity,
        result_outbox_capacity=result_outbox_capacity,
    )
    ctrl.initialize([_evt("e1", 1.0)])
    ctrl._engine.start_running()
    return ctrl


# ──────────────────────────────────────────────
# Constructor validation
# ──────────────────────────────────────────────


class TestResultOutboxCapacityValidation:
    """C02: result_outbox_capacity constructor validation."""

    def test_default_capacity_equals_queue_capacity(self):
        """When result_outbox_capacity=None, defaults to command_queue_capacity."""
        ctrl = _make_running_controller(
            result_outbox_capacity=None,
            command_queue_capacity=500,
        )
        assert ctrl.result_outbox_capacity == 500

    def test_explicit_capacity(self):
        """Explicit result_outbox_capacity is stored and readable."""
        ctrl = _make_running_controller(
            result_outbox_capacity=2048,
            command_queue_capacity=1024,
        )
        assert ctrl.result_outbox_capacity == 2048

    def test_bool_rejected(self):
        """Bool value for result_outbox_capacity is rejected."""
        engine = DiscreteSimulationEngine(
            _rc(), StubDispatcher(), trace_capacity=32,
        )
        with pytest.raises(DiscreteRunControllerError, match="not bool"):
            DiscreteRunController(
                engine,
                result_outbox_capacity=True,
            )

        with pytest.raises(DiscreteRunControllerError, match="not bool"):
            DiscreteRunController(
                engine,
                result_outbox_capacity=False,
            )

    def test_invalid_capacity_rejected__zero(self):
        """Zero capacity is rejected."""
        engine = DiscreteSimulationEngine(
            _rc(), StubDispatcher(), trace_capacity=32,
        )
        with pytest.raises(DiscreteRunControllerError, match="int > 0"):
            DiscreteRunController(engine, result_outbox_capacity=0)

    def test_invalid_capacity_rejected__negative(self):
        """Negative capacity is rejected."""
        engine = DiscreteSimulationEngine(
            _rc(), StubDispatcher(), trace_capacity=32,
        )
        with pytest.raises(DiscreteRunControllerError, match="int > 0"):
            DiscreteRunController(engine, result_outbox_capacity=-1)

    def test_invalid_capacity_rejected__non_int(self):
        """Non-int capacity is rejected."""
        engine = DiscreteSimulationEngine(
            _rc(), StubDispatcher(), trace_capacity=32,
        )
        with pytest.raises(DiscreteRunControllerError, match="int > 0"):
            DiscreteRunController(engine, result_outbox_capacity=1.5)

        with pytest.raises(DiscreteRunControllerError, match="int > 0"):
            DiscreteRunController(engine, result_outbox_capacity="1024")

    def test_capacity_below_queue_capacity_rejected(self):
        """result_outbox_capacity < command_queue_capacity is rejected."""
        engine = DiscreteSimulationEngine(
            _rc(), StubDispatcher(), trace_capacity=32,
        )
        with pytest.raises(DiscreteRunControllerError, match="must be >="):
            DiscreteRunController(
                engine,
                command_queue_capacity=100,
                result_outbox_capacity=50,
            )

    def test_equal_capacity_accepted(self):
        """result_outbox_capacity == command_queue_capacity is accepted."""
        ctrl = _make_running_controller(
            result_outbox_capacity=100,
            command_queue_capacity=100,
        )
        assert ctrl.result_outbox_capacity == 100


# ──────────────────────────────────────────────
# Capacity exhaustion — explicit enforcement
# ──────────────────────────────────────────────


class TestCapacityExhaustion:
    """C02: result_outbox_capacity exhaustion with explicit enforcement."""

    # --- helper for capacity=3 tests ---
    @staticmethod
    def _cap3_ctrl():
        return _make_running_controller(
            result_outbox_capacity=3, command_queue_capacity=3,
        )

    def test_accept_three_commands_with_capacity_three(self):
        """capacity=3: accept exactly 3 commands."""
        ctrl = self._cap3_ctrl()

        r1 = ctrl.submit_command(_cmd("c1"))
        r2 = ctrl.submit_command(_cmd("c2"))
        r3 = ctrl.submit_command(_cmd("c3"))

        assert r1.status == "accepted"
        assert r2.status == "accepted"
        assert r3.status == "accepted"
        assert r1.command_sequence is not None
        assert r2.command_sequence is not None
        assert r3.command_sequence is not None

    def test_fourth_command_rejected_with_capacity_three(self):
        """capacity=3: 4th command is rejected with capacity_exhausted."""
        ctrl = self._cap3_ctrl()

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))

        r4 = ctrl.submit_command(_cmd("c4"))
        assert r4.status == "rejected"
        assert r4.rejection_code == "command_result_capacity_exhausted"

    def test_fourth_command_sequence_is_none(self):
        """Rejected 4th command has command_sequence=None."""
        ctrl = self._cap3_ctrl()

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))

        r4 = ctrl.submit_command(_cmd("c4"))
        assert r4.command_sequence is None

    def test_first_three_results_unchanged_after_rejection(self):
        """After 4th rejection, first three accepted results unchanged."""
        ctrl = self._cap3_ctrl()

        r1 = ctrl.submit_command(_cmd("c1"))
        r2 = ctrl.submit_command(_cmd("c2"))
        r3 = ctrl.submit_command(_cmd("c3"))
        _ = ctrl.submit_command(_cmd("c4"))

        # First three should still be accepted with sequences 1,2,3
        assert r1.status == "accepted"
        assert r1.command_sequence == 1
        assert r2.status == "accepted"
        assert r2.command_sequence == 2
        assert r3.status == "accepted"
        assert r3.command_sequence == 3

    def test_drain_releases_capacity(self):
        """After draining outbox, new commands can be accepted."""
        ctrl = self._cap3_ctrl()

        # Accept 3 pause commands (valid in RUNNING)
        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))

        # Apply via step_once — moves commands to outbox.
        # First PAUSE transitions RUNNING→PAUSED, rest rejected (invalid_for_status).
        ctrl.step_once()

        # Now outbox has 3 results, queue=0. Engine is PAUSED.
        # Capacity check fires before status check → capacity_exhausted.
        r4 = ctrl.submit_command(_cmd("c4"))
        assert r4.status == "rejected"
        assert r4.rejection_code == "command_result_capacity_exhausted"

        # Drain frees capacity
        drained = ctrl.drain_command_results()
        assert len(drained) == 3

        # Now can accept RESUME (valid from PAUSED)
        r5 = ctrl.submit_command(_cmd("c5", command_type=ControlCommandType.RESUME))
        assert r5.status == "accepted"

    def test_next_accepted_command_sequence_monotonic(self):
        """Drain + new accept preserves monotonic sequence numbering."""
        ctrl = self._cap3_ctrl()

        r1 = ctrl.submit_command(_cmd("c1"))
        r2 = ctrl.submit_command(_cmd("c2"))
        r3 = ctrl.submit_command(_cmd("c3"))

        seq1 = r1.command_sequence
        seq2 = r2.command_sequence
        seq3 = r3.command_sequence

        assert seq1 is not None
        assert seq2 is not None
        assert seq3 is not None
        assert seq1 < seq2 < seq3

        # Apply → outbox has 3 (engine becomes PAUSED)
        ctrl.step_once()
        ctrl.drain_command_results()

        # Accept RESUME (valid from PAUSED) — sequence continues monotonically
        r4 = ctrl.submit_command(_cmd("c4", command_type=ControlCommandType.RESUME))
        assert r4.command_sequence is not None
        assert r4.command_sequence > seq3


# ──────────────────────────────────────────────
# No silent eviction
# ──────────────────────────────────────────────


class TestNoSilentEviction:
    """C02: No silent eviction — deque without maxlen, explicit enforcement."""

    def test_no_oldest_eviction(self):
        """When at capacity, oldest result is NOT silently evicted."""
        ctrl = _make_running_controller(result_outbox_capacity=2)

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))

        # Apply → outbox has 2 results
        ctrl.step_once()

        # Both results must be present (no oldest eviction)
        drained = ctrl.drain_command_results()
        assert len(drained) == 2
        assert drained[0].command_id == "c1"
        assert drained[1].command_id == "c2"

    def test_no_newest_eviction(self):
        """When at capacity, newest result is NOT silently evicted."""
        ctrl = _make_running_controller(result_outbox_capacity=2)

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))

        ctrl.step_once()

        drained = ctrl.drain_command_results()
        assert len(drained) == 2
        # Both present
        cmd_ids = [r.command_id for r in drained]
        assert "c1" in cmd_ids
        assert "c2" in cmd_ids

    def test_no_duplicate_terminal_result(self):
        """Every command produces exactly one terminal result — no duplicates."""
        ctrl = _make_running_controller(result_outbox_capacity=5)

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))

        ctrl.step_once()

        drained = ctrl.drain_command_results()
        cmd_ids = [r.command_id for r in drained]
        # Each command_id appears exactly once
        assert cmd_ids.count("c1") == 1
        assert cmd_ids.count("c2") == 1
        assert cmd_ids.count("c3") == 1

    def test_no_missing_terminal_result(self):
        """Every accepted command has a terminal result — no missing ones."""
        ctrl = _make_running_controller(result_outbox_capacity=5)

        ids = ["c1", "c2", "c3", "c4", "c5"]
        for cid in ids:
            ctrl.submit_command(_cmd(cid))

        ctrl.step_once()

        drained = ctrl.drain_command_results()
        drained_ids = {r.command_id for r in drained}
        assert drained_ids == set(ids)

    def test_terminal_drain_preserves_all_results(self):
        """drain_command_results() returns all results, second call returns ()."""
        ctrl = _make_running_controller(result_outbox_capacity=5)

        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))
        ctrl.step_once()

        drained1 = ctrl.drain_command_results()
        assert len(drained1) == 3

        # Second drain returns empty
        drained2 = ctrl.drain_command_results()
        assert drained2 == ()


# ──────────────────────────────────────────────
# Read-only properties
# ──────────────────────────────────────────────


class TestPendingCounts:
    """C02: pending_command_count, pending_result_count, result_outbox_capacity."""

    def test_pending_command_count_starts_zero(self):
        ctrl = _make_running_controller()
        assert ctrl.pending_command_count == 0

    def test_pending_command_count_increments(self):
        ctrl = _make_running_controller(result_outbox_capacity=10)
        ctrl.submit_command(_cmd("c1"))
        assert ctrl.pending_command_count == 1
        ctrl.submit_command(_cmd("c2"))
        assert ctrl.pending_command_count == 2

    def test_pending_result_count_starts_zero(self):
        ctrl = _make_running_controller()
        assert ctrl.pending_result_count == 0

    def test_pending_result_count_after_apply(self):
        ctrl = _make_running_controller(result_outbox_capacity=10)
        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.submit_command(_cmd("c3"))

        assert ctrl.pending_result_count == 0
        assert ctrl.pending_command_count == 3

        ctrl.step_once()

        assert ctrl.pending_command_count == 0
        assert ctrl.pending_result_count == 3

    def test_result_outbox_capacity_property(self):
        ctrl = _make_running_controller(result_outbox_capacity=777)
        assert ctrl.result_outbox_capacity == 777

    def test_counts_after_drain(self):
        ctrl = _make_running_controller(result_outbox_capacity=10)
        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        ctrl.step_once()

        assert ctrl.pending_result_count == 2

        ctrl.drain_command_results()

        assert ctrl.pending_result_count == 0
        assert ctrl.pending_command_count == 0


# ──────────────────────────────────────────────
# Capacity exhaustion with mixed queue+outbox
# ──────────────────────────────────────────────


class TestCapacityExhaustionMixedQueueOutbox:
    """C02: Capacity counts both queued commands AND results in outbox."""

    def test_queue_plus_outbox_count_toward_capacity(self):
        """Pending = queue.size + len(outbox). Both count against capacity."""
        ctrl = _make_running_controller(result_outbox_capacity=4)

        # Accept 2 pause commands (valid in RUNNING)
        ctrl.submit_command(_cmd("c1"))
        ctrl.submit_command(_cmd("c2"))
        # Apply → outbox has 2, engine becomes PAUSED
        ctrl.step_once()
        assert ctrl.pending_result_count == 2
        assert ctrl.pending_command_count == 0

        # RESUME is valid from PAUSED.
        # Accept 2 more → total pending = 4 (outbox 2 + queue 2)
        ctrl.submit_command(_cmd("c3", command_type=ControlCommandType.RESUME))
        ctrl.submit_command(_cmd("c4", command_type=ControlCommandType.RESUME))
        assert ctrl.pending_command_count == 2
        # Total = 2 + 2 = 4

        # 5th should be rejected (4 >= 4)
        r5 = ctrl.submit_command(_cmd("c5", command_type=ControlCommandType.RESUME))
        assert r5.status == "rejected"
        assert r5.rejection_code == "command_result_capacity_exhausted"
