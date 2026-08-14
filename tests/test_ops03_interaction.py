"""OPS-03 — Station Interaction UI / Inspector Binding tests.

Contract-level and integration tests for the operation-command surface and the
additive read-model projections (`station_contracts[]`, enriched
`active_operations[]`) that the capability-driven renderer consumes.

No frontend business logic is recreated here — these tests pin the runtime
contract the renderer binds to.
"""

from __future__ import annotations

import pytest

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    AssyLineError,
    ConveyorState,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.assembly.operation_execution import (
    OperationResult,
    OperationState,
)
from virtual_factory.assembly.demo_snapshot import build_snapshot
from virtual_factory.assembly.demo_controller import DemoController, DemoScenario


# ═══════════════════════════════════════════════════════════
# Helpers (self-contained; mirror OPS-02 fast-config)
# ═══════════════════════════════════════════════════════════

CHILD = "MTR-0001"
TIPA_YAML = "configs/plants/tipa_assy_demo.yaml"


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


def to_awaiting(line: AssyLineRuntime, position: str) -> tuple:
    """Advance (AUTO) then switch to MANUAL and fire the target station."""
    advance_to_before(line, position)
    line.global_run_mode = CompletionMode.MANUAL
    line.execute_dwell()
    wip_id = line.conveyor.wip_at(position)
    op = line.operation_registry.active_for(position, wip_id)
    assert op is not None, f"no active operation at {position}"
    assert op.state in (OperationState.AWAITING_COMPLETION, OperationState.AWAITING_DECISION)
    return line, op, wip_id


# ═══════════════════════════════════════════════════════════
# Read-model projections (renderer inputs)
# ═══════════════════════════════════════════════════════════

class TestStationContractProjection:
    def test_snapshot_exposes_capability_contracts(self):
        line = setup_line(make_fast_config())
        d = build_snapshot(line, "HAPPY_PATH").to_dict()
        assert "station_contracts" in d
        contracts = {c["station_id"]: c for c in d["station_contracts"]}
        assert set(contracts) == {
            "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
            "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
        }
        # AP03: checklist gate, NOT quality decision
        ap03 = contracts["AP03"]
        assert ap03["capabilities"]["checklist"] is True
        assert ap03["capabilities"]["quality_decision"] is False
        assert ap03["required_action"] == "CONFIRM_AND_COMPLETE"
        assert ap03["allowed_commands"] == ["CONFIRM_AND_COMPLETE"]
        assert ap03["checklist_required_for_action"] == "CONFIRM_AND_COMPLETE"
        # neutral demo checklist templates only (no TIPA facts)
        assert ap03["checklist_items"] == [
            {"item_id": "demo_item_1", "completed": False},
            {"item_id": "demo_item_2", "completed": False},
            {"item_id": "demo_item_3", "completed": False},
        ]
        # pure execution station: DONE only
        ap01 = contracts["AP01"]
        assert ap01["capabilities"]["checklist"] is False
        assert ap01["required_action"] == "DONE"
        assert ap01["checklist_items"] == []
        assert ap01["checklist_required_for_action"] == ""
        # AP11 has checklist CAPABILITY but is NOT gated by the AP03 demo checklist
        ap11 = contracts["AP11"]
        assert ap11["capabilities"]["checklist"] is True
        assert ap11["required_action"] == "RELEASE"
        assert ap11["checklist_items"] == []
        assert ap11["checklist_required_for_action"] == ""

    def test_contract_view_has_only_renderer_fields(self):
        line = setup_line(make_fast_config())
        d = build_snapshot(line, "HAPPY_PATH").to_dict()
        for c in d["station_contracts"]:
            assert set(c.keys()) == {
                "station_id", "capabilities", "default_mode",
                "required_action", "normal_action", "allowed_commands",
                "checklist_items", "checklist_required_for_action",
                "decision_actions", "exception_actions",
                "final_disposition_actions",
            }
            assert set(c["capabilities"].keys()) == {
                "execution", "checklist", "measurement", "quality_decision",
                "exception", "identity_transformation", "final_disposition",
            }

    def test_no_tipa_specific_checklist_facts(self):
        line = setup_line(make_fast_config())
        d = build_snapshot(line, "HAPPY_PATH").to_dict()
        ids = {
            it["item_id"]
            for c in d["station_contracts"]
            for it in c["checklist_items"]
        }
        assert ids == {"demo_item_1", "demo_item_2", "demo_item_3"}


