"""Tests for the discrete-event simulation kernel — Prompt 003C invariants."""

import math
import types

import pytest

from virtual_factory.discrete.clock import DiscreteClock, DiscreteClockError
from virtual_factory.discrete.events import EventRecordError, ScheduledEvent
from virtual_factory.discrete.run_context import RunContext, RunContextError
from virtual_factory.discrete.scheduler import (
    FutureEventScheduler,
    FutureEventSchedulerError,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _evt(event_id="evt-001", simulation_time_s=1.0, event_type="test", target_id="", priority=0, **kwargs):
    return ScheduledEvent(event_id=event_id, simulation_time_s=simulation_time_s, event_type=event_type, target_id=target_id, priority=priority, **kwargs)


# ──────────────────────────────────────────────
# DiscreteClock
# ──────────────────────────────────────────────

class TestDiscreteClock:
    def test_default_starts_at_zero(self):
        c = DiscreteClock()
        assert c.current_time_s == 0.0
        assert c.now() == 0.0

    def test_explicit_initial_time(self):
        c = DiscreteClock(initial_time_s=5.0)
        assert c.current_time_s == 5.0

    def test_advance_forward(self):
        c = DiscreteClock()
        t = c.advance_to(10.0)
        assert t == 10.0

    def test_advance_same_time_allowed(self):
        c = DiscreteClock(initial_time_s=7.0)
        t = c.advance_to(7.0)
        assert t == 7.0

    def test_advance_backward_raises(self):
        c = DiscreteClock(initial_time_s=10.0)
        with pytest.raises(DiscreteClockError, match="backward"):
            c.advance_to(5.0)

    def test_nan_initial_raises(self):
        with pytest.raises(DiscreteClockError, match="NaN"):
            DiscreteClock(initial_time_s=float("nan"))

    def test_inf_initial_raises(self):
        with pytest.raises(DiscreteClockError, match="infinite"):
            DiscreteClock(initial_time_s=float("inf"))

    def test_advance_to_nan_raises(self):
        c = DiscreteClock()
        with pytest.raises(DiscreteClockError, match="NaN"):
            c.advance_to(float("nan"))

    def test_advance_to_inf_raises(self):
        c = DiscreteClock()
        with pytest.raises(DiscreteClockError, match="infinite"):
            c.advance_to(float("inf"))

    def test_negative_initial_raises(self):
        with pytest.raises(DiscreteClockError, match="non-negative"):
            DiscreteClock(initial_time_s=-1.0)

    def test_bool_initial_raises(self):
        with pytest.raises(DiscreteClockError, match="bool"):
            DiscreteClock(initial_time_s=True)

    def test_bool_advance_to_raises(self):
        c = DiscreteClock()
        with pytest.raises(DiscreteClockError, match="bool"):
            c.advance_to(False)

    def test_int_accepted_and_stored_as_float(self):
        c = DiscreteClock(initial_time_s=5)
        assert isinstance(c.current_time_s, float)
        assert c.current_time_s == 5.0


# ──────────────────────────────────────────────
# ScheduledEvent — construction & validation
# ──────────────────────────────────────────────

class TestScheduledEventConstruction:
    def test_minimal_event(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="test")
        assert e.event_id == "e1"
        assert e.simulation_time_s == 1.0
        assert e.event_type == "test"
        assert e.priority == 0
        assert e.sequence is None
        assert e.target_id == ""
        assert e.payload == types.MappingProxyType({})
        assert e.correlation_id is None
        assert e.causation_id is None

    def test_explicit_fields(self):
        e = ScheduledEvent(
            event_id="evt-001", simulation_time_s=3.5, event_type="fault_inject",
            target_id="pump_A", priority=2, sequence=None,
            payload={"severity": "high"}, correlation_id="corr-99", causation_id="evt-000",
        )
        assert e.event_id == "evt-001"
        assert e.priority == 2
        assert e.payload["severity"] == "high"

    def test_empty_event_id_raises(self):
        with pytest.raises(EventRecordError, match="event_id"):
            ScheduledEvent(event_id="", simulation_time_s=1.0, event_type="x")

    def test_whitespace_event_id_raises(self):
        with pytest.raises(EventRecordError, match="event_id"):
            ScheduledEvent(event_id="   ", simulation_time_s=1.0, event_type="x")

    def test_empty_event_type_raises(self):
        with pytest.raises(EventRecordError, match="event_type"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="")

    def test_whitespace_event_type_raises(self):
        with pytest.raises(EventRecordError, match="event_type"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="   ")

    def test_negative_time_raises(self):
        with pytest.raises(EventRecordError, match=">= 0"):
            ScheduledEvent(event_id="e1", simulation_time_s=-1.0, event_type="x")

    def test_nan_time_raises(self):
        with pytest.raises(EventRecordError, match="NaN"):
            ScheduledEvent(event_id="e1", simulation_time_s=float("nan"), event_type="x")

    def test_inf_time_raises(self):
        with pytest.raises(EventRecordError, match="infinite"):
            ScheduledEvent(event_id="e1", simulation_time_s=float("inf"), event_type="x")

    def test_bool_time_raises(self):
        with pytest.raises(EventRecordError, match="bool"):
            ScheduledEvent(event_id="e1", simulation_time_s=True, event_type="x")

    def test_bool_priority_raises(self):
        with pytest.raises(EventRecordError, match="priority"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", priority=True)

    def test_invalid_priority_type_raises(self):
        with pytest.raises(EventRecordError, match="priority"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", priority="hi")

    def test_empty_correlation_id_raises(self):
        with pytest.raises(EventRecordError, match="correlation_id"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", correlation_id="")

    def test_empty_causation_id_raises(self):
        with pytest.raises(EventRecordError, match="causation_id"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", causation_id="")

    def test_sequence_bool_raises(self):
        with pytest.raises(EventRecordError, match="sequence"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", sequence=True)

    def test_non_string_event_type_raises(self):
        with pytest.raises(EventRecordError, match="event_type"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type=123)


# ──────────────────────────────────────────────
# ScheduledEvent — true immutability
# ──────────────────────────────────────────────

class TestScheduledEventImmutability:
    def test_cannot_assign_public_field(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x")
        with pytest.raises(Exception):
            e.simulation_time_s = 99.0

    def test_cannot_assign_event_id(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x")
        with pytest.raises(Exception):
            e.event_id = "hijacked"

    def test_cannot_assign_priority(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x")
        with pytest.raises(Exception):
            e.priority = 99

    def test_cannot_assign_new_field(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x")
        with pytest.raises(Exception):
            e._extra = "injected"


# ──────────────────────────────────────────────
# ScheduledEvent — payload
# ──────────────────────────────────────────────

class TestScheduledEventPayload:
    def test_payload_is_immutable_view(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"key": "val"})
        with pytest.raises(TypeError):
            e.payload["key"] = "changed"

    def test_external_mutation_has_no_effect(self):
        orig = {"nested": {"a": 1}}
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload=orig)
        orig["nested"]["a"] = 999
        assert e.payload["nested"]["a"] == 1

    def test_deep_nested_immutability(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"l1": {"l2": [1, 2, 3]}})
        inner = e.payload["l1"]["l2"]
        assert isinstance(inner, tuple)
        assert inner == (1, 2, 3)

    def test_to_dict_returns_detached_plain(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"x": [1, 2]})
        d = e.to_dict()
        assert isinstance(d["payload"], dict)
        assert isinstance(d["payload"]["x"], list)
        assert d["payload"]["x"] == [1, 2]

    def test_mutating_to_dict_output_has_no_effect(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"a": 1})
        d = e.to_dict()
        d["payload"]["a"] = 999
        d["payload"]["new"] = "injected"
        assert e.payload["a"] == 1
        assert "new" not in e.payload

    def test_callable_top_level_rejected(self):
        with pytest.raises(EventRecordError, match="callable"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"cb": lambda: None})

    def test_callable_nested_rejected(self):
        with pytest.raises(EventRecordError, match="callable"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"outer": {"inner": lambda: None}})

    def test_unsupported_object_rejected(self):
        class Foo:
            pass
        with pytest.raises(EventRecordError, match="unsupported"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"obj": Foo()})

    def test_non_finite_nested_float_rejected(self):
        with pytest.raises(EventRecordError, match="non-finite"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={"val": float("nan")})

    def test_payload_not_mapping_raises(self):
        with pytest.raises(EventRecordError, match="payload must be a Mapping"):
            ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload=[1, 2, 3])

    def test_null_payload_accepted(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload=None)
        assert e.payload == types.MappingProxyType({})

    def test_json_compatible_values_accepted(self):
        e = ScheduledEvent(event_id="e1", simulation_time_s=1.0, event_type="x", payload={
            "null": None, "bool": True, "int": 42, "float": 3.14, "str": "hello",
            "list": [1, "two", 3.0], "nested": {"a": {"b": [1, 2]}},
        })
        assert e.payload["int"] == 42
        assert e.payload["nested"]["a"]["b"] == (1, 2)


# ──────────────────────────────────────────────
# ScheduledEvent — serialization
# ──────────────────────────────────────────────

class TestScheduledEventSerialization:
    def test_to_dict_includes_all_fields(self):
        e = ScheduledEvent(event_id="evt-x", simulation_time_s=2.0, event_type="go", target_id="T1", priority=5, payload={"k": "v"})
        d = e.to_dict()
        assert d["event_id"] == "evt-x"
        assert d["simulation_time_s"] == 2.0
        assert d["event_type"] == "go"
        assert d["target_id"] == "T1"
        assert d["priority"] == 5
        assert d["sequence"] is None
        assert d["payload"] == {"k": "v"}
        assert d["correlation_id"] is None
        assert d["causation_id"] is None

    def test_repr_contains_key_info(self):
        e = ScheduledEvent(event_id="evt-x", simulation_time_s=1.5, event_type="go", target_id="T1")
        r = repr(e)
        assert "1.5" in r
        assert "go" in r
        assert "T1" in r


# ──────────────────────────────────────────────
# FutureEventScheduler — basic
# ──────────────────────────────────────────────

class TestFutureEventSchedulerBasic:
    def test_empty_scheduler(self):
        s = FutureEventScheduler()
        assert s.pending_count == 0
        assert s.is_empty is True
        assert s.peek_next() is None
        assert s.pop_next() is None
        assert s.pending_snapshot() == []
        assert s.current_time_s == 0.0

    def test_schedule_one(self):
        s = FutureEventScheduler()
        eid = s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        assert eid == "a"
        assert s.pending_count == 1
        assert s.is_empty is False

    def test_peek_does_not_pop(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        assert s.peek_next() is not None
        assert s.pending_count == 1

    def test_pop_next_advances_clock(self):
        s = FutureEventScheduler(initial_time_s=0.0)
        s.schedule(_evt(event_id="a", simulation_time_s=5.0))
        ev = s.pop_next()
        assert ev is not None
        assert ev.simulation_time_s == 5.0
        assert s.current_time_s == 5.0

    def test_pop_next_empty_returns_none(self):
        s = FutureEventScheduler()
        assert s.pop_next() is None

    def test_pop_all(self):
        s = FutureEventScheduler()
        for i in range(5):
            s.schedule(_evt(event_id=f"e{i}", simulation_time_s=float(i)))
        events = list(s.pop_all())
        assert len(events) == 5
        assert s.pending_count == 0
        assert s.current_time_s == 4.0

    def test_now_read_only(self):
        s = FutureEventScheduler(initial_time_s=3.0)
        assert s.now() == 3.0
        assert s.current_time_s == 3.0

    def test_no_clock_exposure(self):
        s = FutureEventScheduler()
        assert not hasattr(s, "clock")


# ──────────────────────────────────────────────
# FutureEventScheduler — ordering
# ──────────────────────────────────────────────

class TestFutureEventSchedulerOrdering:
    def test_ordering_by_time(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="b", simulation_time_s=3.0))
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        s.schedule(_evt(event_id="c", simulation_time_s=2.0))
        times = [s.pop_next().simulation_time_s for _ in range(3)]
        assert times == [1.0, 2.0, 3.0]

    def test_ordering_by_priority(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="x5", simulation_time_s=1.0, priority=5))
        s.schedule(_evt(event_id="x1", simulation_time_s=1.0, priority=1))
        s.schedule(_evt(event_id="x3", simulation_time_s=1.0, priority=3))
        prios = [s.pop_next().priority for _ in range(3)]
        assert prios == [1, 3, 5]

    def test_ordering_by_sequence_FIFO(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        s.schedule(_evt(event_id="b", simulation_time_s=1.0))
        s.schedule(_evt(event_id="c", simulation_time_s=1.0))
        ids = [s.pop_next().event_id for _ in range(3)]
        assert ids == ["a", "b", "c"]

    def test_scheduler_assigned_sequence_visible(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        s.schedule(_evt(event_id="b", simulation_time_s=1.0))
        e1 = s.pop_next()
        e2 = s.pop_next()
        assert isinstance(e1.sequence, int)
        assert isinstance(e2.sequence, int)
        assert e1.sequence < e2.sequence

    def test_sequence_in_snapshot(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="x", simulation_time_s=1.0))
        s.schedule(_evt(event_id="y", simulation_time_s=1.0))
        snap = s.pending_snapshot()
        assert all(isinstance(d["sequence"], int) for d in snap)
        assert snap[0]["sequence"] < snap[1]["sequence"]

    def test_determinism_repeated_inserts(self):
        results = []
        for _ in range(5):
            s = FutureEventScheduler()
            for i in range(10):
                s.schedule(_evt(event_id=f"e{i}", simulation_time_s=float(i % 3), priority=i % 2))
            snap = tuple((e.simulation_time_s, e.priority, e.event_id) for e in s.pop_all())
            results.append(snap)
        assert all(r == results[0] for r in results)


# ──────────────────────────────────────────────
# FutureEventScheduler — time validation
# ──────────────────────────────────────────────

class TestFutureEventSchedulerTimeValidation:
    def test_past_event_rejected(self):
        s = FutureEventScheduler(initial_time_s=10.0)
        with pytest.raises(FutureEventSchedulerError, match="past"):
            s.schedule(_evt(event_id="old", simulation_time_s=5.0))

    def test_current_time_event_accepted(self):
        s = FutureEventScheduler(initial_time_s=10.0)
        s.schedule(_evt(event_id="now", simulation_time_s=10.0))
        assert s.pending_count == 1

    def test_future_event_accepted(self):
        s = FutureEventScheduler(initial_time_s=0.0)
        s.schedule(_evt(event_id="future", simulation_time_s=5.0))
        assert s.pending_count == 1


# ──────────────────────────────────────────────
# FutureEventScheduler — capacity
# ──────────────────────────────────────────────

class TestFutureEventSchedulerCapacity:
    def test_capacity_enforced(self):
        s = FutureEventScheduler(max_events=3)
        for i in range(3):
            s.schedule(_evt(event_id=f"e{i}", simulation_time_s=float(i)))
        with pytest.raises(FutureEventSchedulerError, match="full"):
            s.schedule(_evt(event_id="overflow", simulation_time_s=4.0))

    def test_invalid_max_events_zero(self):
        with pytest.raises(FutureEventSchedulerError, match="positive"):
            FutureEventScheduler(max_events=0)

    def test_invalid_max_events_negative(self):
        with pytest.raises(FutureEventSchedulerError, match="positive"):
            FutureEventScheduler(max_events=-1)

    def test_bool_max_events_raises(self):
        with pytest.raises(FutureEventSchedulerError, match="bool"):
            FutureEventScheduler(max_events=True)


# ──────────────────────────────────────────────
# FutureEventScheduler — duplicate IDs
# ──────────────────────────────────────────────

class TestFutureEventSchedulerDuplicateIDs:
    def test_duplicate_event_id_rejected(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="dup", simulation_time_s=1.0))
        with pytest.raises(FutureEventSchedulerError, match="Duplicate"):
            s.schedule(_evt(event_id="dup", simulation_time_s=2.0))

    def test_unique_ids_accepted(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        s.schedule(_evt(event_id="b", simulation_time_s=1.0))
        assert s.pending_count == 2


# ──────────────────────────────────────────────
# FutureEventScheduler — inspection
# ──────────────────────────────────────────────

class TestFutureEventSchedulerInspection:
    def test_pending_snapshot_sorted(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="b", simulation_time_s=3.0))
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        snap = s.pending_snapshot()
        assert [d["simulation_time_s"] for d in snap] == [1.0, 3.0]

    def test_pending_snapshot_none_limit(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        s.schedule(_evt(event_id="b", simulation_time_s=2.0))
        snap = s.pending_snapshot(limit=None)
        assert len(snap) == 2

    def test_pending_snapshot_zero_limit(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        snap = s.pending_snapshot(limit=0)
        assert snap == []

    def test_pending_snapshot_positive_limit(self):
        s = FutureEventScheduler()
        for i in range(5):
            s.schedule(_evt(event_id=f"e{i}", simulation_time_s=float(i)))
        snap = s.pending_snapshot(limit=3)
        assert len(snap) == 3
        assert [d["simulation_time_s"] for d in snap] == [0.0, 1.0, 2.0]

    def test_pending_snapshot_negative_limit_raises(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError, match="limit"):
            s.pending_snapshot(limit=-1)

    def test_pending_snapshot_bool_limit_raises(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError, match="bool"):
            s.pending_snapshot(limit=True)

    def test_pending_snapshot_float_limit_raises(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError, match="int"):
            s.pending_snapshot(limit=1.5)

    def test_inspection_does_not_mutate(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="x", simulation_time_s=5.0))
        _ = s.peek_next()
        _ = s.pending_snapshot()
        assert s.pending_count == 1
        assert s.current_time_s == 0.0

    def test_peek_then_pop_returns_same(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="look", simulation_time_s=5.0))
        peeked = s.peek_next()
        popped = s.pop_next()
        assert peeked.event_id == popped.event_id

    def test_is_empty(self):
        s = FutureEventScheduler()
        assert s.is_empty is True
        s.schedule(_evt(event_id="a", simulation_time_s=1.0))
        assert s.is_empty is False
        s.pop_next()
        assert s.is_empty is True


