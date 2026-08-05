"""Discrete simulation run status and runtime state.

M2-S01: domain-neutral — no assembly nodes, entities, routes, or resources.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class RunStatus(str, enum.Enum):
    """Engine lifecycle status."""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"    # reserved for M2-S04
    PAUSED = "paused"      # reserved for M2-S04
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(slots=True)
class DiscreteRunState:
    """Mutable engine-owned lifecycle state.

    Not exposed publicly — use ``RuntimeSnapshot`` for inspection.
    """

    run_id: str
    status: RunStatus = RunStatus.CREATED
    simulation_time_s: float = 0.0
    processed_events: int = 0
    pending_events: int = 0
    last_event_id: str | None = None
    stop_reason: str | None = None
    failure_error: str | None = None
    snapshot_sequence: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)
