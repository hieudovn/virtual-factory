"""G7-C02 — Continuous execution bridge (RuntimeService seam, root-only).

Binds the accepted continuous ``RuntimeService`` runtime-control seam
(``step_once`` / ``reset`` / engine time) into the mechanism-neutral
:class:`ExecutionBridge` protocol WITHOUT rewriting the continuous engine and
WITHOUT inventing a G1 scope hierarchy.

Continuous is root-only (Issue #52 / SA C02): the single participant is the
workspace root engine itself. There is no authoritative multi-level G1
sub-structure for the continuous runtime, so no nested scopes are fabricated.

Attempt-bound execution (C01) is preserved: constructing a
``ContinuousExecutionBridge`` reinitializes the shared ``RuntimeService`` to its
accepted initial baseline (t=0), so a restart/replay/new attempt always starts
from fresh execution state while reset stays in-context on the same run/attempt
(the same ``RuntimeService`` object is never replaced).
"""

from __future__ import annotations

from virtual_factory.runcontrol.lifecycle import StepResult
from virtual_factory.workspace import StructuralPath, Workspace

CONTINUOUS_WORKSPACE_ID = "continuous"


def build_continuous_workspace(
    *,
    workspace_id: str = CONTINUOUS_WORKSPACE_ID,
    display_name: str | None = None,
    description: str | None = None,
) -> Workspace:
    """Build the root-only continuous Workspace (no invented scopes).

    ``workspace_id`` is the stable canonical structural identity of the
    continuous workspace authority. The loaded plant config's ``plant_id`` is a
    config/display fact (never promoted into a structural scope).
    """
    return Workspace(
        workspace_id=workspace_id,
        path=StructuralPath.workspace_root(workspace_id),
        display_name=display_name or "Continuous Workspace",
        description=description
        or "Root-only continuous-process workspace authority; no authoritative "
        "G1 scope sub-structure.",
        top_level_scopes=(),
    )


class ContinuousExecutionBridge:
    """Execution bridge over one continuous ``RuntimeService``.

    - ``natural_next_boundary`` = engine time + dt_s (the engine's fixed-step
      scan cadence — the only truthful continuous boundary).
    - ``advance`` = one ``RuntimeService.step_once()`` (the accepted seam).
    - ``reset`` = ``RuntimeService.reset()`` (in-context reinitialize to t=0).
    - Root-only: the selected ``scope_ids`` (empty for a workspace target) map
      to the single root engine participant; no fabricated sub-scopes.
    """

    def __init__(self, runtime, *, participant_id: str) -> None:
        self._runtime = runtime
        self._participant_id = participant_id
        self._window_seq = 0
        # Attempt-bound freshness: each new run attempt gets a fresh execution
        # context at the accepted initial baseline (t=0) on the SAME
        # RuntimeService object. No engine rewrite; no second runtime instance.
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
        # In-context reinitialize to t=0 (same RuntimeService object). This is
        # the accepted continuous reset contract, never a run-identity rebuild.
        self._runtime.reset()
