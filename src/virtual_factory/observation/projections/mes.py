"""MESProjection — semantic MES projection from neutral ObservationEnvelope.

M5-S04: Explicit semantic discriminator — maps envelope data to MES
semantic classes.  No substring heuristics, no Odoo IDs.
Returns None when semantics are insufficient.
"""

from __future__ import annotations

from virtual_factory.observation.envelope import ObservationEnvelope, ObservationType
from virtual_factory.observation.projection import ProjectedMessage


# ═══════════════════════════════════════════════════
# Semantic discriminator: event_type or semantic_type → MES class
# ═══════════════════════════════════════════════════

# Envelope payload.event_type → MES message_type
_EVENT_TYPE_TO_MES: dict[str, str] = {
    "PROCESS_START": "mes.execution_event",
    "PROCESS_COMPLETE": "mes.execution_event",
    "WIP_CREATED": "mes.execution_event",
    "WIP_COMPLETED": "mes.execution_event",
    "QUALITY_CHECK": "mes.quality_result",
    "CHECKLIST_COMPLETE": "mes.checklist_result",
    "REWORK_TRIGGERED": "mes.execution_event",
    "SCRAP_TRIGGERED": "mes.execution_event",
    "OPERATOR_CHECK": "mes.checklist_result",
}

# Envelope payload or context.semantic_type → MES message_type
# Explicit semantic_type overrides event_type mapping.
_SEMANTIC_TYPE_TO_MES: dict[str, str] = {
    "execution_event": "mes.execution_event",
    "measurement": "mes.measurement",
    "quality_result": "mes.quality_result",
    "checklist_result": "mes.checklist_result",
    "genealogy_relationship": "mes.genealogy_relationship",
    "run_status": "mes.run_status",
    "issue": "mes.issue",
}

_SCHEMA_PREFIX = "vf.mes"


def _resolve_mes_type(envelope: ObservationEnvelope) -> str | None:
    """Resolve MES message_type from envelope semantics.

    1. context.semantic_type (explicit, highest priority)
    2. payload.event_type mapped via _EVENT_TYPE_TO_MES
    3. ObservationType for MEASUREMENT/STATE (generic fallback)
    4. None → irrelevant
    """
    # Explicit semantic in context
    semantic = envelope.context.get("semantic_type")
    if semantic and semantic in _SEMANTIC_TYPE_TO_MES:
        return _SEMANTIC_TYPE_TO_MES[semantic]

    # Event-based mapping
    event_type = envelope.payload.get("event_type")
    if event_type and event_type in _EVENT_TYPE_TO_MES:
        return _EVENT_TYPE_TO_MES[event_type]

    # Generic fallback for measurement/state only
    if envelope.observation_type == ObservationType.MEASUREMENT:
        return "mes.measurement"
    if envelope.observation_type == ObservationType.STATE:
        return "mes.state_snapshot"

    # Insufficient semantics
    return None


class MESProjection:
    """Semantic MES projection from neutral ObservationEnvelope.

    Uses explicit semantic discriminator.  Returns None for irrelevant
    envelopes (e.g. EVENT with unknown event_type, HUMAN_ENTRY without
    explicit semantic_type).  No Odoo DB IDs, no substring heuristics.
    """

    projection_id: str = "mes"

    def project(self, envelope: ObservationEnvelope) -> ProjectedMessage | None:
        msg_type = _resolve_mes_type(envelope)
        if msg_type is None:
            return None

        # Derive schema_name from the message_type
        schema_suffix = msg_type[len("mes."):]  # e.g. "quality_result"
        schema_name = f"{_SCHEMA_PREFIX}.{schema_suffix}"

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

        # Envelope payload fields
        for k, v in envelope.payload.items():
            if k not in payload:
                payload[k] = v

        return ProjectedMessage(
            projection_id=self.projection_id,
            message_type=msg_type,
            schema_name=schema_name,
            schema_version="1.0",
            key=envelope.idempotency_key,
            headers={
                "correlation_id": envelope.correlation_id or "",
                "causation_id": envelope.causation_id or "",
            },
            payload=payload,
        )
