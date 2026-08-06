"""Tests for EventTraceEntry, EventTraceBuffer, RuntimeDiagnostics — M2-S03."""

import pytest

from virtual_factory.discrete.trace import (
    EventTraceBuffer,
    EventTraceBufferError,
    EventTraceEntry,
    EventTraceEntryError,
    RuntimeDiagnostics,
    RuntimeDiagnosticsError,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _committed_entry(trace_sequence=1, event_id="e1", event_type="test", **kw):
    defaults = dict(
        trace_sequence=trace_sequence,
        event_id=event_id,
        event_type=event_type,
        target_id="",
        simulation_time_s=0.0,
        priority=0,
        scheduler_sequence=1,
        correlation_id=None,
        causation_id=None,
        result="committed",
        error_code=None,
        error_detail=None,
        state_changes=(),
        requested_follow_up_events=0,
        scheduled_follow_up_events=0,
        processed_events_after=1,
        pending_events_after=0,
    )
    defaults.update(kw)
    return EventTraceEntry(**defaults)


def _failed_entry(error_code="test_failure", **kw):
    return _committed_entry(result="failed", error_code=error_code, **kw)


# ──────────────────────────────────────────────
# EventTraceEntry
# ──────────────────────────────────────────────

class TestEventTraceEntry:
    def test_valid_committed_entry(self):
        e = _committed_entry()
        assert e.result == "committed"
        assert e.trace_sequence == 1

    def test_valid_failed_entry(self):
        e = _failed_entry(error_code="bad")
        assert e.result == "failed"
        assert e.error_code == "bad"

    def test_invalid_trace_sequence_zero(self):
        with pytest.raises(EventTraceEntryError, match="trace_sequence"):
            _committed_entry(trace_sequence=0)

    def test_invalid_trace_sequence_negative(self):
        with pytest.raises(EventTraceEntryError, match="trace_sequence"):
            _committed_entry(trace_sequence=-1)

    def test_bool_trace_sequence_rejected(self):
        with pytest.raises(EventTraceEntryError, match="trace_sequence"):
            _committed_entry(trace_sequence=True)

    def test_empty_event_id_rejected(self):
        with pytest.raises(EventTraceEntryError, match="event_id"):
            _committed_entry(event_id="")

    def test_empty_event_type_rejected(self):
        with pytest.raises(EventTraceEntryError, match="event_type"):
            _committed_entry(event_type="")

    def test_non_finite_simulation_time_rejected(self):
        with pytest.raises(EventTraceEntryError, match="simulation_time_s"):
            _committed_entry(simulation_time_s=float("nan"))

    def test_negative_simulation_time_rejected(self):
        with pytest.raises(EventTraceEntryError, match="simulation_time_s"):
            _committed_entry(simulation_time_s=-1.0)

    def test_invalid_result_vocabulary(self):
        with pytest.raises(EventTraceEntryError, match="result"):
            _committed_entry(result="pending")

    def test_committed_with_error_rejected(self):
        with pytest.raises(EventTraceEntryError, match="committed"):
            _committed_entry(error_code="should-be-none")

    def test_failed_without_error_code_rejected(self):
        with pytest.raises(EventTraceEntryError, match="error_code"):
            _failed_entry(error_code="")

    def test_non_tuple_state_changes_rejected(self):
        with pytest.raises(EventTraceEntryError, match="state_changes"):
            _committed_entry(state_changes=["a"])

    def test_non_string_state_change_member_rejected(self):
        with pytest.raises(EventTraceEntryError, match="state_changes"):
            _committed_entry(state_changes=(1,))

    def test_negative_counter_rejected(self):
        with pytest.raises(EventTraceEntryError, match="processed_events_after"):
            _committed_entry(processed_events_after=-1)

    def test_bool_counter_rejected(self):
        with pytest.raises(EventTraceEntryError, match="processed_events_after"):
            _committed_entry(processed_events_after=True)

    def test_scheduled_gt_requested_rejected(self):
        with pytest.raises(EventTraceEntryError, match="scheduled"):
            _committed_entry(requested_follow_up_events=1, scheduled_follow_up_events=2)

    def test_multiline_error_normalized(self):
        e = _failed_entry(error_code="bad", error_detail="line1\nline2\r\nline3")
        assert "\n" not in e.error_detail
        assert "\r" not in e.error_detail
        assert "line1 line2 line3" in e.error_detail

    def test_long_error_truncated(self):
        e = _failed_entry(error_code="bad", error_detail="x" * 500)
        assert len(e.error_detail) <= 259


# ──────────────────────────────────────────────
# EventTraceBuffer
# ──────────────────────────────────────────────

class TestEventTraceBuffer:
    def test_default_capacity_128(self):
        buf = EventTraceBuffer()
        assert buf.capacity == 128

    def test_custom_capacity(self):
        buf = EventTraceBuffer(capacity=5)
        assert buf.capacity == 5

    def test_zero_capacity_rejected(self):
        with pytest.raises(EventTraceBufferError, match="capacity"):
            EventTraceBuffer(capacity=0)

    def test_negative_capacity_rejected(self):
        with pytest.raises(EventTraceBufferError, match="capacity"):
            EventTraceBuffer(capacity=-1)

    def test_bool_capacity_rejected(self):
        with pytest.raises(EventTraceBufferError, match="capacity"):
            EventTraceBuffer(capacity=True)

    def test_append_ordering(self):
        buf = EventTraceBuffer(capacity=3)
        buf.append(_committed_entry(trace_sequence=1, event_id="a"))
        buf.append(_committed_entry(trace_sequence=2, event_id="b"))
        assert [e.event_id for e in buf.entries] == ["a", "b"]

    def test_oldest_eviction(self):
        buf = EventTraceBuffer(capacity=2)
        buf.append(_committed_entry(trace_sequence=1, event_id="a"))
        buf.append(_committed_entry(trace_sequence=2, event_id="b"))
        buf.append(_committed_entry(trace_sequence=3, event_id="c"))
        assert [e.event_id for e in buf.entries] == ["b", "c"]

    def test_size_and_total(self):
        buf = EventTraceBuffer(capacity=2)
        buf.append(_committed_entry(trace_sequence=1))
        buf.append(_committed_entry(trace_sequence=2))
        assert buf.size == 2
        assert buf.total_entries == 2
        buf.append(_committed_entry(trace_sequence=3))
        assert buf.size == 2
        assert buf.total_entries == 3
        assert buf.dropped_entries == 1

    def test_detached_immutable_tuple(self):
        buf = EventTraceBuffer(capacity=2)
        buf.append(_committed_entry(trace_sequence=1))
        entries = buf.entries
        assert isinstance(entries, tuple)
        # Verify detached — modifying original doesn't affect returned tuple
        buf.append(_committed_entry(trace_sequence=2))
        buf.append(_committed_entry(trace_sequence=3))
        assert len(entries) == 1  # snapshot from when we called entries

    def test_thousand_entries_capacity_never_exceeded(self):
        buf = EventTraceBuffer(capacity=10)
        for i in range(1000):
            buf.append(_committed_entry(trace_sequence=i + 1, event_id=str(i)))
        assert buf.size == 10
        assert buf.total_entries == 1000
        assert buf.dropped_entries == 990
        assert buf.size + buf.dropped_entries == buf.total_entries


# ──────────────────────────────────────────────
# RuntimeDiagnostics
# ──────────────────────────────────────────────

class TestRuntimeDiagnostics:
    def test_valid_empty(self):
        d = RuntimeDiagnostics()
        assert d.trace_capacity == 0
        assert d.trace_size == 0

    def test_valid_populated(self):
        d = RuntimeDiagnostics(
            trace_capacity=128, trace_size=5,
            trace_total_entries=100, trace_dropped_entries=95,
        )
        assert d.trace_capacity == 128

    def test_negative_counter_rejected(self):
        with pytest.raises(RuntimeDiagnosticsError, match="trace_capacity"):
            RuntimeDiagnostics(trace_capacity=-1)

    def test_bool_counter_rejected(self):
        with pytest.raises(RuntimeDiagnosticsError, match="trace_capacity"):
            RuntimeDiagnostics(trace_capacity=True)

    def test_size_gt_capacity_rejected(self):
        with pytest.raises(RuntimeDiagnosticsError, match="trace_size"):
            RuntimeDiagnostics(trace_capacity=10, trace_size=11)

    def test_capacity_zero_implies_size_zero(self):
        with pytest.raises(RuntimeDiagnosticsError, match="trace_capacity"):
            RuntimeDiagnostics(trace_capacity=0, trace_size=1)

    def test_inconsistent_dropped_rejected(self):
        with pytest.raises(RuntimeDiagnosticsError, match="trace_dropped_entries"):
            RuntimeDiagnostics(
                trace_capacity=10, trace_size=5,
                trace_total_entries=100, trace_dropped_entries=0,
            )

    def test_failure_detail_normalized(self):
        d = RuntimeDiagnostics(failure_detail="line1\nline2")
        assert "\n" not in d.failure_detail

    def test_frozen(self):
        d = RuntimeDiagnostics()
        with pytest.raises(Exception):
            d.trace_capacity = 999
