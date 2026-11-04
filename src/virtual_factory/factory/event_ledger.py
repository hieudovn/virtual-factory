"""Append-only committed simulated event ledger with canonical digests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from virtual_factory.factory.module_contract import (
    DEFINITION_PROVENANCES,
    SOURCE_KINDS,
    CausalPhase,
    freeze_payload,
    thaw_payload,
)
from virtual_factory.factory.run_context import SimTick, coerce_tick


class LedgerError(ValueError):
    """Base error for event ledger invariants."""


class DuplicateEventError(LedgerError):
    """Raised when an event_id is appended twice."""


class IdempotencyConflictError(LedgerError):
    """Raised when a scoped local sequence is reused."""


class LedgerDigestError(LedgerError):
    """Raised when a restored ledger digest does not match."""


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"value is not canonical JSON: {exc}") from exc


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{name} must be a non-empty str")
    return value


def _require_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise LedgerError(f"{name} must be int, not bool")
    if not isinstance(value, int) or value < 0:
        raise LedgerError(f"{name} must be int >= 0")
    return value


@dataclass(frozen=True, slots=True)
class CommittedEvent:
    factory_run_id: str
    generation: int
    module_id: str
    local_sequence: int
    tick: SimTick
    event_id: str
    event_type: str
    sequence: int
    causal_phase: CausalPhase
    definition_digest: str
    payload: Any = None
    causation_id: str | None = None
    correlation_id: str | None = None
    source_id: str | None = None
    source_kind: str = "SIMULATED"
    definition_provenance: str = "SYNTHETIC_ASSUMPTION"

    def __post_init__(self) -> None:
        _require_text(self.factory_run_id, "factory_run_id")
        _require_nonnegative_int(self.generation, "generation")
        _require_text(self.module_id, "module_id")
        _require_nonnegative_int(self.local_sequence, "local_sequence")
        object.__setattr__(self, "tick", coerce_tick(self.tick))
        _require_text(self.event_id, "event_id")
        _require_text(self.event_type, "event_type")
        if isinstance(self.sequence, bool):
            raise LedgerError("sequence must be int, not bool")
        if not isinstance(self.sequence, int) or self.sequence <= 0:
            raise LedgerError("sequence must be int > 0")
        if not isinstance(self.causal_phase, CausalPhase):
            try:
                object.__setattr__(
                    self, "causal_phase", CausalPhase(self.causal_phase)
                )
            except ValueError as exc:
                raise LedgerError(
                    f"invalid causal_phase: {self.causal_phase!r}"
                ) from exc
        _require_text(self.definition_digest, "definition_digest")
        _require_text(self.source_kind, "source_kind")
        _require_text(self.definition_provenance, "definition_provenance")
        if self.source_kind not in SOURCE_KINDS:
            raise LedgerError(
                f"source_kind must be one of {sorted(SOURCE_KINDS)}, "
                f"got {self.source_kind!r}"
            )
        if self.definition_provenance not in DEFINITION_PROVENANCES:
            raise LedgerError(
                "definition_provenance must be one of "
                f"{sorted(DEFINITION_PROVENANCES)}, "
                f"got {self.definition_provenance!r}"
            )
        for name, value in (
            ("causation_id", self.causation_id),
            ("correlation_id", self.correlation_id),
            ("source_id", self.source_id),
        ):
            if value is not None:
                _require_text(value, name)
        object.__setattr__(self, "payload", freeze_payload(self.payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "factory_run_id": self.factory_run_id,
            "generation": self.generation,
            "module_id": self.module_id,
            "local_sequence": self.local_sequence,
            "tick_us": self.tick.tick_us,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sequence": self.sequence,
            "causal_phase": self.causal_phase.value,
            "definition_digest": self.definition_digest,
            "payload": thaw_payload(self.payload),
            "causation_id": self.causation_id,
            "correlation_id": self.correlation_id,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "definition_provenance": self.definition_provenance,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CommittedEvent:
        try:
            values = dict(data)
            tick_us = values.pop("tick_us")
            return cls(tick=SimTick(tick_us), **values)
        except (KeyError, TypeError, ValueError) as exc:
            raise LedgerError(f"malformed committed event: {exc}") from exc

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


class ReadSnapshot:
    """Immutable read view handed to modules during proposal gathering."""

    __slots__ = ("_factory_run_id", "_generation", "_tick", "_events", "_by_id")

    def __init__(
        self,
        factory_run_id: str,
        generation: int,
        tick: SimTick,
        events: tuple[CommittedEvent, ...],
    ) -> None:
        self._factory_run_id = factory_run_id
        self._generation = generation
        self._tick = coerce_tick(tick)
        self._events = tuple(events)
        self._by_id = {event.event_id: event for event in self._events}

    @property
    def factory_run_id(self) -> str:
        return self._factory_run_id

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def tick(self) -> SimTick:
        return self._tick

    @property
    def events(self) -> tuple[CommittedEvent, ...]:
        return self._events

    def get_event(self, event_id: str) -> CommittedEvent | None:
        return self._by_id.get(event_id)

    def has_event(self, event_id: str) -> bool:
        return event_id in self._by_id


class EventLedger:
    """Append-only ledger scoped to one factory run."""

    def __init__(self, factory_run_id: str | None = None) -> None:
        if factory_run_id is not None:
            _require_text(factory_run_id, "factory_run_id")
        self._factory_run_id = factory_run_id
        self._events: list[CommittedEvent] = []
        self._event_ids: set[str] = set()
        self._idempotency: set[tuple[int, str, int]] = set()

    @property
    def cursor(self) -> int:
        return len(self._events)

    @property
    def events(self) -> tuple[CommittedEvent, ...]:
        return tuple(self._events)

    def has_event_id(self, event_id: str) -> bool:
        return event_id in self._event_ids

    def get_event(self, event_id: str) -> CommittedEvent | None:
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def _validate_next(self, event: CommittedEvent) -> None:
        if not isinstance(event, CommittedEvent):
            raise LedgerError(
                f"event must be CommittedEvent, got {type(event).__name__}"
            )
        if (
            self._factory_run_id is not None
            and event.factory_run_id != self._factory_run_id
        ):
            raise LedgerError(
                f"event run id {event.factory_run_id!r} does not match ledger "
                f"{self._factory_run_id!r}"
            )
        if event.event_id in self._event_ids:
            raise DuplicateEventError(f"duplicate event_id: {event.event_id!r}")
        key = (event.generation, event.module_id, event.local_sequence)
        if key in self._idempotency:
            raise IdempotencyConflictError(
                f"idempotency key already used: {key!r}"
            )
        expected_sequence = self.cursor + 1
        if event.sequence != expected_sequence:
            raise LedgerError(
                f"event sequence {event.sequence} != expected {expected_sequence}"
            )

    def check_append(self, event: CommittedEvent) -> None:
        self._validate_next(event)

    def append(self, event: CommittedEvent) -> int:
        self._validate_next(event)
        self._events.append(event)
        self._event_ids.add(event.event_id)
        self._idempotency.add(
            (event.generation, event.module_id, event.local_sequence)
        )
        return event.sequence

    def trace(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.to_dict() for event in self._events)

    def digest(self) -> str:
        return canonical_digest([event.to_dict() for event in self._events])

    def read_snapshot(self, tick: SimTick, generation: int) -> ReadSnapshot:
        return ReadSnapshot(
            factory_run_id=self._factory_run_id or "",
            generation=generation,
            tick=tick,
            events=self.events,
        )
