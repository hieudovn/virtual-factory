"""OPS-03-C01-R1 — StationContract loader / schema coherence tests.

Ensures YAML-loaded contracts preserve the same checklist-gate semantics as
in-code contracts, fail closed on contradictory combinations, and that the
schema is coherent with the runtime contract serialization.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

import jsonschema

from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
    build_default_assy_contracts,
    load_station_contracts_from_yaml,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    AssyLineError,
    ConveyorState,
)
from virtual_factory.assembly.operation_execution import OperationResult

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / ".ai-harness" / "schemas" / "station-contract.schema.json"
)
EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs" / "design" / "station-contracts.example.yaml"
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


def load_yaml_text(text: str):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_station_contracts_from_yaml(path)
    finally:
        os.unlink(path)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════
# YAML loader round-trip semantics
# ═══════════════════════════════════════════════════════════

class TestYamlLoaderRoundTrip:
    def test_ap03_preserves_checklist_metadata(self):
        contracts = load_station_contracts_from_yaml(str(EXAMPLE_PATH))
        ap03 = contracts["AP03"]
        assert ap03.checklist_items == ("demo_item_1", "demo_item_2", "demo_item_3")
        assert ap03.checklist_required_for_action == StationCommand.CONFIRM_AND_COMPLETE

    def test_ap11_checklist_capability_no_gate_valid(self):
        contracts = load_station_contracts_from_yaml(str(EXAMPLE_PATH))
        ap11 = contracts["AP11"]
        assert ap11.capabilities.checklist is True
        assert ap11.checklist_items == ()
        assert ap11.checklist_required_for_action is None

    def test_ap11_does_not_inherit_ap03_checklist(self):
        contracts = load_station_contracts_from_yaml(str(EXAMPLE_PATH))
        assert contracts["AP11"].checklist_items != contracts["AP03"].checklist_items
        assert contracts["AP11"].checklist_items == ()

    def test_yaml_ap03_enforces_exact_set_at_runtime(self):
        contracts = load_station_contracts_from_yaml(str(EXAMPLE_PATH))
        line = setup_line(make_fast_config())
        line.station_contracts = contracts
        advance_to_before(line, "AP03")
        line.global_run_mode = CompletionMode.MANUAL
        line.execute_dwell()
        wip = line.conveyor.wip_at("AP03")
        # partial subset rejected
        with pytest.raises(AssyLineError):
            line.submit_operation_command(
                "AP03", wip, StationCommand.CONFIRM_AND_COMPLETE,
                payload={"checklist": [
                    {"item_id": "demo_item_1", "completed": True},
                ]},
            )
        assert line.conveyor.is_position_complete("AP03") is False
        # full set accepted
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


# ═══════════════════════════════════════════════════════════
# Invalid contract combinations (fail closed)
# ═══════════════════════════════════════════════════════════

class TestInvalidContractCombinations:
    def test_gate_without_checklist_capability_rejected(self):
        with pytest.raises(ValueError):
            load_yaml_text(
                "stations:\n"
                "  - station_id: X01\n"
                "    capabilities:\n"
                "      execution: true\n"
                "      checklist: false\n"
                "    required_action: CONFIRM_AND_COMPLETE\n"
                "    checklist_items: [demo_item_1]\n"
                "    checklist_required_for_action: CONFIRM_AND_COMPLETE\n"
            )

    def test_gate_with_empty_items_rejected(self):
        with pytest.raises(ValueError):
            load_yaml_text(
                "stations:\n"
                "  - station_id: X02\n"
                "    capabilities:\n"
                "      execution: true\n"
                "      checklist: true\n"
                "    required_action: CONFIRM_AND_COMPLETE\n"
                "    checklist_required_for_action: CONFIRM_AND_COMPLETE\n"
            )

    def test_gate_not_in_allowed_commands_rejected(self):
        with pytest.raises(ValueError):
            load_yaml_text(
                "stations:\n"
                "  - station_id: X03\n"
                "    capabilities:\n"
                "      execution: true\n"
                "      checklist: true\n"
                "    normal_action: CONFIRM_AND_COMPLETE\n"
                "    required_action: CONFIRM_AND_COMPLETE\n"
                "    checklist_items: [demo_item_1]\n"
                "    checklist_required_for_action: RELEASE\n"
            )

    def test_duplicate_checklist_items_rejected(self):
        with pytest.raises(ValueError):
            load_yaml_text(
                "stations:\n"
                "  - station_id: X04\n"
                "    capabilities:\n"
                "      execution: true\n"
                "      checklist: true\n"
                "    required_action: CONFIRM_AND_COMPLETE\n"
                "    checklist_items: [demo_item_1, demo_item_1]\n"
                "    checklist_required_for_action: CONFIRM_AND_COMPLETE\n"
            )

    def test_empty_checklist_item_id_rejected(self):
        with pytest.raises(ValueError):
            load_yaml_text(
                "stations:\n"
                "  - station_id: X05\n"
                "    capabilities:\n"
                "      execution: true\n"
                "      checklist: true\n"
                "    required_action: CONFIRM_AND_COMPLETE\n"
                "    checklist_items: ['']\n"
                "    checklist_required_for_action: CONFIRM_AND_COMPLETE\n"
            )


# ═══════════════════════════════════════════════════════════
# Schema coherence
# ═══════════════════════════════════════════════════════════

class TestSchemaCoherence:
    def test_schema_parses(self):
        schema = load_schema()
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_checklist_description_is_neutral(self):
        schema = load_schema()
        desc = schema["properties"]["capabilities"]["properties"]["checklist"]["description"]
        # no longer implies checklist is always a completion gate
        assert "requires checklist item confirmation" not in desc
        assert "supports checklist-based interaction" in desc

    def test_ap03_contract_validates(self):
        validator = jsonschema.Draft202012Validator(load_schema())
        ap03 = build_default_assy_contracts()["AP03"].to_dict()
        assert not list(validator.iter_errors(ap03))

    def test_ap11_contract_validates(self):
        validator = jsonschema.Draft202012Validator(load_schema())
        ap11 = build_default_assy_contracts()["AP11"].to_dict()
        assert not list(validator.iter_errors(ap11))

    def test_invalid_gate_shape_fails(self):
        validator = jsonschema.Draft202012Validator(load_schema())
        bad = build_default_assy_contracts()["AP03"].to_dict()
        bad["checklist_required_for_action"] = "BOGUS"
        assert list(validator.iter_errors(bad))
