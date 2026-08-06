"""Tests for control commands, results, and queue — M2-S04."""

import pytest

from virtual_factory.discrete.commands import (
    ControlCommandQueue,
    ControlCommandQueueError,
    ControlCommandResult,
    ControlCommandResultError,
    ControlCommandType,
    RunControlCommand,
    RunControlCommandError,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _cmd(cmd_id="c1", run_id="run-001", cmd_type=ControlCommandType.PAUSE, **kw):
    return RunControlCommand(
        command_id=cmd_id,
        run_id=run_id,
        command_type=cmd_type,
        **kw,
    )


# ──────────────────────────────────────────────
# RunControlCommand validation
# ──────────────────────────────────────────────

class TestRunControlCommand:
    def test_valid_pause(self):
        c = _cmd()
        assert c.command_id == "c1"
        assert c.run_id == "run-001"
        assert c.command_type == ControlCommandType.PAUSE
        assert c.reason is None
        assert c.command_sequence is None

    def test_with_reason(self):
        c = _cmd(reason="operator requested")
        assert c.reason == "operator requested"

    def test_empty_command_id_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_id"):
            _cmd(cmd_id="")

    def test_whitespace_command_id_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_id"):
            _cmd(cmd_id="   ")

    def test_empty_run_id_rejected(self):
        with pytest.raises(RunControlCommandError, match="run_id"):
            _cmd(run_id="")

    def test_invalid_command_type_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_type"):
            RunControlCommand(command_id="c1", run_id="r1", command_type="pause")

    def test_bool_sequence_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_sequence"):
            RunControlCommand(
                command_id="c1", run_id="r1",
                command_type=ControlCommandType.PAUSE,
                command_sequence=True,
            )

    def test_zero_sequence_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_sequence"):
            RunControlCommand(
                command_id="c1", run_id="r1",
                command_type=ControlCommandType.PAUSE,
                command_sequence=0,
            )

    def test_negative_sequence_rejected(self):
        with pytest.raises(RunControlCommandError, match="command_sequence"):
            RunControlCommand(
                command_id="c1", run_id="r1",
                command_type=ControlCommandType.PAUSE,
                command_sequence=-1,
            )

    def test_frozen(self):
        c = _cmd()
        with pytest.raises(Exception):
            c.command_id = "x"

    def test_all_command_types(self):
        for ct in ControlCommandType:
            c = _cmd(cmd_type=ct)
            assert c.command_type == ct


# ──────────────────────────────────────────────
# ControlCommandResult validation
# ──────────────────────────────────────────────

class TestControlCommandResult:
    def test_accepted_result(self):
        r = ControlCommandResult(
            command_id="c1", command_sequence=1,
            command_type="pause", status="accepted",
            snapshot_sequence=None,
            rejection_code=None, rejection_detail=None,
        )
        assert r.status == "accepted"
        assert r.command_sequence == 1

    def test_applied_result(self):
        r = ControlCommandResult(
            command_id="c1", command_sequence=1,
            command_type="pause", status="applied",
            snapshot_sequence=5,
            rejection_code=None, rejection_detail=None,
        )
        assert r.status == "applied"
        assert r.snapshot_sequence == 5

    def test_rejected_result(self):
        r = ControlCommandResult(
            command_id="c1", command_sequence=None,
            command_type="pause", status="rejected",
            snapshot_sequence=None,
            rejection_code="run_id_mismatch",
            rejection_detail="wrong run",
        )
        assert r.status == "rejected"
        assert r.rejection_code == "run_id_mismatch"

    def test_failed_result(self):
        r = ControlCommandResult(
            command_id="c1", command_sequence=1,
            command_type="pause", status="failed",
            snapshot_sequence=None,
            rejection_code="engine_error",
            rejection_detail="boom",
        )
        assert r.status == "failed"

    def test_empty_command_id_rejected(self):
        with pytest.raises(ControlCommandResultError, match="command_id"):
            ControlCommandResult(
                command_id="", command_sequence=1,
                command_type="pause", status="accepted",
                snapshot_sequence=None,
                rejection_code=None, rejection_detail=None,
            )

    def test_invalid_status_rejected(self):
        with pytest.raises(ControlCommandResultError, match="status"):
            ControlCommandResult(
                command_id="c1", command_sequence=1,
                command_type="pause", status="pending",
                snapshot_sequence=None,
                rejection_code=None, rejection_detail=None,
            )

    def test_bool_command_sequence_rejected(self):
        with pytest.raises(ControlCommandResultError, match="command_sequence"):
            ControlCommandResult(
                command_id="c1", command_sequence=True,
                command_type="pause", status="accepted",
                snapshot_sequence=None,
                rejection_code=None, rejection_detail=None,
            )

    def test_bool_snapshot_sequence_rejected(self):
        with pytest.raises(ControlCommandResultError, match="snapshot_sequence"):
            ControlCommandResult(
                command_id="c1", command_sequence=1,
                command_type="pause", status="applied",
                snapshot_sequence=True,
                rejection_code=None, rejection_detail=None,
            )

    def test_rejected_without_code_fails(self):
        with pytest.raises(ControlCommandResultError, match="rejection_code"):
            ControlCommandResult(
                command_id="c1", command_sequence=None,
                command_type="pause", status="rejected",
                snapshot_sequence=None,
                rejection_code=None, rejection_detail=None,
            )

    def test_accepted_with_rejection_code_fails(self):
        with pytest.raises(ControlCommandResultError, match="rejection_code"):
            ControlCommandResult(
                command_id="c1", command_sequence=1,
                command_type="pause", status="accepted",
                snapshot_sequence=None,
                rejection_code="unexpected", rejection_detail=None,
            )

    def test_frozen(self):
        r = ControlCommandResult(
            command_id="c1", command_sequence=1,
            command_type="pause", status="accepted",
            snapshot_sequence=None,
            rejection_code=None, rejection_detail=None,
        )
        with pytest.raises(Exception):
            r.status = "x"


# ──────────────────────────────────────────────
# ControlCommandQueue — construction
# ──────────────────────────────────────────────

class TestQueueConstruction:
    def test_default_capacity(self):
        q = ControlCommandQueue()
        assert q.capacity == 1024
        assert q.size == 0
        assert q.is_empty

    def test_custom_capacity(self):
        q = ControlCommandQueue(capacity=5)
        assert q.capacity == 5

    def test_bool_capacity_rejected(self):
        with pytest.raises(ControlCommandQueueError, match="capacity"):
            ControlCommandQueue(capacity=True)

    def test_zero_capacity_rejected(self):
        with pytest.raises(ControlCommandQueueError, match="capacity"):
            ControlCommandQueue(capacity=0)

    def test_negative_capacity_rejected(self):
        with pytest.raises(ControlCommandQueueError, match="capacity"):
            ControlCommandQueue(capacity=-1)


# ──────────────────────────────────────────────
# ControlCommandQueue — acceptance
# ──────────────────────────────────────────────

class TestQueueAcceptance:
    def test_accept_pause_when_running(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.PAUSE),
            engine_status="running", engine_run_id="run-001",
        )
        assert result.status == "accepted"
        assert result.command_sequence == 1

    def test_accept_stop_when_running(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.STOP),
            engine_status="running", engine_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_accept_resume_when_paused(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.RESUME),
            engine_status="paused", engine_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_accept_stop_when_paused(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.STOP),
            engine_status="paused", engine_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_accept_stop_when_ready(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.STOP),
            engine_status="ready", engine_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_accept_stop_when_created(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.STOP),
            engine_status="created", engine_run_id="run-001",
        )
        assert result.status == "accepted"

    def test_reject_pause_when_ready(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.PAUSE),
            engine_status="ready", engine_run_id="run-001",
        )
        assert result.status == "rejected"
        assert result.rejection_code == "invalid_for_status"

    def test_reject_resume_when_running(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(cmd_type=ControlCommandType.RESUME),
            engine_status="running", engine_run_id="run-001",
        )
        assert result.status == "rejected"

    def test_reject_all_when_terminal(self):
        q = ControlCommandQueue()
        for status in ("completed", "stopped", "failed"):
            for ct in ControlCommandType:
                result = q.try_accept(
                    _cmd(cmd_type=ct),
                    engine_status=status, engine_run_id="run-001",
                )
                assert result.status == "rejected", f"{ct} from {status}"