class TestActiveOperationProjection:
    def test_checklist_field_is_present(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        d = build_snapshot(line, "HAPPY_PATH").to_dict()
        ap03_ops = [o for o in d["active_operations"] if o["station_id"] == "AP03"]
        assert ap03_ops
        assert "checklist" in ap03_ops[0]

    def test_operation_correlates_station_and_wip(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP05")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP05")
        d = build_snapshot(line, "HAPPY_PATH").to_dict()
        op = [o for o in d["active_operations"]
              if o["station_id"] == "AP05" and o["wip_id"] == wip]
        assert len(op) == 1
        assert op[0]["state"] == "AWAITING_COMPLETION"
        assert op[0]["completion_mode"] == "MANUAL"


# ═══════════════════════════════════════════════════════════
# Command surface (runtime truth; renderer never mutates directly)
# ═══════════════════════════════════════════════════════════

class TestPureExecutionCommand:
    def test_ap05_manual_done_completes(self):
        line = setup_line(make_fast_config())
        _, op, wip = to_awaiting(line, "AP05")
        assert op.state == OperationState.AWAITING_COMPLETION
        line.submit_operation_command("AP05", wip, StationCommand.DONE)
        assert line.operation_registry.active_for("AP05", wip) is None
        assert line.conveyor.is_position_complete("AP05") is True

    def test_auto_does_not_surface_action_required(self):
        line = setup_line(make_fast_config())
        line.global_run_mode = CompletionMode.AUTO
        advance_to_before(line, "AP05")
        line.execute_dwell()
        snap = build_snapshot(line, "HAPPY_PATH")
        awaiting = [
            o for o in snap.active_operations
            if o.station_id == "AP05"
            and o.state in ("AWAITING_COMPLETION", "AWAITING_DECISION")
        ]
        assert awaiting == []

    def test_stale_command_rejected(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.AUTO
        line.execute_dwell()  # AUTO completes → no active op
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP01", "SSO2-0001", StationCommand.DONE)


class TestChecklistCommand:
    def test_ap03_incomplete_rejected(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", wip, StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": []},
            )
        assert line.conveyor.is_position_complete("AP03") is False

    def test_ap03_complete_accepted_confirmed(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        line.submit_operation_command(
            "AP03", wip, StationCommand.CONFIRM_AND_COMPLETE,
            payload={"checklist": [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
            ]},
        )
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP03" and o.wip_id == wip]
        assert found[-1].operation_result == OperationResult.CONFIRMED
        assert found[-1].quality_result is None
        assert line.conveyor.is_position_complete("AP03") is True


class TestChecklistRequiredSetValidation:
    """OPS-03-C01: server validates the EXACT required set (authority)."""

    def _awaiting_ap03(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        return line, wip

    def _submit(self, line, wip, items):
        line.submit_operation_command(
            "AP03", wip, StationCommand.CONFIRM_AND_COMPLETE,
            payload={"checklist": items},
        )

    def test_missing_checklist_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP03", wip, StationCommand.CONFIRM_AND_COMPLETE)

    def test_one_of_three_subset_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [{"item_id": "demo_item_1", "completed": True}])
        assert line.conveyor.is_position_complete("AP03") is False

    def test_two_of_three_subset_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
            ])
        assert line.conveyor.is_position_complete("AP03") is False

    def test_unknown_extra_item_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
                {"item_id": "not_a_real_item", "completed": True},
            ])

    def test_duplicate_required_item_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_3", "completed": True},
            ])

    def test_required_item_incomplete_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": False},
                {"item_id": "demo_item_3", "completed": True},
            ])

    def test_malformed_item_rejected(self):
        line, wip = self._awaiting_ap03()
        with pytest.raises(AssyLineError):
            self._submit(line, wip, [
                {"item_id": "demo_item_1", "completed": True},
                {"item_id": "demo_item_2", "completed": True},
                "demo_item_3",
            ])

    def test_full_set_accepted(self):
        line, wip = self._awaiting_ap03()
        self._submit(line, wip, [
            {"item_id": "demo_item_1", "completed": True},
            {"item_id": "demo_item_2", "completed": True},
            {"item_id": "demo_item_3", "completed": True},
        ])
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP03" and o.wip_id == wip]
        assert found[-1].operation_result == OperationResult.CONFIRMED
        assert found[-1].quality_result is None
        assert line.conveyor.is_position_complete("AP03") is True


