"""Federated ASSY host / composition (G5-C).

Smallest production federation host that:

- creates/owns the TIPA :class:`Workspace` structure (G5-A);
- creates six isolated ``AssyLineRuntime`` contexts directly from the accepted
  ASSY config/identity sources, reproducing the PROVEN config-isolation
  mechanics only (per-sub-line deep-copied config + stable ordinal random-seed
  isolation) — it does NOT instantiate, own or reuse the demo presentation
  composition (``AssyDemoComposition``) or any demo-only orchestration policy
  (no ``DemoScenario``, no scenario-targeting, no continuous-feed policy, no
  selected-sub-line/demo-step state, no implicit seeded upstream inventory);
- binds each context to its matching executable G1 scope (structural identity
  authority is the G1 :class:`StructuralPath`);
- exposes G4-compliant :class:`AssySubLineAdapter` participants so supported
  ASSY sub-lines can be registered with a G4 :class:`Coordinator` where a valid
  shared coordination boundary is explicitly available;
- never makes the ``ASSY`` container itself executable;
- never replaces domain truth with coordinator state (the runtime remains the
  single source of ASSY truth);
- never promotes demo feed/scenario policy to production/plant truth.

Seeding upstream WIP is NOT implicit production policy: runtimes are created at
time 0 with no WIP. Tests/tools that need seeded upstream state prepare it
explicitly (or via a clearly-named demo/test preparation helper).

VF-vNEXT-R1 — prepared production mode (additive, opt-in):
``initialize(run_profile=...)`` prepares each of the six isolated sub-lines from
an EXPLICIT immutable :class:`AssyRunProfile` (per-line effective scenario +
quality/config transforms before runtime construction, initial SSO2/RSO2
inventory, deterministic carrier/feed sequencing and continuous-feed settings),
and binds each sub-line's own run state to its G4 adapter. The profile is run
INPUT only: the host still owns no simulation truth, and the plain
``initialize()`` contract (six unseeded runtimes, no demo policy) is unchanged.

The host is a *federation/migration* seam, NOT a plant-synchronization policy.
It does not force sub-line clocks to align; ``run_window`` fails closed for any
sub-line that cannot reach the requested boundary through its natural ASSY
advancement.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Iterable

from virtual_factory.assembly.assy_run_profile import (
    AssyRunProfile,
    AssySubLineRunState,
    apply_scenario_quality_overrides,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.sub_line_identity import (
    AssyProductionLineIdentity,
    AssySubLineIdentity,
    load_assy_demo_identity_from_yaml,
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

    R1: ``run_state`` (when a run profile is applied) is that sub-line's OWN
    mutable feed/sequencing state and ``effective_scenario`` is the accepted
    scenario value actually applied to its config.
    """

    sub_line_id: str
    identity: AssySubLineIdentity
    path: StructuralPath
    config: AssyLineConfig
    runtime: AssyLineRuntime
    adapter: AssySubLineAdapter
    run_state: AssySubLineRunState | None = None
    effective_scenario: str = ""


class FederationError(ValueError):
    """Raised when the TIPA ASSY federation cannot be built/run honestly."""


