"""Immutable domain-neutral runtime snapshot.

M2-S03: schema v1.1 — added recent_events, diagnostics.
M2-S04: schema v1.2 — added allowed_actions projection.
Transport-free — no message_sequence, nodes, entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from virtual_factory.discrete.trace import EventTraceEntry, RuntimeDiagnostics


class RuntimeSnapshotError(ValueError):
    """Raised when a RuntimeSnapshot invariant is violated."""


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Immutable projection of ``DiscreteRunState`` for inspection.

    Fields ordered so defaults come last.
    """

    run_id: str
    model_id: str
    model_version: str | None
    scenario_id: str | None
    scenario_version: str | None
    status: str
    simulation_time_s: float
    stop_reason: str | None
    failure_error: str | None
    processed_events: int
    pending_events: int
    last_event_id: str | None
    snapshot_sequence: int

    # Preserve legacy positional location (field index 13)
    schema_version: str = "1.2.0"

    # M2-S03 fields appended after legacy contract
    recent_events: tuple[EventTraceEntry, ...] = ()
    diagnostics: RuntimeDiagnostics = field(default_factory=RuntimeDiagnostics)

    # M2-S04: controller-projected allowed actions
    allowed_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # run_id
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise RuntimeSnapshotError("run_id must be non-empty str")

        # model_id
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise RuntimeSnapshotError("model_id must be non-empty str")

        # status — must be a valid RunStatus value
        from virtual_factory.discrete.state import RunStatus
        valid_statuses = {s.value for s in RunStatus}
        if self.status not in valid_statuses:
            raise RuntimeSnapshotError(
                f"status must be one of {sorted(valid_statuses)}, got {self.status!r}"
            )

        # simulation_time_s
        import math
        if isinstance(self.simulation_time_s, bool):
            raise RuntimeSnapshotError("simulation_time_s must be numeric, not bool")
        if not isinstance(self.simulation_time_s, (int, float)):
            raise RuntimeSnapshotError("simulation_time_s must be numeric")
        if math.isnan(self.simulation_time_s) or math.isinf(self.simulation_time_s):
            raise RuntimeSnapshotError("simulation_time_s must be finite")
        if self.simulation_time_s < 0.0:
            raise RuntimeSnapshotError("simulation_time_s must be >= 0")

        # counters
        for name in ["processed_events", "pending_events", "snapshot_sequence"]:
            val = getattr(self, name)
            if isinstance(val, bool):
                raise RuntimeSnapshotError(f"{name} must be int, not bool")
            if not isinstance(val, int) or val < 0:
                raise RuntimeSnapshotError(f"{name} must be int >= 0")

        # recent_events
        if not isinstance(self.recent_events, tuple):
            raise RuntimeSnapshotError("recent_events must be tuple")
        for i, e in enumerate(self.recent_events):
            if not isinstance(e, EventTraceEntry):
                raise RuntimeSnapshotError(
                    f"recent_events[{i}] must be EventTraceEntry, got {type(e).__name__}"
                )

        # diagnostics
        if not isinstance(self.diagnostics, RuntimeDiagnostics):
            raise RuntimeSnapshotError(
                f"diagnostics must be RuntimeDiagnostics, got {type(self.diagnostics).__name__}"
            )

        # schema_version
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise RuntimeSnapshotError("schema_version must be non-empty str")

        # allowed_actions (M2-S04)
        if not isinstance(self.allowed_actions, tuple):
            raise RuntimeSnapshotError("allowed_actions must be tuple")
        for i, action in enumerate(self.allowed_actions):
            if not isinstance(action, str):
                raise RuntimeSnapshotError(
                    f"allowed_actions[{i}] must be str, got {type(action).__name__}"
                )
