"""Future-event scheduler using a stable min-heap.

Data-driven — callbacks, lambdas and executable handlers are prohibited.
"""

from __future__ import annotations

import dataclasses
import heapq
from dataclasses import dataclass
from typing import Any, Iterator

from virtual_factory.discrete.clock import DiscreteClock, DiscreteClockError
from virtual_factory.discrete.events import ScheduledEvent


class FutureEventSchedulerError(RuntimeError):
    """Raised when a scheduler invariant is violated."""


@dataclass(frozen=True, order=True)
class _ScheduleKey:
    """Lightweight ordering key — fields in sort order.

    Ordering: simulation_time_s → priority → sequence.
    No UID or random component.
    """

    simulation_time_s: float
    priority: int
    sequence: int


class FutureEventScheduler:
    """A stable future-event scheduler backed by a min-heap.

    Events are ordered deterministically:
    1. ``simulation_time_s`` — lower first
    2. ``priority`` — lower first
    3. ``sequence`` — lower first (monotonic, per scheduler)

    Capacity:
    - Default ``max_events=100_000``.
    - ``schedule()`` raises ``FutureEventSchedulerError`` when full.

    Clock:
    - Self-contained ``DiscreteClock``, not exposed mutably.
    - ``current_time_s`` / ``now()`` are read-only.
    - ``pop_next()`` advances the clock atomically.

    Identity:
    - Duplicate ``event_id`` values are rejected within a scheduler lifetime.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        max_events: int = 100_000,
        initial_time_s: float = 0.0,
    ) -> None:
        if isinstance(max_events, bool):
            raise FutureEventSchedulerError("max_events must be int, not bool")
        if not isinstance(max_events, int) or max_events < 1:
            raise FutureEventSchedulerError(
                f"max_events must be a positive int, got {max_events!r}"
            )

        self._max_events = max_events
        self._clock = DiscreteClock(initial_time_s)
        self._heap: list[tuple[_ScheduleKey, ScheduledEvent]] = []
        self._sequence_counter: int = 0
        self._seen_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def current_time_s(self) -> float:
        return self._clock.current_time_s

    def now(self) -> float:
        """Return the current simulation time (read-only)."""
        return self._clock.now()

    @property
    def max_events(self) -> int:
        return self._max_events

    @property
    def pending_count(self) -> int:
        return len(self._heap)

    @property
    def is_empty(self) -> bool:
        return len(self._heap) == 0

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    def schedule(self, event: ScheduledEvent) -> str:
        """Insert an event.  Returns its ``event_id``.

        Caller-assigned sequence is rejected; the scheduler assigns sequence
        via ``dataclasses.replace``.

        Raises:
            FutureEventSchedulerError: if the event has a preassigned sequence,
                is in the past, has a duplicate ID, or the scheduler is full.
        """
        # --- Reject caller-assigned sequence ---
        if event.sequence is not None:
            raise FutureEventSchedulerError(
                "sequence is scheduler-owned; "
                "schedule an event with sequence=None"
            )

        # --- Capacity ---
        if len(self._heap) >= self._max_events:
            raise FutureEventSchedulerError(
                f"Scheduler full (capacity={self._max_events})"
            )

        # --- Duplicate ID ---
        if event.event_id in self._seen_ids:
            raise FutureEventSchedulerError(
                f"Duplicate event_id: {event.event_id!r}"
            )

        # --- Time validation ---
        t = event.simulation_time_s
        if t < self._clock.current_time_s:
            raise FutureEventSchedulerError(
                f"Cannot schedule event in the past: "
                f"event_time={t} < current={self._clock.current_time_s}"
            )
        # (NaN/inf/negative already rejected by ScheduledEvent)

        # --- Assign sequence ---
        self._sequence_counter += 1
        canonical = dataclasses.replace(event, sequence=self._sequence_counter)

        key = _ScheduleKey(
            simulation_time_s=canonical.simulation_time_s,
            priority=canonical.priority,
            sequence=canonical.sequence,
        )
        heapq.heappush(self._heap, (key, canonical))
        self._seen_ids.add(canonical.event_id)
        return canonical.event_id

    # ------------------------------------------------------------------
    # Inspection (non-mutating)
    # ------------------------------------------------------------------

    def peek_next(self) -> ScheduledEvent | None:
        """Return the next event without removing it or advancing the clock."""
        if not self._heap:
            return None
        return self._heap[0][1]

    def pending_snapshot(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return a stable sorted copy of pending events as dicts.

        Args:
            limit: Max events to return. ``None`` = all, ``0`` = empty list.

        Raises:
            FutureEventSchedulerError: if *limit* is negative, bool, or
                non-integer.

        Does NOT mutate the heap or clock.
        """
        if limit is not None:
            if isinstance(limit, bool):
                raise FutureEventSchedulerError("limit must be int or None, not bool")
            if not isinstance(limit, int):
                raise FutureEventSchedulerError(
                    f"limit must be int or None, got {type(limit).__name__}"
                )
            if limit < 0:
                raise FutureEventSchedulerError(
                    f"limit must be >= 0, got {limit}"
                )

        sorted_events = sorted(
            self._heap, key=lambda item: (
                item[0].simulation_time_s,
                item[0].priority,
                item[0].sequence,
            )
        )
        if limit is not None:
            sorted_events = sorted_events[:limit]
        return [event.to_dict() for _, event in sorted_events]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def pop_next(self) -> ScheduledEvent | None:
        """Pop and return the next event, advancing the clock atomically.

        The clock is advanced **after** the event is successfully removed
        from the heap.  If the clock refuses the advance (should never
        happen for a valid heap), the popped event is pushed back
        and a ``FutureEventSchedulerError`` is raised — no event is lost.

        Returns ``None`` when the heap is empty.
        """
        if not self._heap:
            return None

        key, event = heapq.heappop(self._heap)
        try:
            self._clock.advance_to(key.simulation_time_s)
        except DiscreteClockError:
            # Atomic guarantee: push back, re-raise
            heapq.heappush(self._heap, (key, event))
            raise FutureEventSchedulerError(
                f"Clock rejected advance to {key.simulation_time_s} "
                f"(current={self._clock.current_time_s}). Event not lost."
            ) from None
        return event

    def pop_all(self) -> Iterator[ScheduledEvent]:
        """Yield all pending events in order, empties the heap.

        Clock is advanced to the time of the final event.
        """
        while event := self.pop_next():
            yield event

