"""MQTT gateway for publishable industrial telemetry frames.

This gateway publishes already-built telemetry frames only. It never reads
runtime truth state directly. Sparkplug B and production-grade reconnect logic
are future scope.

DDAY-B7-X01-C01: ``publish_raw`` uses acknowledged QoS 1 by default and
``disconnect`` drains the outstanding publish tail before dropping the client.
``publish_frame`` is unchanged.
"""

import json
import socket
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from virtual_factory.telemetry.signal_value import SignalValue

DEFAULT_QOS = 1
PUBLISH_ACK_TIMEOUT_S = 2.0
DRAIN_TIMEOUT_S = 2.0


@dataclass(slots=True)
class MqttGateway:
    """Simple MQTT JSON publisher for publishable SignalValue frames."""

    host: str = "localhost"
    port: int = 1883
    topic_prefix: str = "virtual-factory"
    client_id: str | None = None
    enabled: bool = True
    client: Any | None = field(default=None, repr=False)
    _pending: list = field(default_factory=list, repr=False)
    _loop_started: bool = field(default=False, repr=False)

    def connect(self, retries: int = 20, delay_s: float = 1.0) -> None:
        """Connect to the MQTT broker."""
        if not self.enabled:
            return
        if self.client is None:
            self.client = self._create_client()

        attempts = max(1, retries)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                self.client.connect(self.host, self.port)
                self._start_network_loop()
                return
            except (socket.gaierror, ConnectionRefusedError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == attempts:
                    break
                time.sleep(delay_s)
        raise RuntimeError(
            f"Failed to connect to MQTT broker at {self.host}:{self.port} after {attempts} attempts"
        ) from last_error

    def drain_pending(self, timeout_s: float = DRAIN_TIMEOUT_S) -> dict:
        """Wait for outstanding QoS-1 publishes, then drop any leftover tail.

        Bounded: never waits longer than ``timeout_s``. Leftover unpublished
        handles are discarded so disconnect cannot hang.
        """
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        remaining: list = []
        for result in list(self._pending):
            leftover = deadline - time.monotonic()
            if leftover <= 0:
                remaining.append(result)
                continue
            if not self._wait_for_ack(result, leftover):
                remaining.append(result)
        drained = len(self._pending) - len(remaining)
        self._pending = []
        return {
            "drained": drained,
            "remaining": len(remaining),
            "timed_out": bool(remaining),
            "timeout_s": float(timeout_s),
        }

    def disconnect(self, drain_timeout_s: float = DRAIN_TIMEOUT_S) -> dict:
        """Drain the outstanding publish tail, then disconnect."""
        summary = self.drain_pending(timeout_s=drain_timeout_s)
        if self.client is not None:
            self._stop_network_loop()
            self.client.disconnect()
        return summary

    def publish_frame(self, frame: list[SignalValue]) -> None:
        """Publish each SignalValue in a publishable telemetry frame."""
        if not self.enabled:
            return
        if self.client is None:
            self.client = self._create_client()
        for signal in frame:
            if not isinstance(signal, SignalValue):
                raise TypeError("MqttGateway.publish_frame accepts SignalValue objects only.")
            if signal.category == "internal_truth":
                raise ValueError(f"Refusing to publish internal_truth signal: {signal.name}")
            payload = json.dumps(self.build_payload(signal))
            self.client.publish(self.build_topic(signal), payload)

    def build_topic(self, signal: SignalValue) -> str:
        """Build the MQTT topic for one signal."""
        return f"{self.topic_prefix.rstrip('/')}/{signal.name}"

    def build_payload(self, signal: SignalValue) -> dict:
        """Build a simple JSON-serializable payload for one signal."""
        if signal.category == "internal_truth":
            raise ValueError(f"Refusing to build MQTT payload for internal_truth signal: {signal.name}")
        return asdict(signal)

    def publish_raw(self, topic: str, payload: str,
                    qos: int | None = None, retain: bool = False,
                    ack_timeout_s: float = PUBLISH_ACK_TIMEOUT_S) -> int:
        """Publish a raw payload string to *topic* at QoS 1 by default.

        Returns paho rc. Acknowledged delivery: the publish is recorded on
        the outstanding tail and a bounded wait is used when the client
        exposes ``wait_for_publish`` / ``is_published``.
        """
        if self.client is None:
            self.client = self._create_client()
        if qos is None:
            qos = DEFAULT_QOS
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        self._pending.append(result)
        self._wait_for_ack(result, ack_timeout_s)
        if self._is_published(result):
            self._pending = [item for item in self._pending if item is not result]
        return result.rc if hasattr(result, "rc") else 0

    def _start_network_loop(self) -> None:
        if self.client is not None and hasattr(self.client, "loop_start") and not self._loop_started:
            self.client.loop_start()
            self._loop_started = True

    def _stop_network_loop(self) -> None:
        if self.client is not None and self._loop_started and hasattr(self.client, "loop_stop"):
            try:
                self.client.loop_stop()
            except Exception:
                pass
        self._loop_started = False

    @staticmethod
    def _is_published(result: Any) -> bool:
        checker = getattr(result, "is_published", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:
                return False
        return not hasattr(result, "wait_for_publish")

    def _wait_for_ack(self, result: Any, timeout_s: float) -> bool:
        if timeout_s <= 0:
            return self._is_published(result)
        waiter = getattr(result, "wait_for_publish", None)
        if callable(waiter):
            try:
                waiter(timeout=timeout_s)
            except TypeError:
                try:
                    waiter(timeout_s)
                except Exception:
                    return self._is_published(result)
            except Exception:
                return self._is_published(result)
        return self._is_published(result)

    def _create_client(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("MQTT support requires installing the mqtt extra: pip install -e .[mqtt]") from exc
        return mqtt.Client(client_id=self.client_id)


MQTTGateway = MqttGateway
