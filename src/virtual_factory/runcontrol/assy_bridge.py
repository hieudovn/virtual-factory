"""G7-C — ASSY execution bridge (TipaAssyFederation + AssySubLineAdapter + G4).

Reuses the accepted G5 federation + G4 Coordinator seams to advance ASSY
sub-lines at LEGITIMATE natural coordination boundaries only. No AssyLineRuntime
rewrite, no demo-policy promotion, no new synchronization rule, no fractional
dwell/index.

A "step" for a set of ASSY sub-lines advances to the next natural common
boundary (current time + nominal dwell). If a selected sub-line cannot reach the
target exactly through its natural dwell/index cadence, the G4 coordinator fails
closed (the lifecycle service then marks the run failed).
"""

from __future__ import annotations

from virtual_factory.federation import TipaAssyFederation
from virtual_factory.runcontrol.lifecycle import StepResult


class AssyExecutionBridge:
    """Execution bridge over one ``TipaAssyFederation``."""

    def __init__(self, federation: TipaAssyFederation) -> None:
        if not isinstance(federation, TipaAssyFederation):
            raise TypeError(
                f"federation must be TipaAssyFederation, got {type(federation).__name__}"
            )
        self._federation = federation
        self._window_seq = 0

    @property
    def supports_reset(self) -> bool:
        # AssyLineRuntime exposes an accepted public in-context reset().
        return True

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        ids = tuple(scope_ids)
        if not ids:
            raise ValueError("no executable sub-lines to advance")
        nominal = (
            self._federation.get(ids[0]).config.conveyor.nominal_line_dwell_time_s
        )
        current = max(
            self._federation.get(sid).runtime.simulation_time_s for sid in ids
        )
        return current + nominal

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        ids = tuple(scope_ids)
        self._window_seq += 1
        coordinator = self._federation.make_coordinator()
        outcome = self._federation.run_window(
            coordinator,
            target_time_s,
            sub_line_ids=ids,
            window_id=window_id,
        )
        return StepResult(
            status=outcome.status,
            target_time_s=outcome.target_time_s,
            participants=outcome.participants,
            committed=outcome.committed,
            failure=outcome.failure,
        )

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        # Capability-scoped in-context reset via the existing public runtime
        # contract (same object, time back to 0). Never rebuilds run identity.
        for sid in tuple(scope_ids):
            self._federation.get(sid).runtime.reset()
