"""AUTO-TIME-01D — backend validation matrix runner (V1..V10).

Produces deterministic authoritative values for the AUTO-TIME-01D evidence.
Read-only against the runtime; no production changes.
"""

from __future__ import annotations

from pathlib import Path

from virtual_factory.assembly.auto_timing import (
    AutoTimingProfile,
    DurationPolicy,
    DurationPolicyType,
    SubActionTiming,
    TimingBehavior,
)
from virtual_factory.assembly.demo_snapshot import build_snapshot
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
)
from virtual_factory.assembly.operation_execution import OperationResult
from virtual_factory.assembly.station_contracts import CompletionMode

TIPA_YAML = str(
    Path(__file__).resolve().parents[4]
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
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def advance_to_before(line: AssyLineRuntime, position: str) -> None:
    target_idx = line.conveyor.positions.index(position)
    for _ in range(target_idx):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()


def fixed_profile(station: str, seconds: float) -> AutoTimingProfile:
    return AutoTimingProfile(
        profile_id=f"{station}_TEST_V1", station_id=station,
        sub_actions=(SubActionTiming(
            id="a", duration=DurationPolicy(
                type=DurationPolicyType.FIXED, seconds=seconds)),),
    )


def normal_profile(station, mean_s, stddev_s, min_s, max_s) -> AutoTimingProfile:
    return AutoTimingProfile(
        profile_id=f"{station}_TEST_V1", station_id=station,
        sub_actions=(SubActionTiming(
            id="a", duration=DurationPolicy(
                type=DurationPolicyType.NORMAL,
                mean_s=mean_s, stddev_s=stddev_s, min_s=min_s, max_s=max_s)),),
    )


def ap_op(line: AssyLineRuntime, station_id: str):
    ops = [o for o in line.operation_registry._operations.values()
           if o.station_id == station_id]
    return ops[-1] if ops else None


rows: list[tuple] = []
detail: dict = {}


# ---- V1 Deterministic normal profile ----
def v1():
    cfg = make_fast_config()
    cfg.conveyor.nominal_line_dwell_time_s = 120.0
    cfg.auto_timing_profiles["AP05"] = AutoTimingProfile(
        profile_id="AP05_V1", station_id="AP05",
        sub_actions=(
            SubActionTiming(id="asm", duration=DurationPolicy(
                type=DurationPolicyType.NORMAL, mean_s=60.0, stddev_s=6.0,
                min_s=48.0, max_s=78.0)),
            SubActionTiming(id="ver", duration=DurationPolicy(
                type=DurationPolicyType.FIXED, seconds=30.0)),
        ),
    )
    line = setup_line(cfg)
    advance_to_before(line, "AP05")
    op = line._ensure_operation_for_position("AP05", "MTR-0001")
    before = line.simulation_time_s
    line.execute_dwell()
    actual = line.simulation_time_s - before
    p = line.dwell_performance
    rows.append(("V1", "AUTO", "DETERMINISTIC", 42,
                 op.timing.effective_duration_s if op.timing else None,
                 actual, p.dwell_overrun_s, p.bottleneck_station_id))
    detail["v1"] = {
        "nominal": op.timing.nominal_duration_s if op.timing else None,
        "effective": op.timing.effective_duration_s if op.timing else None,
        "work_duration": op.work_duration_s,
        "actual_dwell": actual,
    }


# ---- V2 Forced bottleneck AP05=135 ----
def v2():
    cfg = make_fast_config()
    cfg.conveyor.nominal_line_dwell_time_s = 120.0
    cfg.auto_timing_profiles["AP05"] = fixed_profile("AP05", 135.0)
    line = setup_line(cfg)
    advance_to_before(line, "AP05")
    op = line._ensure_operation_for_position("AP05", "MTR-0001")
    before = line.simulation_time_s
    line.execute_dwell()
    actual = line.simulation_time_s - before
    p = line.dwell_performance
    rows.append(("V2", "AUTO", "DETERMINISTIC", 42,
                 op.timing.effective_duration_s, actual,
                 p.dwell_overrun_s, p.bottleneck_station_id))
    detail["v2"] = {
        "effective": op.timing.effective_duration_s,
        "first_dwell": actual,
        "overrun": p.dwell_overrun_s,
        "bottleneck": p.bottleneck_station_id,
        "bottleneck_duration": p.bottleneck_duration_s,
        "state_after": line.conveyor.state.value,
    }


# ---- V3 VARIABLE reproducibility ----
def v3():
    cfg = make_fast_config()
    cfg.timing_behavior = TimingBehavior.VARIABLE
    cfg.auto_timing_profiles["AP01"] = normal_profile("AP01", 50.0, 20.0, 1.0, 100.0)

    def sample(seed):
        c = AssyLineConfig()
        c.conveyor.nominal_line_dwell_time_s = 10.0
        c.conveyor.index_movement_duration_s = 0.0
        for k in c.station_durations:
            c.station_durations[k] = 5.0
        c.timing_behavior = TimingBehavior.VARIABLE
        c.random_seed = seed
        c.auto_timing_profiles["AP01"] = cfg.auto_timing_profiles["AP01"]
        line = AssyLineRuntime(config=c)
        line.produce_sso2_wip(); line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        advance_to_before(line, "AP01")
        return line._ensure_operation_for_position(
            "AP01", "SSO2-0001").timing.effective_duration_s

    a1 = sample(42)
    a2 = sample(42)
    b = sample(43)
    rows.append(("V3", "AUTO", "VARIABLE", "42/42/43",
                 f"{a1:.4f} / {a2:.4f} / {b:.4f}", "-", "-", "-"))
    detail["v3"] = {"seed42_a": a1, "seed42_b": a2, "seed43": b}


# ---- V4 Sample once (snapshot/step) ----
def v4():
    cfg = make_fast_config()
    cfg.timing_behavior = TimingBehavior.VARIABLE
    cfg.auto_timing_profiles["AP01"] = normal_profile("AP01", 50.0, 20.0, 1.0, 100.0)
    line = setup_line(cfg)
    advance_to_before(line, "AP01")
    op = line._ensure_operation_for_position("AP01", "SSO2-0001")
    eid = op.execution_id
    sample1 = op.timing.effective_duration_s
    # multiple snapshots must not mutate/re-sample
    vals = set()
    for _ in range(5):
        snap = build_snapshot(line)
        v = next(a for a in snap.active_operations if a.station_id == "AP01")
        vals.add(v.timing["effective_duration_s"])
    op_after = line.operation_registry.active_for("AP01", "SSO2-0001")
    rows.append(("V4", "AUTO", "VARIABLE", 42, sample1,
                 "snapshots", "unchanged", "same sample"))
    detail["v4"] = {
        "execution_id": eid,
        "sample": sample1,
        "snapshot_samples": sorted(vals),
        "same_execution_id": op_after.execution_id == eid,
        "same_sample": len(vals) == 1,
    }


# ---- V5 MANUAL ----
def v5():
    cfg = make_fast_config()
    cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 999.0)
    line = setup_line(cfg)
    advance_to_before(line, "AP01")
    line.global_run_mode = CompletionMode.MANUAL
    op = line._ensure_operation_for_position("AP01", "SSO2-0001")
    rows.append(("V5", "MANUAL", "-", "-", op.work_duration_s, "-", "-",
                 "timing=%s" % (op.timing,)))
    detail["v5"] = {"work_duration": op.work_duration_s, "timing": op.timing}


