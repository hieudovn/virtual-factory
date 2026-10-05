"""DDAY-B7-X01-C02 — no synthesized state events; fail-closed QoS-1 ACK."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    OPERATING_STATE_EVENT_TYPE,
    SIX_EVENT_TYPES,
    TRANSPORT_KIND_EVENT_ONLY,
    UnmappedExportError,
    dictionary_summary,
    event_only_state_keys,
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


def _runtime_state_events(snapshot: dict) -> list[dict]:
    return [
        event for event in snapshot.get("recent_events") or ()
        if event.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]


def _mapped_state_events(snapshot: dict) -> list:
    return [
        item for item in map_snapshot(snapshot)
        if item.payload.get("event_type") == OPERATING_STATE_EVENT_TYPE
    ]


class _AckHandle:
    def __init__(self, rc: int = 0, acked: bool = True) -> None:
        self.rc = rc
        self.acked = acked

    def is_published(self) -> bool:
        return self.acked

    def wait_for_publish(self, timeout: float = 1.0) -> None:
        if not self.acked:
            raise TimeoutError("publish acknowledgement timed out")


def test_c02_01_identical_snapshots_add_zero_state_events():
    factory = _factory()
    factory.start()
    for _ in range(4):
        factory.step(1.0)
    first = factory.snapshot()
    second = factory.snapshot()
    assert first["factory"]["simulation_time_s"] == second["factory"]["simulation_time_s"]
    assert len(_mapped_state_events(first)) == len(_mapped_state_events(second))
    assert len(_mapped_state_events(second)) == len(_runtime_state_events(second))


def test_c02_02_real_transition_maps_exactly_one_state_event():
    factory = _factory()
    before = factory.snapshot()
    assert _runtime_state_events(before) == []
    assert _mapped_state_events(before) == []
    factory.start()
    after = factory.snapshot()
    runtime = _runtime_state_events(after)
    mapped = _mapped_state_events(after)
    assert len(runtime) == 1
    assert len(mapped) == 1
    assert mapped[0].kind == "event"
    assert mapped[0].signal_or_event == OPERATING_STATE_EVENT_TYPE
    assert mapped[0].payload["source_id"] == runtime[0]["source_id"]
    assert mapped[0].payload["detail"] == runtime[0]["detail"]
    assert mapped[0].payload["not_a_measurement"] is True


def test_c02_03_mapped_state_events_equal_runtime_records():
    factory = _factory()
    factory.start()
    factory.pause()
    factory.resume()
    snapshot = factory.snapshot()
    runtime = _runtime_state_events(snapshot)
    mapped = _mapped_state_events(snapshot)
    assert len(runtime) >= 2
    assert len(mapped) == len(runtime)
    assert [item.payload["detail"] for item in mapped] == [event["detail"] for event in runtime]


def test_c02_04_operating_state_stays_event_only_metadata():
    assert CONTRACT_VERSION == "dday-bw-b1-v2"
    assert [entry["event_type"] for entry in selected_event_entries()] == list(SIX_EVENT_TYPES)
    assert set(event_only_state_keys()) == set(SELECTED_STATES)
    factory = _factory()
    factory.start()
    snapshot = factory.snapshot()
    signals = {
        (item.asset_id, item.signal_or_event)
        for item in map_snapshot(snapshot)
        if item.kind == "signal"
    }
    for source_id, signal_id in SELECTED_STATES:
        assert (source_id, signal_id) not in signals
        assert (source_id, signal_id) not in set(selected_signal_keys())
        with pytest.raises(UnmappedExportError, match="not a measurement"):
            lookup_signal_entry(source_id, signal_id)
    metadata = dictionary_summary()["event_only_states"]
    assert len(metadata) == 3
    assert all(item["not_a_measurement"] is True for item in metadata)
    assert all(item["transport_kind"] == TRANSPORT_KIND_EVENT_ONLY for item in metadata)
    assert all(
        not item.topic.endswith("/signal/" + item.asset_id + "/operating_state")
        for item in map_snapshot(snapshot)
    )


def test_c02_05_confirmed_qos1_ack_counts_as_delivered():
    factory = _factory()
    factory.start()
    messages = map_snapshot(factory.snapshot())
    recorded = []

    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            recorded.append((topic, payload, qos, retain))
            return _AckHandle(rc=0, acked=True)

        def disconnect(self) -> None:
            self.disconnected = True

    gateway = MqttGateway(client=_Fake())
    published = publish_via_existing_mqtt(gateway, messages)
    assert published == len(messages)
    assert {item[2] for item in recorded} == {1}
    assert gateway.disconnect(drain_timeout_s=0.2)["ok"] is True


def test_c02_06_ack_timeout_is_not_counted_as_delivered():
    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            return _AckHandle(rc=0, acked=False)

    factory = _factory()
    factory.start()
    messages = map_snapshot(factory.snapshot())
    assert messages
    gateway = MqttGateway(client=_Fake())
    with pytest.raises(MqttPublishError, match="ACK not confirmed"):
        publish_via_existing_mqtt(gateway, messages[:1])


def test_c02_07_negative_rc_is_not_counted_as_delivered():
    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            return _AckHandle(rc=4, acked=True)

    gateway = MqttGateway(client=_Fake())
    with pytest.raises(MqttPublishError, match="rc=4"):
        gateway.publish_raw("vf/neg", "x")
    published = 0
    try:
        published = publish_via_existing_mqtt(
            gateway,
            map_snapshot(_factory().snapshot())[:1],
        )
    except MqttPublishError:
        published = 0
    assert published == 0


def test_c02_08_undelivered_tail_is_not_successful_shutdown():
    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            return _AckHandle(rc=0, acked=False)

        def disconnect(self) -> None:
            self.disconnected = True

    gateway = MqttGateway(client=_Fake())
    with pytest.raises(MqttPublishError, match="ACK not confirmed"):
        gateway.publish_raw("vf/tail", "x", ack_timeout_s=0.01)
    summary = gateway.drain_pending(timeout_s=0.01)
    assert summary["ok"] is False
    assert summary["timed_out"] is True
    with pytest.raises(MqttPublishError, match="undelivered tail"):
        gateway.disconnect(drain_timeout_s=0.01)
    assert gateway.client.disconnected is True


def test_c02_09_frozen_helpers_and_overview():
    for rel, expected in FROZEN.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel
