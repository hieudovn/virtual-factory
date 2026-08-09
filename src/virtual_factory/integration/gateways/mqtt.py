"""MQTT observation gateway — composes existing MqttGateway transport.

M5-S05-C01: Reuses existing MqttGateway.publish_raw() via composition.
Topic mapping + ProjectedMessage serialization owned here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.integration.gateway import DeliveryResult, DeliveryStatus
from virtual_factory.observation.projection import ProjectedMessage
from virtual_factory.protocols.mqtt_gateway import MqttGateway


# ═══════════════════════════════════════════════════
# Strict JSON serialization
# ═══════════════════════════════════════════════════

def _serialize_envelope(message: ProjectedMessage) -> str:
    """Serialize ProjectedMessage to JSON transport envelope.

    Only JSON-native types.  Raises TypeError on unsupported objects.
    """
    return json.dumps({
        "message_key": message.key,
        "projection_id": message.projection_id,
        "message_type": message.message_type,
        "schema_name": message.schema_name,
        "schema_version": message.schema_version,
        "headers": dict(message.headers),
        "payload": dict(message.payload),
    })


# ═══════════════════════════════════════════════════
# MqttObsGateway
# ═══════════════════════════════════════════════════

@dataclass
class MqttObsGateway:
    """Delivers ProjectedMessages via MQTT.

    Composes existing MqttGateway for transport mechanics.
    Topic selection is owned here (not ObservationPoint/Envelope/Message).
    """

    gateway_id: str = "mqtt"
    topic_map: dict[str, str] = field(default_factory=dict)
    qos: int = 0
    retain: bool = False
    _mqtt: MqttGateway | None = None

    def set_mqtt(self, mqtt: MqttGateway) -> None:
        """Inject the existing MqttGateway transport."""
        self._mqtt = mqtt

    def send(self, message: ProjectedMessage) -> DeliveryResult:
        if self._mqtt is None:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="no_transport",
                error_message="MqttGateway not configured",
            )

        topic = self._resolve_topic(message.message_type)
        if topic is None:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.SKIPPED,
                error_code="unmapped_type",
                error_message=f"No topic mapping for {message.message_type}",
            )

        # Strict JSON serialization
        try:
            payload_str = _serialize_envelope(message)
        except (TypeError, ValueError) as exc:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="serialization_error",
                error_message=str(exc),
            )

        # Delegate to existing MqttGateway transport
        try:
            rc = self._mqtt.publish_raw(topic, payload_str,
                                        qos=self.qos, retain=self.retain)
        except Exception as exc:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="publish_error",
                error_message=str(exc),
            )

        if rc != 0:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="publish_rc",
                error_message=f"MQTT publish rc={rc}",
                transport_metadata={"topic": topic, "rc": str(rc)},
            )

        return DeliveryResult(
            gateway_id=self.gateway_id,
            message_key=message.key,
            status=DeliveryStatus.DELIVERED,
            transport_metadata={"topic": topic, "qos": str(self.qos)},
        )

    def send_many(self, messages: list[ProjectedMessage]) -> list[DeliveryResult]:
        return [self.send(m) for m in messages]

    def _resolve_topic(self, message_type: str) -> str | None:
        if message_type in self.topic_map:
            return self.topic_map[message_type]
        for pattern, topic in self.topic_map.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if message_type.startswith(prefix):
                    return topic
        return None
