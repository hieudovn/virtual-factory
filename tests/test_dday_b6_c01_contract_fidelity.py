"""DDAY-B6-C01 — VF→PlantOS contract fidelity.

Governed by .ai-harness/tasks/DDAY-B6-C01.json. The Whole Factory Overview
stays accepted. Capper/Compressor helpers are not edited.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

from virtual_factory.workspaces.plantos_compat import (
    compatibility_status,
    exact_minimal_gap,
)
from virtual_factory.workspaces.plantos_export import (
    ACCEPTED_AREAS,
    ADAPTER_ROLE,
    CONTRACT_VERSION,
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    PLANT_SOURCE_ID,
    REQUIRED_ENVELOPE_FIELDS,
    REQUIRED_SIGNAL_FAMILIES,
    TOPIC_PATTERN,
    UnmappedExportError,
    dictionary_summary,
    load_export_dictionary,
    lookup_event_entry,
    lookup_signal_entry,
    map_selected_event,
    map_selected_signal,
    map_snapshot,
    overview_from_snapshot,
    selected_event_entries,
    selected_signal_keys,
    utc_timestamp,
)
from virtual_factory.workspaces.bottled_water import BottledWaterFactory

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
DICTIONARY_YAML = WORKSPACE / "plantos_export.dictionary.yaml"
FROZEN_PROTOCOL_HASHES = {
    "src/virtual_factory/protocols/mqtt_gateway.py":
        "f540ef429dbcedfef4baeddbe2f5c41c152d547f057a4a3d93762c6406414872",
    "src/virtual_factory/telemetry/signal_value.py":
        "67fb1387495cecc3e9b9f39954166d01bdec2738f3d18331f74d79811fd1c009",
}
TOPIC_RE = re.compile(
    r"^virtual-factory/bottled-water-dday/(signal|event)/[A-Z0-9-]+/[A-Za-z0-9_]+$"
)
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _factory(**kwargs) -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML, **kwargs)


def _run(factory: BottledWaterFactory, steps: int, dt: float = 1.0) -> None:
    for _ in range(steps):
        factory.step(dt)


def collect_durable_examples(steps: int = 330) -> dict:
    """Accepted B5 trajectories only. No scenario-fidelity expansion."""
    factory = _factory()
    factory.start()
    capper_warning = None
    capper_downtime = None
    capper_recovery = None
    compressor_warning = None
    compressor_undersupply = None
    classified = False
    for _ in range(steps):
        factory.step(1.0)
        snap = factory.snapshot()
        capper_phase = (snap.get("scenario") or {}).get("phase")
        compressor_phase = (snap.get("compressor_scenario") or {}).get("phase")
        if capper_phase == "WARNING" and capper_warning is None:
            capper_warning = _phase_bundle(factory, "capper_warning")
        if capper_phase == "INTERMITTENT_STOP" and capper_downtime is None:
            capper_downtime = _phase_bundle(factory, "capper_downtime")
        if capper_phase == "RECOVERY" and capper_recovery is None:
            capper_recovery = _phase_bundle(factory, "capper_recovery")
        if compressor_phase == "LOW_PRESSURE_WARNING" and compressor_warning is None:
            factory.classify("downtime_code", "DT-AIR", target="compressor")
            factory.classify("failure_code", "FAIL-AIR", target="BW-UT-CMP01")
            classified = True
            compressor_warning = _phase_bundle(factory, "compressor_warning")
        if compressor_phase == "UNDERSUPPLY" and compressor_undersupply is None:
            compressor_undersupply = _phase_bundle(factory, "compressor_undersupply")
    final = factory.plantos_export()
    history = factory._export_sink.historian(limit=-1)
    return {
        "classified": classified,
        "capper_warning": capper_warning,
        "capper_downtime": capper_downtime,
        "capper_recovery": capper_recovery,
        "compressor_warning": compressor_warning,
        "compressor_undersupply": compressor_undersupply,
        "final": final,
        "process_history": [
            item for item in history
            if item["asset_id"] == "BW-WT-TK01" and item["signal_or_event"] == "level"
        ],
        "condition_history": [
            item for item in history
            if item["asset_id"] == "BW-FP-CAP01"
            and item["signal_or_event"] == "motor_current"
        ],
        "energy_history": [
            item for item in history
            if item["asset_id"] == "BW-UT-PWR01"
            and item["signal_or_event"] == "plant_active_power"
        ],
    }


def _phase_bundle(factory: BottledWaterFactory, label: str) -> dict:
    bundle = factory.plantos_export()
    return {
        "label": label,
        "simulation_time_s": bundle["simulation_time_s"],
        "capper_phase": (factory.snapshot().get("scenario") or {}).get("phase"),
        "compressor_phase": (factory.snapshot().get("compressor_scenario") or {}).get("phase"),
        "events": bundle["events"],
        "current_values": bundle["current_values"],
        "sample_envelopes": [
            item["payload"]
            for item in bundle["current_values"][:4]
        ] + [
            item["payload"]
            for item in bundle["events"][-4:]
        ],
    }


def test_c01_01_versioned_utc_envelope():
    factory = _factory()
    factory.start()
    _run(factory, 8)
    messages = map_snapshot(factory.snapshot())
    assert messages
    for message in messages:
        payload = message.payload
        for field in REQUIRED_ENVELOPE_FIELDS:
            assert field in payload, field
        assert payload["contract_version"] == CONTRACT_VERSION
        assert payload["workspace_id"] == "bottled-water-dday"
        assert payload["plant_source_id"] == PLANT_SOURCE_ID
        assert payload["source_id"] == message.asset_id
        assert UTC_RE.match(payload["timestamp"]), payload["timestamp"]
        assert payload["timestamp"] == utc_timestamp(payload["simulation_time_s"])
        assert payload["quality"] == "GOOD"
        assert payload["provenance"] == "SIMULATED_RAW"
        assert "unit" in payload or message.kind == "event"
        assert "timestamp_s" not in payload


def test_c01_02_mqtt_topic_and_source_ids_remain_compatible():
    factory = _factory()
    factory.start()
    _run(factory, 4)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    for message in messages:
        assert TOPIC_RE.match(message.topic), message.topic
        assert message.topic == f"virtual-factory/bottled-water-dday/{message.kind}/{message.asset_id}/{message.signal_or_event}"
        assert message.payload["asset_id"] == message.payload["source_id"]
    assert TOPIC_PATTERN == "virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}"
    hierarchy = {node["source_id"] for node in snapshot["hierarchy"]}
    for message in messages:
        assert message.payload["source_id"] in hierarchy


def test_c01_03_selected_dictionary_covers_required_families():
    selected = load_export_dictionary(DICTIONARY_YAML)
    assert selected["contract_version"] == CONTRACT_VERSION
    assert selected["fail_closed"] is True
    summary = dictionary_summary(selected)
    assert set(summary["families"]) == set(REQUIRED_SIGNAL_FAMILIES)
    required_fields = (
        "semantic_role", "datatype", "unit", "cadence",
        "provenance", "quality", "plantos_mapping_key",
    )
    for entry in selected["signals"]:
        for field in required_fields:
            assert entry.get(field), (entry, field)
        assert entry["plantos_mapping_key"].startswith("plant:BW-DEMO-01/")
    keys = set(selected_signal_keys(selected))
    assert ("BW-WT-TK01", "level") in keys
    assert ("BW-FP", "total_count") in keys
    assert ("BW-FP-CAP01", "motor_current") in keys
    assert ("BW-UT-CMP01", "air_pressure") in keys
    assert ("BW-WH-FG01", "inventory_count") in keys
    assert ("BW-UT-PWR01", "plant_active_power") in keys
    event_types = {entry["event_type"] for entry in selected_event_entries(selected)}
    assert {
        "ALARM_RAISED", "ALARM_CLEARED", "DOWNTIME_START",
        "DOWNTIME_END", "SCENARIO_PHASE_CHANGED", "MACHINE_STATE_CHANGED",
    } <= event_types


def test_c01_04_mapper_fail_closed_on_unmapped_signal_or_event():
    factory = _factory()
    factory.start()
    _run(factory, 6)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    exported = {(item.asset_id, item.signal_or_event) for item in messages if item.kind == "signal"}
    assert exported <= set(selected_signal_keys())
    assert ("BW-FP-RIN01", "operating_state") not in exported
    with pytest.raises(UnmappedExportError):
        lookup_signal_entry("BW-FP-RIN01", "operating_state")
    with pytest.raises(UnmappedExportError):
        map_selected_signal(snapshot, "BW-FP-RIN01", "operating_state")
    with pytest.raises(UnmappedExportError):
        lookup_event_entry("NOT_A_DDAY_EVENT")
    with pytest.raises(UnmappedExportError):
        map_selected_event(snapshot, {"event_type": "NOT_A_DDAY_EVENT", "source_id": "BW-FP"})


def test_c01_05_in_memory_sink_is_adapter_only():
    factory = _factory()
    factory.start()
    _run(factory, 4)
    bundle = factory.plantos_export()
    assert bundle["ingestion_path"] == "local_in_memory_plantos_compatible"
    assert bundle["adapter_role"] == ADAPTER_ROLE
    assert bundle["plantos_ingestion_proven"] is False
    assert bundle["plantos_historian_proven"] is False
    assert bundle["plantos_compatibility"]["vf_adapter_only"] is True
    assert bundle["plantos_compatibility"]["wtp_ingest_used"] is False
    assert "not_plantos_historian" in bundle["adapter_role"]


def test_c01_06_plantos_compatibility_records_exact_gap():
    status = compatibility_status(live_probe=True)
    gap = exact_minimal_gap()
    assert status["plantos_ingestion_proven"] is False
    assert status["plantos_historian_proven"] is False
    assert status["plantos_repo_present_locally"] is False
    assert status["plantos_named_repos"] == []
    assert "github.com/hieudovn/virtual-factory" in status["environment_repos"]
    assert "Grant this agent read access to the current PlantOS repo" in gap[
        "minimal_sa_authorization_required"
    ][0]
    assert status["gap"]["requires_plantos_production_changes"] == "UNKNOWN_UNTIL_REPO_ACCESS"
    serialised = json.dumps(status).lower()
    assert "wtp" in serialised
    assert "not authorized as a plantos substitute" in serialised


@pytest.fixture(scope="module")
def durable_examples() -> dict:
    return collect_durable_examples()


def test_c01_07_durable_capper_warning_downtime_recovery(durable_examples):
    examples = durable_examples
    assert examples["capper_warning"]["capper_phase"] == "WARNING"
    assert examples["capper_downtime"]["capper_phase"] == "INTERMITTENT_STOP"
    assert examples["capper_recovery"]["capper_phase"] == "RECOVERY"
    types = {item["payload"]["event_type"] for item in examples["final"]["events"]}
    assert "ALARM_RAISED" in types
    assert "DOWNTIME_START" in types
    assert "DOWNTIME_END" in types or "ALARM_CLEARED" in types
    assert "SCENARIO_PHASE_CHANGED" in types
    warning_events = [
        item for item in examples["capper_warning"]["events"]
        if item["payload"].get("event_type") == "SCENARIO_PHASE_CHANGED"
        and item["asset_id"] == "BW-FP-CAP01"
    ]
    assert warning_events
    assert warning_events[-1]["payload"]["contract_version"] == CONTRACT_VERSION
    assert warning_events[-1]["payload"]["source_id"] == "BW-FP-CAP01"
    downtime = [
        item for item in examples["final"]["events"]
        if item["payload"].get("event_type") == "DOWNTIME_START"
        and item["asset_id"] == "BW-FP-CAP01"
    ]
    assert downtime
    assert downtime[0]["payload"]["timestamp"].endswith("Z")


def test_c01_08_durable_compressor_warning_undersupply_classification(durable_examples):
    examples = durable_examples
    assert examples["compressor_warning"]["compressor_phase"] == "LOW_PRESSURE_WARNING"
    assert examples["compressor_undersupply"]["compressor_phase"] == "UNDERSUPPLY"
    assert examples["classified"] is True
    events = examples["final"]["events"]
    compressor_events = [
        item for item in events if item["asset_id"] == "BW-UT-CMP01"
    ]
    types = {item["payload"]["event_type"] for item in compressor_events}
    assert "ALARM_RAISED" in types
    assert "SCENARIO_PHASE_CHANGED" in types
    classified = [
        item for item in compressor_events
        if item["payload"].get("downtime_code") == "DT-AIR"
        or item["payload"].get("failure_code") == "FAIL-AIR"
    ]
    assert classified
    for item in classified:
        assert item["payload"]["contract_version"] == CONTRACT_VERSION
        assert item["payload"]["plant_source_id"] == PLANT_SOURCE_ID
        assert item["payload"]["source_id"] == "BW-UT-CMP01"


def test_c01_09_process_and_condition_history_samples(durable_examples):
    examples = durable_examples
    process = examples["process_history"]
    condition = examples["condition_history"]
    energy = examples["energy_history"]
    assert len(process) >= 8
    assert len(condition) >= 8
    assert len(energy) >= 8
    process_times = [item["payload"]["simulation_time_s"] for item in process]
    condition_times = [item["payload"]["simulation_time_s"] for item in condition]
    assert max(process_times) > min(process_times)
    assert max(condition_times) > min(condition_times)
    utc_stamps = {item["payload"]["timestamp"] for item in process + condition}
    assert len(utc_stamps) >= 2
    for item in process + condition + energy:
        assert item["payload"]["timestamp"].endswith("Z")
        assert item["payload"]["contract_version"] == CONTRACT_VERSION
        assert item["payload"]["plantos_mapping_key"]


def test_c01_10_overview_remains_accepted_five_area_view():
    factory = _factory()
    factory.start()
    _run(factory, 6)
    overview = overview_from_snapshot(factory.snapshot())
    assert [area["id"] for area in overview["areas"]] == list(ACCEPTED_AREAS)
    assert overview["drill_down"] == {"BW-FP": "/bottled-water-demo"}
    page = (
        REPO_ROOT / "src/virtual_factory/ui/static/bottled_water_overview.html"
    ).read_text(encoding="utf-8")
    for area_id in ACCEPTED_AREAS:
        assert f'data-area="{area_id}"' in page


def test_c01_11_protocols_and_telemetry_unchanged():
    for rel, expected in FROZEN_PROTOCOL_HASHES.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, f"{rel} changed vs B5-closed content"
    export_text = (
        REPO_ROOT / "src/virtual_factory/workspaces/plantos_export.py"
    ).read_text(encoding="utf-8")
    assert "class BottledWaterFactory" not in export_text


def test_c01_12_no_kpi_or_hidden_truth_in_selected_export():
    factory = _factory()
    factory.start()
    _run(factory, 20)
    serialised = json.dumps(factory.plantos_export()).lower()
    for hidden in HIDDEN_TRUTH_KEYS:
        assert hidden.lower() not in serialised
    for kpi in FORBIDDEN_KPI_KEYS:
        assert kpi.lower() not in serialised
    raw = yaml.safe_load(DICTIONARY_YAML.read_text(encoding="utf-8"))
    assert raw["contract_version"] == CONTRACT_VERSION
