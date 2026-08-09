"""MQTT gateway for publishable industrial telemetry frames.

This gateway publishes already-built telemetry frames only. It never reads
runtime truth state directly. Sparkplug B and production-grade reconnect logic
are future scope.
"""

import json
import socket
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from virtual_factory.telemetry.signal_value import SignalValue


@dataclass(slots=True)
class MqttGateway:
    """Simple MQTT JSON publisher for publishable SignalValue frames."""

    host: str = "localhost"
    port: int = 1883
    topic_prefix: str = "virtual-factory"
    client_id: str | None = None
    enabled: bool = True
    client: Any | None = field(default=None, repr=False)

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
                return
            except (socket.gaierror, ConnectionRefusedError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == attempts:
                    break
                time.sleep(delay_s)
        raise RuntimeError(
            f"Failed to connect to MQTT broker at {self.host}:{self.port} after {attempts} attempts"
        ) from last_error

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.client is not None:
            self.client.disconnect()

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
                    qos: int = 0, retain: bool = False) -> int:
        """Publish a raw payload string to *topic*.  Returns paho rc.

        Backward-compatible addition for M5 ObservationGateway reuse.
        Existing ``publish_frame`` is unchanged.
        """
        if self.client is None:
            self.client = self._create_client()
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        return result.rc if hasattr(result, "rc") else 0

    def _create_client(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("MQTT support requires installing the mqtt extra: pip install -e .[mqtt]") from exc
        return mqtt.Client(client_id=self.client_id)


MQTTGateway = MqttGateway
