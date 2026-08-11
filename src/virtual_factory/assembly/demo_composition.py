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
from virtual_factory.assembly.quality_records import QualityStatus


# ═══════════════════════════════════════════════════════════
# Scenario (reused from demo_controller for isolation)
# ═══════════════════════════════════════════════════════════

class DemoScenario(str, enum.Enum):
    HAPPY_PATH = "HAPPY_PATH"
    AP06_FAIL_RETEST_PASS = "AP06_FAIL_RETEST_PASS"
    AP08_NG_REINSPECT_PASS = "AP08_NG_REINSPECT_PASS"
    FAILED_FINAL = "FAILED_FINAL"


# HAPPY_PATH normalisation: override base YAML exception config to clean PASS
_HAPPY_PATH_QUALITY_NORMALIZE: dict = {
    "ap06": {"scenario": "PASS", "overrides": {}},
    "ap08": {"scenario": "PASS", "overrides": {}},
}

SCENARIO_QUALITY_OVERRIDES: dict[DemoScenario, dict] = {
    DemoScenario.HAPPY_PATH: _HAPPY_PATH_QUALITY_NORMALIZE,
    DemoScenario.AP06_FAIL_RETEST_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["FAIL", "PASS"]}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
    DemoScenario.AP08_NG_REINSPECT_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["NG", "PASS"]}},
    },
    DemoScenario.FAILED_FINAL: {
        "ap06": {"scenario": "ALWAYS_FAIL", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
}

# Default target sub-line per scenario (demo policy, not plant truth)
SCENARIO_TARGET_DEFAULTS: dict[DemoScenario, str] = {
    DemoScenario.HAPPY_PATH: "",            # no target — all HAPPY_PATH
    DemoScenario.AP06_FAIL_RETEST_PASS: "ASSY-SL03",
    DemoScenario.AP08_NG_REINSPECT_PASS: "ASSY-SL02",
    DemoScenario.FAILED_FINAL: "ASSY-SL03",
}


# ═══════════════════════════════════════════════════════════
# AssyDemoContext
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyDemoContext:
    """One logical ASSY sub-line execution context for the demo.

    Holds identity, isolated config, runtime, and per-context feed state.
    Does NOT hold projection/UI state.
    """

    identity: AssySubLineIdentity
    config: AssyLineConfig
    runtime: AssyLineRuntime
    effective_scenario: DemoScenario = DemoScenario.HAPPY_PATH

    # Per-context feed state (isolated — not shared across contexts)
    carrier_seq: int = 1
    sso2_idx: int = 0
    sso2_ids: list[str] = field(default_factory=list)

    # --- Per-context step helpers ---

    def introduce_next_sso2(self) -> None:
        """Introduce the next SSO2 WIP into this context's ASSY line."""
        if self.sso2_idx < len(self.sso2_ids):
            wip = self.sso2_ids[self.sso2_idx]
            self.sso2_idx += 1
            cid = f"PAL-{self.carrier_seq:03d}"
            self.carrier_seq += 1
            self.runtime.introduce_to_assy(wip, cid)

    def step_context(self) -> None:
        """Execute one demo cycle for this context.

        Reuses existing S04 single-context demo orchestration semantics:
        on-demand RSO2, execute_dwell, release detection, conditional index.
        """
        # On-demand RSO2
        if (self.runtime.conveyor.wip_at("AP04")
                and self.runtime.rso2_buffer_size == 0):
            self.runtime.produce_rso2_wip()

        # Execute dwell
        self.runtime.execute_dwell()

        # Index if ready
        if self.runtime.conveyor.state == ConveyorState.READY_TO_INDEX:
            self.runtime.index_line()
            # Introduce next SSO2
            self.introduce_next_sso2()


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

        for sl_identity in self.identity.sub_lines:
            ctx_config = copy.deepcopy(base_config)

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
                carrier_seq=1,
                sso2_idx=0,
                sso2_ids=[],
            )

            # Seed upstream WIPs
            total = 7
            for _ in range(total):
                ctx.sso2_ids.append(runtime.produce_sso2_wip())
            for _ in range(total):
                runtime.produce_rso2_wip()

            # Introduce first WIP
            ctx.introduce_next_sso2()

            self.contexts[sl_identity.sub_line_id] = ctx

    def _resolve_target(self) -> str:
        """Determine which sub-line gets the exception scenario.

        Scenario-specific default takes priority, identity default as fallback.
        """
        if self.scenario == DemoScenario.HAPPY_PATH:
            return ""
        scenario_target = SCENARIO_TARGET_DEFAULTS.get(self.scenario, "")
        if scenario_target:
            return scenario_target
        if self.identity and self.identity.target_sub_line_for_exception:
            return self.identity.target_sub_line_for_exception
        return ""

    @staticmethod
    def _apply_quality_overrides(config: AssyLineConfig, scenario: DemoScenario) -> None:
        """Apply scenario-specific quality overrides to a config instance.

        Mutates the given config ONLY.  Caller owns isolation (deepcopy).
        """
        overrides = SCENARIO_QUALITY_OVERRIDES.get(scenario, {})
        for station_key, cfg in overrides.items():
            sqc = getattr(config.quality, station_key, None)
            if sqc is not None:
                sqc.scenario = cfg.get("scenario", "PASS")
                sqc.overrides = dict(cfg.get("overrides", {}))
                # Adjust max_attempts for FAILED_FINAL
                if scenario == DemoScenario.FAILED_FINAL:
                    sqc.max_attempts = 2

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

    def step_all(self) -> None:
        """Execute one demo cycle for all contexts.

        DEMO_EXECUTION_POLICY: COMMON_DEMO_CLOCK.
        Each context advances independently via step_context().
        demo_step_number increments once per composition step.
        No assertion about equal simulation_time_s.
        """
        for ctx in self.contexts.values():
            ctx.step_context()
        self.demo_step_number += 1

    # --- Snapshot ---

    def snapshot(self) -> AssyDemoSnapshot:
        """Build detached snapshot for the currently selected context.

        Uses the context's effective scenario, not the global demo scenario.
        """
        ctx = self.selected_context
        if ctx is None:
            return AssyDemoSnapshot()
        return build_snapshot(ctx.runtime, ctx.effective_scenario.value)

    # --- Reset ---

    def reset(self) -> None:
        """Full reset: rebuild all 6 contexts from scratch."""
        self.initialize()

    # --- Set scenario ---

    def set_scenario(self, scenario: DemoScenario) -> None:
        """Set scenario.  Takes effect on next reset()/initialize()."""
        self.scenario = scenario
