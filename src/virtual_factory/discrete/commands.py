"""Domain-neutral control commands, results, and bounded FIFO queue.

M2-S04: command types, command records, results, queue.
No wall-clock, no async, no domain logic, no audit log.
"""

from __future__ import annotations

import enum
from collections import deque
from dataclasses import dataclass


# ──────────────────────────────────────────────
# Command type enum
# ──────────────────────────────────────────────


class ControlCommandType(str, enum.Enum):
    """Kinds of control commands the controller accepts."""

    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


# ──────────────────────────────────────────────
# RunControlCommand
# ──────────────────────────────────────────────


class RunControlCommandError(ValueError):
    """Raised when a RunControlCommand invariant is violated."""


@dataclass(frozen=True, slots=True)
class RunControlCommand:
    """Immutable domain-neutral control command.

    Caller supplies ``command_id``.  Controller assigns ``command_sequence``.
    """

    command_id: str
    run_id: str
    command_type: ControlCommandType
    reason: str | None = None
    command_sequence: int | None = None

    def __post_init__(self) -> None:
        # command_id
        if not isinstance(self.command_id, str) or not self.command_id.strip():
            raise RunControlCommandError("command_id must be non-empty str")

        # run_id
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise RunControlCommandError("run_id must be non-empty str")

        # command_type
        if not isinstance(self.command_type, ControlCommandType):
            raise RunControlCommandError(
                f"command_type must be ControlCommandType, "
                f"got {type(self.command_type).__name__}"
            )

        # command_sequence must be None before acceptance
        if self.command_sequence is not None:
            if isinstance(self.command_sequence, bool):
                raise RunControlCommandError(
                    "command_sequence must be int or None, not bool"
                )
            if not isinstance(self.command_sequence, int) or self.command_sequence < 1:
                raise RunControlCommandError(
                    "command_sequence must be int >= 1 or None"
                )


# ──────────────────────────────────────────────
# ControlCommandResult
# ──────────────────────────────────────────────


class ControlCommandResultError(ValueError):
    """Raised when a ControlCommandResult invariant is violated."""


_VALID_STATUSES = frozenset({"accepted", "applied", "rejected", "failed"})


@dataclass(frozen=True, slots=True)
class ControlCommandResult:
    """Immutable result of submitting or applying a control command."""

    command_id: str
    command_sequence: int | None
    command_type: str
    status: str
    snapshot_sequence: int | None
    rejection_code: str | None
    rejection_detail: str | None

    def __post_init__(self) -> None:
        # command_id
        if not isinstance(self.command_id, str) or not self.command_id.strip():
            raise ControlCommandResultError("command_id must be non-empty str")

        # command_sequence
        if self.command_sequence is not None:
            if isinstance(self.command_sequence, bool):
                raise ControlCommandResultError(
                    "command_sequence must be int or None, not bool"
                )
            if not isinstance(self.command_sequence, int) or self.command_sequence < 1:
                raise ControlCommandResultError(
                    "command_sequence must be int >= 1 or None"
                )

        # command_type
        if not isinstance(self.command_type, str) or not self.command_type.strip():
            raise ControlCommandResultError("command_type must be non-empty str")

        # status
        if self.status not in _VALID_STATUSES:
            raise ControlCommandResultError(
                f"status must be one of {sorted(_VALID_STATUSES)}, "
                f"got {self.status!r}"
            )

        # snapshot_sequence
        if self.snapshot_sequence is not None:
            if isinstance(self.snapshot_sequence, bool):
                raise ControlCommandResultError(
                    "snapshot_sequence must be int or None, not bool"
                )
            if not isinstance(self.snapshot_sequence, int) or self.snapshot_sequence < 0:
                raise ControlCommandResultError(
                    "snapshot_sequence must be int >= 0 or None"
                )

        # rejection_code consistency
        if self.status == "rejected":
            if not isinstance(self.rejection_code, str) or not self.rejection_code.strip():
                raise ControlCommandResultError(
                    "rejected result must have non-empty rejection_code"
                )
        elif self.status in ("accepted", "applied"):
            if self.rejection_code is not None:
                raise ControlCommandResultError(
                    f"{self.status} result must have rejection_code=None"
                )
            if self.rejection_detail is not None:
                raise ControlCommandResultError(
                    f"{self.status} result must have rejection_detail=None"
                )
        # "failed" may carry rejection_code and rejection_detail

        # rejection_detail
        if self.rejection_detail is not None and not isinstance(self.rejection_detail, str):
            raise ControlCommandResultError("rejection_detail must be str or None")


# ──────────────────────────────────────────────
# ControlCommandQueue
# ──────────────────────────────────────────────


class ControlCommandQueueError(ValueError):
    """Raised when a ControlCommandQueue invariant is violated."""


