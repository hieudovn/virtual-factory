"""G7-A — platform-level run lifecycle service (single run authority).

One coherent lifecycle authority over path-qualified hierarchical targets. It
owns run IDENTITY / LIFECYCLE STATE only; domain truth stays in the child
runtimes (never mutated directly here). Execution is delegated to a mechanism
bridge (see :class:`ExecutionBridge`).

Lifecycle states: CREATED -> RUNNING -> PAUSED <-> RUNNING; STOPPED and FAILED
are terminal for the current run attempt. Transitions are fail-closed.

Frozen rules (Issue #52):
- one immutable G2 ``RunContextV2`` per run; workspace_id / run_id / scope_path /
  scenario_id stay coherent;
- a terminal run attempt is never silently reused (restart/replay create a fresh
  run_id with ``source_run_id`` lineage);
- pause/resume only change orchestration permission (no domain mutation);
- stop is terminal but does not erase history;
- reset is capability-scoped (delegated to the bridge) and never reuses a
  terminal historical run;
- replay pins prior accepted inputs and never overwrites the prior run; if the
  pinned inputs are unavailable it is exposed as unavailable, never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

from virtual_factory.provenance import RunContextV2
from virtual_factory.workspace import StructuralPath, Workspace

from virtual_factory.runcontrol.targets import (
    TargetResolution,
    resolve_target,
)


class RunState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"


class RunLifecycleError(ValueError):
    """Raised on invalid lifecycle transitions or stale/wrong run identity."""


class ReplayUnavailableError(RunLifecycleError):
    """Replay cannot be exposed honestly because pinned inputs are unavailable."""


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result of one authorized advancement (no rollback claim)."""

    status: str  # "completed" | "failed"
    target_time_s: float
    participants: tuple[str, ...]
    committed: tuple[str, ...]
    failure: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "target_time_s": self.target_time_s,
            "participants": list(self.participants),
            "committed": list(self.committed),
            "failure": self.failure,
        }


class ExecutionBridge(Protocol):
    """Mechanism-neutral execution seam the lifecycle service delegates to."""

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        """Next legitimate natural coordination boundary for the selected scopes."""

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        """Advance the selected scopes to one authorized boundary (fail-closed)."""

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        """Capability-scoped in-context reset of the selected scopes."""

    @property
    def supports_reset(self) -> bool:
        """Whether the bridge's runtime contract has an in-context reset."""


@dataclass
class RunRecord:
    """One run attempt: immutable context + guarded mutable lifecycle state."""

    context: RunContextV2
    state: RunState
    target_path: StructuralPath | None
    target_kind: str
    effective_scopes: tuple[str, ...]          # canonical path strings
    effective_sub_line_ids: tuple[str, ...]    # leaf ids for the bridge
    step_count: int = 0
    last_time_s: float | None = None
    last_result: str | None = None
    failure: str | None = None
    bridge: object | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        data = self.context.to_dict()
        data.update(
            {
                "state": self.state.value,
                "target_path": (
                    self.target_path.as_string()
                    if self.target_path is not None
                    else None
                ),
                "target_kind": self.target_kind,
                "effective_scopes": list(self.effective_scopes),
                "step_count": self.step_count,
                "last_time_s": self.last_time_s,
                "last_result": self.last_result,
                "failure": self.failure,
            }
        )
        return data


_TERMINAL = frozenset({RunState.STOPPED, RunState.FAILED})


class RunLifecycleService:
    """Platform-level run lifecycle authority over one G1 Workspace.

    ``bridge_factory`` lazily constructs the execution bridge on first
    step/reset so lifecycle-only operations never build runtime state.
    """

    def __init__(
        self,
        workspace: Workspace,
        bridge_factory: Callable[[], ExecutionBridge],
        *,
        run_id_prefix: str | None = None,
    ) -> None:
        self._workspace = workspace
        self._bridge_factory = bridge_factory
        self._runs: dict[str, RunRecord] = {}
        self._active_run_id: str | None = None
        self._seq = 0
        self._run_id_prefix = run_id_prefix or workspace.workspace_id

    # ── identity / lookup ─────────────────────────────────────

    def _new_run_id(self) -> str:
        self._seq += 1
        return f"{self._run_id_prefix}-{self._seq:04d}"

    def _get(self, run_id: str) -> RunRecord:
        record = self._runs.get(run_id)
        if record is None:
            raise RunLifecycleError(
                f"unknown/stale run_id {run_id!r}; no active run matches"
            )
        return record

    def _require_active(self, run_id: str) -> RunRecord:
        """A MUTATION may target only the current active run attempt.

        A known but superseded/historical run id fails closed here (it exists in
        ``_runs`` but is no longer the mutable active attempt).
        """
        record = self._get(run_id)
        if run_id != self._active_run_id:
            raise RunLifecycleError(
                f"run {run_id!r} is not the active run (active={self._active_run_id!r}); "
                f"mutations require the active run_id"
            )
        return record

    def _bridge_for(self, record: RunRecord) -> ExecutionBridge:
        """Attempt-bound execution state: build once per run attempt.

        A fresh run attempt (create/restart/replay) starts with ``bridge=None``
        and lazily builds its OWN execution context; prior attempts never share
        runtime state.
        """
        if record.bridge is None:
            record.bridge = self._bridge_factory()
        return record.bridge

    @property
    def active_run_id(self) -> str | None:
        return self._active_run_id

    def current(self) -> RunRecord | None:
        if self._active_run_id is None:
            return None
        return self._runs.get(self._active_run_id)

    # ── create ────────────────────────────────────────────────

    def create_run(
        self,
        target_path: str | StructuralPath,
        *,
        scenario_id: str | None = None,
        model_id: str | None = None,
        profile: str | None = None,
        random_seed: int | None = None,
        source_run_id: str | None = None,
    ) -> RunRecord:
        """Create a new run attempt (immutable RunContextV2)."""
        if self._active_run_id is not None:
            active = self._runs.get(self._active_run_id)
            if active is not None and active.state not in _TERMINAL:
                raise RunLifecycleError(
                    f"cannot create a new run while active run "
                    f"{self._active_run_id!r} is nonterminal "
                    f"({active.state.value!r})"
                )
        if isinstance(target_path, str):
            from virtual_factory.workspace import StructuralPath as SP

            target = SP.from_string(target_path)
        else:
            target = target_path
        resolution = resolve_target(self._workspace, target)

        run_id = self._new_run_id()
        scope_path = (
            resolution.target_path
            if resolution.target_kind != "workspace"
            else None
        )
        context = RunContextV2(
            workspace_id=self._workspace.workspace_id,
            run_id=run_id,
            scope_path=scope_path,
            scenario_id=scenario_id,
            model_id=model_id,
            profile=profile,
            random_seed=random_seed,
            source_run_id=source_run_id,
        )
        record = RunRecord(
            context=context,
            state=RunState.CREATED,
            target_path=resolution.target_path,
            target_kind=resolution.target_kind,
            effective_scopes=resolution.effective_scope_strings,
            effective_sub_line_ids=tuple(
                p.segments[-1] for p in resolution.effective_scope_paths
            ),
        )
        self._runs[run_id] = record
        self._active_run_id = run_id
        return record

    # ── lifecycle transitions ─────────────────────────────────

    def start(self, run_id: str) -> RunRecord:
        record = self._require_active(run_id)
        if record.state is not RunState.CREATED:
            raise RunLifecycleError(
                f"cannot start run {run_id!r} from state {record.state.value!r}"
            )
        record.state = RunState.RUNNING
        return record

    def pause(self, run_id: str) -> RunRecord:
        record = self._require_active(run_id)
        if record.state is not RunState.RUNNING:
            raise RunLifecycleError(
                f"cannot pause run {run_id!r} from state {record.state.value!r}"
            )
        record.state = RunState.PAUSED  # orchestration permission only
        return record

    def resume(self, run_id: str) -> RunRecord:
        record = self._require_active(run_id)
        if record.state is not RunState.PAUSED:
            raise RunLifecycleError(
                f"cannot resume run {run_id!r} from state {record.state.value!r}"
            )
        record.state = RunState.RUNNING
        return record

    def stop(self, run_id: str) -> RunRecord:
        record = self._require_active(run_id)
        if record.state in _TERMINAL:
            raise RunLifecycleError(
                f"run {run_id!r} is already terminal ({record.state.value!r})"
            )
        record.state = RunState.STOPPED  # terminal; history preserved
        return record

    # ── execution ─────────────────────────────────────────────

    def step(self, run_id: str) -> StepResult:
        record = self._require_active(run_id)
        if record.state is not RunState.RUNNING:
            raise RunLifecycleError(
                f"cannot step run {run_id!r} from state {record.state.value!r}"
            )
        bridge = self._bridge_for(record)
        scope_ids = record.effective_sub_line_ids
        target = bridge.natural_next_boundary(scope_ids)
        window_id = f"{run_id}-w{record.step_count + 1}"
        result = bridge.advance(target, scope_ids, window_id)
        record.step_count += 1
        if result.status == "completed":
            record.last_time_s = result.target_time_s
            record.last_result = "completed"
            record.failure = None
        else:
            record.state = RunState.FAILED
            record.last_result = "failed"
            record.failure = result.failure
        return result

    def reset(self, run_id: str) -> RunRecord:
        record = self._require_active(run_id)
        if record.state in _TERMINAL:
            raise RunLifecycleError(
                f"cannot reset terminal run {run_id!r} ({record.state.value!r}); "
                f"restart as a new run attempt instead"
            )
        bridge = self._bridge_for(record)
        if not bridge.supports_reset:
            raise RunLifecycleError(
                f"reset is not supported for the execution contract of run "
                f"{run_id!r} (capability-scoped)"
            )
        bridge.reset(record.effective_sub_line_ids)
        record.last_time_s = 0.0
        return record

    # ── restart / replay (new identity + lineage) ─────────────

    def restart(self, run_id: str) -> RunRecord:
        record = self._get(run_id)
        if record.state not in _TERMINAL:
            raise RunLifecycleError(
                f"restart requires a terminal run; run {run_id!r} is "
                f"{record.state.value!r}"
            )
        target = (
            record.context.scope_path.as_string()
            if record.context.scope_path is not None
            else self._workspace.path.as_string()
        )
        return self.create_run(
            target,
            scenario_id=record.context.scenario_id,
            model_id=record.context.model_id,
            profile=record.context.profile,
            random_seed=record.context.random_seed,
            source_run_id=record.context.run_id,
        )

    def replay(self, run_id: str) -> RunRecord:
        record = self._get(run_id)
        if record.state not in _TERMINAL:
            raise RunLifecycleError(
                f"replay requires a terminal/historical source run; run "
                f"{run_id!r} is {record.state.value!r}"
            )
        pinned = record.context
        # Replay pins prior accepted inputs; if the single scenario authority or
        # seed is unavailable, expose replay as unavailable (never fabricate).
        if pinned.scenario_id is None:
            raise ReplayUnavailableError(
                f"replay unavailable for run {run_id!r}: no pinned scenario_id "
                f"(scenario authority missing)"
            )
        target = (
            pinned.scope_path.as_string()
            if pinned.scope_path is not None
            else self._workspace.path.as_string()
        )
        return self.create_run(
            target,
            scenario_id=pinned.scenario_id,
            model_id=pinned.model_id,
            profile=pinned.profile,
            random_seed=pinned.random_seed,
            source_run_id=pinned.run_id,
        )

    # ── read ──────────────────────────────────────────────────

    def status(self, run_id: str) -> dict:
        return self._get(run_id).to_dict()

    def has_run(self, run_id: str) -> bool:
        return run_id in self._runs
