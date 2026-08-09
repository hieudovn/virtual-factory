"""IIoTProjection — semantic IIoT projection from neutral ObservationEnvelope.

M5-S04: Explicit mapping. No MQTT topic, no OPC node, no protocol addressing.
"""

from __future__ import annotations

from virtual_factory.observation.envelope import ObservationEnvelope, ObservationType
from virtual_factory.observation.projection import ProjectedMessage


# ═══════════════════════════════════════════════════
# Mapping
# ═══════════════════════════════════════════════════

_OBS_TYPE_TO_IIOT: dict[ObservationType, str] = {
    ObservationType.EVENT: "iiot.event",
    ObservationType.MEASUREMENT: "iiot.signal",
    ObservationType.STATE: "iiot.state",
    ObservationType.HUMAN_ENTRY: "iiot.human_entry",
}

_SCHEMA_PREFIX = "vf.iiot"


class IIoTProjection:
    """Semantic IIoT projection from neutral ObservationEnvelope.

    No MQTT/OPC/transport addressing.  Signal-level semantics only.
    """

    projection_id: str = "iiot"

    def project(self, envelope: ObservationEnvelope) -> ProjectedMessage | None:
        msg_type = _OBS_TYPE_TO_IIOT.get(envelope.observation_type)
        if msg_type is None:
            return None

        payload: dict = {
            "observation_id": envelope.observation_id,
            "idempotency_key": envelope.idempotency_key,
            "simulation_time_s": envelope.simulation_time_s,
            "source_domain": envelope.source_domain,
            "source_path": envelope.source_path,
            "quality": envelope.quality,
        }

        if envelope.subject_type:
            payload["subject_type"] = envelope.subject_type
        if envelope.subject_id:
            payload["subject_id"] = envelope.subject_id

        # Envelope payload fields
        for k, v in envelope.payload.items():
            if k not in payload:
                payload[k] = v

        return ProjectedMessage(
            projection_id=self.projection_id,
            message_type=msg_type,
            schema_name=f"{_SCHEMA_PREFIX}.{envelope.observation_type.value}",
            schema_version="1.0",
            key=envelope.idempotency_key,
            payload=payload,
        )