# Map engine status → accepted command types (checked at submission time)
_ACCEPTANCE_TABLE: dict[str, frozenset[str]] = {
    "running":  frozenset({"pause", "stop"}),
    "paused":   frozenset({"resume", "stop"}),
    "ready":    frozenset({"stop"}),
    "created":  frozenset({"stop"}),
}


class ControlCommandQueue:
    """Deterministic bounded FIFO queue for control commands.

    - Sequence begins at 1, increments only for accepted commands.
    - No wall-clock ordering, no priority reordering, no background worker.
    - Queue-full and wrong-run commands are rejected immediately.
    """

    def __init__(self, capacity: int = 1024) -> None:
        if isinstance(capacity, bool):
            raise ControlCommandQueueError("capacity must be int, not bool")
        if not isinstance(capacity, int) or capacity <= 0:
            raise ControlCommandQueueError(
                f"capacity must be int > 0, got {capacity!r}"
            )
        self._capacity = capacity
        self._deque: deque[RunControlCommand] = deque()
        self._next_sequence: int = 1

    # ----------------------------------------------------------------
    # Read-only
    # ----------------------------------------------------------------

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return len(self._deque)

    @property
    def is_empty(self) -> bool:
        return len(self._deque) == 0

    @property
    def queued_commands(self) -> tuple[RunControlCommand, ...]:
        """Return detached immutable tuple of queued commands (FIFO order)."""
        return tuple(self._deque)

    # ----------------------------------------------------------------
    # Submission
    # ----------------------------------------------------------------

    def try_accept(
        self,
        command: RunControlCommand,
        *,
        engine_status: str,
        engine_run_id: str,
    ) -> ControlCommandResult:
        """Validate and accept (or reject) a control command.

        Returns an *accepted* result (with assigned sequence) or a *rejected*
        result (with ``command_sequence=None``).

        Accepted commands are appended to the queue.
        Rejected commands are never queued.

        Acceptance does NOT mutate engine state or ``snapshot_sequence``.
        """
        if not isinstance(command, RunControlCommand):
            raise ControlCommandQueueError(
                f"command must be RunControlCommand, got {type(command).__name__}"
            )

        # --- Run ID mismatch ---
        if command.run_id != engine_run_id:
            return ControlCommandResult(
                command_id=command.command_id,
                command_sequence=None,
                command_type=command.command_type.value,
                status="rejected",
                snapshot_sequence=None,
                rejection_code="run_id_mismatch",
                rejection_detail=(
                    f"Command run_id {command.run_id!r} does not match "
                    f"engine run_id {engine_run_id!r}"
                ),
            )

        # --- Queue full ---
        if len(self._deque) >= self._capacity:
            return ControlCommandResult(
                command_id=command.command_id,
                command_sequence=None,
                command_type=command.command_type.value,
                status="rejected",
                snapshot_sequence=None,
                rejection_code="command_queue_full",
                rejection_detail=(
                    f"Queue at capacity {self._capacity}"
                ),
            )

        # --- Acceptance policy ---
        allowed = _ACCEPTANCE_TABLE.get(engine_status, frozenset())
        if command.command_type.value not in allowed:
            return ControlCommandResult(
                command_id=command.command_id,
                command_sequence=None,
                command_type=command.command_type.value,
                status="rejected",
                snapshot_sequence=None,
                rejection_code="invalid_for_status",
                rejection_detail=(
                    f"Command {command.command_type.value!r} not allowed "
                    f"when engine status is {engine_status!r}"
                ),
            )

        # --- Accept ---
        seq = self._next_sequence
        self._next_sequence += 1

        accepted = RunControlCommand(
            command_id=command.command_id,
            run_id=command.run_id,
            command_type=command.command_type,
            reason=command.reason,
            command_sequence=seq,
        )
        self._deque.append(accepted)

        return ControlCommandResult(
            command_id=command.command_id,
            command_sequence=seq,
            command_type=command.command_type.value,
            status="accepted",
            snapshot_sequence=None,
            rejection_code=None,
            rejection_detail=None,
        )

    # ----------------------------------------------------------------
    # Drain (safe-point consumption)
    # ----------------------------------------------------------------

    def pop_all(self) -> tuple[RunControlCommand, ...]:
        """Remove and return all queued commands in FIFO order, then clear."""
        commands = tuple(self._deque)
        self._deque.clear()
        return commands

    def drain_and_reject(
        self,
        reason_code: str,
        reason_detail: str,
    ) -> tuple[ControlCommandResult, ...]:
        """Drain all queued commands, returning a rejected result for each."""
        results: list[ControlCommandResult] = []
        while self._deque:
            cmd = self._deque.popleft()
            results.append(ControlCommandResult(
                command_id=cmd.command_id,
                command_sequence=cmd.command_sequence,
                command_type=cmd.command_type.value,
                status="rejected",
                snapshot_sequence=None,
                rejection_code=reason_code,
                rejection_detail=reason_detail,
            ))
        return tuple(results)