# ──────────────────────────────────────────────
# ControlCommandQueue — run ID mismatch
# ──────────────────────────────────────────────

class TestQueueRunIdMismatch:
    def test_wrong_run_id_rejected(self):
        q = ControlCommandQueue()
        result = q.try_accept(
            _cmd(run_id="run-002"),
            engine_status="running", engine_run_id="run-001",
        )
        assert result.status == "rejected"
        assert result.rejection_code == "run_id_mismatch"
        assert result.command_sequence is None


# ──────────────────────────────────────────────
# ControlCommandQueue — capacity
# ──────────────────────────────────────────────

class TestQueueCapacity:
    def test_queue_full_rejected(self):
        q = ControlCommandQueue(capacity=2)
        # Accept 2
        assert q.try_accept(
            _cmd(cmd_id="c1", cmd_type=ControlCommandType.PAUSE),
            engine_status="running", engine_run_id="run-001",
        ).status == "accepted"
        assert q.try_accept(
            _cmd(cmd_id="c2", cmd_type=ControlCommandType.STOP),
            engine_status="running", engine_run_id="run-001",
        ).status == "accepted"
        # 3rd rejected
        result = q.try_accept(
            _cmd(cmd_id="c3", cmd_type=ControlCommandType.PAUSE),
            engine_status="running", engine_run_id="run-001",
        )
        assert result.status == "rejected"
        assert result.rejection_code == "command_queue_full"


