"""WIP identity and state model for assembly domain.

M3-S01: Deterministic WipId, mutable WipState with location and lifecycle status.
Lightweight — no ERP/MES master data.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class WipStatus(str, enum.Enum):
    """Lifecycle status of a work item."""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    INSPECTING = "inspecting"
    REWORK = "rework"
    COMPLETED = "completed"
    SCRAPPED = "scrapped"


class WipError(ValueError):
    """Raised when a WIP invariant is violated."""


@dataclass(frozen=True, slots=True)
class WipId:
    """Immutable, deterministic work-item identity.

    Two WipId instances with the same ``id`` are semantically equivalent.
    """

    id: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise WipError("WipId.id must be non-empty str")

    def __str__(self) -> str:
        return self.id


@dataclass(slots=True)
class WipState:
    """Mutable runtime state for a single work item.

    Tracks current location, lifecycle status, and progression.
    Explicitly mutable to support handler-driven state transitions.
    """

    wip_id: WipId
    location: str = ""           # current primitive/station ID
    status: WipStatus = WipStatus.CREATED
    step_count: int = 0          # number of processing steps completed

    def __post_init__(self) -> None:
        if not isinstance(self.wip_id, WipId):
            raise WipError(f"wip_id must be WipId, got {type(self.wip_id).__name__}")
        if not isinstance(self.location, str):
            raise WipError(f"location must be str, got {type(self.location).__name__}")
        if not isinstance(self.status, WipStatus):
            raise WipError(f"status must be WipStatus, got {type(self.status).__name__}")
        if isinstance(self.step_count, bool):
            raise WipError("step_count must be int, not bool")
        if not isinstance(self.step_count, int) or self.step_count < 0:
            raise WipError(f"step_count must be int >= 0, got {self.step_count!r}")

    def advance(self, new_location: str, new_status: WipStatus) -> None:
        """Transition to a new location and status, incrementing step count."""
        if self.status in (WipStatus.COMPLETED, WipStatus.SCRAPPED):
            raise WipError(
                f"Cannot advance from terminal status {self.status.value}"
            )
        self.location = new_location
        self.status = new_status
        self.step_count += 1
