"""VF-vNEXT-R1 — explicit immutable ASSY domain run profile + shared run prep.

This module is the SMALLEST shared seam that lets the canonical vNext TIPA
``RuntimeSession`` run the already-accepted six-sub-line ASSY production
semantics, while the legacy accepted demo path keeps the *same* domain-run
preparation semantics (no copy-pasted divergence).

It owns, and only owns:

- the accepted synthetic scenario vocabulary and its config/quality transforms;
- deterministic synthetic exception target resolution;
- an IMMUTABLE run profile (run INPUT, never mutable simulation truth);
- a shared per-sub-line mutable RUN STATE holder (feed/sequencing only);
- the shared production driver around the accepted public ``AssyLineRuntime``
  operations (prepare feed -> on-demand RSO2 -> dwell -> conditional index ->
  introduce the next SSO2);
- explicit exploration/"simulation" provenance marking.

Explicit non-goals (frozen by the R0 architecture):

- no second runtime/controller/engine/session/lifecycle authority;
- no ``AssyLineRuntime`` semantics rewrite (public operations only);
- no platform coordinator logic (G4 stays ignorant of ASSY stations/scenarios);
- no promotion of demo/scenario policy to plant or site truth.

All scenario/quality/inventory values here are DEMO_SYNTHETIC simulation inputs,
NOT TIPA site truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
)


# ═══════════════════════════════════════════════════════════
# Accepted scenario vocabulary (values only — no demo enum dependency)
# ═══════════════════════════════════════════════════════════

ASSY_RUN_PROFILE_VERSION = "1"

#: Provenance marking: these run inputs are simulated/synthetic, never site truth.
PROFILE_PROVENANCE = "simulation_synthetic_profile_input"

HAPPY_PATH = "HAPPY_PATH"
AP06_FAIL_RETEST_PASS = "AP06_FAIL_RETEST_PASS"
AP08_NG_REINSPECT_PASS = "AP08_NG_REINSPECT_PASS"
FAILED_FINAL = "FAILED_FINAL"

KNOWN_RUN_SCENARIOS: tuple[str, ...] = (
    HAPPY_PATH,
    AP06_FAIL_RETEST_PASS,
    AP08_NG_REINSPECT_PASS,
    FAILED_FINAL,
)

# HAPPY_PATH normalisation: override base YAML exception config to clean PASS.
_HAPPY_PATH_QUALITY_NORMALIZE: dict = {
    "ap06": {"scenario": "PASS", "overrides": {}},
    "ap08": {"scenario": "PASS", "overrides": {}},
}

#: Accepted per-scenario quality transforms (single semantic source).
SCENARIO_QUALITY_OVERRIDES_BY_VALUE: dict[str, dict] = {
    HAPPY_PATH: _HAPPY_PATH_QUALITY_NORMALIZE,
    AP06_FAIL_RETEST_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["FAIL", "PASS"]}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
    AP08_NG_REINSPECT_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["NG", "PASS"]}},
    },
    FAILED_FINAL: {
        "ap06": {"scenario": "ALWAYS_FAIL", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
}

#: Deterministic synthetic exception target per scenario (demo policy, not truth).
SCENARIO_TARGET_DEFAULTS_BY_VALUE: dict[str, str] = {
    HAPPY_PATH: "",                        # no target — all HAPPY_PATH
    AP06_FAIL_RETEST_PASS: "ASSY-SL03",
    AP08_NG_REINSPECT_PASS: "ASSY-SL02",
    FAILED_FINAL: "ASSY-SL03",
}

#: Canonical RuntimeSession ``scenario_id`` values -> accepted run scenario.
SESSION_SCENARIO_ALIASES: dict[str, str] = {
    "tipa-default": HAPPY_PATH,
    "tipa-happy-path": HAPPY_PATH,
    "tipa-ap06-retest": AP06_FAIL_RETEST_PASS,
    "tipa-ap08-reinspect": AP08_NG_REINSPECT_PASS,
    "tipa-failed-final": FAILED_FINAL,
}

#: Accepted demo feed/sequencing constants (DEMO_SYNTHETIC simulation inputs).
DEFAULT_INITIAL_SSO2_INVENTORY = 7
DEFAULT_INITIAL_RSO2_INVENTORY = 7


class AssyRunProfileError(ValueError):
    """Raised when a run profile/scenario cannot be resolved honestly."""


# ═══════════════════════════════════════════════════════════
# Pure scenario helpers (shared by canonical and legacy paths)
# ═══════════════════════════════════════════════════════════

def resolve_run_scenario(scenario_id: str) -> str:
    """Resolve a session scenario id to an accepted run scenario value.

    Accepts either an accepted scenario value (exact or case-insensitive) or one
    of the canonical TIPA session aliases (e.g. ``tipa-default``). Unknown input
    fails closed — a scenario id is never silently ignored.
    """
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise AssyRunProfileError("scenario_id must be a non-empty str")
    key = scenario_id.strip()
    alias = SESSION_SCENARIO_ALIASES.get(key)
    if alias is not None:
        return alias
    upper = key.upper()
    if upper in KNOWN_RUN_SCENARIOS:
        return upper
    raise AssyRunProfileError(
        f"unknown ASSY run scenario {scenario_id!r}; accepted session aliases: "
        f"{sorted(SESSION_SCENARIO_ALIASES)} or one of {list(KNOWN_RUN_SCENARIOS)}"
    )


def resolve_scenario_target_id(scenario: str, identity_default: str = "") -> str:
    """Deterministic synthetic exception target sub-line for one scenario.

    Accepted precedence (unchanged from the accepted demo): scenario default
    first, then the identity default. HAPPY_PATH never targets a sub-line.
    """
    if scenario == HAPPY_PATH:
        return ""
    return SCENARIO_TARGET_DEFAULTS_BY_VALUE.get(scenario, "") or (identity_default or "")


def apply_scenario_quality_overrides(config: AssyLineConfig, scenario: str) -> None:
    """Apply the accepted scenario quality transforms to ONE config instance.

    Mutates the given config only (the caller owns isolation via deepcopy).
    """
    overrides = SCENARIO_QUALITY_OVERRIDES_BY_VALUE.get(scenario, {})
    for station_key, cfg in overrides.items():
        sqc = getattr(config.quality, station_key, None)
        if sqc is None:
            continue
        sqc.scenario = cfg.get("scenario", "PASS")
        sqc.overrides = dict(cfg.get("overrides", {}))
        if scenario == FAILED_FINAL:
            sqc.max_attempts = 2


# ═══════════════════════════════════════════════════════════
# Immutable run profile (run INPUT)
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class AssyFeedPolicy:
    """Bounded upstream replenishment settings (DEMO_SYNTHETIC inputs).

    Replenishes the SSO2 feed queue and tops up the RSO2 buffer. Never modifies
    ``AssyLineRuntime`` business semantics; replenished WIPs enter ASSY only
    through the existing public ``introduce_to_assy`` entry.
    """

    sso2_target: int = 10
    sso2_low_watermark: int = 3
    rso2_target: int = 6


@dataclass(frozen=True, slots=True)
class AssyRunProfile:
    """Immutable ASSY domain run profile (explicit run INPUT).

    Pinned per run attempt and re-resolved deterministically from the session
    ``scenario_id`` on reset/new-attempt/replay. It owns NO mutable simulation
    truth and NO lifecycle authority.
    """

    profile_id: str
    session_scenario_id: str
    scenario: str
    target_sub_line_id: str = ""
    version: str = ASSY_RUN_PROFILE_VERSION
    initial_sso2_inventory: int = DEFAULT_INITIAL_SSO2_INVENTORY
    initial_rso2_inventory: int = DEFAULT_INITIAL_RSO2_INVENTORY
    continuous_feed_enabled: bool = True
    feed_policy: AssyFeedPolicy = field(default_factory=AssyFeedPolicy)
    provenance: str = PROFILE_PROVENANCE

    # ── effective per-sub-line scenario ──────────────────────

    def is_exception_target(self, sub_line_id: str) -> bool:
        """Whether this sub-line receives the synthetic exception scenario."""
        return bool(self.target_sub_line_id) and sub_line_id == self.target_sub_line_id

    def effective_scenario_for(self, sub_line_id: str) -> str:
        """Effective scenario for one sub-line (non-targets stay HAPPY_PATH)."""
        return self.scenario if self.is_exception_target(sub_line_id) else HAPPY_PATH

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "version": self.version,
            "session_scenario_id": self.session_scenario_id,
            "scenario": self.scenario,
            "target_sub_line_id": self.target_sub_line_id,
            "initial_sso2_inventory": self.initial_sso2_inventory,
            "initial_rso2_inventory": self.initial_rso2_inventory,
            "continuous_feed_enabled": self.continuous_feed_enabled,
            "feed_policy": {
                "sso2_target": self.feed_policy.sso2_target,
                "sso2_low_watermark": self.feed_policy.sso2_low_watermark,
                "rso2_target": self.feed_policy.rso2_target,
            },
            "provenance": self.provenance,
        }


def build_tipa_run_profile(scenario_id: str) -> AssyRunProfile:
    """Resolve the canonical TIPA run profile for a session ``scenario_id``.

    ``tipa-default`` resolves to the accepted HAPPY_PATH-style production
    profile (never an empty federation). Unknown scenario ids fail closed.
    """
    scenario = resolve_run_scenario(scenario_id)
    target = resolve_scenario_target_id(scenario)
    return AssyRunProfile(
        profile_id=f"tipa-assy-{scenario.lower()}",
        session_scenario_id=scenario_id,
        scenario=scenario,
        target_sub_line_id=target,
    )


# ═══════════════════════════════════════════════════════════
# Shared per-sub-line run state (feed/sequencing only)
# ═══════════════════════════════════════════════════════════

@dataclass
class AssySubLineRunState:
    """Mutable per-sub-line RUN state: upstream feed queue + carrier sequencing.

    One distinct holder per sub-line. It never owns conveyor/WIP-position/
    quality/genealogy truth — that stays inside the wrapped
    ``AssyLineRuntime``.
    """

    carrier_seq: int = 1
    sso2_idx: int = 0
    sso2_ids: list[str] = field(default_factory=list)
    profile_id: str = ""

    @property
    def remaining_sso2(self) -> int:
        return max(0, len(self.sso2_ids) - self.sso2_idx)

    def seed_inventories(
        self,
        runtime: AssyLineRuntime,
        *,
        sso2_count: int,
        rso2_count: int,
    ) -> None:
        """(Re)build the deterministic initial upstream inventory for a line."""
        self.carrier_seq = 1
        self.sso2_idx = 0
        self.sso2_ids = []
        for _ in range(sso2_count):
            self.sso2_ids.append(runtime.produce_sso2_wip())
        for _ in range(rso2_count):
            runtime.produce_rso2_wip()

    def prepare(self, runtime: AssyLineRuntime, profile: AssyRunProfile) -> None:
        """Prepare a line for a profile: initial inventory + first SSO2 entry."""
        self.seed_inventories(
            runtime,
            sso2_count=profile.initial_sso2_inventory,
            rso2_count=profile.initial_rso2_inventory,
        )
        self.profile_id = profile.profile_id
        self.introduce_next(runtime)

    # ── feed + sequencing ───────────────────────────────────

    def replenish(self, runtime: AssyLineRuntime, policy: AssyFeedPolicy) -> None:
        """Top up the SSO2 feed queue and RSO2 buffer for this line only."""
        if self.remaining_sso2 < policy.sso2_low_watermark:
            for _ in range(policy.sso2_target - self.remaining_sso2):
                self.sso2_ids.append(runtime.produce_sso2_wip())
        if runtime.rso2_buffer_size < policy.rso2_target:
            for _ in range(policy.rso2_target - runtime.rso2_buffer_size):
                runtime.produce_rso2_wip()

    def introduce_next(self, runtime: AssyLineRuntime) -> None:
        """Introduce the next queued SSO2 through the existing public entry."""
        if self.sso2_idx < len(self.sso2_ids):
            wip = self.sso2_ids[self.sso2_idx]
            self.sso2_idx += 1
            cid = f"PAL-{self.carrier_seq:03d}"
            self.carrier_seq += 1
            runtime.introduce_to_assy(wip, cid)


# ═══════════════════════════════════════════════════════════
# Shared production driver (accepted behaviour, one implementation)
# ═══════════════════════════════════════════════════════════

def step_prepared_line(
    runtime: AssyLineRuntime,
    state: AssySubLineRunState,
    *,
    feed_policy: AssyFeedPolicy | None = None,
) -> None:
    """One accepted ASSY production cycle for ONE prepared sub-line.

    Order (unchanged accepted behaviour):

    1. optional bounded feed replenishment BEFORE the natural line step;
    2. on-demand RSO2 availability for AP04 when a unit is waiting there;
    3. ``execute_dwell()`` (the only time-advancing operation);
    4. ``index_line()`` ONLY when the line is ``READY_TO_INDEX``;
    5. introduce the next SSO2 through the existing public runtime entry.

    No fractional dwell/index and no invented synchronization/time semantics.
    """
    if feed_policy is not None:
        state.replenish(runtime, feed_policy)
    if runtime.conveyor.wip_at("AP04") and runtime.rso2_buffer_size == 0:
        runtime.produce_rso2_wip()
    runtime.execute_dwell()
    if runtime.conveyor.state == ConveyorState.READY_TO_INDEX:
        runtime.index_line()
        state.introduce_next(runtime)


__all__ = [
    "ASSY_RUN_PROFILE_VERSION",
    "PROFILE_PROVENANCE",
    "HAPPY_PATH",
    "AP06_FAIL_RETEST_PASS",
    "AP08_NG_REINSPECT_PASS",
    "FAILED_FINAL",
    "KNOWN_RUN_SCENARIOS",
    "SESSION_SCENARIO_ALIASES",
    "SCENARIO_QUALITY_OVERRIDES_BY_VALUE",
    "SCENARIO_TARGET_DEFAULTS_BY_VALUE",
    "DEFAULT_INITIAL_SSO2_INVENTORY",
    "DEFAULT_INITIAL_RSO2_INVENTORY",
    "AssyRunProfileError",
    "AssyFeedPolicy",
    "AssyRunProfile",
    "AssySubLineRunState",
    "resolve_run_scenario",
    "resolve_scenario_target_id",
    "apply_scenario_quality_overrides",
    "build_tipa_run_profile",
    "step_prepared_line",
]
