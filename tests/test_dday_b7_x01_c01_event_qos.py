"""DDAY-B7-X01-C01 — event-only operating_state, v2 contract, QoS-1 drain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from virtual_factory.protocols.mqtt_gateway import DEFAULT_QOS, MqttGateway
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    MQTT_QOS,
    OPERATING_STATE_EVENT_TYPE,
    SIX_EVENT_TYPES,
    TRANSPORT_KIND_EVENT_ONLY,
    UnmappedExportError,
    dictionary_summary,
    event_only_state_keys,
    load_export_dictionary,
    lookup_signal_entry,
    map_snapshot,
    publish_via_existing_mqtt,
    selected_event_entries,
    selected_signal_keys,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
FROZEN_C02_HASHES = {
    "src/virtual_factory/workspaces/capper_degradation.py":
        "c5b2883a9a5ca50878a9cc7bab850ad0a296df19e73c0a6fc62c56a499e0891b",
    "src/virtual_factory/workspaces/compressor_pressure.py":
        "f35a639aced026e497edb53174034b207b86a6d0fa12db63fe7c80f18ca1ac08",
    "src/virtual_factory/ui/static/bottled_water_overview.html":
        "46ab475e5594014f0e2bd4384b0bb46e0623c6a8f2f4a453565346d1e961b8ae",
    "src/virtual_factory/ui/static/bottled_water_overview.js":
        "aba11b2b9c434da2c5aaec794904bd7e4278c9b2030188fccc53fe2cba093425",
    "src/virtual_factory/ui/static/bottled_water_overview.css":
        "8d4424b81772e591b8c5ce9ccb81fd5d03c4a9dd07517b942e877f94f4b21dc5",
}
SELECTED_STATES = (
    ("BW-FP", "operating_state"),
    ("BW-FP-CAP01", "operating_state"),
    ("BW-UT-CMP01", "operating_state"),
)


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML)


def _run(factory: BottledWaterFactory, steps: int = 8) -> dict:
    factory.start()
    for _ in range(steps):
        factory.step(1.0)
    return factory.snapshot()


def test_c01_01_operating_state_is_not_a_measurement_signal():
    factory = _factory()
    snapshot = _run(factory)
    messages = map_snapshot(snapshot)
    signal_keys = {
        (item.asset_id, item.signal_or_event)
        for item in messages
        if item.kind == "signal"
    }
    current = {
        (item["asset_id"], item["signal_or_event"])
        for item in factory.plantos_export()["current_values"]
    }
    for source_id, signal_id in SELECTED_STATES:
        assert (source_id, signal_id) not in signal_keys
        assert (source_id, signal_id) not in current
        assert (source_id, signal_id) not in set(selected_signal_keys())
        with pytest.raises(UnmappedExportError, match="not a measurement"):
            lookup_signal_entry(source_id, signal_id)
        raw = snapshot["nodes"][source_id]["signals"][signal_id]["value"]
        assert raw in {"RUNNING", "IDLE", "STOPPED", "FAULT", "UNKNOWN"}


def test_c01_02_operating_state_is_event_only_metadata_not_synthesized():
    factory = _factory()
    snapshot = _run(factory)
    assert set(event_only_state_keys()) == set(SELECTED_STATES)
    runtime = [
        event for event in snapshot.get("recent_events") or ()
        if event.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]
    mapped = [
        item for item in map_snapshot(snapshot)
        if item.payload.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]
    assert len(mapped) == len(runtime)
    assert not any(item.kind == "signal" and item.signal_or_event == "operating_state" for item in map_snapshot(snapshot))
    metadata = {
        (item["source_id"], item["signal_id"]): item
        for item in dictionary_summary()["event_only_states"]
    }
    for source_id, signal_id in SELECTED_STATES:
        entry = metadata[(source_id, signal_id)]
        assert entry["not_a_measurement"] is True
        assert entry["transport_kind"] == TRANSPORT_KIND_EVENT_ONLY
        assert entry["event_type"] == OPERATING_STATE_EVENT_TYPE
    if mapped:
        assert mapped[0].payload["contract_version"] == CONTRACT_VERSION
        assert mapped[0].payload.get("not_a_measurement") is True


def test_c01_03_all_six_event_types_remain():
    types = [entry["event_type"] for entry in selected_event_entries()]
    assert types == list(SIX_EVENT_TYPES)
    assert len(types) == 6


def test_c01_04_contract_version_is_dday_bw_b1_v2():
    assert CONTRACT_VERSION == "dday-bw-b1-v2"
    dictionary = load_export_dictionary()
    assert dictionary["contract_version"] == CONTRACT_VERSION
    signals = yaml.safe_load((WORKSPACE / "signals.yaml").read_text(encoding="utf-8"))
    workspace = yaml.safe_load(
        (WORKSPACE / "workspace.contract.yaml").read_text(encoding="utf-8")
    )
    assert signals["contract_version"] == CONTRACT_VERSION
    assert workspace["contract_version"] == CONTRACT_VERSION
    assert signals["common_machine_signals"]["operating_state"]["not_a_measurement"] is True
    factory = _factory()
    snapshot = _run(factory, 3)
    for message in map_snapshot(snapshot):
        assert message.payload["contract_version"] == CONTRACT_VERSION
    bundle = factory.plantos_export()
    assert bundle["contract_version"] == CONTRACT_VERSION
    assert dictionary_summary()["contract_version"] == CONTRACT_VERSION


def test_c01_05_mqtt_publish_raw_is_acknowledged_qos1():
    assert DEFAULT_QOS == MQTT_QOS == 1
    factory = _factory()
    snapshot = _run(factory, 2)
    messages = map_snapshot(snapshot)
    recorded = []

    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            recorded.append((topic, payload, qos, retain))
            handle = type("Result", (), {})()
            handle.rc = 0
            handle.is_published = lambda: True
            handle.wait_for_publish = lambda timeout=1.0: None
            return handle

    gateway = MqttGateway(enabled=True, client=_Fake())
    published = publish_via_existing_mqtt(gateway, messages)
    assert published == len(messages)
    assert recorded
    assert {item[2] for item in recorded} == {1}


def test_c01_06_disconnect_drains_bounded_tail():
    class _Handle:
        def __init__(self) -> None:
            self.rc = 0
            self.acked = False

        def is_published(self) -> bool:
            return self.acked

        def wait_for_publish(self, timeout: float = 1.0) -> None:
            self.acked = True

    class _Fake:
        def __init__(self) -> None:
            self.disconnected = False
            self.published = []

        def publish(self, topic, payload, qos=0, retain=False):
            handle = _Handle()
            self.published.append((topic, payload, qos, retain, handle))
            return handle

        def disconnect(self) -> None:
            self.disconnected = True

    gateway = MqttGateway(client=_Fake())
    gateway.publish_raw("vf/a", "1")
    summary = gateway.disconnect(drain_timeout_s=0.5)
    assert gateway.client.disconnected is True
    assert summary["timed_out"] is False
    assert summary["remaining"] == 0


def test_c01_07_capper_compressor_overview_unchanged():
    for rel, expected in FROZEN_C02_HASHES.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, f"{rel} changed vs C02-closed content"


def test_c01_08_no_kpi_leak_and_six_events_still_emitted():
    factory = _factory()
    factory.start()
    for _ in range(220):
        factory.step(1.0)
    bundle = factory.plantos_export()
    serialised = json.dumps(bundle).lower()
    for hidden in HIDDEN_TRUTH_KEYS:
        assert hidden.lower() not in serialised
    for kpi in FORBIDDEN_KPI_KEYS:
        assert kpi.lower() not in serialised
    types = {item["payload"]["event_type"] for item in bundle["events"]}
    assert SIX_EVENT_TYPES[0] in types
    assert "ALARM_RAISED" in types
    assert "SCENARIO_PHASE_CHANGED" in types
    assert bundle["overview"]["areas"][2]["id"] == "BW-FP"
    snapshot = factory.snapshot()
    assert snapshot["nodes"]["BW-FP-CAP01"]["signals"]["operating_state"]["value"]
    assert snapshot["nodes"]["BW-UT-CMP01"]["signals"]["air_pressure"]["value"] is not None
