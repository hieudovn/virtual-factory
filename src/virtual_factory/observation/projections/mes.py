"""MESProjection — semantic MES projection from neutral ObservationEnvelope.

M5-S04: Explicit mapping, not substring heuristics.
No Odoo RPC, no DB IDs, no network.
"""

from __future__ import annotations

from virtual_factory.observation.envelope import ObservationEnvelope, ObservationType
from virtual_factory.observation.projection import ProjectedMessage


# ═══════════════════════════════════════════════════
# Mapping table: ObservationType → MES message_type
# ═══════════════════════════════════════════════════

_OBS_TYPE_TO_MES: dict[ObservationType, str] = {
    ObservationType.EVENT: "mes.execution_event",
    ObservationType.MEASUREMENT: "mes.measurement",
    ObservationType.STATE: "mes.state_snapshot",
    ObservationType.HUMAN_ENTRY: "mes.human_entry",
}

_SCHEMA_PREFIX = "vf.mes"


# ═══════════════════════════════════════════════════
# MESProjection
# ═══════════════════════════════════════════════════

class MESProjection:
    """Semantic MES projection from neutral ObservationEnvelope.

    Uses explicit mapping tables.  Returns None for irrelevant envelopes.
    No Odoo DB IDs, no substring heuristics, no ORM calls.
    """

    projection_id: str = "mes"

    def project(self, envelope: ObservationEnvelope) -> ProjectedMessage | None:
        msg_type = _OBS_TYPE_TO_MES.get(envelope.observation_type)
        if msg_type is None:
            return None

        payload: dict = {
            "observation_id": envelope.observation_id,
            "idempotency_key": envelope.idempotency_key,
            "run_id": envelope.run_id,
            "simulation_time_s": envelope.simulation_time_s,
            "occurred_at": envelope.occurred_at,
        }

        # Subject
        if envelope.subject_type:
            payload["subject_type"] = envelope.subject_type
        if envelope.subject_id:
            payload["subject_id"] = envelope.subject_id

        # Station from context or source_path
        station = envelope.context.get("station_id") or envelope.source_path
        if station:
            payload["station_id"] = station

        # Envelope payload (already field-selected)
        for k, v in envelope.payload.items():
            if k not in payload:
                payload[k] = v

        return ProjectedMessage(
            projection_id=self.projection_id,
            message_type=msg_type,
            schema_name=f"{_SCHEMA_PREFIX}.{envelope.observation_type.value}",
            schema_version="1.0",
            key=envelope.idempotency_key,
            headers={
                "correlation_id": envelope.correlation_id or "",
                "causation_id": envelope.causation_id or "",
            },
            payload=payload,
        )