# ──────────────────────────────────────────────
# FutureEventScheduler — atomic pop
# ──────────────────────────────────────────────

class TestFutureEventSchedulerAtomicPop:
    def test_pop_on_empty_is_safe(self):
        s = FutureEventScheduler()
        assert s.pop_next() is None
        assert s.is_empty

    def test_no_event_loss_scenario(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="first", simulation_time_s=5.0))
        s.pop_next()
        s.schedule(_evt(event_id="second", simulation_time_s=10.0))
        s.pop_next()
        # Scheduling a past event is rejected — no loss
        with pytest.raises(FutureEventSchedulerError, match="past"):
            s.schedule(_evt(event_id="late", simulation_time_s=3.0))
        assert s.pending_count == 0


# ──────────────────────────────────────────────
# RunContext
# ──────────────────────────────────────────────

class TestRunContext:
    def test_minimal_valid(self):
        ctx = RunContext(run_id="r1", model_id="m1")
        assert ctx.run_id == "r1"
        assert ctx.model_id == "m1"
        assert ctx.engine_kind == "discrete_manufacturing"
        assert ctx.source_kind == "simulation"
        assert ctx.environment == "demo"
        assert ctx.random_seed == 42

    def test_explicit_fields(self):
        ctx = RunContext(
            run_id="run-001", model_id="model-xyz",
            engine_kind="discrete_manufacturing", model_version="1.0",
            scenario_id="sc-01", scenario_version="2.0",
            random_seed=123, environment="test", source_kind="simulation",
        )
        assert ctx.run_id == "run-001"
        assert ctx.model_id == "model-xyz"
        assert ctx.model_version == "1.0"
        assert ctx.scenario_id == "sc-01"
        assert ctx.scenario_version == "2.0"
        assert ctx.random_seed == 123
        assert ctx.environment == "test"

    def test_empty_run_id_raises(self):
        with pytest.raises(RunContextError, match="run_id"):
            RunContext(run_id="", model_id="m1")

    def test_empty_model_id_raises(self):
        with pytest.raises(RunContextError, match="model_id"):
            RunContext(run_id="r1", model_id="")

    def test_wrong_engine_kind_raises(self):
        with pytest.raises(RunContextError, match="engine_kind"):
            RunContext(run_id="r1", model_id="m1", engine_kind="batch")

    def test_wrong_source_kind_raises(self):
        with pytest.raises(RunContextError, match="source_kind"):
            RunContext(run_id="r1", model_id="m1", source_kind="api")

    def test_negative_seed_raises(self):
        with pytest.raises(RunContextError, match="random_seed"):
            RunContext(run_id="r1", model_id="m1", random_seed=-1)

    def test_bool_seed_raises(self):
        with pytest.raises(RunContextError, match="random_seed"):
            RunContext(run_id="r1", model_id="m1", random_seed=True)

    def test_empty_environment_raises(self):
        with pytest.raises(RunContextError, match="environment"):
            RunContext(run_id="r1", model_id="m1", environment="")

    def test_optional_empty_model_version_raises(self):
        with pytest.raises(RunContextError, match="model_version"):
            RunContext(run_id="r1", model_id="m1", model_version="")

    def test_optional_empty_scenario_id_raises(self):
        with pytest.raises(RunContextError, match="scenario_id"):
            RunContext(run_id="r1", model_id="m1", scenario_id="")

    def test_optional_empty_scenario_version_raises(self):
        with pytest.raises(RunContextError, match="scenario_version"):
            RunContext(run_id="r1", model_id="m1", scenario_version="")

    def test_true_immutability(self):
        ctx = RunContext(run_id="r1", model_id="m1")
        with pytest.raises(Exception):
            ctx.run_id = "hijacked"
        with pytest.raises(Exception):
            ctx.random_seed = 999

    def test_to_dict_includes_all_fields(self):
        ctx = RunContext(run_id="r1", model_id="m1", model_version="v1", scenario_id="s1", scenario_version="sv1")
        d = ctx.to_dict()
        assert d["run_id"] == "r1"
        assert d["model_id"] == "m1"
        assert d["model_version"] == "v1"
        assert d["scenario_id"] == "s1"
        assert d["scenario_version"] == "sv1"
        assert d["engine_kind"] == "discrete_manufacturing"
        assert d["source_kind"] == "simulation"
        assert d["environment"] == "demo"
        assert d["random_seed"] == 42

    def test_to_dict_is_detached(self):
        ctx = RunContext(run_id="r1", model_id="m1")
        d = ctx.to_dict()
        d["run_id"] = "fake"
        assert ctx.run_id == "r1"

    def test_none_optionals_accepted(self):
        ctx = RunContext(run_id="r1", model_id="m1", model_version=None, scenario_id=None, scenario_version=None)
        assert ctx.model_version is None
        assert ctx.scenario_id is None
        assert ctx.scenario_version is None


