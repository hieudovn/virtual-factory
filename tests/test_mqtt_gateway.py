import json

import pytest

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
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

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        self.published.append((topic, payload, qos, retain))
        return type("Result", (), {"rc": 0})()


class FlakyConnectClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.connect_attempts = 0

    def connect(self, host: str, port: int) -> None:
        self.connect_attempts += 1
        if self.connect_attempts == 1:
            raise OSError("temporary failure")
        super().connect(host, port)


class AlwaysFailConnectClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.connect_attempts = 0

    def connect(self, host: str, port: int) -> None:
        self.connect_attempts += 1
        raise OSError("still unavailable")


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


def test_connect_retries_and_succeeds_after_transient_error() -> None:
    fake_client = FlakyConnectClient()
    gateway = MqttGateway(host="mqtt", port=1883, client=fake_client)

    gateway.connect(retries=2, delay_s=0.0)

    assert fake_client.connect_attempts == 2
    assert fake_client.connected == ("mqtt", 1883)


def test_connect_retries_then_raises_runtime_error() -> None:
    fake_client = AlwaysFailConnectClient()
    gateway = MqttGateway(host="mqtt", port=1883, client=fake_client)

    with pytest.raises(RuntimeError, match="Failed to connect to MQTT broker at mqtt:1883 after 3 attempts"):
        gateway.connect(retries=3, delay_s=0.0)

    assert fake_client.connect_attempts == 3


class AckClient(FakeClient):
    def __init__(self, delay_before_ack: float = 0.0) -> None:
        super().__init__()
        self.delay_before_ack = delay_before_ack
        self.loop_started = False
        self.loop_stopped = False

    def loop_start(self) -> None:
        self.loop_started = True

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        handle = _AckHandle(delay_s=self.delay_before_ack)
        self.published.append((topic, payload, qos, retain, handle))
        return handle


class _AckHandle:
    def __init__(self, delay_s: float = 0.0) -> None:
        self.rc = 0
        self.delay_s = delay_s
        self.acked = delay_s <= 0
        self.waited = []

    def is_published(self) -> bool:
        return self.acked

    def wait_for_publish(self, timeout: float = 1.0) -> None:
        self.waited.append(timeout)
        if self.delay_s <= timeout:
            self.acked = True
        else:
            raise TimeoutError("publish acknowledgement timed out")


def test_publish_raw_negative_rc_is_not_delivered() -> None:
    class _Fail:
        def publish(self, topic, payload, qos=0, retain=False):
            return type("Result", (), {"rc": 1})()

    gateway = MqttGateway(client=_Fail())
    with pytest.raises(MqttPublishError, match="rc=1"):
        gateway.publish_raw("vf/bad", "x")


def test_publish_raw_defaults_to_acknowledged_qos1() -> None:
    fake_client = AckClient()
    gateway = MqttGateway(client=fake_client)

    rc = gateway.publish_raw("vf/demo", '{"ok": true}')

    assert rc == 0
    assert fake_client.published[0][2] == 1
    assert fake_client.published[0][4].acked is True
    assert fake_client.published[0][4].waited


def test_disconnect_drains_outstanding_tail_before_client_drop() -> None:
    fake_client = AckClient(delay_before_ack=0.0)
    gateway = MqttGateway(host="mqtt.local", port=1884, client=fake_client)
    gateway.connect()
    gateway.publish_raw("vf/one", "1")
    gateway.publish_raw("vf/two", "2")

    summary = gateway.disconnect()

    assert summary["remaining"] == 0
    assert summary["timed_out"] is False
    assert summary["drained"] >= 0
    assert fake_client.disconnected is True
    assert fake_client.loop_started is True
    assert fake_client.loop_stopped is True


def test_drain_pending_is_bounded_when_ack_does_not_arrive() -> None:
    fake_client = AckClient(delay_before_ack=10.0)
    gateway = MqttGateway(client=fake_client)
    with pytest.raises(MqttPublishError, match="ACK not confirmed"):
        gateway.publish_raw("vf/slow", "x", ack_timeout_s=0.01)

    summary = gateway.drain_pending(timeout_s=0.02)

    assert summary["timed_out"] is True
    assert summary["ok"] is False
    assert summary["remaining"] == 1
    with pytest.raises(MqttPublishError, match="undelivered tail"):
        gateway.disconnect(drain_timeout_s=0.01)
