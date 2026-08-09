"""JSONL file observation gateway.

M5-S05: Writes one ProjectedMessage per line as JSON.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence

from virtual_factory.integration.gateway import DeliveryResult, DeliveryStatus
from virtual_factory.observation.projection import ProjectedMessage


class JsonlObsGateway:
    """Writes ProjectedMessages as JSONL (one JSON object per line).

    Append-safe for single-process demo use.  Not enterprise durability.
    """

    gateway_id: str

    def __init__(self, filepath: str, gateway_id: str = "jsonl") -> None:
        self.gateway_id = gateway_id
        self._filepath = filepath
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    def send(self, message: ProjectedMessage) -> DeliveryResult:
        try:
            record = {
                "message_key": message.key,
                "projection_id": message.projection_id,
                "message_type": message.message_type,
                "schema_name": message.schema_name,
                "schema_version": message.schema_version,
                "headers": dict(message.headers),
                "payload": dict(message.payload),
            }
            # Strict JSON: no default=str — fail on unsupported types
            line = json.dumps(record, ensure_ascii=False)
            with open(self._filepath, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.DELIVERED,
            )
        except (TypeError, ValueError) as exc:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="serialization_error",
                error_message=str(exc),
            )
        except Exception as exc:
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="write_error",
                error_message=str(exc),
            )

    def send_many(self, messages: Sequence[ProjectedMessage]) -> list[DeliveryResult]:
        return [self.send(m) for m in messages]
