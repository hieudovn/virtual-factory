"""Typed immutable platform Event fact + Alarm specialization (G3).

ARCH-03 / Issue #48 contract (frozen):

- Runtime/domain state is the SOLE mutable simulation truth.
- An Event is an immutable, append-style downstream occurrence/activity fact.
- Alarm is a specialization/category of Event — never a parallel truth store.
- Mutable alarm condition/state is a DERIVED projection
  (``telemetry.alarm_manager.AlarmState``) and never mutates the historical fact.
- Event Timeline / Alarm List, when projected, are views over these same facts
  (this module provides no historian/database).

This module is dependency-light and consumer-neutral: G1 structural identity and
G2 provenance are carried ONLY when explicitly supplied and never fabricated.
PIM canonical identity and evidence maturity are never invented here.
"""

from __future__ import annotations

import math
import types
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from virtual_factory.provenance.envelope import ProvenanceV2
from virtual_factory.workspace.identity import StructuralPath


class EventFactError(ValueError):
    """Raised when an event-fact invariant is violated."""


class EventCategory(str, Enum):
    """Occurrence/activity classification captured at event creation.

    ``ALARM`` is the Event specialization/category used by alarm occurrence
    facts (Alarm ⊂ Event). This is an occurrence classification, NOT a mutable
    acknowledgement/workflow lifecycle status.
    """

    PROCESS = "process"
    ACTIVITY = "activity"
    QUALITY = "quality"
    LIFECYCLE = "lifecycle"
    ALARM = "alarm"


# ──────────────────────────────────────────────────────────────
# Payload freezing (deep-immutable JSON-compatible data)
# ──────────────────────────────────────────────────────────────

def _freeze(value: Any, path: str) -> Any:
    """Recursively validate and freeze event payload data."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise EventFactError(f"{path}: non-finite float is not allowed")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v, f"{path}[{i}]") for i, v in enumerate(value))
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise EventFactError(f"{path}: mapping keys must be str")
            frozen[k] = _freeze(v, f"{path}.{k}")
        return types.MappingProxyType(frozen)
    if callable(value):
        raise EventFactError(f"{path}: callables are not allowed in payload")
    raise EventFactError(
        f"{path}: unsupported payload type {type(value).__name__}"
    )


def _to_plain(value: Any) -> Any:
    """Convert frozen payload back to plain dict/list for serialization."""
    if isinstance(value, Mapping):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(v) for v in value]
    return value


def _require_nonempty(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EventFactError(f"{name} must be a non-empty str")


# ──────────────────────────────────────────────────────────────
# EventFact
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class EventFact:
    """Immutable platform event/occurrence fact.

    An Event is a FACT: no acknowledgement/active/clear workflow may mutate or
    erase it. ``status``/``severity`` are occurrence/fact classifications
    captured at creation (not mutable lifecycle workflow status).
    """

    # ── identity ──
    event_id: str
    event_type: str
    category: EventCategory

    # ── occurrence time (simulation truth) ──
    simulation_time_s: float

    # ── run / structural context (optional, never fabricated) ──
    run_id: str | None = None
    workspace_id: str | None = None
    scope_path: StructuralPath | None = None

    # ── source / classification ──
    source: str | None = None
    severity: str | None = None
    status: str | None = None

    # ── immutable payload / context ──
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None

    # ── G2 provenance reference/value where appropriate ──
    provenance: ProvenanceV2 | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.event_id, "event_id")
        _require_nonempty(self.event_type, "event_type")
        if not isinstance(self.category, EventCategory):
            raise EventFactError(
                f"category must be EventCategory, got {type(self.category).__name__}"
            )
        if isinstance(self.simulation_time_s, bool) or not isinstance(
            self.simulation_time_s, (int, float)
        ):
            raise EventFactError("simulation_time_s must be numeric, not bool")
        if self.simulation_time_s < 0:
            raise EventFactError("simulation_time_s must be >= 0")

        for name in ("run_id", "workspace_id", "source", "severity", "status",
                     "correlation_id", "causation_id"):
            value = getattr(self, name)
            if value is not None:
                _require_nonempty(value, name)

        if self.scope_path is not None and not isinstance(
            self.scope_path, StructuralPath
        ):
            raise EventFactError(
                f"scope_path must be StructuralPath, "
                f"got {type(self.scope_path).__name__}"
            )
        if (
            self.workspace_id is not None
            and self.scope_path is not None
            and self.scope_path.workspace_id != self.workspace_id
        ):
            raise EventFactError(
                "scope_path.workspace_id must match workspace_id"
            )

        if self.provenance is not None:
            if not isinstance(self.provenance, ProvenanceV2):
                raise EventFactError(
                    "provenance must be ProvenanceV2, "
                    f"got {type(self.provenance).__name__}"
                )
            if (
                self.workspace_id is not None
                and self.provenance.workspace_id != self.workspace_id
            ):
                raise EventFactError(
                    "provenance.workspace_id must match workspace_id"
                )

        # Deep-freeze the payload so no retroactive dict mutation is possible.
        object.__setattr__(self, "payload", _freeze(self.payload, "payload"))

    def to_dict(self) -> dict[str, Any]:
        """Deterministic, detached, key-stable serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "category": self.category.value,
            "simulation_time_s": self.simulation_time_s,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "scope_path": (
                self.scope_path.as_string() if self.scope_path is not None else None
            ),
            "source": self.source,
            "severity": self.severity,
            "status": self.status,
            "payload": _to_plain(self.payload),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "provenance": (
                self.provenance.to_dict() if self.provenance is not None else None
            ),
        }


# ──────────────────────────────────────────────────────────────
# AlarmEventFact — Alarm ⊂ Event
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AlarmEventFact(EventFact):
    """Alarm occurrence fact — an EventFact specialization.

    Every alarm occurrence fact IS an ``EventFact`` (``category=ALARM``) with
    alarm-specific metadata carried beside the shared event identity. Alarm
    identity (``alarm_id``) is a dimension of the fact, NOT a duplicate event
    identity; mutable current alarm condition/state lives in
    ``AlarmManager.states`` (AlarmState, a derived projection) and never mutates
    this historical fact.
    """

    alarm_id: str = ""
    alarm_kind: str = ""  # high | low | bad_quality | equals | not_equals
    transition: str = "assert"  # assert | clear  (occurrence classification)
    threshold: float | int | str | bool | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        # NOTE: do NOT use zero-arg super() inside a slotted dataclass method:
        # dataclasses recreates the class for __slots__, leaving the method's
        # __class__ cell stale. Call the base validator explicitly instead.
        EventFact.__post_init__(self)
        if self.category is not EventCategory.ALARM:
            raise EventFactError("AlarmEventFact category must be ALARM")
        _require_nonempty(self.alarm_id, "alarm_id")
        _require_nonempty(self.alarm_kind, "alarm_kind")
        if self.transition not in ("assert", "clear"):
            raise EventFactError(
                "transition must be 'assert' or 'clear', "
                f"got {self.transition!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        # Explicit base call (zero-arg super() is unsafe inside slotted-dataclass
        # subclass methods — stale __class__ cell).
        d = EventFact.to_dict(self)
        d["alarm"] = {
            "alarm_id": self.alarm_id,
            "alarm_kind": self.alarm_kind,
            "transition": self.transition,
            "threshold": self.threshold,
            "message": self.message,
        }
        return d