# ──────────────────────────────────────────────
# Scheduler + Clock integration
# ──────────────────────────────────────────────

class TestSchedulerClockIntegration:
    def test_pop_advances_clock_to_event_time(self):
        s = FutureEventScheduler(initial_time_s=1.0)
        s.schedule(_evt(event_id="go", simulation_time_s=5.0))
        s.pop_next()
        assert s.current_time_s == 5.0

    def test_multiple_pops_clock_monotonic(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="a", simulation_time_s=3.0))
        s.schedule(_evt(event_id="b", simulation_time_s=1.0))
        t1 = s.pop_next().simulation_time_s
        c1 = s.current_time_s
        t2 = s.pop_next().simulation_time_s
        c2 = s.current_time_s
        assert c1 == t1 == 1.0
        assert c2 == t2 == 3.0

    def test_sequence_starts_at_1(self):
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="first", simulation_time_s=1.0))
        e = s.pop_next()
        assert e.sequence == 1


# ──────────────────────────────────────────────
# Prompt 003D — C-001: non-string payload keys
# ──────────────────────────────────────────────

class TestPayloadNonStringKeysRejected:
    def test_top_level_int_key_rejected(self):
        with pytest.raises(EventRecordError, match="keys must be str"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload={1: "value"}
            )

    def test_nested_int_key_rejected(self):
        with pytest.raises(EventRecordError, match="keys must be str"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload={"outer": {2: "inner"}}
            )

    def test_mixed_keys_rejected_not_collapsed(self):
        with pytest.raises(EventRecordError, match="keys must be str"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload={1: "a", "1": "b"}
            )

    def test_valid_string_key_payload_still_serializes(self):
        e = ScheduledEvent(
            event_id="e1", simulation_time_s=1.0, event_type="x",
            payload={"key": "val", "nested": {"inner": [1, 2]}}
        )
        d = e.to_dict()
        assert d["payload"] == {"key": "val", "nested": {"inner": [1, 2]}}