class TipaAssyFederation:
    """Host that owns the TIPA Workspace and six isolated ASSY sub-line
    runtimes, each bound to its executable G1 scope.

    Production construction takes only a config path. It accepts NO
    ``DemoScenario`` and owns no demo presentation composition, scenario
    targeting, continuous-feed policy, selected-sub-line/demo-step state, or
    seeded upstream inventory.
    """

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.workspace: Workspace | None = None
        self.identity: AssyProductionLineIdentity | None = None
        self.sub_lines: dict[str, FederatedAssySubLine] = {}
        # R1: the immutable run profile applied to this federation (if any).
        self.run_profile: AssyRunProfile | None = None

    # ── Initialization ────────────────────────────────────────

    def initialize(self, run_profile: AssyRunProfile | None = None) -> "TipaAssyFederation":
        """Build the TIPA Workspace and six isolated, bound sub-line contexts.

        Builds each ``AssyLineRuntime`` DIRECTLY from the accepted ASSY config/
        identity sources (``load_assy_config_from_yaml`` /
        ``load_assy_demo_identity_from_yaml``), reproducing the proven
        isolation mechanics only: per-sub-line deep-copied config + stable
        ordinal random-seed isolation. It never constructs ``AssyDemoComposition``
        and applies no implicit demo-only policy. Runtimes are created at time 0
        with no seeded WIP (upstream seeding is explicit, never implicit policy).

        R1: when an explicit immutable ``run_profile`` is supplied, each
        sub-line is PREPARED for accepted production: its effective scenario is
        resolved per line, the accepted scenario quality/config transforms are
        applied to its own config BEFORE runtime construction, its own run state
        seeds the deterministic initial SSO2/RSO2 inventory and first entry, and
        the G4 adapter drives the accepted production step for that line.
        """
        base_config = load_assy_config_from_yaml(self.config_path)
        pline = load_assy_demo_identity_from_yaml(self.config_path)
        self.workspace = build_tipa_workspace()
        self.identity = pline
        self.run_profile = run_profile
        self.sub_lines = {}

        for ordinal, sub_line_id in enumerate(SUB_LINE_IDS):
            sl_identity = pline.get_sub_line(sub_line_id)
            if sl_identity is None:
                raise FederationError(
                    f"identity source has no sub-line {sub_line_id!r}"
                )
            path = sub_line_path(sub_line_id)
            # G1 authority: the bound scope must resolve and be executable.
            scope = self.workspace.resolve_scope(path)
            if not scope.is_executable_capable:
                raise FederationError(
                    f"scope {path.as_string()!r} is not executable-capable"
                )
            # Proven isolation mechanics only: deep-copied config + stable
            # ordinal seed (base seed + canonical ordinal), never shared.
            ctx_config = copy.deepcopy(base_config)
            ctx_config.random_seed = base_config.random_seed + ordinal
            effective_scenario = ""
            if run_profile is not None:
                # Effective per-line scenario + accepted transforms are applied
                # to THIS line's config only, before the runtime exists.
                effective_scenario = run_profile.effective_scenario_for(sub_line_id)
                apply_scenario_quality_overrides(ctx_config, effective_scenario)
            runtime = AssyLineRuntime(config=ctx_config)
            run_state: AssySubLineRunState | None = None
            if run_profile is not None:
                run_state = AssySubLineRunState()
                run_state.prepare(runtime, run_profile)
            adapter = AssySubLineAdapter(
                scope_path=path,
                runtime=runtime,
                run_state=run_state,
                run_profile=(run_profile if run_state is not None else None),
            )
            self.sub_lines[sub_line_id] = FederatedAssySubLine(
                sub_line_id=sub_line_id,
                identity=sl_identity,
                path=path,
                config=ctx_config,
                runtime=runtime,
                adapter=adapter,
                run_state=run_state,
                effective_scenario=effective_scenario,
            )
        return self

    # ── Accessors ─────────────────────────────────────────────

    @property
    def sub_line_ids(self) -> tuple[str, ...]:
        return SUB_LINE_IDS

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

    # ── R1: prepared production accessors ─────────────────────

    def run_state(self, sub_line_id: str) -> AssySubLineRunState | None:
        """The sub-line's OWN run state (or ``None`` without a run profile)."""
        return self.get(sub_line_id).run_state

    def effective_scenario(self, sub_line_id: str) -> str:
        """The accepted scenario value actually applied to that sub-line."""
        return self.get(sub_line_id).effective_scenario

    def reset_sub_line(self, sub_line_id: str) -> None:
        """In-context domain reset of ONE sub-line (profile-consistent).

        Same runtime object, time back to 0. When an immutable run profile is
        applied, the line's own run state is re-prepared so the resulting state
        is identical to a freshly prepared run (no hidden state carry-over).
        """
        sl = self.get(sub_line_id)
        sl.runtime.reset()
        if sl.run_state is not None and self.run_profile is not None:
            sl.run_state.prepare(sl.runtime, self.run_profile)

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

    def standalone_replica(self, sub_line_id: str) -> AssyLineRuntime:
        """Build a fresh, identical runtime for one sub-line using its isolated
        config (deep-copied, same seed) — used to prove standalone/federated
        semantic parity under EXPLICIT equivalent initial conditions.

        Returns an UNSEEDED runtime at time 0; the caller applies the same
        explicit preparation it applied to the federated runtime. No demo
        policy is applied here.
        """
        fed = self.get(sub_line_id)
        config = copy.deepcopy(fed.config)
        return AssyLineRuntime(config=config)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"TipaAssyFederation(workspace={self.workspace.workspace_id if self.workspace else None!r}, "
            f"sub_lines={sorted(self.sub_lines)})"
        )
