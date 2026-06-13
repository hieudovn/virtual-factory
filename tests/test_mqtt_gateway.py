import json

import pytest

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.telemetry.signal_value import SignalValue


class FakeClient:
    def __init__(self) -> None:
        self.published = []
        self.connected = None
        self.disconnected = False

    def connect(self, host: str, port: int) -> None:
        self.connected = (host, port)

    def disconnect(self) -> None:
        self.disconnected = True

    def publish(self, topic: str, payload: str) -> None:
        self.published.append((topic, payload))


def test_build_topic_returns_prefix_and_signal_name() -> None:
    signal = SignalValue("LT102_LEVEL", 1.23, "m", "industrial_signal", 12.0, source="LT102")
    gateway = MqttGateway(topic_prefix="virtual-factory/test")

    assert gateway.build_topic(signal) == "virtual-factory/test/LT102_LEVEL"


def test_build_payload_returns_expected_dict() -> None:
    signal = SignalValue("LT102_LEVEL", 1.23, "m", "industrial_signal", 12.0, source="LT102")
    gateway = MqttGateway()

    assert gateway.build_payload(signal) == {
        "name": "LT102_LEVEL",
        "value": 1.23,
        "unit": "m",
        "category": "industrial_signal",
        "quality": "GOOD",
        "timestamp_s": 12.0,
        "source": "LT102",
    }


def test_publish_frame_calls_client_publish_for_each_signal() -> None:
    fake_client = FakeClient()
    gateway = MqttGateway(topic_prefix="virtual-factory/test", client=fake_client)
    frame = [
        SignalValue("LT102_LEVEL", 1.23, "m", "industrial_signal", 12.0, source="LT102"),
        SignalValue("FT101_FLOW", 0.01, "m3/s", "industrial_signal", 12.0, source="FT101"),
    ]

    gateway.publish_frame(frame)

    assert len(fake_client.published) == 2
    assert fake_client.published[0][0] == "virtual-factory/test/LT102_LEVEL"
    assert json.loads(fake_client.published[0][1])["value"] == 1.23


def test_publish_frame_refuses_internal_truth() -> None:
    fake_client = FakeClient()
    gateway = MqttGateway(client=fake_client)
    frame = [SignalValue("T102_LEVEL_TRUE", 1.0, "m", "internal_truth", 0.0, source="T102")]

    with pytest.raises(ValueError, match="internal_truth"):
        gateway.publish_frame(frame)

    assert fake_client.published == []


def test_connect_and_disconnect_use_client_without_broker() -> None:
    fake_client = FakeClient()
    gateway = MqttGateway(host="mqtt.local", port=1884, client=fake_client)

    gateway.connect()
    gateway.disconnect()

    assert fake_client.connected == ("mqtt.local", 1884)
    assert fake_client.disconnected is True
