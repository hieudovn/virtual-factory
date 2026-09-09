"""Generic runtime-session/lifecycle seam (VF-vNEXT-G22).

A small, orchestration-only session facade over the accepted G7
:class:`~virtual_factory.runcontrol.RunLifecycleService`, usable across
executable workspaces (TIPA ASSY and the SH-WTP G21 plant slice).

- A session has explicit Workspace identity, run/attempt identity, and
  scenario/config identity.
- ``reset`` (in-context, same run identity), ``new_attempt`` (fresh run/attempt
  identity), and ``replay`` (fresh run/attempt identity re-pinning the same
  scenario inputs) are distinct and explicit.
- Every fresh attempt/replay rebuilds fresh runtime state from the SAME
  immutable scenario/config inputs — no hidden state carry-over.
- Deterministic: identical scenario/config reproduces an identical step trace.
- The session is lifecycle/orchestration authority only; the domain runtime
  remains the domain-truth owner.

This module is domain-agnostic and must not reference SH-WTP (frozen G7
boundary). Domain-specific session factories live in their own packages.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.runcontrol.lifecycle import (
    RunLifecycleService,
    RunState,
    StepResult,
)

_TERMINAL = frozenset({RunState.STOPPED, RunState.FAILED})


class SessionError(ValueError):
    """Raised when a runtime-session identity/lifecycle invariant is violated."""


@dataclass(frozen=True)
class SessionIdentity:
    """Explicit identity of one runtime session."""

    workspace_id: str
    run_id: str
    scenario_id: str
    state: str


class RuntimeSession:
    """Generic orchestration-only runtime session over one Workspace."""

    def __init__(
        self,
        service: RunLifecycleService,
        workspace_id: str,
        scenario_id: str,
    ) -> None:
        if not isinstance(service, RunLifecycleService):
            raise SessionError(
                f"service must be RunLifecycleService, got {type(service).__name__}"
            )
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise SessionError("workspace_id must be a non-empty str")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise SessionError("scenario_id must be a non-empty str")
        self._service = service
        self._scenario_id = scenario_id
        self._run = service.create_run(workspace_id, scenario_id=scenario_id)
        # Authoritative workspace identity comes from the created run context;
        # any mismatch fails closed (never silently re-key).
        if self._run.context.workspace_id != workspace_id:
            raise SessionError(
                f"workspace identity mismatch: requested {workspace_id!r}, "
                f"run context is {self._run.context.workspace_id!r}"
            )
        self._trace: list[StepResult] = []

    # ── identity ────────────────────────────────────────────────

    @property
    def workspace_id(self) -> str:
        return self._run.context.workspace_id

    @property
    def run_id(self) -> str:
        return self._run.context.run_id

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def state(self) -> RunState:
        return self._run.state

    @property
    def identity(self) -> SessionIdentity:
        return SessionIdentity(
            workspace_id=self.workspace_id,
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            state=self.state.value,
        )

    @property
    def record(self):
        """The current run record (white-box inspection for tests/bridges)."""
        return self._run

    # ── orchestration ───────────────────────────────────────────

    def advance(self) -> StepResult:
        """Advance exactly one authorized boundary (start-then-step)."""
        run_id = self._run.context.run_id
        if self._run.state is RunState.CREATED:
            self._run = self._service.start(run_id)
        result = self._service.step(run_id)
        self._trace.append(result)
        return result

    def reset(self) -> None:
        """In-context reset: same run identity, fresh runtime state."""
        self._service.reset(self._run.context.run_id)
        self._trace = []

    def stop(self) -> None:
        """Stop the current attempt (terminal; history preserved)."""
        self._run = self._service.stop(self._run.context.run_id)

    def new_attempt(self) -> str:
        """Fresh attempt: fresh run identity + fresh runtime state."""
        if self._run.state not in _TERMINAL:
            self.stop()
        self._run = self._service.restart(self._run.context.run_id)
        self._trace = []
        return self._run.context.run_id

    def replay(self) -> str:
        """Deterministic replay: fresh run identity re-pinning the same scenario."""
        if self._run.state not in _TERMINAL:
            self.stop()
        self._run = self._service.replay(self._run.context.run_id)
        self._trace = []
        return self._run.context.run_id

    # ── trace ───────────────────────────────────────────────────

    def trace(self) -> tuple[StepResult, ...]:
        """Deterministic step trace captured so far (immutable view)."""
        return tuple(self._trace)

    def run_all(self, windows: int) -> tuple[StepResult, ...]:
        """Advance ``windows`` boundaries and return the resulting trace."""
        for _ in range(windows):
            self.advance()
        return self.trace()


def build_tipa_session(
    config_path: str,
    scenario_id: str,
    workspace_id: str = "TIPA",
) -> RuntimeSession:
    """Build a TIPA ASSY runtime session (6 sub-lines, one workspace)."""
    from virtual_factory.federation import TipaAssyFederation, build_tipa_workspace
    from virtual_factory.runcontrol import AssyExecutionBridge, RunLifecycleService

    workspace = build_tipa_workspace()
    if workspace.workspace_id != workspace_id:
        raise SessionError(
            f"workspace_id {workspace_id!r} does not match TIPA workspace "
            f"{workspace.workspace_id!r}"
        )

    def bridge_factory():
        federation = TipaAssyFederation(config_path=config_path)
        federation.initialize()
        return AssyExecutionBridge(federation)

    service = RunLifecycleService(workspace, bridge_factory)
    return RuntimeSession(service, workspace_id, scenario_id)
