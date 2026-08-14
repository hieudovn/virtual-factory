"""OPS-04-C01 — Production Decision Semantics & Manual E2E Readiness.

Pins the runtime contract for:
  A. HOLD as a first-class HELD state + explicit RESUME recovery.
  B. Operator/exception holds distinguishable from quality retry holds.
  C. Measurement causality: observations are generated BEFORE the decision and
     are NEVER rewritten based on the eventual disposition.
  D. Machine proposal (`proposed_quality_result`) visible before decision.
  E. Explicit routing (CONTINUE / STAY_AT_STATION).
  F. AP11 final QC separated from the RELEASE final disposition.
"""

from __future__ import annotations

import pytest

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    AssyLineError,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.quality_records import (
    QualityStatus,
    MeasurementValue,
)
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.assembly.operation_execution import (
    OperationResult,
    OperationState,
)
from virtual_factory.assembly.demo_snapshot import build_snapshot


CHILD = "MTR-0001"


def make_fast_config(ap06: str = "PASS", ap08: str = "PASS") -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = ap06
    c.quality.ap08.scenario = ap08
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


def to_awaiting(line: AssyLineRuntime, position: str):
    """Advance (AUTO) then switch to MANUAL and fire the target station."""
    advance_to_before(line, position)
    line.global_run_mode = CompletionMode.MANUAL
    line.execute_dwell()
    wip_id = line.conveyor.wip_at(position)
    op = line.operation_registry.active_for(position, wip_id)
    assert op is not None, f"no active operation at {position}"
    assert op.state in (OperationState.AWAITING_COMPLETION,
                        OperationState.AWAITING_DECISION)
    return line, op, wip_id


# ═══════════════════════════════════════════════════════════
# A. HOLD lifecycle + RESUME recovery (10 items)
# ═══════════════════════════════════════════════════════════

