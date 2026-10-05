"""DDAY-B7-X01-C03 — export-session event cursor / watermark."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    OPERATING_STATE_EVENT_TYPE,
    SIX_EVENT_TYPES,
    dictionary_summary,
    event_only_state_keys,
    map_snapshot,
    map_unseen_transport_events,
    publish_snapshot_via_existing_mqtt,
    selected_event_entries,
    selected_signal_keys,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
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


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML)


def _accepted_events(snapshot: dict) -> list[dict]:
    accepted = set(SIX_EVENT_TYPES)
    return [
        event for event in snapshot.get("recent_events") or ()
        if event.get("event_type") in accepted
    ]


def _mapped_events(snapshot: dict) -> list:
    return [item for item in map_snapshot(snapshot) if item.kind == "event"]


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


def _event_records(recorder: _Recorder) -> list[tuple[str, str, int]]:
    return [item for item in recorder.recorded if "/event/" in item[0]]


def _event_types(recorder: _Recorder) -> list[str]:
    types = []
    for _topic, payload, _qos in _event_records(recorder):
        types.append(json.loads(payload)["event_type"])
    return types


def test_c03_01_first_observation_publishes_once():
    factory = _factory()
    factory.start()
    snapshot = factory.snapshot()
    runtime = [
        event for event in _accepted_events(snapshot)
        if event.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]
    assert len(runtime) == 1
    recorder = _Recorder()
    published = publish_snapshot_via_existing_mqtt(
        MqttGateway(client=recorder), snapshot, factory.export_cursor
    )
    assert published >= 1
    state_types = [
        event_type for event_type in _event_types(recorder)
        if event_type == OPERATING_STATE_EVENT_TYPE
    ]
    assert state_types == [OPERATING_STATE_EVENT_TYPE]


def test_c03_02_identical_snapshots_publish_zero_additional_events():
    factory = _factory()
    factory.start()
    first = factory.snapshot()
    second = factory.snapshot()
    assert first["factory"]["simulation_time_s"] == second["factory"]["simulation_time_s"]
    assert _accepted_events(first) == _accepted_events(second)
    first_rec = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=first_rec), first, factory.export_cursor
    )
    first_events = _event_types(first_rec)
    assert first_events
    second_rec = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=second_rec), second, factory.export_cursor
    )
    assert _event_records(second_rec) == []
    assert all(item[2] == 1 for item in second_rec.recorded)


def test_c03_03_new_runtime_event_publishes_exactly_once():
    factory = _factory()
    factory.start()
    started = factory.snapshot()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=_Recorder()), started, factory.export_cursor
    )
    factory.pause()
    paused = factory.snapshot()
    new_events = [
        event for event in _accepted_events(paused)
        if event not in _accepted_events(started)
    ]
    assert len(new_events) == 1
    assert new_events[0]["event_type"] == OPERATING_STATE_EVENT_TYPE
    recorder = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=recorder), paused, factory.export_cursor
    )
    assert _event_types(recorder) == [OPERATING_STATE_EVENT_TYPE]
    assert json.loads(_event_records(recorder)[0][1])["detail"] == new_events[0]["detail"]


def test_c03_04_reset_clears_cursor_so_transition_can_publish_again():
    factory = _factory()
    factory.start()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=_Recorder()), factory.snapshot(), factory.export_cursor
    )
    assert factory.export_cursor.seen_count > 0
    factory.reset()
    assert factory.export_cursor.seen_count == 0
    factory.start()
    recorder = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=recorder), factory.snapshot(), factory.export_cursor
    )
    assert OPERATING_STATE_EVENT_TYPE in _event_types(recorder)


def test_c03_05_dedup_applies_to_all_six_event_types():
    factory = _factory()
    factory.start()
    for _ in range(220):
        factory.step(1.0)
    snapshot = factory.snapshot()
    present = {event["event_type"] for event in _accepted_events(snapshot)}
    assert present == set(SIX_EVENT_TYPES)
    first = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=first), snapshot, factory.export_cursor
    )
    first_types = set(_event_types(first))
    assert first_types == set(SIX_EVENT_TYPES)
    assert len(_event_records(first)) == len(_accepted_events(snapshot))
    second = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=second), factory.snapshot(), factory.export_cursor
    )
    assert _event_records(second) == []


def test_c03_06_map_snapshot_stays_pure_full_projection():
    factory = _factory()
    factory.start()
    factory.pause()
    snapshot = factory.snapshot()
    mapped = _mapped_events(snapshot)
    runtime = _accepted_events(snapshot)
    assert len(mapped) == len(runtime)
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=_Recorder()), snapshot, factory.export_cursor
    )
    again = factory.snapshot()
    assert len(_mapped_events(again)) == len(_accepted_events(again))
    assert len(_mapped_events(again)) == len(runtime)
    assert [item["event_type"] for item in selected_event_entries()] == list(SIX_EVENT_TYPES)


def test_c03_07_export_does_not_mutate_recent_events():
    factory = _factory()
    factory.start()
    snapshot = factory.snapshot()
    before = copy.deepcopy(snapshot.get("recent_events") or [])
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=_Recorder()), snapshot, factory.export_cursor
    )
    assert snapshot.get("recent_events") == before
    assert factory.snapshot().get("recent_events") == before


def test_c03_08_failed_ack_does_not_mark_cursor():
    factory = _factory()
    factory.start()
    snapshot = factory.snapshot()
    pending = map_unseen_transport_events(snapshot, factory.export_cursor)
    assert pending

    class _FailEvents(_Recorder):
        def publish(self, topic, payload, qos=0, retain=False):
            self.recorded.append((topic, payload, qos))
            if "/event/" in topic:
                return _AckHandle(rc=0, acked=False)
            return _AckHandle(rc=0, acked=True)

    before = factory.export_cursor.seen_count
    with pytest.raises(MqttPublishError, match="ACK not confirmed"):
        publish_snapshot_via_existing_mqtt(
            MqttGateway(client=_FailEvents()), snapshot, factory.export_cursor
        )
    assert factory.export_cursor.seen_count == before
    retry = _Recorder()
    publish_snapshot_via_existing_mqtt(
        MqttGateway(client=retry), snapshot, factory.export_cursor
    )
    assert _event_records(retry)


def test_c03_09_preserved_contract_and_frozen_assets():
    assert CONTRACT_VERSION == "dday-bw-b1-v2"
    assert [entry["event_type"] for entry in selected_event_entries()] == list(SIX_EVENT_TYPES)
    assert set(event_only_state_keys()) == set(SELECTED_STATES)
    factory = _factory()
    factory.start()
    snapshot = factory.snapshot()
    signal_keys = {
        (item.asset_id, item.signal_or_event)
        for item in map_snapshot(snapshot)
        if item.kind == "signal"
    }
    for source_id, signal_id in SELECTED_STATES:
        assert (source_id, signal_id) not in signal_keys
        assert (source_id, signal_id) not in set(selected_signal_keys())
    metadata = dictionary_summary()["event_only_states"]
    assert len(metadata) == 3
    assert all(item["not_a_measurement"] is True for item in metadata)
    for rel, expected in FROZEN.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel
