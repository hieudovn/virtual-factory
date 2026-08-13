"""OPS-02 — OperationExecution runtime state machine.

Design authority: docs/design/OPS-01_OPERATION_EXECUTION_CONTRACT.md
Schema: .ai-harness/schemas/operation-execution.schema.json

One OperationExecution per (station, WIP) describes the execution state of the
operation at that station. It is orthogonal to:
  - physical position (`positions[]`)
  - quality status
  - exception case
  - WIP identity
  - line/conveyor state

Only the legal transitions defined by OPS-01 are allowed; anything else fails
closed (InvalidTransitionError).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
    StationContract,
)


class OperationState(str, enum.Enum):
    ARRIVED = "ARRIVED"
    READY = "READY"
    WORKING = "WORKING"
    AWAITING_COMPLETION = "AWAITING_COMPLETION"
    AWAITING_DECISION = "AWAITING_DECISION"
    COMPLETED = "COMPLETED"
    HELD = "HELD"
    FAILED = "FAILED"
    EXCEPTION_PENDING = "EXCEPTION_PENDING"
    ELIGIBLE_TO_INDEX = "ELIGIBLE_TO_INDEX"


class OperationResult(str, enum.Enum):
    """Normalized result of a successful completion (OPS-01 §7 model A)."""

    DONE = "DONE"
    CONFIRMED = "CONFIRMED"
    JOIN_COMPLETE = "JOIN_COMPLETE"
    TEST_COMPLETE = "TEST_COMPLETE"
    INSPECTION_COMPLETE = "INSPECTION_COMPLETE"
    RELEASED = "RELEASED"


# Legal transitions (OPS-01 §4 — Legal transition table).
# HELD / FAILED / EXCEPTION_PENDING are NEVER eligible.
_LEGAL_TRANSITIONS: dict[OperationState, set[OperationState]] = {
    OperationState.ARRIVED: {OperationState.READY},
    OperationState.READY: {OperationState.WORKING},
    OperationState.WORKING: {
        OperationState.AWAITING_COMPLETION,
        OperationState.AWAITING_DECISION,
    },
    OperationState.AWAITING_COMPLETION: {OperationState.COMPLETED},
    OperationState.AWAITING_DECISION: {
        OperationState.COMPLETED,
        OperationState.FAILED,
    },
    OperationState.COMPLETED: {
        OperationState.ELIGIBLE_TO_INDEX,
        OperationState.HELD,  # post-completion exception (exception capability only)
    },
    OperationState.FAILED: {
        OperationState.AWAITING_DECISION,  # new attempt (attempt < max_attempts)
        # exhausted attempts → terminal (FAILED + FAILED_FINAL): NO transition.
    },
    OperationState.HELD: {OperationState.AWAITING_DECISION},  # explicit recovery
    OperationState.EXCEPTION_PENDING: {
        OperationState.READY,
        OperationState.WORKING,
        OperationState.COMPLETED,
    },
    OperationState.ELIGIBLE_TO_INDEX: set(),  # terminal for this operation
}


class InvalidTransitionError(ValueError):
    """Raised when an operation transition is not legal."""


@dataclass(slots=True)
class OperationExecution:
    """Runtime state for one operation execution at a station."""

    execution_id: str
    station_id: str
    wip_id: str
    state: OperationState = OperationState.ARRIVED
    started_at_sim_s: Optional[float] = None
    completed_at_sim_s: Optional[float] = None
    work_duration_s: float = 0.0
    completion_mode: CompletionMode = CompletionMode.AUTO
    command: Optional[StationCommand] = None
    inputs: dict = field(default_factory=dict)
    checklist: list[str] = field(default_factory=list)
    measurements: list[dict] = field(default_factory=list)
    operation_result: Optional[OperationResult] = None
    quality_result: Optional[str] = None   # "PASS" | "FAIL" | "NG" | None
    routing_action: Optional[str] = None   # "CONTINUE" | "STAY_AT_STATION" | None
    source: str = "simulated"
    attempt_number: int = 0
    terminal: bool = False                 # FAILED + FAILED_FINAL ⇒ terminal (no recovery)

    @property
    def is_eligible(self) -> bool:
        return self.state == OperationState.ELIGIBLE_TO_INDEX

    def transition(self, new_state: OperationState) -> None:
        """Move to `new_state` only if legal. Fails closed otherwise."""
        if new_state not in _LEGAL_TRANSITIONS.get(self.state, set()):
            raise InvalidTransitionError(
                f"Illegal transition {self.state.value} → {new_state.value} "
                f"for {self.execution_id} (station={self.station_id}, wip={self.wip_id})"
            )
        self.state = new_state

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "station_id": self.station_id,
            "wip_id": self.wip_id,
            "state": self.state.value,
            "started_at_sim_s": self.started_at_sim_s,
            "completed_at_sim_s": self.completed_at_sim_s,
            "work_duration_s": self.work_duration_s,
            "completion_mode": self.completion_mode.value,
            "command": self.command.value if self.command else None,
            "inputs": dict(self.inputs),
            "checklist": list(self.checklist),
            "measurements": list(self.measurements),
            "operation_result": self.operation_result.value if self.operation_result else None,
            "quality_result": self.quality_result,
            "routing_action": self.routing_action,
            "source": self.source,
            "attempt_number": self.attempt_number,
            "terminal": self.terminal,
        }


class OperationRegistry:
    """Registry of active operation executions.

    Keyed by execution_id, with a (station_id, wip_id) → execution_id index for
    O(1) active-operation lookup. Terminal operations are retained for history
    but excluded from `active_operations()`.
    """

    def __init__(self) -> None:
        self._operations: dict[str, OperationExecution] = {}
        self._index: dict[tuple[str, str], str] = {}
        self._seq: int = 0

    def _next_id(self) -> str:
        self._seq += 1
        return f"EXEC-{self._seq:05d}"

    def get(self, execution_id: str) -> Optional[OperationExecution]:
        return self._operations.get(execution_id)

    def active_for(self, station_id: str, wip_id: str) -> Optional[OperationExecution]:
        """Return the active (non-indexed) operation for a station/WIP pair.

        Terminal FAILED operations are returned (they still block the line).
        ELIGIBLE_TO_INDEX operations are treated as inactive (indexed/done).
        """
        eid = self._index.get((station_id, wip_id))
        if eid is None:
            return None
        op = self._operations.get(eid)
        if op is None or op.state == OperationState.ELIGIBLE_TO_INDEX:
            return None
        return op

    def start(
        self,
        station_id: str,
        wip_id: str,
        contract: StationContract,
        completion_mode: CompletionMode,
        sim_time_s: float,
    ) -> OperationExecution:
        """Create and return a new operation in READY state (indexed as active)."""
        op = OperationExecution(
            execution_id=self._next_id(),
            station_id=station_id,
            wip_id=wip_id,
            state=OperationState.ARRIVED,
            started_at_sim_s=sim_time_s,
            work_duration_s=contract.work_duration_s or 0.0,
            completion_mode=completion_mode,
            source="simulated",
        )
        op.transition(OperationState.READY)
        self._operations[op.execution_id] = op
        self._index[(station_id, wip_id)] = op.execution_id
        return op

    def active_operations(self) -> list[OperationExecution]:
        """All non-indexed operations, in creation order.

        Includes blocking terminal FAILED operations; excludes ELIGIBLE_TO_INDEX
        (already completed and indexed).
        """
        return [
            op for op in self._operations.values()
            if op.state != OperationState.ELIGIBLE_TO_INDEX
        ]

    def clear(self) -> None:
        self._operations.clear()
        self._index.clear()
        self._seq = 0
