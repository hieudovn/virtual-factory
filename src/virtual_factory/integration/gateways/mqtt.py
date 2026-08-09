"""MQTT observation gateway — wraps existing MqttGateway.

M5-S05: Sends ProjectedMessage via MQTT using topic mappings.
Reuses existing MqttGateway transport mechanics (composition).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.integration.gateway import DeliveryResult, DeliveryStatus
from virtual_factory.observation.projection import ProjectedMessage


@dataclass
class MqttObsGateway:
    """Delivers ProjectedMessages via MQTT.

    Topic selection is owned by gateway configuration (topic_map),
    not by ObservationPoint, ObservationEnvelope, or ProjectedMessage.

    Wraps an existing MQTT client via dependency injection.
    """

    gateway_id: str = "mqtt"
    topic_map: dict[str, str] = field(default_factory=dict)
    qos: int = 0
    retain: bool = False
    _client: Any = None  # injected MQTT client (paho or mock)

    def set_client(self, client: Any) -> None:
        """Inject an MQTT client (real paho.mqtt.client or mock)."""
        self._client = client

    def send(self, message: ProjectedMessage) -> DeliveryResult:
        if self._client is None:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="no_client",
                error_message="MQTT client not configured",
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

        try:
            payload = json.dumps({
                "message_key": message.key,
                "projection_id": message.projection_id,
                "message_type": message.message_type,
                "schema_name": message.schema_name,
                "schema_version": message.schema_version,
                "headers": dict(message.headers),
                "payload": dict(message.payload),
            }, default=str)

            self._client.publish(topic, payload, qos=self.qos, retain=self.retain)
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.DELIVERED,
                transport_metadata={"topic": topic, "qos": str(self.qos)},
            )
        except Exception as exc:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="publish_error",
                error_message=str(exc),
            )

    def send_many(self, messages: list[ProjectedMessage]) -> list[DeliveryResult]:
        return [self.send(m) for m in messages]

    def _resolve_topic(self, message_type: str) -> str | None:
        """Exact match first, then prefix/wildcard match."""
        if message_type in self.topic_map:
            return self.topic_map[message_type]
        # Prefix match: mes.* -> vf/mes
        for pattern, topic in self.topic_map.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if message_type.startswith(prefix):
                    return topic
        return None
