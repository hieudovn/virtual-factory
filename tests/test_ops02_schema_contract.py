"""OPS-02-C03 — Runtime / Schema contract reconciliation tests.

Proves that every valid `OperationExecution.to_dict()` emitted by the runtime
validates against `.ai-harness/schemas/operation-execution.schema.json`
(JSON Schema Draft 2020-12), and that the schema fails closed on invalid
payloads.

Contract coherence only — no runtime behavior changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import jsonschema

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / ".ai-harness" / "schemas" / "operation-execution.schema.json"
)

# ═══════════════════════════════════════════════════════════
# Helpers (self-contained; mirror the OPS-02 test fast-config)
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
    target_idx = line.conveyor.positions.index(position)
    for _ in range(target_idx):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()


def last_op(line: AssyLineRuntime, station_id: str, wip_id: str = ""):
    ops = [
        o for o in line.operation_registry._operations.values()
        if o.station_id == station_id and (not wip_id or o.wip_id == wip_id)
    ]
    assert ops, f"no operation recorded for {station_id} {wip_id}"
    return ops[-1]


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema: dict):
    return jsonschema.Draft202012Validator(schema)


def assert_valid(validator, payload: dict) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    assert not errors, (
        f"Expected payload to validate, got errors: "
        f"{[e.message for e in errors]}"
    )


def assert_invalid(validator, payload: dict) -> None:
    errors = list(validator.iter_errors(payload))
    assert errors, "Expected schema validation to fail closed"


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
        "routing_action": None,
        "source": "simulated",
        "attempt_number": 0,
        "terminal": False,
    }


# ═══════════════════════════════════════════════════════════
# Schema file quality
# ═══════════════════════════════════════════════════════════

def test_schema_is_draft_2020_12_with_metadata(schema: dict):
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert schema.get("$id")
    assert schema.get("title")
    assert schema.get("additionalProperties") is False


def test_schema_is_itself_valid(schema: dict):
    jsonschema.Draft202012Validator.check_schema(schema)


# ═══════════════════════════════════════════════════════════
# Positive — representative runtime payloads validate
# ═══════════════════════════════════════════════════════════

def test_case1_simple_auto_execution(validator):
    line = setup_line(make_fast_config())
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP01")
    line.execute_dwell()
    payload = last_op(line, "AP01").to_dict()
    assert payload["state"] == "ELIGIBLE_TO_INDEX"
    assert payload["operation_result"] == "DONE"
    assert_valid(validator, payload)


def test_case2_manual_waiting(validator):
    line = setup_line(make_fast_config())
    advance_to_before(line, "AP01")
    line.global_run_mode = CompletionMode.MANUAL
    line.execute_dwell()
    payload = last_op(line, "AP01").to_dict()
    assert payload["state"] == "AWAITING_COMPLETION"
    assert payload["operation_result"] is None
    assert_valid(validator, payload)


def test_case3_ap03_structured_checklist(validator):
    line = setup_line(make_fast_config())
    advance_to_before(line, "AP03")
    line.global_run_mode = CompletionMode.MANUAL
    line.execute_dwell()
    line.submit_operation_command(
        "AP03", "SSO2-0001", StationCommand.CONFIRM_AND_COMPLETE,
        payload={"checklist": [
            {"item_id": "demo_item_1", "completed": True},
            {"item_id": "demo_item_2", "completed": True},
            {"item_id": "demo_item_3", "completed": True},
        ]},
    )
    payload = last_op(line, "AP03", "SSO2-0001").to_dict()
    assert payload["checklist"] == [
        {"item_id": "demo_item_1", "completed": True},
        {"item_id": "demo_item_2", "completed": True},
        {"item_id": "demo_item_3", "completed": True},
    ]
    assert payload["operation_result"] == "CONFIRMED"
    assert payload["quality_result"] is None
    assert_valid(validator, payload)


def test_case4_ap06_pass(validator):
    line = setup_line(make_fast_config(ap06="PASS"))
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP06")
    line.execute_dwell()
    payload = last_op(line, "AP06", "MTR-0001").to_dict()
    assert payload["operation_result"] == "TEST_COMPLETE"
    assert payload["quality_result"] == "PASS"
    assert_valid(validator, payload)


def test_case5_ap06_fail_retest_pending(validator):
    cfg = make_fast_config(ap06="FAIL_FIRST_THEN_PASS")
    cfg.quality.ap06.max_attempts = 2
    line = setup_line(cfg)
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP06")
    line.execute_dwell()
    assert line.get_current_quality_status("MTR-0001") == QualityStatus.RETEST_PENDING
    payload = last_op(line, "AP06", "MTR-0001").to_dict()
    assert payload["quality_result"] == "FAIL"
    assert_valid(validator, payload)


def test_case6_ap06_terminal_failed_final(validator):
    cfg = make_fast_config(ap06="ALWAYS_FAIL")
    cfg.quality.ap06.max_attempts = 2
    line = setup_line(cfg)
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP06")
    line.execute_dwell()
    line.execute_dwell()
    assert line.get_current_quality_status("MTR-0001") == QualityStatus.FAILED_FINAL
    payload = last_op(line, "AP06", "MTR-0001").to_dict()
    assert payload["state"] == "FAILED"
    assert payload["terminal"] is True
    assert_valid(validator, payload)


def test_case7_ap08_inspection(validator):
    line = setup_line(make_fast_config(ap08="PASS"))
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP08")
    line.execute_dwell()
    payload = last_op(line, "AP08", "MTR-0001").to_dict()
    assert payload["operation_result"] == "INSPECTION_COMPLETE"
    assert payload["quality_result"] == "PASS"
    assert_valid(validator, payload)


def test_case8_ap11_released(validator):
    line = setup_line(make_fast_config())
    line.global_run_mode = CompletionMode.AUTO
    advance_to_before(line, "AP11")
    line.execute_dwell()   # final QC decision
    line.execute_dwell()   # RELEASE
    payload = last_op(line, "AP11", "MTR-0001").to_dict()
    assert payload["operation_result"] == "RELEASED"
    assert_valid(validator, payload)


def test_case9_assisted_waiting(validator):
    line = setup_line(make_fast_config())
    advance_to_before(line, "AP03")
    line.global_run_mode = CompletionMode.ASSISTED
    line.execute_dwell()
    payload = last_op(line, "AP03", "SSO2-0001").to_dict()
    assert payload["state"] == "AWAITING_COMPLETION"
    assert payload["completion_mode"] == "ASSISTED"
    assert_valid(validator, payload)


def test_case10_active_operations_projection_is_a_view():
    """active_operations[] is a UI read model subset, NOT the full contract.

    Its `ActiveOperationView` uses empty-string defaults for enum fields and
    omits source/inputs, so it is intentionally NOT validated against the full
    operation-execution schema. OPS-04-C01 additively exposes
    `proposed_quality_result` and pending `measurements` (observed-before-decision).
    """
    from virtual_factory.assembly.demo_snapshot import ActiveOperationView

    view = ActiveOperationView(
        execution_id="EXEC-00001", station_id="AP01",
        wip_id="SSO2-0001", state="WORKING",
    )
    d = view.to_dict()
    assert set(d) == {
        "execution_id", "station_id", "wip_id", "state",
        "completion_mode", "command", "operation_result", "quality_result",
        "proposed_quality_result", "routing_action", "attempt_number",
        "terminal", "checklist", "measurements",
    }
    assert "source" not in d and "inputs" not in d


# ═══════════════════════════════════════════════════════════
# Negative — schema fails closed
# ═══════════════════════════════════════════════════════════

def test_negative_checklist_missing_item_id(validator):
    p = base_payload()
    p["checklist"] = [{"completed": True}]
    assert_invalid(validator, p)


def test_negative_checklist_non_boolean_completed(validator):
    p = base_payload()
    p["checklist"] = [{"item_id": "demo_item_1", "completed": "yes"}]
    assert_invalid(validator, p)


def test_negative_invalid_completion_mode(validator):
    p = base_payload()
    p["completion_mode"] = "HYBRID"
    assert_invalid(validator, p)


def test_negative_unknown_top_level_property(validator):
    p = base_payload()
    p["unexpected_field"] = 1
    assert_invalid(validator, p)


def test_negative_invalid_state_enum(validator):
    p = base_payload()
    p["state"] = "NOT_A_STATE"
    assert_invalid(validator, p)


def test_negative_missing_required_field(validator):
    for field in ("attempt_number", "terminal", "source", "work_duration_s"):
        p = base_payload()
        del p[field]
        assert_invalid(validator, p)
