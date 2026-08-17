"""AUTO-TIME-01B — runtime timing resolution & dwell semantics tests.

Covers the mandatory test list from the AUTO-TIME-01B PM prompt.
Pure runtime behavior: operation creation before dwell sizing, frozen
sample-once timing, MANUAL/ASSISTED preservation, reset reproducibility,
and sub-line seed derivation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from virtual_factory.assembly.auto_timing import (
    AutoTimingProfile,
    DurationPolicy,
    DurationPolicyType,
    SubActionTiming,
    TimingBehavior,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.operation_execution import (
    OperationResult,
    OperationState,
)
from virtual_factory.assembly.station_contracts import CompletionMode

TIPA_YAML = (
    Path(__file__).resolve().parents[1]
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


def make_fast_config() -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    line = AssyLineRuntime(config=cfg)
    line.produce_sso2_wip()   # SSO2-0001
    line.produce_rso2_wip()   # RSO2-0001
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def advance_to_before(line: AssyLineRuntime, position: str) -> None:
    """Advance the line until the next WIP sits AT `position`, unprocessed."""
    target_idx = line.conveyor.positions.index(position)
    for _ in range(target_idx):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()


def fixed_profile(station: str, seconds: float) -> AutoTimingProfile:
    return AutoTimingProfile(
        profile_id=f"{station}_TEST_V1",
        station_id=station,
        sub_actions=(
            SubActionTiming(
                id="a",
                duration=DurationPolicy(
                    type=DurationPolicyType.FIXED, seconds=seconds),
            ),
        ),
    )


def normal_profile(
    station: str, mean_s: float, stddev_s: float, min_s: float, max_s: float,
) -> AutoTimingProfile:
    return AutoTimingProfile(
        profile_id=f"{station}_TEST_V1",
        station_id=station,
        sub_actions=(
            SubActionTiming(
                id="a",
                duration=DurationPolicy(
                    type=DurationPolicyType.NORMAL,
                    mean_s=mean_s, stddev_s=stddev_s, min_s=min_s, max_s=max_s,
                ),
            ),
        ),
    )


def ap_op(line: AssyLineRuntime, station_id: str):
    ops = [
        o for o in line.operation_registry._operations.values()
        if o.station_id == station_id
    ]
    assert ops, f"no operation recorded for {station_id}"
    return ops[-1]


# ═══════════════════════════════════════════════════════════
# 1-3. AUTO sampling at op creation, sample-once
# ═══════════════════════════════════════════════════════════

class TestAutoSampling:
    def test_deterministic_freezes_nominal_mean_sum(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.DETERMINISTIC
        cfg.auto_timing_profiles["AP01"] = AutoTimingProfile(
            profile_id="AP01_T", station_id="AP01",
            sub_actions=(
                SubActionTiming(
                    id="a",
                    duration=DurationPolicy(
                        type=DurationPolicyType.NORMAL,
                        mean_s=15.0, stddev_s=3.0, min_s=10.0, max_s=25.0,
                    ),
                ),
                SubActionTiming(
                    id="b",
                    duration=DurationPolicy(
                        type=DurationPolicyType.FIXED, seconds=5.0),
                ),
            ),
        )
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.work_duration_s == pytest.approx(20.0)
        assert op.timing is not None
        assert op.timing.effective_duration_s == pytest.approx(20.0)

    def test_variable_samples_once_per_operation(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        cfg.auto_timing_profiles["AP01"] = normal_profile(
            "AP01", 50.0, 20.0, 1.0, 100.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        first = op.timing
        assert first is not None
        # Same position/WIP → same op → no re-sample.
        again = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert again.execution_id == op.execution_id
        assert again.timing is first

    def test_repeated_dwell_does_not_resample(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        cfg.auto_timing_profiles["AP01"] = normal_profile(
            "AP01", 50.0, 20.0, 1.0, 100.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        # Freeze the op before dwell sizing (as execute_dwell does internally).
        op0 = line._ensure_operation_for_position("AP01", "SSO2-0001")
        t0 = op0.timing
        assert t0 is not None
        line.execute_dwell()
        # Exactly one op for AP01, same object, same frozen sample.
        ops = [
            o for o in line.operation_registry._operations.values()
            if o.station_id == "AP01"
        ]
        assert len(ops) == 1
        assert ops[0] is op0
        assert ops[0].timing is t0


# ═══════════════════════════════════════════════════════════
# 4-6. dwell sizing uses frozen op duration
# ═══════════════════════════════════════════════════════════

class TestDwellSizing:
    def test_active_op_duration_used_by_max_remaining(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 40.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        before = line.simulation_time_s
        line.execute_dwell()
        assert line.simulation_time_s - before == pytest.approx(40.0)

    def test_ap05_sampled_135_nominal_120_first_dwell_135(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        cfg.station_durations["AP05"] = 90.0  # legacy
        cfg.auto_timing_profiles["AP05"] = fixed_profile("AP05", 135.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP05")
        before = line.simulation_time_s
        line.execute_dwell()
        # First active dwell must be 135, NOT 120 then another 120.
        assert line.simulation_time_s - before == pytest.approx(135.0)
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX

    def test_all_below_nominal_dwell_exactly_nominal(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        # all station durations 5.0 (fast config) < 120
        line = AssyLineRuntime(config=cfg)
        for i in range(3):
            wid = line.produce_sso2_wip()
            line.introduce_to_assy(wid, f"PAL-{i + 1:03d}")
            if i < 2:
                line.execute_dwell()
                if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                    line.index_line()
        before = line.simulation_time_s
        line.execute_dwell()
        assert line.simulation_time_s - before == pytest.approx(120.0)


# ═══════════════════════════════════════════════════════════
# 7-9. fallback + MANUAL/ASSISTED preservation
# ═══════════════════════════════════════════════════════════

class TestModePreservation:
    def test_auto_no_profile_fallback(self):
        cfg = make_fast_config()  # no profiles
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.work_duration_s == pytest.approx(
            line.station_contracts["AP01"].work_duration_s)
        assert op.timing is None

    def test_manual_ignores_profile(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 999.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")   # AUTO advance
        line.global_run_mode = CompletionMode.MANUAL
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.work_duration_s == pytest.approx(5.0)  # legacy, not 999
        assert op.timing is None

    def test_assisted_ignores_profile(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 999.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")   # AUTO advance
        line.global_run_mode = CompletionMode.ASSISTED
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.work_duration_s == pytest.approx(5.0)  # legacy, not 999
        assert op.timing is None


# ═══════════════════════════════════════════════════════════
# 10-13. seed / determinism
# ═══════════════════════════════════════════════════════════

class TestDeterminism:
    def test_same_seed_reset_reproduces_sequence(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        cfg.auto_timing_profiles["AP01"] = normal_profile(
            "AP01", 50.0, 20.0, 1.0, 100.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        v1 = line._ensure_operation_for_position(
            "AP01", "SSO2-0001").timing.effective_duration_s

        line.reset()
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        advance_to_before(line, "AP01")
        v2 = line._ensure_operation_for_position(
            "AP01", "SSO2-0001").timing.effective_duration_s
        assert v1 == pytest.approx(v2)

    def test_different_seed_changes_realization(self):
        profile = normal_profile("AP01", 50.0, 20.0, 1.0, 100.0)
        cfg1 = make_fast_config()
        cfg1.timing_behavior = TimingBehavior.VARIABLE
        cfg1.random_seed = 42
        cfg1.auto_timing_profiles["AP01"] = profile
        cfg2 = make_fast_config()
        cfg2.timing_behavior = TimingBehavior.VARIABLE
        cfg2.random_seed = 43
        cfg2.auto_timing_profiles["AP01"] = profile
        r1 = AssyLineRuntime(config=cfg1)._timing_resolver
        r2 = AssyLineRuntime(config=cfg2)._timing_resolver
        s1 = r1.resolve(profile, TimingBehavior.VARIABLE)
        s2 = r2.resolve(profile, TimingBehavior.VARIABLE)
        assert s1.effective_duration_s != s2.effective_duration_s

    def test_deterministic_does_not_depend_on_rng(self):
        profile = normal_profile("AP01", 20.0, 5.0, 10.0, 30.0)
        cfg1 = make_fast_config()
        cfg1.timing_behavior = TimingBehavior.DETERMINISTIC
        cfg1.random_seed = 42
        cfg1.auto_timing_profiles["AP01"] = profile
        cfg2 = make_fast_config()
        cfg2.timing_behavior = TimingBehavior.DETERMINISTIC
        cfg2.random_seed = 99
        cfg2.auto_timing_profiles["AP01"] = profile
        r1 = AssyLineRuntime(config=cfg1)._timing_resolver
        r2 = AssyLineRuntime(config=cfg2)._timing_resolver
        assert r1.resolve(profile, TimingBehavior.DETERMINISTIC).effective_duration_s == pytest.approx(20.0)
        assert r2.resolve(profile, TimingBehavior.DETERMINISTIC).effective_duration_s == pytest.approx(20.0)

    def test_sub_line_streams_deterministic_and_uncoupled(self):
        from virtual_factory.assembly.demo_composition import (
            AssyDemoComposition,
            DemoScenario,
        )
        comp = AssyDemoComposition(
            config_path=str(TIPA_YAML), scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        seeds = [ctx.config.random_seed for ctx in comp.contexts.values()]
        assert seeds == [42, 43, 44, 45, 46, 47]

        comp2 = AssyDemoComposition(
            config_path=str(TIPA_YAML), scenario=DemoScenario.HAPPY_PATH)
        comp2.initialize()
        seeds2 = [ctx.config.random_seed for ctx in comp2.contexts.values()]
        assert seeds2 == seeds


# ═══════════════════════════════════════════════════════════
# 14-15. retry / AP11 semantics preserved
# ═══════════════════════════════════════════════════════════

class TestLifecyclePreservation:
    def test_retry_does_not_resample(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        # bounded sample always < nominal dwell (10) → FAIL on first dwell
        cfg.auto_timing_profiles["AP06"] = normal_profile(
            "AP06", 3.0, 0.5, 1.0, 5.0)
        cfg.quality.ap06.scenario = "FAIL_FIRST_THEN_PASS"
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()  # first attempt → FAIL → retry scheduled
        op_fail = ap_op(line, "AP06")
        eid = op_fail.execution_id
        timing_after_fail = op_fail.timing
        assert op_fail.state in (
            OperationState.AWAITING_DECISION, OperationState.FAILED)

        line.execute_dwell()  # retry → re-observe → PASS → complete
        op_after = ap_op(line, "AP06")
        assert op_after.execution_id == eid
        assert op_after.timing is timing_after_fail  # no re-sample
        assert op_after.state == OperationState.ELIGIBLE_TO_INDEX

    def test_ap11_qc_then_release_unchanged(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP11"] = fixed_profile("AP11", 5.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP11")
        line.execute_dwell()  # final QC
        op = ap_op(line, "AP11")
        assert op.operation_result == OperationResult.CONFIRMED
        assert op.state == OperationState.AWAITING_COMPLETION
        line.execute_dwell()  # RELEASE
        op = ap_op(line, "AP11")
        assert op.operation_result == OperationResult.RELEASED
        assert op.state == OperationState.ELIGIBLE_TO_INDEX


# ═══════════════════════════════════════════════════════════
# 17. config + station-contract backward compatibility
# ═══════════════════════════════════════════════════════════

class TestConfigBackwardCompatible:
    def test_tipa_yaml_loads_timing_and_legacy(self):
        cfg = load_assy_config_from_yaml(str(TIPA_YAML))
        assert cfg.station_durations["AP05"] == 90.0
        assert cfg.conveyor.nominal_line_dwell_time_s == 120.0
        assert cfg.timing_behavior == TimingBehavior.DETERMINISTIC
        assert cfg.random_seed == 42
        assert set(cfg.auto_timing_profiles) == {
            "AP03", "AP04", "AP05", "AP06", "AP08", "AP11"}

    def test_default_config_and_contracts_intact(self):
        c = AssyLineConfig()
        assert len(c.station_durations) == 12
        assert c.timing_behavior == TimingBehavior.DETERMINISTIC
        assert c.random_seed == 42
        assert c.auto_timing_profiles == {}
        line = AssyLineRuntime(config=c)
        assert len(line.station_contracts) == 12