class TestHoldLifecycle:
    def test_hold_from_awaiting_completion_becomes_held(self):
        line = setup_line(make_fast_config())
        _, op, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        assert op.state == OperationState.HELD
        assert op.routing_action == "STAY_AT_STATION"

    def test_hold_from_awaiting_decision_becomes_held(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        op = line.operation_registry.active_for("AP11", wip)
        assert op.state == OperationState.AWAITING_DECISION
        line.submit_station_action("AP11", wip, "HOLD")
        assert op.state == OperationState.HELD
        assert op.routing_action == "STAY_AT_STATION"

    def test_hold_from_working_rejected(self):
        # WORKING is a transient pre-completion state; force it directly to
        # pin the HOLD state precondition (awaiting states only).
        line = setup_line(make_fast_config())
        contract = line.station_contracts["AP03"]
        op = line.operation_registry.start(
            "AP03", CHILD, contract, CompletionMode.MANUAL, 0.0)
        op.transition(OperationState.WORKING)
        with pytest.raises(AssyLineError):
            line.submit_station_action("AP03", CHILD, "HOLD")

    def test_resume_non_quality_returns_to_awaiting_completion(self):
        line = setup_line(make_fast_config())
        _, op, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        assert op.state == OperationState.HELD
        line.submit_station_action("AP03", wip, "RESUME")
        assert op.state == OperationState.AWAITING_COMPLETION
        assert op.routing_action is None

    def test_resume_quality_returns_to_awaiting_decision(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        op = line.operation_registry.active_for("AP11", wip)
        line.submit_station_action("AP11", wip, "HOLD")
        assert op.state == OperationState.HELD
        line.submit_station_action("AP11", wip, "RESUME")
        assert op.state == OperationState.AWAITING_DECISION

    def test_resume_returns_to_held_awaiting_completion_state(self):
        # AP11 after final QC PASS is AWAITING_COMPLETION; HOLD then RESUME
        # must return to AWAITING_COMPLETION, not re-open the QC decision.
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        line.submit_operation_command(
            "AP11", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        op = line.operation_registry.active_for("AP11", wip)
        assert op.state == OperationState.AWAITING_COMPLETION
        line.submit_station_action("AP11", wip, "HOLD")
        assert op.state == OperationState.HELD
        line.submit_station_action("AP11", wip, "RESUME")
        assert op.state == OperationState.AWAITING_COMPLETION

    def test_resume_from_non_held_rejected(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        with pytest.raises(AssyLineError):
            line.submit_station_action("AP03", wip, "RESUME")

    def test_completion_command_while_held_rejected(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP03", wip, StationCommand.CONFIRM_AND_COMPLETE)

    def test_held_wip_never_indexes(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        line.execute_dwell()
        assert line.conveyor.is_position_complete("AP03") is False
        assert line.conveyor.state != ConveyorState.READY_TO_INDEX

    def test_hold_projected_as_operator_hold(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        snap = build_snapshot(line)
        assert snap.production.operator_holds == 1
        assert snap.production.active_quality_holds == 0

    def test_hold_then_resume_then_complete(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        line.submit_station_action("AP03", wip, "RESUME")
        line.submit_operation_command(
            "AP03", wip, StationCommand.CONFIRM_AND_COMPLETE,
            payload={"checklist": [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
            ]})
        assert line.conveyor.is_position_complete("AP03") is True


# ═══════════════════════════════════════════════════════════
# C/D/E. AP06 measurement causality (8 items)
# ═══════════════════════════════════════════════════════════

class TestAP06Causality:
    def test_observation_generated_before_decision(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, op, _ = to_awaiting(line, "AP06")
        assert op.state == OperationState.AWAITING_DECISION
        assert op.proposed_quality_result == "PASS"
        assert len(op.measurements) == 3
        assert op.proposed_quality_reason is not None

    def test_pass_proposal_has_coherent_evidence(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, op, _ = to_awaiting(line, "AP06")
        assert op.proposed_quality_result == "PASS"
        assert op.proposed_quality_reason == {
            "code": "DEMO_IN_RANGE", "source": "simulated_test"}
        assert all(MeasurementValue(**m).in_range for m in op.measurements)

    def test_fail_proposal_has_coherent_anomaly(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, _ = to_awaiting(line, "AP06")
        assert op.proposed_quality_result == "FAIL"
        assert op.proposed_quality_reason == {
            "code": "DEMO_OUT_OF_RANGE", "source": "simulated_test"}
        mvs = [MeasurementValue(**m) for m in op.measurements]
        assert not mvs[0].in_range and mvs[0].name == "R_U-V"
        assert mvs[1].in_range and mvs[2].in_range

    def test_fail_does_not_rewrite_measurements(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP06")
        observed = [dict(m) for m in op.measurements]
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        rec = line.get_quality_history(wip).records_for("AP06")[0]
        assert [m.to_dict() for m in rec.measurements] == observed  # frozen evidence
        assert not rec.measurements[0].in_range
        assert rec.measurements[1].in_range and rec.measurements[2].in_range

    def test_override_preserves_evidence_and_proposal(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP06")
        assert op.proposed_quality_result == "FAIL"
        observed = [dict(m) for m in op.measurements]
        reason = dict(op.proposed_quality_reason)
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        rec = line.get_quality_history(wip).records_for("AP06")[0]
        # operator override recorded, but evidence and proposal stay frozen
        assert rec.disposition == "PASS"
        assert [m.to_dict() for m in rec.measurements] == observed
        assert not rec.measurements[0].in_range
        assert op.proposed_quality_result == "FAIL"
        assert op.proposed_quality_reason == reason

    def test_quality_record_matches_observation_on_fail(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP06")
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        rec = line.get_quality_history(wip).records_for("AP06")[0]
        assert rec.disposition == "FAIL"
        assert len(rec.measurements) == 3

    def test_operator_decision_overrides_proposal(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP06")
        assert op.proposed_quality_result == "FAIL"
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert line.conveyor.is_position_complete("AP06") is True

    def test_manual_requires_decision(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, _, wip = to_awaiting(line, "AP06")
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP06", wip, StationCommand.CONFIRM)

    def test_fail_routes_stay_at_station(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP06")
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        assert line.get_current_quality_status(wip) == QualityStatus.RETEST_PENDING
        assert op.routing_action == "STAY_AT_STATION"
        assert line.conveyor.is_position_complete("AP06") is False

    def test_pass_routes_continue_and_completes(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, op, wip = to_awaiting(line, "AP06")
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert op.operation_result == OperationResult.TEST_COMPLETE
        assert op.routing_action == "CONTINUE"
        assert line.conveyor.is_position_complete("AP06") is True


# ═══════════════════════════════════════════════════════════
# C/D/E. AP08 measurement/proposal causality (5 items)
# ═══════════════════════════════════════════════════════════

class TestAP08Causality:
    def test_proposal_generated_before_decision(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, _ = to_awaiting(line, "AP08")
        assert op.state == OperationState.AWAITING_DECISION
        assert op.proposed_quality_result == "NG"

    def test_ng_proposal_has_neutral_observation(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, _ = to_awaiting(line, "AP08")
        assert op.proposed_quality_result == "NG"
        assert op.proposed_quality_reason == {
            "code": "demo_visual_rule_1", "source": "simulated_vision"}
        assert any(o["result"] == "anomaly" for o in op.observations)
        assert all(o["observation_id"].startswith("demo_visual_observation_")
                   for o in op.observations)

    def test_pass_proposal_has_neutral_observation(self):
        cfg = make_fast_config(ap08="PASS")
        line = setup_line(cfg)
        _, op, _ = to_awaiting(line, "AP08")
        assert op.proposed_quality_result == "PASS"
        assert all(o["result"] == "ok" for o in op.observations)

    def test_override_does_not_rewrite_observation(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP08")
        observed = [dict(o) for o in op.observations]
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert op.observations == observed  # frozen pre-decision evidence
        assert op.proposed_quality_result == "NG"

    def test_ng_decision_reinspects(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP08")
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "NG"})
        assert line.get_current_quality_status(wip) == QualityStatus.REINSPECT_PENDING
        assert op.routing_action == "STAY_AT_STATION"
        assert line.conveyor.is_position_complete("AP08") is False

    def test_operator_pass_overrides_ng_proposal(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP08")
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert op.operation_result == OperationResult.INSPECTION_COMPLETE

    def test_pass_routes_continue(self):
        cfg = make_fast_config(ap08="PASS")
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP08")
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert op.routing_action == "CONTINUE"
        assert line.conveyor.is_position_complete("AP08") is True

    def test_retry_regenerates_proposal(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        _, op, wip = to_awaiting(line, "AP08")
        assert op.proposed_quality_result == "NG"
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "NG"})
        # After NG, op → FAILED → retry scheduled; fresh observation next dwell.
        assert op.proposed_quality_result is None
        assert op.proposed_quality_reason is None
        assert op.measurements == []
        assert op.observations == []


# ═══════════════════════════════════════════════════════════
# F. AP11 final QC vs RELEASE separation (6 items)
# ═══════════════════════════════════════════════════════════

class TestAP11Separation:
    def test_final_qc_then_release_two_step(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        op = line.operation_registry.active_for("AP11", wip)
        assert op.state == OperationState.AWAITING_DECISION
        line.submit_operation_command(
            "AP11", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert op.state == OperationState.AWAITING_COMPLETION
        assert op.operation_result == OperationResult.CONFIRMED
        assert line.get_wip(wip).lifecycle != WipLifecycle.RELEASED
        line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        assert line.get_wip(wip).lifecycle == WipLifecycle.RELEASED
        assert op.operation_result == OperationResult.RELEASED
        assert line.conveyor.is_position_complete("AP11") is True

    def test_release_blocked_before_qc_pass(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP11", wip, StationCommand.RELEASE)

    def test_negative_qc_fails_closed(self):
        # AP11 decision surface is PASS-only; FAIL must not become REINSPECT.
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP11", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        assert line.get_wip(wip).lifecycle != WipLifecycle.RELEASED
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert line.conveyor.is_position_complete("AP11") is False

    def test_negative_proposal_fails_closed(self):
        # Scenario-derived FAIL at final QC must not silently route to
        # REINSPECT_PENDING; it fails closed.
        cfg = make_fast_config()
        cfg.quality.ap11.scenario = "ALWAYS_FAIL"
        line = setup_line(cfg)
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        op = line.operation_registry.active_for("AP11", wip)
        assert op.proposed_quality_result == "FAIL"
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP11", wip, StationCommand.CONFIRM)
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert line.get_wip(wip).lifecycle != WipLifecycle.RELEASED

    def test_hold_blocks_release(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        line.submit_operation_command(
            "AP11", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        line.submit_station_action("AP11", wip, "HOLD")
        op = line.operation_registry.active_for("AP11", wip)
        assert op.state == OperationState.HELD
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        assert line.get_wip(wip).lifecycle != WipLifecycle.RELEASED

    def test_qc_fail_is_rejected_not_terminal(self):
        # Negative QC at final QC is rejected (fail closed), never mapped to
        # FAILED_FINAL / REINSPECT_PENDING by the generic quality mapping.
        cfg = make_fast_config()
        cfg.quality.ap11.max_attempts = 1
        line = setup_line(cfg)
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP11", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        op = line.operation_registry.active_for("AP11", wip)
        assert op.state == OperationState.AWAITING_DECISION
        assert op.terminal is False

    def test_release_marks_released_and_continue(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        line.submit_operation_command(
            "AP11", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP11"]
        assert found[-1].operation_result == OperationResult.RELEASED
        assert found[-1].routing_action == "CONTINUE"
        assert line.get_wip(wip).lifecycle == WipLifecycle.RELEASED


# ═══════════════════════════════════════════════════════════
# Dwell regression — completed positions must not re-execute
# ═══════════════════════════════════════════════════════════

class TestCompletedPositionDwellFix:
    def test_ap04_cannot_join_twice_while_blocked(self):
        line = setup_line(make_fast_config())
        line.produce_sso2_wip()   # SSO2-0002
        line.produce_rso2_wip()   # RSO2-0002
        advance_to_before(line, "AP04")   # SSO2-0001 at AP04
        line.introduce_to_assy("SSO2-0002", "PAL-002")  # blocks PRE-ASSY
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip04 = line.conveyor.wip_at("AP04")
        line.submit_operation_command("AP04", wip04, StationCommand.JOIN_COMPLETE)
        assert line.conveyor.state != ConveyorState.READY_TO_INDEX
        # Extra dwell while blocked must NOT re-JOIN the child at AP04.
        line.execute_dwell()
        records = list(line.genealogy.all_records())
        assert len(records) == 1
        assert records[0].child_wip_id == "MTR-0001"

    def test_completed_pure_execution_station_count_not_repeated(self):
        line = setup_line(make_fast_config())
        line.produce_sso2_wip()   # SSO2-0002
        line.produce_rso2_wip()   # RSO2-0002
        advance_to_before(line, "AP01")   # SSO2-0001 at AP01
        line.introduce_to_assy("SSO2-0002", "PAL-002")  # blocks PRE-ASSY
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip01 = line.conveyor.wip_at("AP01")
        line.submit_operation_command("AP01", wip01, StationCommand.DONE)
        assert line.conveyor.state != ConveyorState.READY_TO_INDEX
        before = line.get_wip(wip01).station_count
        line.execute_dwell()
        assert line.get_wip(wip01).station_count == before

    def test_completed_quality_station_no_duplicate_records(self):
        line = setup_line(make_fast_config())
        line.produce_sso2_wip()   # SSO2-0002 (blocker)
        line.produce_rso2_wip()   # RSO2-0002
        advance_to_before(line, "AP06")   # AUTO: MTR-0001 at AP06
        line.introduce_to_assy("SSO2-0002", "PAL-002")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip06 = line.conveyor.wip_at("AP06")
        line.submit_operation_command(
            "AP06", wip06, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.conveyor.state != ConveyorState.READY_TO_INDEX
        before = len(line.get_quality_history(wip06).records_for("AP06"))
        line.execute_dwell()
        after = len(line.get_quality_history(wip06).records_for("AP06"))
        assert after == before == 1

    def test_next_index_proceeds_normally(self):
        line = setup_line(make_fast_config())
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        advance_to_before(line, "AP01")
        line.introduce_to_assy("SSO2-0002", "PAL-002")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip01 = line.conveyor.wip_at("AP01")
        line.submit_operation_command("AP01", wip01, StationCommand.DONE)
        # Unblock PRE-ASSY → all complete → index proceeds normally.
        wip_pre = line.conveyor.wip_at("PRE-ASSY")
        line.submit_operation_command("PRE-ASSY", wip_pre, StationCommand.DONE)
        assert line.conveyor.all_occupied_complete() is True
        line.execute_dwell()
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX

    def test_incomplete_stations_are_never_skipped(self):
        line = setup_line(make_fast_config())
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        advance_to_before(line, "AP01")
        line.introduce_to_assy("SSO2-0002", "PAL-002")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip01 = line.conveyor.wip_at("AP01")
        line.submit_operation_command("AP01", wip01, StationCommand.DONE)
        # PRE-ASSY is still incomplete; an extra dwell must keep it waiting,
        # never skip it.
        assert line.conveyor.is_position_complete("PRE-ASSY") is False
        line.execute_dwell()
        wip_pre = line.conveyor.wip_at("PRE-ASSY")
        op = line.operation_registry.active_for("PRE-ASSY", wip_pre)
        assert op is not None
        assert op.state == OperationState.AWAITING_COMPLETION


# ═══════════════════════════════════════════════════════════
# Synthetic-fact hygiene
# ═══════════════════════════════════════════════════════════

def test_no_unconfirmed_tipa_checklist_facts_in_runtime():
    """No TIPA-looking domain facts may be hard-coded in the runtime."""
    import inspect
    import virtual_factory.assembly.line_runtime as lr
    src = inspect.getsource(lr)
    for fact in ("surface_quality", "label_presence", "assembly_alignment",
                 "packaging_integrity", "label_correct",
                 "documentation_complete", "mechanical_prep_ok",
                 "visual_check_ok", "measurement_subset_ok"):
        assert fact not in src, f"unconfirmed TIPA-looking fact {fact!r} in runtime"
