"""AUTO-TIME-01C — snapshot timing provenance & bottleneck metrics tests.

Covers the mandatory test list from the AUTO-TIME-01C PM prompt:
OperationExecution timing serialization, schema validation, ActiveOperationView
carriage, snapshot dwell metrics, deterministic bottleneck, reset neutrality,
and side-effect-free snapshot refresh.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import jsonschema

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
)
from virtual_factory.assembly.demo_snapshot import build_snapshot
from virtual_factory.assembly.operation_execution import (
    OperationResult,
    OperationState,
)
from virtual_factory.assembly.station_contracts import CompletionMode

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / ".ai-harness" / "schemas" / "operation-execution.schema.json"
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
# Schema helpers
# ═══════════════════════════════════════════════════════════

def base_payload() -> dict:
    """A minimal valid serialization mirroring OperationExecution.to_dict()."""
    return {
        "execution_id": "EXEC-00001",
        "station_id": "AP01",
        "wip_id": "SSO2-0001",
        "state": "WORKING",
        "started_at_sim_s": 0.0,
        "completed_at_sim_s": None,
        "work_duration_s": 5.0,
        "completion_mode": "AUTO",
        "command": None,
        "inputs": {},
        "checklist": [],
        "measurements": [],
        "operation_result": None,
        "quality_result": None,
        "proposed_quality_result": None,
        "proposed_quality_reason": None,
        "observations": [],
        "routing_action": None,
        "source": "simulated",
        "attempt_number": 0,
        "terminal": False,
        "timing": None,
    }


def validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)


def assert_valid(v, payload: dict) -> None:
    errors = sorted(v.iter_errors(payload), key=lambda e: list(e.path))
    assert not errors, [e.message for e in errors]


def assert_invalid(v, payload: dict) -> None:
    errors = list(v.iter_errors(payload))
    assert errors, "Expected schema validation to fail closed"


# ═══════════════════════════════════════════════════════════
# 1-5. timing serialization + schema
# ═══════════════════════════════════════════════════════════

class TestTimingSerialization:
    def test_to_dict_serializes_timing(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 20.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        d = op.to_dict()
        assert "timing" in d
        assert d["timing"] == op.timing.to_dict()
        assert d["timing"]["profile_id"] == "AP01_TEST_V1"
        assert d["timing"]["effective_duration_s"] == 20.0

    def test_timing_schema_valid_positive(self):
        v = validator()
        p = base_payload()
        p["timing"] = {
            "profile_id": "AP05_AUTO_V1",
            "timing_behavior": "VARIABLE",
            "nominal_duration_s": 90.0,
            "effective_duration_s": 87.4,
            "sub_actions": [
                {"id": "a", "policy": "normal", "nominal_duration_s": 60.0,
                 "effective_duration_s": 57.4, "mean_s": 60.0, "stddev_s": 6.0,
                 "min_s": 48.0, "max_s": 78.0},
                {"id": "b", "policy": "fixed", "nominal_duration_s": 30.0,
                 "effective_duration_s": 30.0, "seconds": 30.0},
            ],
        }
        assert_valid(v, p)

    def test_invalid_timing_schema_rejected(self):
        v = validator()
        p = base_payload()
        p["timing"] = {"profile_id": 123}  # missing required + wrong types
        assert_invalid(v, p)
        p2 = base_payload()
        p2["timing"] = {
            "profile_id": "X", "timing_behavior": "CHAOS",
            "nominal_duration_s": 1, "effective_duration_s": 1, "sub_actions": [],
        }
        assert_invalid(v, p2)

    def test_manual_timing_null_accepted(self):
        v = validator()
        p = base_payload()
        p["completion_mode"] = "MANUAL"
        p["timing"] = None
        assert_valid(v, p)
        # runtime: MANUAL op emits timing null
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 999.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.MANUAL
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.to_dict()["timing"] is None

    def test_auto_fallback_timing_null_accepted(self):
        v = validator()
        p = base_payload()
        p["timing"] = None
        assert_valid(v, p)
        # runtime: AUTO no-profile fallback emits timing null
        cfg = make_fast_config()  # no profiles
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.to_dict()["timing"] is None


# ═══════════════════════════════════════════════════════════
# 6-8. active operation view + snapshot exposure
# ═══════════════════════════════════════════════════════════

class TestSnapshotProjection:
    def test_active_view_carries_work_duration_and_timing(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 25.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        snap = build_snapshot(line)
        view = next(a for a in snap.active_operations if a.station_id == "AP01")
        assert view.work_duration_s == 25.0
        assert view.timing == op.timing.to_dict()

    def test_snapshot_exposes_actual_dwell(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        cfg.auto_timing_profiles["AP05"] = fixed_profile("AP05", 135.0)
        line = AssyLineRuntime(config=cfg)
        w = line.produce_sso2_wip()
        c = line.conveyor.create_carrier("PAL-001")
        line.conveyor.place_carrier(c, "AP05", w)
        line.execute_dwell()
        snap = build_snapshot(line)
        assert snap.actual_dwell_s == 135.0
        assert snap.dwell_overrun_s == 15.0
        assert snap.bottleneck_station_id == "AP05"
        assert snap.bottleneck_duration_s == 135.0
        d = snap.to_dict()
        assert d["actual_dwell_s"] == 135.0
        assert d["bottleneck_station_id"] == "AP05"


# ═══════════════════════════════════════════════════════════
# 9-12. bottleneck semantics
# ═══════════════════════════════════════════════════════════

class TestBottleneckSemantics:
    def test_no_overrun_zero_bottleneck(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        line = AssyLineRuntime(config=cfg)
        w = line.produce_sso2_wip()
        c = line.conveyor.create_carrier("PAL-001")
        line.conveyor.place_carrier(c, "AP01", w)
        line.execute_dwell()  # duration 5 < 120
        perf = line.dwell_performance
        assert perf.actual_dwell_s == 120.0
        assert perf.dwell_overrun_s == 0.0
        assert perf.bottleneck_station_id == ""
        assert perf.bottleneck_duration_s == 0.0

    def test_ap05_135_produces_overrun_and_bottleneck(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        cfg.auto_timing_profiles["AP05"] = fixed_profile("AP05", 135.0)
        line = AssyLineRuntime(config=cfg)
        w = line.produce_sso2_wip()
        c = line.conveyor.create_carrier("PAL-001")
        line.conveyor.place_carrier(c, "AP05", w)
        line.execute_dwell()
        perf = line.dwell_performance
        assert perf.actual_dwell_s == 135.0
        assert perf.dwell_overrun_s == 15.0
        assert perf.bottleneck_station_id == "AP05"
        assert perf.bottleneck_duration_s == 135.0

    def test_tie_deterministic_earlier_position_wins(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 140.0)
        cfg.auto_timing_profiles["AP02"] = fixed_profile("AP02", 140.0)
        line = AssyLineRuntime(config=cfg)
        w1 = line.produce_sso2_wip()
        w2 = line.produce_sso2_wip()
        c1 = line.conveyor.create_carrier("PAL-001")
        line.conveyor.place_carrier(c1, "AP01", w1)
        c2 = line.conveyor.create_carrier("PAL-002")
        line.conveyor.place_carrier(c2, "AP02", w2)
        line.execute_dwell()
        perf = line.dwell_performance
        assert perf.actual_dwell_s == 140.0
        assert perf.bottleneck_station_id == "AP01"  # earlier in position order

    def test_reset_clears_dwell_metrics(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 120.0
        cfg.auto_timing_profiles["AP05"] = fixed_profile("AP05", 135.0)
        line = AssyLineRuntime(config=cfg)
        w = line.produce_sso2_wip()
        c = line.conveyor.create_carrier("PAL-001")
        line.conveyor.place_carrier(c, "AP05", w)
        line.execute_dwell()
        assert line.dwell_performance.actual_dwell_s == 135.0
        line.reset()
        assert line.dwell_performance.actual_dwell_s == 0.0
        assert line.dwell_performance.dwell_overrun_s == 0.0
        assert line.dwell_performance.bottleneck_station_id == ""


# ═══════════════════════════════════════════════════════════
# 13-16. side-effect-free refresh + invariant + retry/AP11
# ═══════════════════════════════════════════════════════════

class TestStabilityAndInvariants:
    def test_snapshot_refresh_does_not_change_sample(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        cfg.auto_timing_profiles["AP01"] = normal_profile(
            "AP01", 50.0, 20.0, 1.0, 100.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        snap1 = build_snapshot(line)
        snap2 = build_snapshot(line)
        v1 = next(a for a in snap1.active_operations if a.station_id == "AP01")
        v2 = next(a for a in snap2.active_operations if a.station_id == "AP01")
        assert v1.timing == v2.timing
        assert v1.timing["effective_duration_s"] == op.timing.effective_duration_s

    def test_timing_effective_equals_work_duration(self):
        cfg = make_fast_config()
        cfg.auto_timing_profiles["AP01"] = fixed_profile("AP01", 25.0)
        line = setup_line(cfg)
        advance_to_before(line, "AP01")
        op = line._ensure_operation_for_position("AP01", "SSO2-0001")
        assert op.timing is not None
        assert op.work_duration_s == op.timing.effective_duration_s

    def test_retry_same_timing_provenance(self):
        cfg = make_fast_config()
        cfg.timing_behavior = TimingBehavior.VARIABLE
        cfg.auto_timing_profiles["AP06"] = normal_profile(
            "AP06", 3.0, 0.5, 1.0, 5.0)
        cfg.quality.ap06.scenario = "FAIL_FIRST_THEN_PASS"
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()  # FAIL -> retry scheduled
        op_fail = ap_op(line, "AP06")
        timing1 = op_fail.timing
        line.execute_dwell()  # retry -> PASS -> complete
        op_after = ap_op(line, "AP06")
        assert op_after.timing is timing1
        assert op_after.to_dict()["timing"] == timing1.to_dict()

    def test_ap11_semantics_unchanged(self):
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
