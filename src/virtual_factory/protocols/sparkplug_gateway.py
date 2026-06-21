"""Sparkplug B MQTT gateway for publishable industrial telemetry.

Implements the Sparkplug B topic structure (``spBv1.0/...``) and
birth/death certificate lifecycle on top of ``MqttGateway``.

Payloads are JSON.  A future version should switch to the standard
Sparkplug B Protobuf encoding (``sparkplug_b.proto``).

Specification reference
-----------------------
- Group ID: ``virtual-factory``
- Edge Node ID: the plant config ``id`` (e.g. ``continuous_mvp_01``)
- Devices: one per signal category (instrumentation, control, actuation, events)
- NBIRTH sent on connect, NDEATH on disconnect, NDATA per frame
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.telemetry.signal_value import SignalValue

# Sparkplug B topic levels
_SPB_VERSION = "spBv1.0"
_MESSAGE_TYPE_NBIRTH = "NBIRTH"
_MESSAGE_TYPE_NDEATH = "NDEATH"
_MESSAGE_TYPE_DBIRTH = "DBIRTH"
_MESSAGE_TYPE_DDATA = "DDATA"
_MESSAGE_TYPE_NDATA = "NDATA"

# Map signal categories to Sparkplug device ids
_CATEGORY_DEVICE_MAP: dict[str, str] = {
    "industrial_signal": "instrumentation",
    "controller_signal": "control",
    "actuator_feedback": "actuation",
    "industrial_event": "events",
}


@dataclass(slots=True)
class SparkplugBGateway:
    """Sparkplug B publisher wrapping a plain MQTT gateway.

    Parameters
    ----------
    mqtt : MqttGateway
        The underlying MQTT connection (must be connected).
    group_id : str
        Sparkplug group id (default ``virtual-factory``).
    edge_node_id : str
        Sparkplug edge node id, typically the plant config id.
    """

    mqtt: MqttGateway
    group_id: str = "virtual-factory"
    edge_node_id: str = "continuous_mvp_01"
    seq: int = field(default=0, init=False)
    _birth_sent: bool = field(default=False, init=False)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def send_birth(self) -> None:
        """Send NBIRTH for the edge node. Must be called once."""
        devices = self._collect_devices()
        for device_id in sorted(devices):
            self._publish(_MESSAGE_TYPE_DBIRTH, device_id, devices[device_id])
        self._birth_sent = True

    def send_death(self) -> None:
        """Send NDEATH for the edge node."""
        self._publish_raw(_MESSAGE_TYPE_NDEATH, payload={})

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def publish_frame(self, frame: list[SignalValue]) -> None:
        """Group signals by device and publish NDATA per device."""
        if not self._birth_sent:
            self.send_birth()

        devices = self._collect_devices(frame)

        # Group signals by device
        by_device: dict[str, list[SignalValue]] = {}
        for signal in frame:
            if signal.category == "internal_truth":
                raise ValueError(
                    f"Refusing to publish internal_truth signal: {signal.name}"
                )
            device_id = _CATEGORY_DEVICE_MAP.get(signal.category, "other")
            by_device.setdefault(device_id, []).append(signal)

        for device_id, signals in by_device.items():
            metrics = [self._signal_to_metric(s) for s in signals]
            devices[device_id] = {"metrics": metrics}
            self._publish(_MESSAGE_TYPE_DDATA, device_id, devices[device_id])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _publish(self, message_type: str, device_id: str, payload: dict) -> None:
        topic = f"{_SPB_VERSION}/{self.group_id}/{message_type}/{self.edge_node_id}/{device_id}"
        payload["timestamp"] = int(time.time() * 1000)
        payload["seq"] = self._next_seq()
        self.mqtt.client.publish(topic, json.dumps(payload))

    def _publish_raw(self, message_type: str, payload: dict) -> None:
        topic = f"{_SPB_VERSION}/{self.group_id}/{message_type}/{self.edge_node_id}"
        payload["timestamp"] = int(time.time() * 1000)
        payload["seq"] = self._next_seq()
        self.mqtt.client.publish(topic, json.dumps(payload))

    def _next_seq(self) -> int:
        self.seq = (self.seq + 1) % 256
        return self.seq

    @staticmethod
    def _signal_to_metric(signal: SignalValue) -> dict:
        """Map one SignalValue to a Sparkplug metric dict."""
        return {
            "name": signal.name,
            "value": signal.value,
            "timestamp": int(signal.timestamp_s * 1000) if signal.timestamp_s else int(time.time() * 1000),
            "dataType": _sparkplug_type(signal.value),
        }

    @staticmethod
    def _collect_devices(frame: list[SignalValue] | None = None) -> dict[str, dict]:
        """Return a standard device listing with empty metrics."""
        devices: dict[str, dict] = {}
        for spb_device in sorted(set(_CATEGORY_DEVICE_MAP.values())):
            devices[spb_device] = {"metrics": []}
        return devices


def _sparkplug_type(value: object) -> str:
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Int64"
    if isinstance(value, float):
        return "Double"
    return "String"