class TestAP11NoChecklistInherit:
    def test_release_works_without_demo_checklist(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        # Step 1: final QC decision (no demo checklist required)
        line.submit_operation_command("AP11", wip, StationCommand.CONFIRM,
                                      payload={"decision": "PASS"})
        # Step 2: RELEASE — distinct final disposition, no checklist
        line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP11"]
        assert found[-1].operation_result == OperationResult.RELEASED
        assert line.get_wip(wip).lifecycle.value == "released"


class TestStationActionException:
    def test_ap03_hold_marks_stay_non_eligible(self):
        line = setup_line(make_fast_config())
        _, op, wip = to_awaiting(line, "AP03")
        line.submit_station_action("AP03", wip, "HOLD")
        assert op.routing_action == "STAY_AT_STATION"
        assert op.state == OperationState.HELD
        assert op.operation_result is None
        assert op.quality_result is None
        assert line.conveyor.is_position_complete("AP03") is False

    def test_unsupported_action_fails_closed(self):
        line = setup_line(make_fast_config())
        _, _, wip = to_awaiting(line, "AP03")
        with pytest.raises(AssyLineError):
            line.submit_station_action("AP03", wip, "LINE_OUT")

    def test_ap11_hold_keeps_non_released(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        line.submit_station_action("AP11", wip, "HOLD")
        op = line.operation_registry.active_for("AP11", wip)
        assert op.routing_action == "STAY_AT_STATION"
        assert line.get_wip(wip).lifecycle.value != "released"
        assert line.conveyor.is_position_complete("AP11") is False


class TestQualityDecisionCommand:
    def test_ap06_pass_read_from_runtime(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, _, wip = to_awaiting(line, "AP06")
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP06"]
        assert found[-1].quality_result == "PASS"
        assert found[-1].operation_result == OperationResult.TEST_COMPLETE

    def test_ap06_manual_requires_decision(self):
        line = setup_line(make_fast_config(ap06="PASS"))
        _, _, wip = to_awaiting(line, "AP06")
        # MANUAL with no decision must fail closed
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP06", wip, StationCommand.CONFIRM)
        # invalid decision must fail closed
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP06", wip, StationCommand.CONFIRM, payload={"decision": "MAYBE"})

    def test_ap06_fail_retest_keeps_wip_at_ap06(self):
        cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP06")
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "FAIL"})
        assert line.get_current_quality_status(wip) == QualityStatus.RETEST_PENDING
        assert line.conveyor.is_position_complete("AP06") is False
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP06"]
        assert found[-1].quality_result == "FAIL"
        # retest attempt → PASS, then eligible
        line.submit_operation_command(
            "AP06", wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
        assert line.get_current_quality_status(wip) == QualityStatus.CLEAR
        assert line.conveyor.is_position_complete("AP06") is True

    def test_ap08_ng_reinspect_stays_at_ap08(self):
        cfg = make_fast_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP08")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP08")
        line.submit_operation_command(
            "AP08", wip, StationCommand.CONFIRM, payload={"decision": "NG"})
        assert line.get_current_quality_status(wip) == QualityStatus.REINSPECT_PENDING
        assert line.conveyor.is_position_complete("AP08") is False


class TestIdentityCommand:
    def test_join_idempotent_no_duplicate_child(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP04")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP04")
        assert line.motor_count == 0
        line.submit_operation_command("AP04", wip, StationCommand.JOIN_COMPLETE)
        assert line.motor_count == 1
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP04", wip, StationCommand.JOIN_COMPLETE)
        assert line.motor_count == 1


class TestReleaseCommand:
    def test_release_only_when_awaiting_and_marks_released(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP11")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP11")
        # RELEASE before final QC is blocked
        with pytest.raises(AssyLineError):
            line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        # Final QC PASS then RELEASE
        line.submit_operation_command("AP11", wip, StationCommand.CONFIRM,
                                      payload={"decision": "PASS"})
        line.submit_operation_command("AP11", wip, StationCommand.RELEASE)
        found = [o for o in line.operation_registry._operations.values()
                 if o.station_id == "AP11"]
        assert found[-1].operation_result == OperationResult.RELEASED
        assert line.get_wip(wip).lifecycle.value == "released"


class TestAssistedInteraction:
    def test_assisted_pure_execution_auto_submits(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP01")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        assert line.conveyor.is_position_complete("AP01") is True

    def test_assisted_checklist_waits(self):
        line = setup_line(make_fast_config())
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.ASSISTED
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP03")
        op = line.operation_registry.active_for("AP03", wip)
        assert op.state == OperationState.AWAITING_COMPLETION
        assert line.conveyor.is_position_complete("AP03") is False


# ═══════════════════════════════════════════════════════════
# Controller integration (run mode + command adapter)
# ═══════════════════════════════════════════════════════════

class TestControllerIntegration:
    def test_run_mode_surfaces_waiting_operation(self):
        ctrl = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        ctrl.initialize()
        ctrl.set_run_mode(CompletionMode.MANUAL)
        assert ctrl.run_mode == CompletionMode.MANUAL
        snap = ctrl.step()
        d = snap.to_dict()
        awaiting = [
            o for o in d["active_operations"]
            if o["state"] in ("AWAITING_COMPLETION", "AWAITING_DECISION")
        ]
        assert awaiting, "MANUAL mode should surface a waiting operation"

    def test_auto_surfaces_no_waiting_operation(self):
        ctrl = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        ctrl.initialize()
        snap = ctrl.step()
        d = snap.to_dict()
        waiting = [
            o for o in d["active_operations"]
            if o["state"] in ("AWAITING_COMPLETION", "AWAITING_DECISION")
            and o["completion_mode"] == "AUTO"
        ]
        # AUTO operations resolve within the dwell; they should not persist as
        # action-required waiting states (quality retest aside, which is not
        # action-required either).
        assert waiting == []


# ═══════════════════════════════════════════════════════════
# API endpoints (thin adapter)
# ═══════════════════════════════════════════════════════════

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402
from virtual_factory.ui.api import create_app  # noqa: E402


class TestOperationApi:
    def test_snapshot_has_contracts_and_operations(self):
        client = TestClient(create_app(config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0))
        resp = client.post("/assy-demo/reset", json={"scenario": "HAPPY_PATH"})
        assert resp.status_code == 200
        d = resp.json()
        assert "station_contracts" in d
        assert "active_operations" in d

    def test_run_mode_endpoint(self):
        client = TestClient(create_app(config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0))
        assert client.post("/assy-demo/run-mode", json={"mode": "MANUAL"}).status_code == 200
        assert client.post("/assy-demo/run-mode", json={"mode": "BOGUS"}).status_code == 400

    def test_operation_command_fail_closed(self):
        client = TestClient(create_app(config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0))
        client.post("/assy-demo/reset", json={"scenario": "HAPPY_PATH"})
        # missing fields → 400
        assert client.post("/assy-demo/operation-command", json={}).status_code == 400
        # stale/invalid target → 409 (runtime rejection surfaced, not swallowed)
        resp = client.post(
            "/assy-demo/operation-command",
            json={"station_id": "AP01", "wip_id": "NOPE", "command": "DONE"},
        )
        assert resp.status_code == 409
        assert "detail" in resp.json()
