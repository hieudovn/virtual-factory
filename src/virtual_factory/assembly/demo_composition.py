"""M6-S04B-I02 — Demo composition layer for multi-context ASSY sub-lines.

Manages six logical ASSY Sub-line execution contexts using the
existing tested AssyLineRuntime.  No second simulation engine.

Architecture:
    AssyDemoComposition
    ├── AssyDemoContext ASSY-SL01 → AssyLineRuntime
    ├── AssyDemoContext ASSY-SL02 → AssyLineRuntime
    ├── ...
    └── AssyDemoContext ASSY-SL06 → AssyLineRuntime

This is a DEMO PRESENTATION composition.  It does NOT assert:
  - physical conveyor independence;
  - independent PLC ownership;
  - real TIPA control cadence.

Single source of simulation truth: AssyLineRuntime only.
"""

from __future__ import annotations

import copy
import enum
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.sub_line_identity import (
    AssySubLineIdentity,
    AssyProductionLineIdentity,
    load_assy_demo_identity_from_yaml,
)
from virtual_factory.assembly.demo_snapshot import (
    AssyDemoSnapshot,
    build_snapshot,
)
from virtual_factory.assembly.assy_run_profile import (
    AssyFeedPolicy,
    AssySubLineRunState,
    DEFAULT_INITIAL_RSO2_INVENTORY,
    DEFAULT_INITIAL_SSO2_INVENTORY,
    SCENARIO_QUALITY_OVERRIDES_BY_VALUE,
    SCENARIO_TARGET_DEFAULTS_BY_VALUE,
    apply_scenario_quality_overrides,
    resolve_scenario_target_id,
    step_prepared_line,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import CompletionMode


# ═══════════════════════════════════════════════════════════
# Scenario (reused from demo_controller for isolation)
# ═══════════════════════════════════════════════════════════

class DemoScenario(str, enum.Enum):
    HAPPY_PATH = "HAPPY_PATH"
    AP06_FAIL_RETEST_PASS = "AP06_FAIL_RETEST_PASS"
    AP08_NG_REINSPECT_PASS = "AP08_NG_REINSPECT_PASS"
    FAILED_FINAL = "FAILED_FINAL"


# R1: the accepted scenario transforms live in ONE shared module; these
# enum-keyed views are derived so legacy callers keep the same semantics.
SCENARIO_QUALITY_OVERRIDES: dict[DemoScenario, dict] = {
    member: SCENARIO_QUALITY_OVERRIDES_BY_VALUE[member.value]
    for member in DemoScenario
}

# Default target sub-line per scenario (demo policy, not plant truth)
SCENARIO_TARGET_DEFAULTS: dict[DemoScenario, str] = {
    member: SCENARIO_TARGET_DEFAULTS_BY_VALUE[member.value]
    for member in DemoScenario
}


def _scenario_value(scenario: "DemoScenario | str") -> str:
    """Accepted scenario value for either the enum or its plain string form.

    ``DemoScenario`` is a ``str`` enum, so callers historically passed either
    form; both stay supported (unchanged accepted API).
    """
    return scenario.value if isinstance(scenario, DemoScenario) else str(scenario)


# ═══════════════════════════════════════════════════════════
# Continuous Feed Policy (DEMO ORCHESTRATION — not plant truth)
# ═══════════════════════════════════════════════════════════

@dataclass
class ContinuousFeedPolicy:
    """Bounded upstream replenishment policy for DEMO orchestration only.

    Replenishes SSO2 upstream inventory and tops up the RSO2 buffer.
    Does NOT modify AssyLineRuntime business semantics.
    Replenished WIPs enter ASSY only through existing introduce_next_sso2().

    R1: the replenishment mechanics are delegated to the SHARED run-state
    helper so the canonical session path and this demo path cannot diverge.
    """

    sso2_target: int = 10
    sso2_low_watermark: int = 3
    rso2_target: int = 6   # DEMO POLICY — not plant truth

    def to_shared(self) -> AssyFeedPolicy:
        """The equivalent shared feed policy (single semantic source)."""
        return AssyFeedPolicy(
            sso2_target=self.sso2_target,
            sso2_low_watermark=self.sso2_low_watermark,
            rso2_target=self.rso2_target,
        )

    def replenish(self, ctx: "AssyDemoContext") -> None:
        """Top up SSO2 feed queue and RSO2 buffer for one context."""
        ctx.run_state.replenish(ctx.runtime, self.to_shared())


# ═══════════════════════════════════════════════════════════
# AssyDemoContext
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyDemoContext:
    """One logical ASSY sub-line execution context for the demo.

    Holds identity, isolated config, runtime, and per-context feed state.
    Does NOT hold projection/UI state.

    R1: the per-context feed/sequencing state is the SHARED
    :class:`AssySubLineRunState` holder (one distinct holder per context) and
    the step driver is the shared production driver.
    """

    identity: AssySubLineIdentity
    config: AssyLineConfig
    runtime: AssyLineRuntime
    effective_scenario: DemoScenario = DemoScenario.HAPPY_PATH

    # Per-context feed/sequencing state (isolated — not shared across contexts)
    run_state: AssySubLineRunState = field(default_factory=AssySubLineRunState)

    # --- Backward-compatible read views over the shared run state ---

    @property
    def carrier_seq(self) -> int:
        return self.run_state.carrier_seq

    @property
    def sso2_idx(self) -> int:
        return self.run_state.sso2_idx

    @property
    def sso2_ids(self) -> list[str]:
        return self.run_state.sso2_ids

    # --- Per-context step helpers ---

    def introduce_next_sso2(self) -> None:
        """Introduce the next SSO2 WIP into this context's ASSY line."""
        self.run_state.introduce_next(self.runtime)

    def step_context(self) -> None:
        """Execute one demo cycle for this context.

        Delegates to the SHARED production driver (reused by the canonical
        vNext session path): on-demand RSO2, execute_dwell, release detection,
        conditional index + next-SSO2 introduction. Feed replenishment stays a
        separate explicit step (see ContinuousFeedPolicy.replenish).
        """
        step_prepared_line(self.runtime, self.run_state)


# ═══════════════════════════════════════════════════════════
# AssyDemoComposition
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyDemoComposition:
    """Manages six ASSY sub-line demo execution contexts.

    Responsibilities:
    - Initialize 6 isolated contexts from config
    - Step all contexts according to demo execution policy
    - Select one context for detailed view
    - Apply scenario targeting (SINGLE_TARGET_EXCEPTION)
    - Maintain demo_step_number (presentation clock)

    Does NOT: build overview projections, expose API, render UI.
    """

    config_path: str
    scenario: DemoScenario = DemoScenario.HAPPY_PATH
    selected_sub_line_id: str = "ASSY-SL01"

    # DEMO orchestration feed policy (not plant truth)
    continuous_feed_enabled: bool = True
    feed_policy: ContinuousFeedPolicy = field(default_factory=ContinuousFeedPolicy)

    # Initialized state
    identity: Optional[AssyProductionLineIdentity] = None
    contexts: dict[str, AssyDemoContext] = field(default_factory=dict)
    demo_step_number: int = 0
    _resolved_target_id: str = ""

    @property
    def target_sub_line_id(self) -> str:
        """The sub-line currently receiving the exception scenario (read-only)."""
        return self._resolved_target_id

    # --- Initialization ---

    def initialize(self) -> None:
        """Load config, create 6 isolated contexts, seed upstream WIPs.

        Safe initialization sequence (per planning C03):
        1. Load base config + identity
        2. For each sub-line: deepcopy → normalize/scenario → runtime → feed
        """
        base_config = load_assy_config_from_yaml(self.config_path)
        self.identity = load_assy_demo_identity_from_yaml(self.config_path)
        self.contexts = {}
        self.demo_step_number = 0

        target_id = self._resolve_target()
        self._resolved_target_id = target_id

        for ordinal, sl_identity in enumerate(self.identity.sub_lines):
            ctx_config = copy.deepcopy(base_config)

            # AUTO-TIME-01B: derive a stable, uncoupled timing seed per
            # sub-line (base seed + stable ordinal). Never rely on hash().
            ctx_config.random_seed = base_config.random_seed + ordinal

            # Determine scenario for this context
            is_target = (sl_identity.sub_line_id == target_id)
            ctx_scenario = self.scenario if is_target else DemoScenario.HAPPY_PATH

            # Apply quality overrides to THIS config only
            self._apply_quality_overrides(ctx_config, ctx_scenario)

            # Create runtime
            runtime = AssyLineRuntime(config=ctx_config)

            # Create context
            ctx = AssyDemoContext(
                identity=sl_identity,
                config=ctx_config,
                runtime=runtime,
                effective_scenario=ctx_scenario,
                run_state=AssySubLineRunState(),
            )

            # Seed upstream WIPs (shared deterministic preparation)
            ctx.run_state.seed_inventories(
                runtime,
                sso2_count=DEFAULT_INITIAL_SSO2_INVENTORY,
                rso2_count=DEFAULT_INITIAL_RSO2_INVENTORY,
            )

            # Introduce first WIP
            ctx.introduce_next_sso2()

            self.contexts[sl_identity.sub_line_id] = ctx

    def _resolve_target(self) -> str:
        """Determine which sub-line gets the exception scenario.

        Scenario-specific default takes priority, identity default as fallback
        (shared resolver — same precedence as the canonical session path).
        """
        identity_default = ""
        if self.identity and self.identity.target_sub_line_for_exception:
            identity_default = self.identity.target_sub_line_for_exception
        return resolve_scenario_target_id(_scenario_value(self.scenario), identity_default)

    @staticmethod
    def _apply_quality_overrides(
        config: AssyLineConfig, scenario: "DemoScenario | str"
    ) -> None:
        """Apply scenario-specific quality overrides to a config instance.

        Mutates the given config ONLY.  Caller owns isolation (deepcopy).
        Delegates to the shared accepted transform (R1).
        """
        apply_scenario_quality_overrides(config, _scenario_value(scenario))

    # --- Context access ---

    def get_context(self, sub_line_id: str) -> Optional[AssyDemoContext]:
        """Get a context by sub_line_id.  Returns None for invalid IDs."""
        return self.contexts.get(sub_line_id)

    @property
    def selected_context(self) -> Optional[AssyDemoContext]:
        """The currently selected context (for detail view)."""
        return self.contexts.get(self.selected_sub_line_id)

    def select_sub_line(self, sub_line_id: str) -> None:
        """Select a sub-line for detail view.

        Does NOT reconstruct or reset any runtime.
        Raises ValueError for invalid IDs.
        """
        if sub_line_id not in self.contexts:
            raise ValueError(
                f"Unknown sub_line_id: {sub_line_id!r}. "
                f"Valid: {sorted(self.contexts.keys())}"
            )
        self.selected_sub_line_id = sub_line_id

    # --- Step ---

    def step_all(
        self,
        exclude_sub_line_ids: Optional[set[str]] = None,
    ) -> None:
        """Execute one demo cycle for all (non-excluded) contexts.

        DEMO_EXECUTION_POLICY: COMMON_DEMO_CLOCK.
        Each context advances independently via step_context().
        demo_step_number increments once per composition step.
        No assertion about equal simulation_time_s.

        SIM-VAL-01-C01: applies continuous feed policy (when enabled)
        BEFORE each context steps, so upstream inventory is available
        for introduce_next_sso2() during index.

        VF-DM-DEMO-ASSY-MES-02-C02: excluded sub-lines (e.g. the AP05_JAM
        faulted target) are fully frozen — no feed replenish and no
        step_context — so their simulation time, dwell, WIP position,
        operations, quality, genealogy, release and LINE_OUT do not advance
        while the fault is active.
        """
        excluded = exclude_sub_line_ids or set()
        if self.continuous_feed_enabled:
            for sub_line_id, ctx in self.contexts.items():
                if sub_line_id not in excluded:
                    self.feed_policy.replenish(ctx)

        for sub_line_id, ctx in self.contexts.items():
            if sub_line_id not in excluded:
                ctx.step_context()
        self.demo_step_number += 1

    # --- Snapshot ---

    def snapshot(self) -> AssyDemoSnapshot:
        """Build detached snapshot for the currently selected context.

        Uses the context's effective scenario, not the global demo scenario.
        SIM-VAL-01-C01: attaches canonical sub-line identity.
        """
        ctx = self.selected_context
        if ctx is None:
            return AssyDemoSnapshot()
        snap = build_snapshot(ctx.runtime, ctx.effective_scenario.value)
        plant_id = "TIPA"
        if self.identity:
            plant_id = self.identity.plant_id
        snap.plant_id = plant_id
        snap.production_line_id = ctx.identity.production_line_id
        snap.sub_line_id = ctx.identity.sub_line_id
        snap.variant = ctx.identity.variant
        return snap

    # --- Reset ---

    def reset(self) -> None:
        """Full reset: rebuild all 6 contexts from scratch."""
        self.initialize()

    # --- Set scenario ---

    def set_scenario(self, scenario: DemoScenario) -> None:
        """Set scenario.  Takes effect on next reset()/initialize()."""
        self.scenario = scenario

    # --- OPS-03: run mode ---

    def set_run_mode(self, mode: CompletionMode) -> None:
        """Set global run mode on all contexts (additive, UI binding)."""
        for ctx in self.contexts.values():
            ctx.runtime.global_run_mode = mode
