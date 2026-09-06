"""G7-C03 — Continuous execution bridge (RuntimeService seam, PROCESS scope).

Frozen architecture decision (SA ``5557511518``): the continuous Workspace is a
plant/site isolation boundary and does NOT itself own executable runtime
semantics. Runtime ownership lives below the Workspace on one executable
Simulation Scope:

    continuous Workspace -> PROCESS Scope (executable)   path ``continuous/PROCESS``

This is a bounded generic execution-boundary wrapper around the already-existing
single continuous process runtime — NOT an invented plant/unit/area/equipment
topology and NOT a rewrite of the continuous engine.

The bridge executes on behalf of the effective executable Scope
(``continuous/PROCESS``); the Workspace root is never a participant.
"""

from __future__ import annotations

from virtual_factory.runcontrol.lifecycle import StepResult
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

CONTINUOUS_WORKSPACE_ID = "continuous"
PROCESS_SCOPE_ID = "PROCESS"


def process_scope_path() -> StructuralPath:
    """Canonical structural path of the single continuous executable Scope."""
    return StructuralPath((CONTINUOUS_WORKSPACE_ID, PROCESS_SCOPE_ID))


def build_continuous_workspace(
    *,
    display_name: str | None = None,
    description: str | None = None,
) -> Workspace:
    """Build the continuous Workspace with exactly ONE executable child Scope.

    - ``continuous`` (Workspace root) is orchestration-only, non-executable.
    - ``continuous/PROCESS`` is the single executable Scope.
    - No unit/area/equipment/process-section decomposition is introduced.
    """
    specs = [
        ScopeSpec(
            PROCESS_SCOPE_ID,
            ScopeMode.EXECUTABLE_CAPABLE,
            display_name="Continuous Process",
        )
    ]
    return build_workspace(
        CONTINUOUS_WORKSPACE_ID,
        specs,
        display_name=display_name or "Continuous Workspace",
        description=description
        or "Continuous process workspace authority: Workspace root is "
        "non-executable; single executable PROCESS scope at "
        "continuous/PROCESS.",
    )


class ContinuousExecutionBridge:
    """Execution bridge over one continuous ``RuntimeService`` attempt.

    - ``natural_next_boundary`` = engine time + dt_s (the engine's fixed-step
      scan cadence — the only truthful continuous boundary).
    - ``advance`` = one ``RuntimeService.step_once()`` (the accepted seam).
    - ``reset`` = ``RuntimeService.reset()`` (in-context reinitialize to t=0).
    - The participant identity is path-qualified ``continuous/PROCESS`` (the
      effective executable Scope), never the Workspace root.
    """

    def __init__(self, runtime, *, participant_id: str) -> None:
        self._runtime = runtime
        self._participant_id = participant_id
        self._window_seq = 0
        # Attempt-bound baseline: reinitialize this attempt's OWN RuntimeService
        # to its accepted initial state (t=0). Each attempt owns a fresh
        # RuntimeService; this call never touches another attempt's runtime.
        self._runtime.reset()

    @property
    def supports_reset(self) -> bool:
        # RuntimeService.reset() is the accepted public in-context reset.
        return True

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        # Continuous has a single fixed-step cadence; the next natural boundary
        # is exactly the next scan tick (no invented boundaries).
        return self._runtime.engine.time_manager.now() + self._runtime.engine.dt_s

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        self._window_seq += 1
        try:
            self._runtime.step_once()
        except Exception as exc:  # noqa: BLE001 - fail closed, no hidden retry
            return StepResult(
                status="failed",
                target_time_s=target_time_s,
                participants=(),
                committed=(),
                failure=str(exc),
            )
        return StepResult(
            status="completed",
            target_time_s=self._runtime.engine.time_manager.now(),
            participants=(self._participant_id,),
            committed=(self._participant_id,),
            failure=None,
        )

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        # In-context reinitialize to t=0 (same RuntimeService object for this
        # attempt). This is the accepted continuous reset contract, never a
        # run-identity or attempt rebuild.
        self._runtime.reset()