# ---- V6 ASSISTED ----
def v6():
    cfg = make_fast_config()
    cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 999.0)
    line = setup_line(cfg)
    advance_to_before(line, "AP01")
    line.global_run_mode = CompletionMode.ASSISTED
    op = line._ensure_operation_for_position("AP01", "SSO2-0001")
    rows.append(("V6", "ASSISTED", "-", "-", op.work_duration_s, "-", "-",
                 "timing=%s" % (op.timing,)))
    detail["v6"] = {"work_duration": op.work_duration_s, "timing": op.timing}


# ---- V7 AP06 retry ----
def v7():
    cfg = make_fast_config()
    cfg.timing_behavior = TimingBehavior.VARIABLE
    cfg.auto_timing_profiles["AP06"] = normal_profile("AP06", 3.0, 0.5, 1.0, 5.0)
    cfg.quality.ap06.scenario = "FAIL_FIRST_THEN_PASS"
    cfg.quality.ap06.max_attempts = 2
    line = setup_line(cfg)
    advance_to_before(line, "AP06")
    line.execute_dwell()
    op_fail = ap_op(line, "AP06")
    eid = op_fail.execution_id
    t1 = op_fail.timing.effective_duration_s
    line.execute_dwell()
    op_after = ap_op(line, "AP06")
    rows.append(("V7", "AUTO", "VARIABLE", 42, t1, "-", "-",
                 "same op=%s sample_same=%s" % (
                     op_after.execution_id == eid,
                     op_after.timing.effective_duration_s == t1)))
    detail["v7"] = {"same_execution_id": op_after.execution_id == eid,
                    "same_sample": op_after.timing.effective_duration_s == t1,
                    "state": op_after.state.value}


