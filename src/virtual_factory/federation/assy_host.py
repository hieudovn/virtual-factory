"""Federated ASSY host / composition (G5-C).

Smallest production federation host that:

- creates/owns the TIPA :class:`Workspace` structure (G5-A);
- creates six isolated ``AssyLineRuntime`` contexts reusing the EXISTING
  ``AssyDemoComposition`` construction/config-isolation pattern (per-sub-line
  deep-copied config + ordinal random seed + scenario quality normalization) —
  no second simulation engine;
- binds each context to its matching executable G1 scope (structural identity
  authority is the G1 :class:`StructuralPath`);
- exposes G4-compliant :class:`AssySubLineAdapter` participants so supported
  ASSY sub-lines can be registered with a G4 :class:`Coordinator` where a valid
  shared coordination boundary is explicitly available;
- never makes the ``ASSY`` container itself executable;
- never replaces domain truth with coordinator state (the runtime remains the
  single source of ASSY truth).

The host is a *federation/migration* seam, NOT a plant-synchronization policy.
It does not force sub-line clocks to align; ``run_window`` fails closed for any
sub-line that cannot reach the requested boundary through its natural ASSY
advancement.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
)
from virtual_factory.assembly.sub_line_identity import (
    AssyProductionLineIdentity,
    AssySubLineIdentity,
)
from virtual_factory.composition import (
    CompositionGraph,
    CoordinationError,
    Coordinator,
    WindowOutcome,
)
from virtual_factory.federation.assy_participant import AssySubLineAdapter
from virtual_factory.federation.tipa_workspace import (
    PLANT_ID,
    SUB_LINE_IDS,
    build_tipa_workspace,
    sub_line_path,
)
from virtual_factory.workspace import (
    StructuralPath,
    Workspace,
)


@dataclass(frozen=True, slots=True)
class FederatedAssySubLine:
    """One bound ASSY sub-line in the federation.

    ``identity`` is the TIPA demo deployment metadata (label/variant); ``path``
    is the G1 structural path (the runtime structural identity authority).
    Domain truth lives in ``runtime``; ``adapter`` is the G4 seam over it.
    """

    sub_line_id: str
    identity: AssySubLineIdentity
    path: StructuralPath
    config: AssyLineConfig
    runtime: AssyLineRuntime
    adapter: AssySubLineAdapter


class FederationError(ValueError):
    """Raised when the TIPA ASSY federation cannot be built/run honestly."""


class TipaAssyFederation:
    """Host that owns the TIPA Workspace and six isolated ASSY sub-line
    runtimes, each bound to its executable G1 scope."""

    def __init__(
        self,
        config_path: str,
        scenario: DemoScenario = DemoScenario.HAPPY_PATH,
    ) -> None:
        self.config_path = config_path
        self.scenario = scenario
        self._composition: AssyDemoComposition | None = None
        self.workspace: Workspace | None = None
        self.identity: AssyProductionLineIdentity | None = None
        self.sub_lines: dict[str, FederatedAssySubLine] = {}

    # ── Initialization ────────────────────────────────────────

    def initialize(self) -> "TipaAssyFederation":
        """Build the TIPA Workspace and six isolated, bound sub-line contexts.

        Reuses the existing ``AssyDemoComposition`` construction/config-
        isolation pattern (deepcopy + ordinal seed + scenario normalization);
        each context runtime stays the single source of ASSY domain truth.
        """
        composition = AssyDemoComposition(
            config_path=self.config_path,
            scenario=self.scenario,
        )
        composition.initialize()
        self._composition = composition
        self.workspace = build_tipa_workspace()
        self.identity = composition.identity
        self.sub_lines = {}

        for sub_line_id in SUB_LINE_IDS:
            ctx = composition.contexts.get(sub_line_id)
            if ctx is None:
                raise FederationError(
                    f"demo composition did not create context {sub_line_id!r}"
                )
            path = sub_line_path(sub_line_id)
            # G1 authority: the bound scope must resolve and be executable.
            scope = self.workspace.resolve_scope(path)
            if not scope.is_executable_capable:
                raise FederationError(
                    f"scope {path.as_string()!r} is not executable-capable"
                )
            adapter = AssySubLineAdapter(scope_path=path, runtime=ctx.runtime)
            self.sub_lines[sub_line_id] = FederatedAssySubLine(
                sub_line_id=sub_line_id,
                identity=ctx.identity,
                path=path,
                config=ctx.config,
                runtime=ctx.runtime,
                adapter=adapter,
            )
        return self

    # ── Accessors ─────────────────────────────────────────────

    @property
    def sub_line_ids(self) -> tuple[str, ...]:
        return SUB_LINE_IDS

    @property
    def composition(self) -> AssyDemoComposition | None:
        return self._composition

    def get(self, sub_line_id: str) -> FederatedAssySubLine:
        if sub_line_id not in self.sub_lines:
            raise FederationError(
                f"unknown sub-line {sub_line_id!r}; "
                f"valid: {sorted(self.sub_lines)}"
            )
        return self.sub_lines[sub_line_id]

    def runtime(self, sub_line_id: str) -> AssyLineRuntime:
        return self.get(sub_line_id).runtime

    def adapter(self, sub_line_id: str) -> AssySubLineAdapter:
        return self.get(sub_line_id).adapter

    # ── G4 coordinator seam ───────────────────────────────────

    def make_coordinator(self) -> Coordinator:
        """A fresh G4 Coordinator over the TIPA Workspace with an EMPTY
        composition graph (no cross-scope boundary exchange in G5)."""
        if self.workspace is None:
            raise FederationError("federation not initialized")
        return Coordinator(
            self.workspace,
            CompositionGraph(PLANT_ID, bindings=(), ports=()),
        )

    def register(
        self,
        coordinator: Coordinator,
        sub_line_ids: Iterable[str] | None = None,
    ) -> tuple[str, ...]:
        """Register the given (default: all) sub-line adapters on a Coordinator.

        Returns the deterministic registered scope-path order. Fails closed if
        a scope is not executable or already registered (existing G4 rules).
        """
        if self.workspace is None:
            raise FederationError("federation not initialized")
        ids = tuple(sorted(sub_line_ids) if sub_line_ids is not None else SUB_LINE_IDS)
        for sub_line_id in ids:
            coordinator.register(self.get(sub_line_id).adapter)
        return tuple(
            self.get(sub_line_id).path.as_string() for sub_line_id in ids
        )

    def run_window(
        self,
        coordinator: Coordinator,
        target_time_s: float,
        sub_line_ids: Iterable[str] | None = None,
        window_id: str = "w1",
    ) -> WindowOutcome:
        """Register the selected sub-lines and run one shared coordination
        boundary.

        Only succeeds when EVERY selected sub-line reaches the target through
        its natural ASSY advancement (exact landing); otherwise the window fails
        closed and NO new synchronization policy is invented.
        """
        self.register(coordinator, sub_line_ids=sub_line_ids)
        try:
            return coordinator.run_window(window_id, target_time_s)
        except CoordinationError as exc:
            raise FederationError(str(exc)) from exc

    # ── Standalone replica (parity support) ───────────────────

    def standalone_replica(
        self, sub_line_id: str, *, seed_like_demo: bool = True
    ) -> AssyLineRuntime:
        """Build a fresh, identical runtime for one sub-line using its isolated
        config (deep-copied, same seed) — used to prove standalone/federated
        semantic parity. Returns an UNSEEDED runtime at time 0."""
        fed = self.get(sub_line_id)
        config = copy.deepcopy(fed.config)
        return AssyLineRuntime(config=config)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"TipaAssyFederation(workspace={self.workspace.workspace_id if self.workspace else None!r}, "
            f"sub_lines={sorted(self.sub_lines)})"
        )
