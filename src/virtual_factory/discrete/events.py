"""Immutable scheduled-event record — frozen dataclass with deep payload validation.

Events are pure data — no callbacks, lambdas or executable handlers.
"""

from __future__ import annotations

import math
import types
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class EventRecordError(ValueError):
    """Raised when an event record invariant is violated."""


# ──────────────────────────────────────────────
# Payload validation & freezing
# ──────────────────────────────────────────────

def _validate_and_freeze(value: Any, path: str) -> Any:
    """Recursively validate JSON-compatible and return a frozen copy.

    Allowed: None, bool, int, finite float, str, Mapping[str→allowed], list/tuple[allowed].
    Rejected: callables, arbitrary objects, non-finite floats.
    All Mappings (dict, MappingProxyType, etc.) are revalidated — none are trusted.
    Returns: primitives, tuple (for lists), MappingProxyType (for mappings).
    """
    if callable(value):
        raise EventRecordError(f"{path}: callables are not allowed in payload")
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise EventRecordError(
                f"{path}: non-finite float {value!r} is not allowed"
            )
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(
            _validate_and_freeze(item, f"{path}[{i}]")
            for i, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        frozen_items: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise EventRecordError(
                    f"{path}: mapping keys must be str, "
                    f"got {type(k).__name__!r}"
                )
            frozen_items[k] = _validate_and_freeze(v, f"{path}.{k}")
        return types.MappingProxyType(frozen_items)
    raise EventRecordError(
        f"{path}: unsupported type {type(value).__name__!r}"
    )


def _to_plain(value: Any) -> Any:
    """Convert frozen payload back to plain dict/list for ``to_dict()``."""
    if isinstance(value, Mapping):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(v) for v in value]
    return value


# ──────────────────────────────────────────────
# ScheduledEvent
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    """An immutable event scheduled to occur at a specific simulation time.

    Ordering (enforced by the scheduler):
    1. Lowest ``simulation_time_s``
    2. Lowest ``priority`` (lower = earlier)
    3. Lowest ``sequence`` (assigned by scheduler)

    Attributes:
        event_id: Non-empty unique identifier.
        simulation_time_s: When this event should occur (>= 0, finite).
        event_type: Non-empty event kind string.
        target_id: Entity, station or resource this event targets.
        priority: Ordering tie-breaker (int, not bool; lower = earlier).
        sequence: ``None`` before scheduling; assigned by scheduler.
        payload: Deep-immutable JSON-compatible data.
        correlation_id: Optional non-empty grouping/correlation id.
        causation_id: Optional non-empty parent/trigger event id.
    """

    event_id: str
    simulation_time_s: float
    event_type: str
    target_id: str = ""
    priority: int = 0
    sequence: int | None = None
    payload: Any = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        # --- event_id ---
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise EventRecordError("event_id must be a non-empty str")

        # --- simulation_time_s ---
        if isinstance(self.simulation_time_s, bool):
            raise EventRecordError("simulation_time_s must be numeric, got bool")
        if not isinstance(self.simulation_time_s, (int, float)):
            raise EventRecordError(
                f"simulation_time_s must be numeric, "
                f"got {type(self.simulation_time_s).__name__}"
            )
        if math.isnan(self.simulation_time_s):
            raise EventRecordError("simulation_time_s must be finite, got NaN")
        if math.isinf(self.simulation_time_s):
            raise EventRecordError("simulation_time_s must be finite, got infinite")
        if self.simulation_time_s < 0.0:
            raise EventRecordError(
                f"simulation_time_s must be >= 0, got {self.simulation_time_s}"
            )
        object.__setattr__(self, "simulation_time_s", float(self.simulation_time_s))

        # --- event_type ---
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise EventRecordError("event_type must be a non-empty str")

        # --- target_id ---
        if not isinstance(self.target_id, str):
            raise EventRecordError(
                f"target_id must be str, got {type(self.target_id).__name__}"
            )

        # --- priority ---
        if isinstance(self.priority, bool):
            raise EventRecordError("priority must be int, not bool")
        if not isinstance(self.priority, int):
            raise EventRecordError(
                f"priority must be int, got {type(self.priority).__name__}"
            )

        # --- sequence ---
        if self.sequence is not None:
            if isinstance(self.sequence, bool):
                raise EventRecordError("sequence must be int or None, not bool")
            if not isinstance(self.sequence, int):
                raise EventRecordError(
                    f"sequence must be int or None, got {type(self.sequence).__name__}"
                )

        # --- correlation_id ---
        if self.correlation_id is not None:
            if not isinstance(self.correlation_id, str) or not self.correlation_id.strip():
                raise EventRecordError(
                    "correlation_id must be a non-empty str if provided"
                )

        # --- causation_id ---
        if self.causation_id is not None:
            if not isinstance(self.causation_id, str) or not self.causation_id.strip():
                raise EventRecordError(
                    "causation_id must be a non-empty str if provided"
                )

        # --- payload ---
        if self.payload is None:
            object.__setattr__(self, "payload", types.MappingProxyType({}))
        elif not isinstance(self.payload, Mapping):
            raise EventRecordError(
                f"payload must be a Mapping or None, got {type(self.payload).__name__}"
            )
        else:
            # Always revalidate — never trust a Mapping just because it's already frozen
            frozen = _validate_and_freeze(self.payload, "payload")
            object.__setattr__(self, "payload", frozen)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a detached plain dictionary representation.

        Mutating the returned dict has no effect on the event.
        """
        return {
            "event_id": self.event_id,
            "simulation_time_s": self.simulation_time_s,
            "priority": self.priority,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "target_id": self.target_id,
            "payload": _to_plain(self.payload),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }

    def __repr__(self) -> str:
        return (
            f"ScheduledEvent(id={self.event_id!r}, "
            f"t={self.simulation_time_s}, "
            f"seq={self.sequence}, "
            f"type={self.event_type!r}, "
            f"target={self.target_id!r})"
        )