# ──────────────────────────────────────────────
# ControlCommandQueue — FIFO ordering
# ──────────────────────────────────────────────

class TestQueueOrdering:
    def test_fifo_order_preserved(self):
        q = ControlCommandQueue()
        q.try_accept(
            _cmd(cmd_id="a"), engine_status="running", engine_run_id="run-001",
        )
        q.try_accept(
            _cmd(cmd_id="b"), engine_status="running", engine_run_id="run-001",
        )
        q.try_accept(
            _cmd(cmd_id="c"), engine_status="running", engine_run_id="run-001",
        )
        cmds = q.pop_all()
        assert [c.command_id for c in cmds] == ["a", "b", "c"]
        assert [c.command_sequence for c in cmds] == [1, 2, 3]

    def test_sequence_monotonic(self):
        q = ControlCommandQueue()
        seqs = []
        for i in range(5):
            r = q.try_accept(
                _cmd(cmd_id=str(i)),
                engine_status="running", engine_run_id="run-001",
            )
            seqs.append(r.command_sequence)
        assert seqs == [1, 2, 3, 4, 5]

    def test_sequence_does_not_increment_on_reject(self):
        q = ControlCommandQueue()
        q.try_accept(
            _cmd(cmd_id="c1"), engine_status="running", engine_run_id="run-001",
        )
        # This should be rejected
        q.try_accept(
            _cmd(cmd_id="c2"), engine_status="completed", engine_run_id="run-001",
        )
        # Next accepted should get sequence 2
        result = q.try_accept(
            _cmd(cmd_id="c3"), engine_status="running", engine_run_id="run-001",
        )
        assert result.command_sequence == 2


# ──────────────────────────────────────────────
# ControlCommandQueue — immutability
# ──────────────────────────────────────────────

class TestQueueImmutability:
    def test_pop_all_clears_queue(self):
        q = ControlCommandQueue()
        q.try_accept(
            _cmd(), engine_status="running", engine_run_id="run-001",
        )
        assert q.size == 1
        q.pop_all()
        assert q.size == 0
        assert q.is_empty

    def test_queued_commands_is_detached(self):
        q = ControlCommandQueue()
        q.try_accept(
            _cmd(cmd_id="c1"), engine_status="running", engine_run_id="run-001",
        )
        snap = q.queued_commands
        assert len(snap) == 1
        # pop_all and verify snapshot unchanged
        q.pop_all()
        assert len(snap) == 1  # snapshot still has it

    def test_invalid_command_type_rejected_by_try_accept(self):
        q = ControlCommandQueue()
        with pytest.raises(ControlCommandQueueError, match="RunControlCommand"):
            q.try_accept("not-a-command", engine_status="running", engine_run_id="r1")


# ──────────────────────────────────────────────
# ControlCommandQueue — drain_and_reject
# ──────────────────────────────────────────────

class TestQueueDrainReject:
    def test_drain_rejects_all_queued(self):
        q = ControlCommandQueue()
        q.try_accept(
            _cmd(cmd_id="a"), engine_status="running", engine_run_id="run-001",
        )
        q.try_accept(
            _cmd(cmd_id="b"), engine_status="running", engine_run_id="run-001",
        )
        results = q.drain_and_reject("engine_terminal", "done")
        assert len(results) == 2
        assert all(r.status == "rejected" for r in results)
        assert all(r.rejection_code == "engine_terminal" for r in results)
        assert q.is_empty

    def test_drain_empty_returns_empty(self):
        q = ControlCommandQueue()
        results = q.drain_and_reject("x", "y")
        assert results == ()
