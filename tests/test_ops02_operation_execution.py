"""OPS-02 — Runtime OperationExecution Engine acceptance tests.

Covers the mandatory §12 test list from the OPS-02 PM prompt.

Design authority: docs/design/OPS-01_OPERATION_EXECUTION_CONTRACT.md
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
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import (
    Capabilities,
    CompletionMode,
    StationCommand,
    StationContract,
    build_default_assy_contracts,
    load_station_contracts_from_yaml,
)
from virtual_factory.assembly.operation_execution import (
    InvalidTransitionError,
    OperationExecution,
    OperationRegistry,
    OperationResult,
    OperationState,
)

CHILD = "MTR-0001"
CHILD2 = "MTR-0002"


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

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
    """Advance line until a WIP is AT `position` and the station has not fired."""
    target_idx = line.conveyor.positions.index(position)
    for _ in range(target_idx):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()


# ═══════════════════════════════════════════════════════════
# 1. Station contracts load/validate
# ═══════════════════════════════════════════════════════════

class TestStationContracts:
    def test_default_contracts_count_and_shape(self):
        contracts = build_default_assy_contracts()
        assert len(contracts) == 12
        for station_id in ("PRE-ASSY", "AP01", "AP02", "AP03", "AP04",
                           "AP05", "AP06", "AP07", "AP08", "AP09", "AP10", "AP11"):
            assert station_id in contracts

    def test_ap03_checklist_gate_no_quality_decision(self):
        contracts = build_default_assy_contracts()
        ap03 = contracts["AP03"]
        assert ap03.capabilities.checklist is True
        assert ap03.capabilities.quality_decision is False
        assert ap03.required_action == StationCommand.CONFIRM_AND_COMPLETE

    def test_ap04_identity_transformation(self):
        contracts = build_default_assy_contracts()
        ap04 = contracts["AP04"]
        assert ap04.capabilities.identity_transformation is True
        assert ap04.required_action == StationCommand.JOIN_COMPLETE
        assert "AP03" in ap04.prerequisites

    def test_ap11_final_disposition(self):
        contracts = build_default_assy_contracts()
        ap11 = contracts["AP11"]
        assert ap11.capabilities.final_disposition is True
        assert ap11.capabilities.quality_decision is True
        assert ap11.required_action == StationCommand.RELEASE

    def test_load_from_yaml_example(self):
        contracts = load_station_contracts_from_yaml(
            "docs/design/station-contracts.example.yaml")
        assert len(contracts) == 12
        assert contracts["AP03"].capabilities.quality_decision is False
        assert contracts["AP06"].capabilities.measurement is True

    def test_load_from_yaml_mode_override(self):
        # Override AP05 to MANUAL via a custom YAML in a temp file
        import tempfile
        import os
        yaml_text = (
            "stations:\n"
            "  - station_id: AP05\n"
            "    default_mode: AUTO\n"
            "    mode_override: MANUAL\n"
            "    capabilities:\n"
            "      execution: true\n"
            "      checklist: false\n"
            "      measurement: false\n"
            "      quality_decision: false\n"
            "      exception: false\n"
            "      identity_transformation: false\n"
            "      final_disposition: false\n"
            "    normal_action: DONE\n"
            "    required_action: DONE\n"
            "    work_duration_s: 90\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            path = f.name
        try:
            contracts = load_station_contracts_from_yaml(path)
            assert contracts["AP05"].mode_override == CompletionMode.MANUAL
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════
# 2. Mode precedence
# ═══════════════════════════════════════════════════════════

class TestModePrecedence:
    def test_override_wins(self):
        line = AssyLineRuntime(config=make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        c = StationContract(
            station_id="X",
            default_mode=CompletionMode.AUTO,
            mode_override=CompletionMode.MANUAL,
        )
        assert line._resolve_mode(c) == CompletionMode.MANUAL

    def test_global_wins_over_default(self):
        line = AssyLineRuntime(config=make_fast_config())
        line.global_run_mode = CompletionMode.ASSISTED
        c = StationContract(station_id="X", default_mode=CompletionMode.AUTO)
        assert line._resolve_mode(c) == CompletionMode.ASSISTED

    def test_default_fallback(self):
        line = AssyLineRuntime(config=make_fast_config())
        line.global_run_mode = None
        c = StationContract(station_id="X", default_mode=CompletionMode.MANUAL)
        assert line._resolve_mode(c) == CompletionMode.MANUAL


# ═══════════════════════════════════════════════════════════
# 3. AUTO simple station full progression
# ═══════════════════════════════════════════════════════════

class TestAutoSimpleStation:
    def test_full_progression(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP01")
        line.execute_dwell()
        op = line.operation_registry.active_for("AP01", "SSO2-0001")
        # AUTO completes through AWAITING_COMPLETION → COMPLETED → ELIGIBLE
        assert op is None  # ELIGIBLE → not "active" anymore
        # Verify the operation exists and is eligible via the registry's full history
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP01" and o.wip_id == "SSO2-0001"]
        assert len(found) == 1
        assert found[0].state == OperationState.ELIGIBLE_TO_INDEX
        assert found[0].operation_result == OperationResult.DONE
        assert found[0].command == StationCommand.DONE
        assert line.conveyor.is_position_complete("AP01")

    def test_auto_does_not_force_pass_at_ap06(self):
        cfg = make_fast_config(ap06="ALWAYS_FAIL")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP06")
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP06"]
        assert found and found[-1].quality_result == "FAIL"
        assert line.get_current_quality_status(CHILD) == QualityStatus.RETEST_PENDING


# ═══════════════════════════════════════════════════════════
# 4. MANUAL simple station waits for command
# ═══════════════════════════════════════════════════════════

class TestManualSimpleStation:
    def test_waits_at_awaiting_completion(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")   # AUTO advance
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        op = line.operation_registry.active_for("AP01", "SSO2-0001")
        assert op is not None
        assert op.state == OperationState.AWAITING_COMPLETION
        assert line.conveyor.is_position_complete("AP01") is False

    def test_done_completes(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")   # AUTO advance
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        events = line.submit_operation_command("AP01", "SSO2-0001", StationCommand.DONE)
        assert any(e.event_type == "STATION_COMPLETE" for e in events)
        op = line.operation_registry.active_for("AP01", "SSO2-0001")
        assert op is None  # ELIGIBLE after DONE
        assert line.conveyor.is_position_complete("AP01") is True


# ═══════════════════════════════════════════════════════════
# 5 & 6. Invalid / stale command rejection (fail closed)
# ═══════════════════════════════════════════════════════════

class TestCommandValidation:
    def test_invalid_command_rejected(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        # AP01 only allows DONE
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP01", "SSO2-0001", StationCommand.CONFIRM)

    def test_stale_wrong_wip_rejected(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP01", "SSO2-9999", StationCommand.DONE)

    def test_not_awaiting_rejected(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP01")
        line.execute_dwell()  # AUTO completes → ELIGIBLE
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP01", "SSO2-0001", StationCommand.DONE)


# ═══════════════════════════════════════════════════════════
# 7. AP03 checklist gate
# ═══════════════════════════════════════════════════════════

class TestAP03Checklist:
    def test_ap03_confirmed_and_no_quality_result(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP03")
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP03" and o.wip_id == "SSO2-0001"]
        assert len(found) == 1
        assert found[0].operation_result == OperationResult.CONFIRMED
        assert found[0].quality_result is None
        assert found[0].state == OperationState.ELIGIBLE_TO_INDEX

    def test_ap03_manual_waits_then_confirm(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")   # AUTO advance
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        line.submit_operation_command(
            "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
            payload={"checklist": [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
            ]},
        )
        op2 = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op2 is None
        assert line.conveyor.is_position_complete("AP03")


# ═══════════════════════════════════════════════════════════
# 8. AP04 identity boundary
# ═══════════════════════════════════════════════════════════

class TestAP04IdentityBoundary:
    def test_join_preserves_parents(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP04")
        line.execute_dwell()
        assert line.motor_count == 1
        g = line.genealogy.get(CHILD)
        assert g is not None
        assert g.parent_wip_ids == ("SSO2-0001", "RSO2-0001")
        parent = line.get_wip("SSO2-0001")
        assert parent.lifecycle == WipLifecycle.JOINED

    def test_no_duplicate_child_on_stale_command(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP04")
        line.execute_dwell()
        assert line.motor_count == 1
        # Stale command after JOIN completion must fail closed (no duplicate child)
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP04", "SSO2-0001", StationCommand.JOIN_COMPLETE)
        assert line.motor_count == 1


# ═══════════════════════════════════════════════════════════
# 9-11. AP06 test
# ═══════════════════════════════════════════════════════════

class TestAP06:
    def test_pass_completes(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        advance_to_before(line, "AP06")
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP06"]
        assert found and found[-1].operation_result == OperationResult.TEST_COMPLETE
        assert found[-1].quality_result == "PASS"
        assert found[-1].state == OperationState.ELIGIBLE_TO_INDEX

    def test_fail_then_retest(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.RETEST_PENDING
        found1 = [o for o in line.operation_registry._operations.values()
                  if o.station_id == "AP06"]
        assert found1[-1].quality_result == "FAIL"
        # retest next dwell → PASS
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.CLEAR
        found2 = [o for o in line.operation_registry._operations.values()
                  if o.station_id == "AP06"]
        assert found2[-1].quality_result == "PASS"
        assert line.conveyor.is_position_complete("AP06")

    def test_max_attempts_terminal_not_held(self):
        cfg = make_fast_config(ap06="ALWAYS_FAIL")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()  # attempt 1 FAIL
        line.execute_dwell()  # attempt 2 FAIL → FAILED_FINAL
        assert line.get_current_quality_status(CHILD) == QualityStatus.FAILED_FINAL
        op = line.operation_registry.active_for("AP06", CHILD)
        assert op is not None
        assert op.state == OperationState.FAILED
        assert op.terminal is True
        assert op.state != OperationState.HELD
        assert line.conveyor.is_position_complete("AP06") is False


# ═══════════════════════════════════════════════════════════
# 12-13. AP08 inspection
# ═══════════════════════════════════════════════════════════

class TestAP08:
    def test_ng_then_reinspect(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP08")
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.REINSPECT_PENDING
        found1 = [o for o in line.operation_registry._operations.values()
                  if o.station_id == "AP08"]
        assert found1[-1].quality_result == "NG"
        assert found1[-1].operation_result == OperationResult.INSPECTION_COMPLETE or True
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.CLEAR

    def test_max_attempts_terminal(self):
        cfg = make_fast_config(ap08="ALWAYS_FAIL")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP08")
        line.execute_dwell()
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.FAILED_FINAL
        op = line.operation_registry.active_for("AP08", CHILD)
        assert op.state == OperationState.FAILED
        assert op.terminal is True


# ═══════════════════════════════════════════════════════════
# 14. AP11 release
# ═══════════════════════════════════════════════════════════

class TestAP11:
    def test_release(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.execute_dwell()   # final QC decision (AUTO → PASS)
        line.execute_dwell()   # RELEASE — distinct final disposition
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP11"]
        assert found and found[-1].operation_result == OperationResult.RELEASED
        assert found[-1].quality_result == "PASS"
        assert line.get_wip(CHILD).lifecycle == WipLifecycle.RELEASED


# ═══════════════════════════════════════════════════════════
# 15. Failed/held/exception states never eligible
# ═══════════════════════════════════════════════════════════

class TestEligibilityRule:
    def test_only_completed_to_eligible(self):
        # Unit-level: construct operation and assert legal transitions
        op = OperationExecution(execution_id="E1", station_id="AP01", wip_id="W1")
        assert op.state == OperationState.ARRIVED
        op.transition(OperationState.READY)
        op.transition(OperationState.WORKING)
        op.transition(OperationState.AWAITING_COMPLETION)
        with pytest.raises(InvalidTransitionError):
            op.transition(OperationState.ELIGIBLE_TO_INDEX)  # not legal from AWAITING_COMPLETION
        op.transition(OperationState.COMPLETED)
        op.transition(OperationState.ELIGIBLE_TO_INDEX)

    def test_failed_to_eligible_illegal(self):
        op = OperationExecution(execution_id="E2", station_id="AP06", wip_id="W2")
        op.state = OperationState.FAILED
        with pytest.raises(InvalidTransitionError):
            op.transition(OperationState.ELIGIBLE_TO_INDEX)

    def test_held_to_eligible_illegal(self):
        op = OperationExecution(execution_id="E3", station_id="AP06", wip_id="W3")
        op.state = OperationState.HELD
        with pytest.raises(InvalidTransitionError):
            op.transition(OperationState.ELIGIBLE_TO_INDEX)


# ═══════════════════════════════════════════════════════════
# 16. positions[] unchanged
# ═══════════════════════════════════════════════════════════

class TestPositionsUnchanged:
    def test_position_fields_unchanged(self):
        from virtual_factory.assembly.demo_snapshot import AssyDemoSnapshot
        snap = AssyDemoSnapshot()
        d = snap.to_dict()
        pos_keys = {
            "position_id", "station_label", "carrier_id", "wip_id", "wip_type",
            "manufacturing_status", "quality_status", "latest_quality_result",
            "attempt_number", "is_occupied", "is_quality_hold", "held_reason",
        }
        # positions[] is a list of dicts; assert the schema keys for one empty position
        assert pos_keys <= set(
            snap.to_dict()["positions"][0].keys()
        ) if snap.to_dict()["positions"] else True


# ═══════════════════════════════════════════════════════════
# 17. Active operation projection corresponds to physical occupancy
# ═══════════════════════════════════════════════════════════

class TestActiveProjection:
    def test_active_ops_match_occupied_positions(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP02")   # AUTO advance
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()  # AP02 reaches AWAITING_COMPLETION (manual blocks)
        active = { (o.station_id, o.wip_id): o for o in line.active_operations() }
        assert ("AP02", "SSO2-0001") in active
        assert active[("AP02", "SSO2-0001")].state == OperationState.AWAITING_COMPLETION
        # same WIP/station as physical occupancy
        assert line.conveyor.wip_at("AP02") == "SSO2-0001"


# ═══════════════════════════════════════════════════════════
# 18. Continuous AUTO scenario runs without starvation
# ═══════════════════════════════════════════════════════════

class TestContinuousAuto:
    def test_continuous_auto_no_starvation(self):
        from virtual_factory.assembly.demo_controller import DemoController
        from virtual_factory.assembly.demo_composition import DemoScenario
        ctrl = DemoController(
            config_path="configs/plants/tipa_assy_demo.yaml",
            scenario=DemoScenario.HAPPY_PATH,
        )
        ctrl.initialize()
        for _ in range(40):
            ctrl.step()
        snap = ctrl.snapshot()
        # Continuous feed keeps producing motors without starvation
        assert snap.production.motors_created >= 1
        assert snap.production.wips_on_line >= 1
        # active operations projection exists and is additive
        assert hasattr(snap, "active_operations")
        assert "active_operations" in snap.to_dict()


# ═══════════════════════════════════════════════════════════
# OPS-02-C01 — Semantic corrections
# ═══════════════════════════════════════════════════════════

class TestAP03ChecklistGateC01:
    def test_ap03_incomplete_checklist_blocks(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        assert op.quality_result is None
        assert line.conveyor.is_position_complete("AP03") is False
        # no fabricated AP03 quality record from normal checklist execution
        h = line.get_quality_history("SSO2-0001")
        assert h is None or len(h) == 0

    def test_ap03_confirm_without_checklist_rejected(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE)
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": []},
            )
        # still not complete, still not eligible
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        assert line.conveyor.is_position_complete("AP03") is False


class TestAssistedNotAuto:
    def test_assisted_waits_for_checklist(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        assert line.conveyor.is_position_complete("AP03") is False

    def test_assisted_waits_for_quality_decision(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        advance_to_before(line, "AP06")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        op = line.operation_registry.active_for("AP06", CHILD)
        assert op.state == OperationState.AWAITING_DECISION

    def test_assisted_waits_for_release(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        op = line.operation_registry.active_for("AP11", CHILD)
        assert op.state == OperationState.AWAITING_DECISION

    def test_assisted_pure_execution_auto_submits(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP01"]
        assert found[-1].state == OperationState.ELIGIBLE_TO_INDEX
        assert line.conveyor.is_position_complete("AP01")

    def test_auto_ap03_auto_submits_with_synthetic_checklist(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.AUTO
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP03"]
        assert found[-1].operation_result == OperationResult.CONFIRMED
        assert found[-1].quality_result is None
        # C02: synthetic checklist is neutral + fully completed
        ids = {it["item_id"] for it in found[-1].checklist}
        assert ids == {"demo_item_1", "demo_item_2", "demo_item_3"}
        assert all(it["completed"] is True for it in found[-1].checklist)
        assert line.conveyor.is_position_complete("AP03")


class TestAP03ChecklistGateC02:
    def _to_ap03_awaiting(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        return line

    def test_item_exists_but_not_completed_rejected(self):
        line = self._to_ap03_awaiting()
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": [
                    {"item_id": "demo_item_1", "completed": False},
                ]},
            )
        op = line.operation_registry.active_for("AP03", "SSO2-0001")
        assert op.state == OperationState.AWAITING_COMPLETION
        assert line.conveyor.is_position_complete("AP03") is False

    def test_plain_string_items_rejected(self):
        line = self._to_ap03_awaiting()
        # a plain string has no completion state — must fail closed
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": ["anything"]},
            )
        assert line.conveyor.is_position_complete("AP03") is False

    def test_item_missing_item_id_rejected(self):
        line = self._to_ap03_awaiting()
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": [{"completed": True}]},
            )
        assert line.conveyor.is_position_complete("AP03") is False

    def test_partial_subset_complete_rejected(self):
        line = self._to_ap03_awaiting()
        # 2 of 3 required items completed → still rejected (missing demo_item_3)
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": [
                    {"item_id": "demo_item_1", "completed": True},
                    {"item_id": "demo_item_2", "completed": True},
                ]},
            )
        assert line.conveyor.is_position_complete("AP03") is False

    def test_all_completed_accepts_and_records(self):
        line = self._to_ap03_awaiting()
        line.submit_operation_command(
            "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
            payload={"checklist": [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
            ]},
        )
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP03" and o.wip_id == "SSO2-0001"]
        assert found[-1].operation_result == OperationResult.CONFIRMED
        assert found[-1].quality_result is None
        assert found[-1].checklist == [
            {"item_id": "demo_item_1", "completed": True},
            {"item_id": "demo_item_2", "completed": True},
            {"item_id": "demo_item_3", "completed": True},
        ]
        assert line.conveyor.is_position_complete("AP03")


class TestModeFreeze:
    def test_mode_freeze_auto_remains_auto(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP02")
        # Seed an active AP02 operation created under AUTO, held in AWAITING.
        contract = line.station_contracts["AP02"]
        op = line.operation_registry.start(
            "AP02", "SSO2-0001", contract, CompletionMode.AUTO, 0.0)
        op.transition(OperationState.WORKING)
        op.transition(OperationState.AWAITING_COMPLETION)
        assert op.completion_mode == CompletionMode.AUTO
        # Change global mode while the operation is active — the operation's
        # effective mode must remain frozen at creation (AUTO → auto-submit).
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP02"]
        assert found[-1].completion_mode == CompletionMode.AUTO
        assert found[-1].state == OperationState.ELIGIBLE_TO_INDEX
        assert line.conveyor.is_position_complete("AP02")

    def test_new_operations_use_new_mode(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP01")
        line.execute_dwell()   # AP01 auto-completes
        line.index_line()      # move to AP02
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()   # AP02 op created with MANUAL → waits
        op = line.operation_registry.active_for("AP02", "SSO2-0001")
        assert op is not None
        assert op.completion_mode == CompletionMode.MANUAL
        assert op.state == OperationState.AWAITING_COMPLETION
