"""AUTO-TIME-01A — AUTO timing domain + config tests.

Covers the mandatory test list from the AUTO-TIME-01A PM prompt.
No runtime/dwell integration — pure domain + parsing + resolver in isolation.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from virtual_factory.assembly.auto_timing import (
    AutoTimingProfile,
    DurationPolicy,
    DurationPolicyType,
    SubActionTiming,
    TimingBehavior,
    TimingConfigError,
    TimingResolver,
    _clamp,
    check_profiles_against_positions,
    load_auto_timing_config,
    parse_auto_timing_profiles,
    parse_duration_policy,
    parse_random_seed,
    parse_timing_behavior,
)

TIPA_YAML = (
    Path(__file__).resolve().parents[1]
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


def fixed_policy(seconds: float) -> DurationPolicy:
    return DurationPolicy(type=DurationPolicyType.FIXED, seconds=seconds)


def normal_policy(
    mean_s: float, stddev_s: float, min_s: float, max_s: float,
) -> DurationPolicy:
    return DurationPolicy(
        type=DurationPolicyType.NORMAL,
        mean_s=mean_s,
        stddev_s=stddev_s,
        min_s=min_s,
        max_s=max_s,
    )


def profile(*sub_actions: SubActionTiming) -> AutoTimingProfile:
    return AutoTimingProfile(
        profile_id="P_AUTO_V1",
        station_id="AP01",
        sub_actions=tuple(sub_actions),
    )


def sub_action(sid: str, policy: DurationPolicy) -> SubActionTiming:
    return SubActionTiming(id=sid, duration=policy)


# ═══════════════════════════════════════════════════════════
# 1 & 2. FIXED deterministic / variable
# ═══════════════════════════════════════════════════════════

class TestFixed:
    def test_fixed_deterministic(self):
        p = profile(sub_action("a", fixed_policy(10.0)))
        sample = TimingResolver(seed=42).resolve(p, TimingBehavior.DETERMINISTIC)
        assert sample.effective_duration_s == 10.0
        assert sample.sub_actions[0].effective_duration_s == 10.0

    def test_fixed_variable_remains_fixed(self):
        p = profile(sub_action("a", fixed_policy(10.0)))
        sample = TimingResolver(seed=42).resolve(p, TimingBehavior.VARIABLE)
        assert sample.effective_duration_s == 10.0


# ═══════════════════════════════════════════════════════════
# 3. NORMAL deterministic = mean
# ═══════════════════════════════════════════════════════════

class TestNormalDeterministic:
    def test_normal_deterministic_equals_mean(self):
        p = profile(sub_action("a", normal_policy(15.0, 3.0, 10.0, 25.0)))
        sample = TimingResolver(seed=1).resolve(p, TimingBehavior.DETERMINISTIC)
        assert sample.effective_duration_s == 15.0


# ═══════════════════════════════════════════════════════════
# 4 & 5. NORMAL seeded reproducibility / seed difference
# ═══════════════════════════════════════════════════════════

class TestNormalSeeded:
    def test_seeded_reproducibility(self):
        p = profile(sub_action("a", normal_policy(60.0, 6.0, 48.0, 78.0)))
        s1 = TimingResolver(seed=42).resolve(p, TimingBehavior.VARIABLE)
        s2 = TimingResolver(seed=42).resolve(p, TimingBehavior.VARIABLE)
        assert s1.effective_duration_s == pytest.approx(s2.effective_duration_s)

    def test_different_seed_changes_realization(self):
        p = profile(sub_action("a", normal_policy(60.0, 6.0, 48.0, 78.0)))
        s1 = TimingResolver(seed=1).resolve(p, TimingBehavior.VARIABLE)
        s2 = TimingResolver(seed=2).resolve(p, TimingBehavior.VARIABLE)
        # deterministic for Python's MT19937: seed 1 vs seed 2 differ
        assert s1.effective_duration_s != s2.effective_duration_s


# ═══════════════════════════════════════════════════════════
# 6 & 7. min / max clamp (deterministic seeds)
# ═══════════════════════════════════════════════════════════

class TestClamp:
    def test_min_clamp(self):
        # seed 3: normalvariate(10, 5) < 8 → clamped to min_s=8
        p = profile(sub_action("a", normal_policy(10.0, 5.0, 8.0, 20.0)))
        sample = TimingResolver(seed=3).resolve(p, TimingBehavior.VARIABLE)
        assert sample.sub_actions[0].effective_duration_s == 8.0

    def test_max_clamp(self):
        # seed 1: normalvariate(10, 5) > 12 → clamped to max_s=12
        p = profile(sub_action("a", normal_policy(10.0, 5.0, 8.0, 12.0)))
        sample = TimingResolver(seed=1).resolve(p, TimingBehavior.VARIABLE)
        assert sample.sub_actions[0].effective_duration_s == 12.0

    def test_clamp_helper(self):
        assert _clamp(-5.0, 0.0, 10.0) == 0.0
        assert _clamp(15.0, 0.0, 10.0) == 10.0
        assert _clamp(5.0, 0.0, 10.0) == 5.0


# ═══════════════════════════════════════════════════════════
# 8-10. invalid config fails closed
# ═══════════════════════════════════════════════════════════

class TestInvalidConfig:
    @pytest.mark.parametrize("seconds", [0.0, -1.0, -10.0])
    def test_invalid_fixed_rejected(self, seconds):
        with pytest.raises(TimingConfigError):
            fixed_policy(seconds)

    @pytest.mark.parametrize(
        "kwargs",
        [
            # max < min
            dict(mean_s=15.0, stddev_s=3.0, min_s=20.0, max_s=10.0),
            # min <= 0
            dict(mean_s=15.0, stddev_s=3.0, min_s=0.0, max_s=25.0),
            # stddev < 0
            dict(mean_s=15.0, stddev_s=-1.0, min_s=10.0, max_s=25.0),
            # mean <= 0
            dict(mean_s=0.0, stddev_s=1.0, min_s=0.0, max_s=10.0),
        ],
    )
    def test_invalid_normal_bounds_rejected(self, kwargs):
        with pytest.raises(TimingConfigError):
            normal_policy(**kwargs)

    def test_mean_outside_bounds_rejected(self):
        with pytest.raises(TimingConfigError):
            normal_policy(mean_s=50.0, stddev_s=3.0, min_s=10.0, max_s=40.0)


# ═══════════════════════════════════════════════════════════
# 11 & 12. profile structure validation
# ═══════════════════════════════════════════════════════════

class TestProfileValidation:
    def test_duplicate_sub_action_id_rejected(self):
        with pytest.raises(TimingConfigError):
            profile(
                sub_action("a", fixed_policy(10.0)),
                sub_action("a", fixed_policy(20.0)),
            )

    def test_empty_profile_rejected(self):
        with pytest.raises(TimingConfigError):
            AutoTimingProfile(profile_id="P", station_id="AP01", sub_actions=())


# ═══════════════════════════════════════════════════════════
# 13. effective duration equals sum
# ═══════════════════════════════════════════════════════════

class TestEffectiveSum:
    def test_effective_duration_equals_sum(self):
        p = profile(
            sub_action("a", fixed_policy(10.0)),
            sub_action("b", normal_policy(20.0, 3.0, 15.0, 30.0)),
            sub_action("c", fixed_policy(5.0)),
        )
        sample = TimingResolver(seed=42).resolve(p, TimingBehavior.DETERMINISTIC)
        assert sample.effective_duration_s == pytest.approx(35.0)
        assert sample.nominal_duration_s == pytest.approx(35.0)

    def test_nominal_matches_sum_of_sub_actions(self):
        p = profile(
            sub_action("a", fixed_policy(25.0)),
            sub_action("b", normal_policy(15.0, 3.0, 10.0, 25.0)),
            sub_action("c", fixed_policy(5.0)),
        )
        assert p.nominal_duration_s() == pytest.approx(45.0)


# ═══════════════════════════════════════════════════════════
# 14-17. config parsing
# ═══════════════════════════════════════════════════════════

class TestConfigParsing:
    def test_no_profiles_backward_compatible(self):
        # No auto_timing_profiles / timing_behavior / random_seed keys →
        # safe defaults (equivalent to a YAML without the additive section).
        behavior = parse_timing_behavior(None)
        seed = parse_random_seed(None)
        profiles = parse_auto_timing_profiles(None)
        assert behavior == TimingBehavior.DETERMINISTIC
        assert seed == 42
        assert profiles == {}

    def test_timing_behavior_and_random_seed_parse(self):
        assert parse_timing_behavior(None) == TimingBehavior.DETERMINISTIC
        assert parse_timing_behavior("VARIABLE") == TimingBehavior.VARIABLE
        assert parse_timing_behavior("variable") == TimingBehavior.VARIABLE
        assert parse_random_seed(None) == 42
        assert parse_random_seed(7) == 7

    def test_invalid_behavior_rejected(self):
        with pytest.raises(TimingConfigError):
            parse_timing_behavior("CHAOS")

    def test_invalid_policy_type_rejected(self):
        with pytest.raises(TimingConfigError):
            parse_duration_policy({"type": "lognormal", "seconds": 10})

    def test_bool_seed_rejected(self):
        with pytest.raises(TimingConfigError):
            parse_random_seed(True)

    def test_profile_key_not_conveyor_position_rejected(self):
        profiles = parse_auto_timing_profiles({
            "AP99": {
                "profile_id": "AP99_AUTO_V1",
                "sub_actions": [{"id": "x", "duration": {"type": "fixed", "seconds": 10}}],
            }
        })
        with pytest.raises(TimingConfigError):
            check_profiles_against_positions(profiles, ["PRE-ASSY", "AP01"])


# ═══════════════════════════════════════════════════════════
# 18. TIPA YAML profiles load
# ═══════════════════════════════════════════════════════════

class TestTipaYaml:
    def test_tipa_yaml_profiles_load(self):
        behavior, seed, profiles = load_auto_timing_config(str(TIPA_YAML))
        assert behavior == TimingBehavior.DETERMINISTIC
        assert seed == 42
        assert set(profiles) == {"AP03", "AP04", "AP05", "AP06", "AP08", "AP11"}
        assert profiles["AP03"].nominal_duration_s() == pytest.approx(45.0)
        assert profiles["AP04"].nominal_duration_s() == pytest.approx(60.0)
        assert profiles["AP05"].nominal_duration_s() == pytest.approx(90.0)
        assert profiles["AP06"].nominal_duration_s() == pytest.approx(60.0)
        assert profiles["AP08"].nominal_duration_s() == pytest.approx(30.0)
        assert profiles["AP11"].nominal_duration_s() == pytest.approx(30.0)

    def test_tipa_profiles_resolve_deterministically(self):
        _, _, profiles = load_auto_timing_config(str(TIPA_YAML))
        sample = TimingResolver(seed=42).resolve(
            profiles["AP05"], TimingBehavior.DETERMINISTIC)
        assert sample.nominal_duration_s == pytest.approx(90.0)
        assert sample.effective_duration_s == pytest.approx(90.0)

    def test_runtime_config_loader_ignores_additive_keys(self):
        """The existing runtime loader must remain backward-compatible."""
        from virtual_factory.assembly.line_runtime import load_assy_config_from_yaml
        config = load_assy_config_from_yaml(str(TIPA_YAML))
        assert config.station_durations["AP05"] == 90.0
        assert config.conveyor.nominal_line_dwell_time_s == 120.0
