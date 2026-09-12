"""Append-style typed event-fact store (G3).

ARCH-03 / Issue #48: Event storage is append-only over immutable, typed
:class:`EventFact` objects — never arbitrary mutable ``dict`` truth. There is no
mutation/deletion workflow in G3 and no historian/database implementation. Read
order is the deterministic append order; Event Timeline / Alarm List, when
projected, are read-only views over these same facts.
"""

from __future__ import annotations

from typing import Any, Iterator

from virtual_factory.telemetry.event_fact import EventFact, EventFactError


class EventStore:
    """Append-only, in-memory store of typed immutable event facts."""

    def __init__(self) -> None:
        self._facts: list[EventFact] = []

    def append(self, fact: EventFact) -> int:
        """Append one typed immutable event fact; return its sequence index.

        Rejects non-``EventFact`` values (no arbitrary dict mutation).
        """
        if not isinstance(fact, EventFact):
            raise EventFactError(
                f"EventStore.append requires an EventFact, "
                f"got {type(fact).__name__}"
            )
        self._facts.append(fact)
        return len(self._facts) - 1

    def __len__(self) -> int:
        return len(self._facts)

    def __iter__(self) -> Iterator[EventFact]:
        return iter(self._facts)

    @property
    def events(self) -> tuple[EventFact, ...]:
        """Read-only snapshot of stored facts in append order.

        Backward-compatible read name; now an immutable tuple view (no mutation
        of stored facts through this property).
        """
        return tuple(self._facts)

    def to_records(self) -> list[dict[str, Any]]:
        """Deterministic serialization of all stored facts (append order)."""
        return [fact.to_dict() for fact in self._facts]
