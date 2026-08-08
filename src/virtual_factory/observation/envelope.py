"""Consumer-neutral observation envelope and type definitions.

M5-S01: ObservationType enum + ObservationEnvelope frozen dataclass
+ deterministic idempotency key helper.

Immutable. No MES/Odoo/protocol/runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


# ═══════════════════════════════════════════════════
# ObservationType
# ═══════════════════════════════════════════════════

class ObservationType(str, Enum):
    """Consumer-neutral observation types.

    Stable serialized values. No MES/protocol/TIPA-specific names.
    """

    EVENT = "event"
    MEASUREMENT = "measurement"
    STATE = "state"
    HUMAN_ENTRY = "human_entry"


# ═══════════════════════════════════════════════════
# Idempotency key
# ═══════════════════════════════════════════════════

def make_idempotency_key(
    run_id: str,
    source_event_id: str,
    point_id: str,
    schema_version: str = "1.0",
) -> str:
    """Generate a deterministic idempotency key.

    Format: run_id|source_event_id|point_id|schema_version

    Same logical input → same key.  Used for consumer dedup/replay.
    Distinct from observation_id (UUID).
    """
    if not run_id or not source_event_id or not point_id:
        raise ValueError(
            "run_id, source_event_id, and point_id must be non-empty"
        )
    if "|" in run_id or "|" in source_event_id or "|" in point_id:
        raise ValueError(
            "idempotency key components must not contain '|'"
        )
    return f"{run_id}|{source_event_id}|{point_id}|{schema_version}"


# ═══════════════════════════════════════════════════
# ObservationEnvelope
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ObservationEnvelope:
    """Consumer-neutral observation carrier.

    Immutable (frozen dataclass).  Nested dicts (context, payload) are
    shallow-copied on construction via __post_init__ to prevent external
    mutation of the envelope's internal state.

    Fields are ordered by importance.  Optional context remains optional.
    """

    # ── Identity ──
    observation_id: str
    idempotency_key: str
    observation_type: ObservationType

    # ── Run context ──
    run_id: str
    model_id: str

    # ── Time ──
    simulation_time_s: float
    occurred_at: str | None = None       # ISO 8601, None if no run epoch
    emitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ── Source ──
    source_domain: str = ""
    source_path: str = ""

    # ── Subject ──
    subject_type: str | None = None
    subject_id: str | None = None

    # ── Context / payload ──
    context: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    # ── Quality / correlation ──
    quality: str = "GOOD"
    correlation_id: str | None = None
    causation_id: str | None = None

    # ── Schema ──
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        # ── Required fields ──
        if not self.observation_id or not isinstance(self.observation_id, str):
            raise ValueError("observation_id must be a non-empty str")
        if not self.idempotency_key or not isinstance(self.idempotency_key, str):
            raise ValueError("idempotency_key must be a non-empty str")
        if not isinstance(self.observation_type, ObservationType):
            raise ValueError(
                f"observation_type must be ObservationType, "
                f"got {type(self.observation_type).__name__}"
            )
        if not self.run_id or not isinstance(self.run_id, str):
            raise ValueError("run_id must be a non-empty str")
        if not self.model_id or not isinstance(self.model_id, str):
            raise ValueError("model_id must be a non-empty str")

        # ── simulation_time_s ──
        if isinstance(self.simulation_time_s, bool):
            raise ValueError("simulation_time_s must be float, not bool")
        if not isinstance(self.simulation_time_s, (int, float)):
            raise ValueError(
                f"simulation_time_s must be float, "
                f"got {type(self.simulation_time_s).__name__}"
            )
        if self.simulation_time_s < 0:
            raise ValueError("simulation_time_s must be >= 0")

        # ── schema_version ──
        if not self.schema_version or not isinstance(self.schema_version, str):
            raise ValueError("schema_version must be a non-empty str")

        # ── Immutability: shallow-copy mutable fields ──
        object.__setattr__(self, "context", dict(self.context))
        object.__setattr__(self, "payload", dict(self.payload))

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        """Return a plain serializable dict suitable for JSON/JSONL/projections.

        Preserves all fields.  Dates serialize as ISO 8601 strings.
        """
        return {
            "observation_id": self.observation_id,
            "idempotency_key": self.idempotency_key,
            "observation_type": self.observation_type.value,
            "run_id": self.run_id,
            "model_id": self.model_id,
            "simulation_time_s": self.simulation_time_s,
            "occurred_at": self.occurred_at,
            "emitted_at": self.emitted_at,
            "source_domain": self.source_domain,
            "source_path": self.source_path,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "context": dict(self.context),
            "payload": dict(self.payload),
            "quality": self.quality,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "schema_version": self.schema_version,
        }
