"""DDAY-FR1 — freeze Bottled Water D-Day runtime profile."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    SIX_EVENT_TYPES,
    dictionary_summary,
    event_only_state_keys,
    exported_signal_entries,
    load_runtime_profile,
    map_snapshot,
    profile_measurement_map,
    publish_snapshot_via_existing_mqtt,
    selected_event_entries,
    selected_signal_keys,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
PROFILE_YAML = WORKSPACE / "runtime.profile.yaml"
CAP = "BW-FP-CAP01"
SELECTED_STATES = (
    ("BW-FP", "operating_state"),
    ("BW-FP-CAP01", "operating_state"),
    ("BW-UT-CMP01", "operating_state"),
)
FROZEN = {
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
FAST_KEYS = {
    ("BW-FP-CAP01", "motor_current"),
    ("BW-FP-CAP01", "drive_load"),
    ("BW-FP-CAP01", "vibration_rms"),
    ("BW-FP-CAP01", "speed"),
    ("BW-FP-CAP01", "cycle_time"),
    ("BW-FP-CAP01", "cap_torque"),
}
MEDIUM_KEYS = {
    ("BW-FP-FIL01", "fill_rate"),
    ("BW-UT-CMP01", "air_pressure"),
    ("BW-UT-CMP01", "active_power"),
    ("BW-UT-PWR01", "plant_active_power"),
    ("BW-FP-CAP01", "bearing_temperature"),
}
SLOW_KEYS = {
    ("BW-WT-FEED01", "water_flow"),
    ("BW-WT-RO01", "production_flow"),
    ("BW-WT-TK01", "level"),
    ("BW-UT-CMP01", "energy_total"),
    ("BW-UT-PWR01", "plant_energy_total"),
}
COUNT_KEYS = {
    ("BW-FP", "total_count"),
    ("BW-FP", "good_count"),
    ("BW-FP", "reject_count"),
    ("BW-WH-FG01", "inventory_count"),
    ("BW-WH-FG01", "receipt_count"),
    ("BW-WH-FG01", "dispatch_count"),
}


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML)


class _AckHandle:
    def __init__(self, rc: int = 0, acked: bool = True) -> None:
        self.rc = rc
        self.acked = acked

    def is_published(self) -> bool:
        return self.acked

    def wait_for_publish(self, timeout: float = 1.0) -> None:
        if not self.acked:
            raise TimeoutError("publish acknowledgement timed out")


class _Recorder:
    def __init__(self, acked: bool = True, rc: int = 0) -> None:
        self.recorded: list[tuple[str, str, int]] = []
        self.acked = acked
        self.rc = rc
        self.disconnected = False

    def publish(self, topic, payload, qos=0, retain=False):
        self.recorded.append((topic, payload, qos))
        return _AckHandle(self.rc, self.acked)

    def disconnect(self) -> None:
        self.disconnected = True


def _keys(recorder: _Recorder, kind: str) -> list[tuple[str, str]]:
    out = []
    for topic, payload, _qos in recorder.recorded:
        if f"/{kind}/" not in topic:
            continue
        data = json.loads(payload)
        if kind == "signal":
            out.append((data["source_id"], data["signal_id"]))
        else:
            out.append((data["source_id"], data["event_type"]))
    return out


def test_fr1_01_profile_maps_all_22_exported_measurements():
    profile = load_runtime_profile()
    mapped = profile_measurement_map(profile)
    exported = set(selected_signal_keys())
    assert len(exported) == 22
    assert set(mapped) == exported
    assert profile["contract_version"] == CONTRACT_VERSION
    assert profile["not_a_permanent_industrial_standard"] is True
    classes = {entry["class"] for entry in mapped.values()}
    assert classes == {"FAST", "MEDIUM", "SLOW", "COUNT"}


def test_fr1_02_classes_match_issue_117_targets():
    mapped = profile_measurement_map()
    by_class = {name: set() for name in ("FAST", "MEDIUM", "SLOW", "COUNT")}
    for key, entry in mapped.items():
        by_class[entry["class"]].add(key)
    assert by_class["FAST"] == FAST_KEYS
    assert by_class["MEDIUM"] == MEDIUM_KEYS
    assert by_class["SLOW"] == SLOW_KEYS
    assert by_class["COUNT"] == COUNT_KEYS
    assert ("BW-FP-CAP01", "motor_current") in by_class["FAST"]
    assert ("BW-FP-FIL01", "fill_rate") in by_class["MEDIUM"]
    assert ("BW-WT-FEED01", "water_flow") in by_class["SLOW"]
    assert ("BW-FP", "total_count") in by_class["COUNT"]


def test_fr1_03_events_and_operating_state_stay_event_driven():
    profile = load_runtime_profile()
    assert profile["events"]["class"] == "EVENT"
    assert profile["events"]["types"] == list(SIX_EVENT_TYPES)
    assert [entry["event_type"] for entry in selected_event_entries()] == list(SIX_EVENT_TYPES)
    assert set(event_only_state_keys()) == set(SELECTED_STATES)
    factory = _factory()
    factory.start()
    signals = {
        (item.asset_id, item.signal_or_event)
        for item in map_snapshot(factory.snapshot())
        if item.kind == "signal"
    }
    for source_id, signal_id in SELECTED_STATES:
        assert (source_id, signal_id) not in signals
        assert (source_id, signal_id) not in set(selected_signal_keys())
    metadata = dictionary_summary()["event_only_states"]
    assert len(metadata) == 3
    assert all(item["not_a_measurement"] is True for item in metadata)
    first = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=first))
    assert ("BW-FP", "operating_state") not in _keys(first, "signal")
    assert any(event_type == "MACHINE_STATE_CHANGED" for _, event_type in _keys(first, "event"))


def test_fr1_04_periodic_classes_do_not_republish_before_period():
    factory = _factory()
    factory.start()
    first = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=first))
    assert set(_keys(first, "signal")) == FAST_KEYS | MEDIUM_KEYS | SLOW_KEYS | COUNT_KEYS
    second = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=second))
    assert _keys(second, "signal") == []
    factory.step(1.0)
    after_one = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=after_one))
    after_keys = set(_keys(after_one, "signal"))
    assert FAST_KEYS <= after_keys
    assert after_keys.isdisjoint(MEDIUM_KEYS)
    assert after_keys.isdisjoint(SLOW_KEYS)
    factory.step(4.0)
    after_five = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=after_five))
    five_keys = set(_keys(after_five, "signal"))
    assert MEDIUM_KEYS <= five_keys
    assert five_keys.isdisjoint(SLOW_KEYS)
    factory.step(5.0)
    after_ten = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=after_ten))
    assert SLOW_KEYS <= set(_keys(after_ten, "signal"))


def test_fr1_05_count_publishes_on_change_not_spam():
    factory = _factory()
    factory.start()
    factory.publish_live_mqtt(MqttGateway(client=_Recorder()))
    idle = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=idle))
    assert set(_keys(idle, "signal")).isdisjoint(COUNT_KEYS)
    before = factory.snapshot()["nodes"]["BW-FP"]["signals"]["total_count"]["value"]
    changed_value = before
    for _ in range(40):
        factory.step(1.0)
        changed_value = factory.snapshot()["nodes"]["BW-FP"]["signals"]["total_count"]["value"]
        if changed_value != before:
            break
    assert changed_value != before
    changed = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=changed))
    assert ("BW-FP", "total_count") in set(_keys(changed, "signal"))
    again = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=again))
    assert set(_keys(again, "signal")).isdisjoint(COUNT_KEYS)


def test_fr1_06_bounded_live_run_is_not_a_250_msg_burst():
    factory = _factory()
    factory.start()
    recorder = _Recorder()
    gateway = MqttGateway(client=recorder)
    rejects = 0
    horizon_s = 60.0
    factory.publish_live_mqtt(gateway)
    for _ in range(int(horizon_s)):
        factory.step(1.0)
        try:
            factory.publish_live_mqtt(gateway)
        except MqttPublishError:
            rejects += 1
    signals = [item for item in recorder.recorded if "/signal/" in item[0]]
    events = [item for item in recorder.recorded if "/event/" in item[0]]
    total = len(recorder.recorded)
    naive = 22 * (int(horizon_s) + 1)
    rate = total / horizon_s
    assert rejects == 0
    assert gateway.drain_pending(timeout_s=0.2)["ok"] is True
    assert total < naive
    assert rate < 50.0
    assert rate < 250.0
    assert len(signals) < naive
    assert all(item[2] == 1 for item in recorder.recorded)
    counts = Counter(key for key in _keys(recorder, "signal"))
    assert counts[("BW-FP-CAP01", "motor_current")] == int(horizon_s) + 1
    assert counts[("BW-WT-FEED01", "water_flow")] == int(horizon_s) // 10 + 1
    assert events


def test_fr1_07_abnormal_scenario_and_frozen_assets_unchanged():
    for rel, expected in FROZEN.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel
    factory = _factory()
    factory.start()
    for _ in range(220):
        factory.step(1.0)
    types = [
        event["event_type"]
        for event in factory.snapshot()["recent_events"]
        if event.get("source_id") == CAP
    ]
    assert types.count("ALARM_RAISED") == 1
    assert types.count("ALARM_CLEARED") == 1
    assert types.count("DOWNTIME_START") == 1
    assert types.count("DOWNTIME_END") == 1


def test_fr1_08_reset_clears_scheduler_and_map_snapshot_stays_pure():
    factory = _factory()
    factory.start()
    factory.publish_live_mqtt(MqttGateway(client=_Recorder()))
    factory.step(1.0)
    factory.publish_live_mqtt(MqttGateway(client=_Recorder()))
    snapshot = factory.snapshot()
    mapped_signals = [item for item in map_snapshot(snapshot) if item.kind == "signal"]
    assert len(mapped_signals) == 22
    factory.reset()
    factory.start()
    first = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=first))
    assert set(_keys(first, "signal")) == FAST_KEYS | MEDIUM_KEYS | SLOW_KEYS | COUNT_KEYS
    workspace = yaml.safe_load((WORKSPACE / "workspace.contract.yaml").read_text(encoding="utf-8"))
    assert workspace["contract_version"] == CONTRACT_VERSION
    assert workspace["runtime_profile"]["ref"].endswith("runtime.profile.yaml")
    assert PROFILE_YAML.is_file()
    assert len(exported_signal_entries()) == 22
    factory.reset()
    factory.start()
    with pytest.raises(MqttPublishError):
        publish_snapshot_via_existing_mqtt(
            MqttGateway(client=_Recorder(acked=False)),
            factory.snapshot(),
            factory.export_cursor,
            scheduler=factory.export_scheduler,
        )
    retry = _Recorder()
    factory.publish_live_mqtt(MqttGateway(client=retry))
    assert _keys(retry, "signal")
