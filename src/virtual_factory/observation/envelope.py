"""Consumer-neutral observation envelope and type definitions.

M5-S01: ObservationType enum + ObservationEnvelope frozen dataclass
+ deterministic idempotency key helper.

Effectively immutable. No MES/Odoo/protocol/runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


# ═══════════════════════════════════════════════════
# ISO 8601 validation (real datetime parsing)
# ═══════════════════════════════════════════════════

def _parse_iso8601(value: str) -> datetime:
    """Parse an ISO 8601 datetime string.  Raises ValueError on failure.

    Handles ``Z`` suffix by replacing with ``+00:00`` for
    ``datetime.fromisoformat`` compatibility (Python < 3.11).

    Also raises ValueError if the parsed datetime has no timezone
    (naive datetime), since all envelope timestamps must be timezone-aware.
    """
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        raise ValueError(f"datetime must have timezone, got naive: {value!r}")
    return dt


def _is_utc(value: str) -> bool:
    """Return True if *value* represents UTC (Z or +00:00)."""
    return value.endswith("Z") or value.endswith("+00:00")


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

    Effectively immutable: ``frozen=True`` prevents field reassignment;
    ``context`` and ``payload`` are stored as ``MappingProxyType``
    (read-only views) to prevent mutation after construction.

    Nested mutable objects *inside* ``context`` or ``payload`` values
    are not recursively frozen — immutability is top-level only.
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

    # ── Context / payload (read-only via MappingProxyType) ──
    context: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

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

        # ── Idempotency key format validation ──
        _validate_idempotency_key_format(
            self.idempotency_key, self.run_id, self.schema_version
        )

        # ── Time validation (real datetime parsing) ──
        if self.occurred_at is not None:
            try:
                _parse_iso8601(self.occurred_at)
            except ValueError as exc:
                raise ValueError(
                    f"occurred_at must be valid ISO 8601 with timezone, "
                    f"got {self.occurred_at!r}"
                ) from exc
        try:
            _parse_iso8601(self.emitted_at)
        except ValueError as exc:
            raise ValueError(
                f"emitted_at must be valid ISO 8601 with timezone, "
                f"got {self.emitted_at!r}"
            ) from exc
        if not _is_utc(self.emitted_at):
            raise ValueError(
                f"emitted_at must be UTC (Z or +00:00), "
                f"got {self.emitted_at!r}"
            )

        # ── Immutability: wrap mutable fields in read-only proxy ──
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        """Return a plain serializable dict suitable for JSON/JSONL/projections.

        Preserves all fields.  Dates serialize as ISO 8601 strings.
        ``context`` and ``payload`` are returned as plain dict copies.
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


def _validate_idempotency_key_format(
    key: str, run_id: str, schema_version: str
) -> None:
    """Validate idempotency_key format: run_id|source_event_id|point_id|schema_version.

    All 4 parts must be non-empty.  First must equal *run_id*.
    Last must equal *schema_version*.
    """
    parts = key.split("|")
    if len(parts) != 4:
        raise ValueError(
            f"idempotency_key must have 4 pipe-separated parts, "
            f"got {len(parts)}: {key!r}"
        )
    for i, part in enumerate(parts):
        if not part:
            raise ValueError(
                f"idempotency_key part {i} must be non-empty, "
                f"got {key!r}"
            )
    if parts[0] != run_id:
        raise ValueError(
            f"idempotency_key first part must match run_id={run_id!r}, "
            f"got {parts[0]!r}"
        )
    if parts[3] != schema_version:
        raise ValueError(
            f"idempotency_key last part must match schema_version="
            f"{schema_version!r}, got {parts[3]!r}"
        )