# ──────────────────────────────────────────────
# Prompt 003D — C-002: reject caller-assigned sequence
# ──────────────────────────────────────────────

class TestRejectPreassignedSequence:
    def test_preassigned_sequence_99_rejected(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError, match="scheduler-owned"):
            s.schedule(_evt(event_id="bad", simulation_time_s=1.0, sequence=99))

    def test_rejection_does_not_increment_sequence_counter(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError):
            s.schedule(_evt(event_id="bad", simulation_time_s=1.0, sequence=99))
        # Next valid event gets sequence 1
        s.schedule(_evt(event_id="good", simulation_time_s=1.0))
        e = s.pop_next()
        assert e.sequence == 1

    def test_rejection_does_not_add_to_seen_ids(self):
        s = FutureEventScheduler()
        with pytest.raises(FutureEventSchedulerError):
            s.schedule(_evt(event_id="bad", simulation_time_s=1.0, sequence=99))
        # Same ID can be scheduled as a valid unscheduled event
        s.schedule(_evt(event_id="bad", simulation_time_s=2.0))  # sequence=None
        assert s.pending_count == 1

    def test_rejection_does_not_change_pending_count_or_time(self):
        s = FutureEventScheduler(initial_time_s=5.0)
        s.schedule(_evt(event_id="existing", simulation_time_s=10.0))
        count_before = s.pending_count
        time_before = s.current_time_s
        with pytest.raises(FutureEventSchedulerError):
            s.schedule(_evt(event_id="bad", simulation_time_s=6.0, sequence=99))
        assert s.pending_count == count_before
        assert s.current_time_s == time_before


# ──────────────────────────────────────────────
# Prompt 003D — C-003: direct atomic push-back test
# ──────────────────────────────────────────────

class TestAtomicPopPushBack:
    def test_clock_failure_pushes_back_event(self, monkeypatch):
        """When clock.advance_to raises, pop_next restores the event."""
        s = FutureEventScheduler()
        s.schedule(_evt(event_id="safe", simulation_time_s=5.0))

        # Force the internal clock to reject the advance
        def _failing_advance(_target: float) -> float:
            raise DiscreteClockError("injected clock failure")

        monkeypatch.setattr(s._clock, "advance_to", _failing_advance)

        with pytest.raises(FutureEventSchedulerError, match="Clock rejected"):
            s.pop_next()

        # Event is still there
        assert s.pending_count == 1
        assert s.peek_next().event_id == "safe"
        assert s.current_time_s == 0.0  # clock unchanged

# --- Prompt 003E: E-001 mapping-proxy bypass tests ---
import types as _types

class TestMappingProxyBypassClosed:
    """E-001: MappingProxyType can no longer bypass validation."""

    def test_direct_mappingproxy_with_callable_rejected(self):
        with pytest.raises(EventRecordError, match="callable"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({"cb": lambda: None}),
            )

    def test_direct_mappingproxy_nested_callable_rejected(self):
        with pytest.raises(EventRecordError, match="callable"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({"outer": {"inner": lambda: None}}),
            )

    def test_direct_mappingproxy_non_string_key_rejected(self):
        with pytest.raises(EventRecordError, match="keys must be str"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({1: "value"}),
            )

    def test_direct_mappingproxy_nested_non_string_key_rejected(self):
        with pytest.raises(EventRecordError, match="keys must be str"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({"outer": {2: "inner"}}),
            )

    def test_direct_mappingproxy_unsupported_object_rejected(self):
        class Foo:
            pass
        with pytest.raises(EventRecordError, match="unsupported"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({"obj": Foo()}),
            )

    def test_direct_mappingproxy_non_finite_float_rejected(self):
        with pytest.raises(EventRecordError, match="non-finite"):
            ScheduledEvent(
                event_id="e1", simulation_time_s=1.0, event_type="x",
                payload=_types.MappingProxyType({"val": float("nan")}),
            )

    def test_valid_nested_mappingproxy_accepted(self):
        e = ScheduledEvent(
            event_id="e1", simulation_time_s=1.0, event_type="x",
            payload=_types.MappingProxyType({
                "outer": _types.MappingProxyType({
                    "values": (1, 2, 3),
                }),
            }),
        )
        assert e.payload["outer"]["values"] == (1, 2, 3)
        d = e.to_dict()
        assert d["payload"] == {"outer": {"values": [1, 2, 3]}}
        # Mutation of returned dict does not affect event
        d["payload"]["outer"]["values"].append(99)
        assert e.payload["outer"]["values"] == (1, 2, 3)

    def test_scheduler_sequence_replacement_with_nested_mappingproxy(self):
        e = ScheduledEvent(
            event_id="seq-test", simulation_time_s=1.0, event_type="x",
            payload={"data": {"nested": [1, 2]}},
        )
        s = FutureEventScheduler()
        s.schedule(e)
        ev = s.pop_next()
        assert ev.sequence == 1
        assert ev.payload["data"]["nested"] == (1, 2)
        snap = s.pending_snapshot()
        assert len(snap) == 0
