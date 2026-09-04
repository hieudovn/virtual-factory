"""VF-vNEXT-G3 — append-style typed EventStore tests.

Proves (Issue #48): the event store accepts typed immutable facts and preserves
append order; no arbitrary dict mutation can be stored or retroactively change
facts; there is no mutation/deletion workflow in G3.
"""

from __future__ import annotations

import pytest

from virtual_factory.telemetry.event_fact import (
    EventCategory,
    EventFact,
    EventFactError,
)
from virtual_factory.telemetry.event_store import EventStore


def _fact(event_id: str = "evt-1") -> EventFact:
    return EventFact(
        event_id=event_id,
        event_type="process.started",
        category=EventCategory.PROCESS,
        simulation_time_s=1.0,
        payload={"n": 1},
    )


def test_append_accepts_typed_immutable_facts() -> None:
    store = EventStore()
    index = store.append(_fact("evt-1"))
    assert index == 0
    assert store.append(_fact("evt-2")) == 1
    assert len(store) == 2


def test_append_rejects_arbitrary_dict_mutation() -> None:
    store = EventStore()
    with pytest.raises(EventFactError):
        store.append({"event_id": "evt-x"})  # type: ignore[arg-type]


def test_append_order_is_preserved_and_deterministic() -> None:
    store = EventStore()
    store.append(_fact("evt-a"))
    store.append(_fact("evt-b"))
    store.append(_fact("evt-c"))
    assert [f.event_id for f in store] == ["evt-a", "evt-b", "evt-c"]
    assert [f.event_id for f in store.events] == ["evt-a", "evt-b", "evt-c"]
    # Repeated reads are stable (append order).
    assert [f.event_id for f in store.events] == ["evt-a", "evt-b", "evt-c"]


def test_no_mutation_or_deletion_workflow_in_g3() -> None:
    store = EventStore()
    store.append(_fact())
    for attr in ("remove", "delete", "clear", "pop", "update"):
        assert not hasattr(store, attr), f"EventStore must not expose {attr}"


def test_events_property_is_read_only_snapshot() -> None:
    store = EventStore()
    store.append(_fact("evt-a"))
    snapshot = store.events
    store.append(_fact("evt-b"))
    # The earlier snapshot is detached (immutable tuple); new appends don't
    # mutate previously returned snapshots.
    assert [f.event_id for f in snapshot] == ["evt-a"]
    assert len(store) == 2


def test_stored_fact_cannot_be_retroactively_changed() -> None:
    store = EventStore()
    store.append(_fact("evt-a"))
    first = store.events[0]
    records_before = store.to_records()
    # Frozen fact: no field reassignment, no payload mutation.
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        first.event_type = "mutated"  # type: ignore[misc]
    with pytest.raises(TypeError):
        first.payload["n"] = 99  # type: ignore[index]
    assert store.to_records() == records_before


def test_to_records_is_deterministic_serialization() -> None:
    store = EventStore()
    store.append(_fact("evt-a"))
    store.append(_fact("evt-b"))
    records = store.to_records()
    assert [r["event_id"] for r in records] == ["evt-a", "evt-b"]
    assert records == store.to_records()