# ---- V8 AP08 reinspect ----
def v8():
    cfg = make_fast_config()
    cfg.timing_behavior = TimingBehavior.VARIABLE
    cfg.auto_timing_profiles["AP08"] = normal_profile("AP08", 3.0, 0.5, 1.0, 5.0)
    cfg.quality.ap08.scenario = "FAIL_FIRST_THEN_PASS"
    cfg.quality.ap08.max_attempts = 2
    line = setup_line(cfg)
    advance_to_before(line, "AP08")
    line.execute_dwell()
    op_fail = ap_op(line, "AP08")
    eid = op_fail.execution_id
    t1 = op_fail.timing.effective_duration_s
    line.execute_dwell()
    op_after = ap_op(line, "AP08")
    rows.append(("V8", "AUTO", "VARIABLE", 42, t1, "-", "-",
                 "same op=%s sample_same=%s" % (
                     op_after.execution_id == eid,
                     op_after.timing.effective_duration_s == t1)))
    detail["v8"] = {"same_execution_id": op_after.execution_id == eid,
                    "same_sample": op_after.timing.effective_duration_s == t1,
                    "state": op_after.state.value}


# ---- V9 AP11 ----
def v9():
    cfg = make_fast_config()
    cfg.auto_timing_profiles["AP11"] = fixed_profile("AP11", 5.0)
    line = setup_line(cfg)
    advance_to_before(line, "AP11")
    line.execute_dwell()
    op1 = ap_op(line, "AP11")
    r1 = op1.operation_result.value if op1.operation_result else None
    line.execute_dwell()
    op2 = ap_op(line, "AP11")
    r2 = op2.operation_result.value if op2.operation_result else None
    rows.append(("V9", "AUTO", "DETERMINISTIC", 42, "-", "-", "-",
                 "%s -> %s" % (r1, r2)))
    detail["v9"] = {"step1_result": r1, "step2_result": r2}


# ---- V10 six sub-lines ----
def v10():
    from virtual_factory.assembly.demo_composition import (
        AssyDemoComposition, DemoScenario,
    )
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    comp.initialize()
    seeds = [ctx.config.random_seed for ctx in comp.contexts.values()]
    comp2 = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    comp2.initialize()
    seeds2 = [ctx.config.random_seed for ctx in comp2.contexts.values()]
    rows.append(("V10", "AUTO", "DETERMINISTIC", seeds,
                 "6 sub-lines", "-", "-",
                 "re-init same=%s" % (seeds2 == seeds)))
    detail["v10"] = {"seeds": seeds, "reinit_same": seeds2 == seeds}


for fn in (v1, v2, v3, v4, v5, v6, v7, v8, v9, v10):
    fn()

print("=== AUTO-TIME-01D backend validation rows ===")
print("Scenario | Mode | Behavior | Seed | Effective | ActualDwell | Overrun | Bottleneck | Note")
for r in rows:
    print(" | ".join(str(x) for x in r))
print()
print("=== detail ===")
import json
print(json.dumps(detail, indent=2, default=str))
