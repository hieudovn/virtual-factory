"""Bounded domain-neutral event trace and structured runtime diagnostics.

M2-S03: trace buffer, trace entries, diagnostics projection.
No payload, no wall-clock, no domain objects.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

_MAX_ERROR_DETAIL = 256
_VALID_RESULTS = frozenset({"committed", "failed"})


# ──────────────────────────────────────────────
# Error detail normalization
# ──────────────────────────────────────────────

def _normalize_detail(raw: str | None) -> str | None:
    """Normalize an error detail: no newlines, no extra whitespace, max 256 chars."""
    if raw is None:
        return None
    collapsed = re.sub(r"\s+", " ", raw).strip()
    if len(collapsed) > _MAX_ERROR_DETAIL:
        collapsed = collapsed[:_MAX_ERROR_DETAIL - 3] + "..."
    return collapsed


# ──────────────────────────────────────────────
# EventTraceEntry
# ──────────────────────────────────────────────


class EventTraceEntryError(ValueError):
    """Raised when an EventTraceEntry invariant is violated."""


@dataclass(frozen=True, slots=True)
class EventTraceEntry:
    """Immutable trace record for one dispatched event.

    No payload, no wall-clock, no traceback, no random data.
    """

    trace_sequence: int
    event_id: str
    event_type: str
    target_id: str
    simulation_time_s: float
    priority: int
    scheduler_sequence: int
    correlation_id: str | None
    causation_id: str | None
    result: str                     # "committed" | "failed"
    error_code: str | None
    error_detail: str | None
    state_changes: tuple[str, ...]
    requested_follow_up_events: int
    scheduled_follow_up_events: int
    processed_events_after: int
    pending_events_after: int

    def __post_init__(self) -> None:
        # trace_sequence
        if isinstance(self.trace_sequence, bool):
            raise EventTraceEntryError("trace_sequence must be int, not bool")
        if not isinstance(self.trace_sequence, int) or self.trace_sequence <= 0:
            raise EventTraceEntryError(
                f"trace_sequence must be int > 0, got {self.trace_sequence!r}"
            )

        # event_id
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise EventTraceEntryError("event_id must be non-empty str")

        # event_type
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise EventTraceEntryError("event_type must be non-empty str")

        # target_id
        if not isinstance(self.target_id, str):
            raise EventTraceEntryError("target_id must be str")

        # simulation_time_s
        if isinstance(self.simulation_time_s, bool):
            raise EventTraceEntryError("simulation_time_s must be numeric, not bool")
        import math
        if not isinstance(self.simulation_time_s, (int, float)):
            raise EventTraceEntryError("simulation_time_s must be numeric")
        if math.isnan(self.simulation_time_s) or math.isinf(self.simulation_time_s):
            raise EventTraceEntryError("simulation_time_s must be finite")
        if self.simulation_time_s < 0.0:
            raise EventTraceEntryError("simulation_time_s must be >= 0")

        # priority
        if isinstance(self.priority, bool):
            raise EventTraceEntryError("priority must be int, not bool")
        if not isinstance(self.priority, int):
            raise EventTraceEntryError("priority must be int")

        # scheduler_sequence
        if isinstance(self.scheduler_sequence, bool):
            raise EventTraceEntryError("scheduler_sequence must be int, not bool")
        if not isinstance(self.scheduler_sequence, int) or self.scheduler_sequence < 0:
            raise EventTraceEntryError("scheduler_sequence must be int >= 0")

        # correlation_id / causation_id
        for name, val in [("correlation_id", self.correlation_id), ("causation_id", self.causation_id)]:
            if val is not None:
                if not isinstance(val, str) or not val.strip():
                    raise EventTraceEntryError(
                        f"{name} must be None or non-empty str"
                    )

        # result
        if self.result not in _VALID_RESULTS:
            raise EventTraceEntryError(
                f"result must be 'committed' or 'failed', got {self.result!r}"
            )

        # committed vs failed
        if self.result == "committed":
            if self.error_code is not None:
                raise EventTraceEntryError("committed entry must have error_code=None")
            if self.error_detail is not None:
                raise EventTraceEntryError("committed entry must have error_detail=None")
        else:  # failed
            if not isinstance(self.error_code, str) or not self.error_code.strip():
                raise EventTraceEntryError("failed entry must have non-empty error_code")
            if self.error_detail is not None and not isinstance(self.error_detail, str):
                raise EventTraceEntryError("error_detail must be None or str")
            # Normalize error_detail
            if self.error_detail is not None:
                object.__setattr__(self, "error_detail", _normalize_detail(self.error_detail))

        # state_changes
        if not isinstance(self.state_changes, tuple):
            raise EventTraceEntryError("state_changes must be tuple")
        for i, sc in enumerate(self.state_changes):
            if not isinstance(sc, str):
                raise EventTraceEntryError(f"state_changes[{i}] must be str")

        # counters
        for name, val in [
            ("requested_follow_up_events", self.requested_follow_up_events),
            ("scheduled_follow_up_events", self.scheduled_follow_up_events),
            ("processed_events_after", self.processed_events_after),
            ("pending_events_after", self.pending_events_after),
        ]:
            if isinstance(val, bool):
                raise EventTraceEntryError(f"{name} must be int, not bool")
            if not isinstance(val, int) or val < 0:
                raise EventTraceEntryError(f"{name} must be int >= 0")

        if self.scheduled_follow_up_events > self.requested_follow_up_events:
            raise EventTraceEntryError(
                f"scheduled ({self.scheduled_follow_up_events}) > requested ({self.requested_follow_up_events})"
            )


# ──────────────────────────────────────────────
# EventTraceBuffer
# ──────────────────────────────────────────────


class EventTraceBufferError(ValueError):
    """Raised when an EventTraceBuffer invariant is violated."""


class EventTraceBuffer:
    """Bounded circular buffer for EventTraceEntry records.

    Capacity must be int > 0 (not bool). Default 128.
    Oldest entries evicted when full.
    """

    def __init__(self, capacity: int = 128) -> None:
        if isinstance(capacity, bool):
            raise EventTraceBufferError("capacity must be int, not bool")
        if not isinstance(capacity, int) or capacity <= 0:
            raise EventTraceBufferError(
                f"capacity must be int > 0, got {capacity!r}"
            )
        self._capacity = capacity
        self._buffer: deque[EventTraceEntry] = deque()
        self._total: int = 0
        self._dropped: int = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def total_entries(self) -> int:
        return self._total

    @property
    def dropped_entries(self) -> int:
        return self._dropped

    @property
    def entries(self) -> tuple[EventTraceEntry, ...]:
        """Return detached immutable tuple of retained entries (oldest first)."""
        return tuple(self._buffer)

    def append(self, entry: EventTraceEntry) -> None:
        """Append an entry. Evict oldest if at capacity."""
        if not isinstance(entry, EventTraceEntry):
            raise EventTraceBufferError(
                f"entry must be EventTraceEntry, got {type(entry).__name__}"
            )
        self._total += 1
        if len(self._buffer) >= self._capacity:
            self._buffer.popleft()
            self._dropped += 1
        self._buffer.append(entry)


# ──────────────────────────────────────────────
# RuntimeDiagnostics
# ──────────────────────────────────────────────


class RuntimeDiagnosticsError(ValueError):
    """Raised when a RuntimeDiagnostics invariant is violated."""


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    """Structured immutable diagnostics snapshot."""

    failure_detail: str | None = None
    trace_capacity: int = 0
    trace_size: int = 0
    trace_total_entries: int = 0
    trace_dropped_entries: int = 0
    # M2-S05 replay metadata
    random_seed: int = 0
    max_processed_events_limit: int | None = None
    same_time_event_limit: int = 0

    def __post_init__(self) -> None:
        # counters
        for name in ["trace_capacity", "trace_size", "trace_total_entries", "trace_dropped_entries"]:
            val = getattr(self, name)
            if isinstance(val, bool):
                raise RuntimeDiagnosticsError(f"{name} must be int, not bool")
            if not isinstance(val, int) or val < 0:
                raise RuntimeDiagnosticsError(f"{name} must be int >= 0, got {val!r}")

        # consistency
        if self.trace_size > self.trace_capacity:
            raise RuntimeDiagnosticsError(
                f"trace_size ({self.trace_size}) > trace_capacity ({self.trace_capacity})"
            )
        if self.trace_capacity == 0 and self.trace_size != 0:
            raise RuntimeDiagnosticsError(
                "trace_capacity=0 implies trace_size=0"
            )
        expected_dropped = self.trace_total_entries - self.trace_size
        if self.trace_dropped_entries != expected_dropped:
            raise RuntimeDiagnosticsError(
                f"trace_dropped_entries ({self.trace_dropped_entries}) "
                f"!= total ({self.trace_total_entries}) - size ({self.trace_size})"
            )

        # failure_detail normalization
        if self.failure_detail is not None:
            if not isinstance(self.failure_detail, str):
                raise RuntimeDiagnosticsError("failure_detail must be str or None")
            object.__setattr__(self, "failure_detail", _normalize_detail(self.failure_detail))

        # M2-S05: replay metadata validation
        if isinstance(self.random_seed, bool):
            raise RuntimeDiagnosticsError("random_seed must be int, not bool")
        if not isinstance(self.random_seed, int) or self.random_seed < 0:
            raise RuntimeDiagnosticsError(f"random_seed must be int >= 0, got {self.random_seed!r}")
        if self.max_processed_events_limit is not None:
            if isinstance(self.max_processed_events_limit, bool):
                raise RuntimeDiagnosticsError("max_processed_events_limit must be int or None, not bool")
            if not isinstance(self.max_processed_events_limit, int) or self.max_processed_events_limit <= 0:
                raise RuntimeDiagnosticsError(
                    f"max_processed_events_limit must be int > 0 or None, got {self.max_processed_events_limit!r}"
                )
        if isinstance(self.same_time_event_limit, bool):
            raise RuntimeDiagnosticsError("same_time_event_limit must be int, not bool")
        if not isinstance(self.same_time_event_limit, int) or self.same_time_event_limit < 0:
            raise RuntimeDiagnosticsError(
                f"same_time_event_limit must be int >= 0, got {self.same_time_event_limit!r}"
            )
