"""Tests for HandlerRegistry — M2-S02 registration and dispatch policies."""

import pytest

from virtual_factory.discrete.handler_registry import (
    DuplicateHandlerError,
    HandlerRegistrationError,
    HandlerRegistry,
    HandlerRegistryError,
)
from virtual_factory.discrete.dispatcher import (
    EventDispatcherProtocol,
    HandlerOutcome,
)
from virtual_factory.discrete.engine import (
    DiscreteSimulationEngine,
    DiscreteSimulationEngineError,
)
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _rc(**kw):
    defaults = {"run_id": "r1", "model_id": "m1"}
    defaults.update(kw)
    return RunContext(**defaults)


def _evt(event_id, simulation_time_s=0.0, event_type="test", **kw):
    return ScheduledEvent(
        event_id=event_id,
        simulation_time_s=simulation_time_s,
        event_type=event_type,
        **kw,
    )


def _ok_handler(event: ScheduledEvent) -> HandlerOutcome:
    return HandlerOutcome(
        event_id=event.event_id,
        success=True,
        follow_up_events=(),
        state_changes=("handled",),
    )


# ──────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────

class TestRegistration:
    def test_non_string_event_type_rejected(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistrationError, match="str"):
            reg.register(123, _ok_handler)

    def test_empty_event_type_rejected(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistrationError, match="non-empty"):
            reg.register("", _ok_handler)

    def test_whitespace_only_event_type_rejected(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistrationError, match="non-empty"):
            reg.register("   ", _ok_handler)

    def test_non_callable_handler_rejected(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistrationError, match="callable"):
            reg.register("test", "not-callable")

    def test_valid_function_registered(self):
        reg = HandlerRegistry()
        reg.register("test", _ok_handler)
        assert reg.is_registered("test")

    def test_callable_object_registered(self):
        reg = HandlerRegistry()
        class CallableHandler:
            def __call__(self, event):
                return _ok_handler(event)
        reg.register("test", CallableHandler())
        assert reg.is_registered("test")

    def test_duplicate_registration_raises_typed_error(self):
        reg = HandlerRegistry()
        reg.register("dup", _ok_handler)
        with pytest.raises(DuplicateHandlerError, match="dup"):
            reg.register("dup", _ok_handler)

    def test_duplicate_preserves_original_handler(self):
        reg = HandlerRegistry()

        def handler_a(event):
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                follow_up_events=(), state_changes=("a",),
            )

        def handler_b(event):
            return HandlerOutcome(
                event_id=event.event_id, success=True,
                follow_up_events=(), state_changes=("b",),
            )

        reg.register("dup", handler_a)
        with pytest.raises(DuplicateHandlerError):
            reg.register("dup", handler_b)
        outcome = reg.dispatch(_evt("e1", event_type="dup"))
        assert outcome.state_changes == ("a",)

    def test_event_type_matching_is_case_sensitive(self):
        reg = HandlerRegistry()
        reg.register("Test", _ok_handler)
        assert reg.is_registered("Test")
        assert not reg.is_registered("test")
        assert not reg.is_registered("TEST")

    def test_inspection_returns_sorted_tuple(self):
        reg = HandlerRegistry()
        reg.register("c", _ok_handler)
        reg.register("a", _ok_handler)
        reg.register("b", _ok_handler)
        assert reg.registered_event_types == ("a", "b", "c")

    def test_is_registered_exact_matching(self):
        reg = HandlerRegistry()
        reg.register("foo", _ok_handler)
        assert reg.is_registered("foo")
        assert not reg.is_registered("bar")
        assert not reg.is_registered("fo")


# ──────────────────────────────────────────────
# Dispatch
# ──────────────────────────────────────────────

class TestDispatch:
    def test_known_handler_called_exactly_once(self):
        calls = []
        def counting_handler(event):
            calls.append(event.event_id)
            return _ok_handler(event)

        reg = HandlerRegistry()
        reg.register("test", counting_handler)
        reg.dispatch(_evt("e1"))
        assert calls == ["e1"]

    def test_valid_outcome_returned(self):
        reg = HandlerRegistry()
        reg.register("test", _ok_handler)
        outcome = reg.dispatch(_evt("e1"))
        assert outcome.success is True
        assert outcome.event_id == "e1"

    def test_unknown_event_returns_no_handler(self):
        reg = HandlerRegistry()
        outcome = reg.dispatch(_evt("e1", event_type="unknown"))
        assert outcome.success is False
        assert outcome.error_code == "no_handler"

    def test_unknown_event_does_not_raise(self):
        reg = HandlerRegistry()
        outcome = reg.dispatch(_evt("e1", event_type="unknown"))
        assert isinstance(outcome, HandlerOutcome)

    def test_handler_exception_returns_handler_error(self):
        def broken(_event):
            raise ValueError("boom")

        reg = HandlerRegistry()
        reg.register("test", broken)
        outcome = reg.dispatch(_evt("e1"))
        assert outcome.success is False
        assert outcome.error_code == "handler_error"
        assert "ValueError" in outcome.error_detail
        assert "boom" in outcome.error_detail

    def test_keyboard_interrupt_not_swallowed(self):
        def interrupt(_event):
            raise KeyboardInterrupt()

        reg = HandlerRegistry()
        reg.register("test", interrupt)
        with pytest.raises(KeyboardInterrupt):
            reg.dispatch(_evt("e1"))

    def test_system_exit_not_swallowed(self):
        def exit_handler(_event):
            raise SystemExit(1)

        reg = HandlerRegistry()
        reg.register("test", exit_handler)
        with pytest.raises(SystemExit):
            reg.dispatch(_evt("e1"))

    def test_invalid_return_type_normalized(self):
        def bad_return(_event):
            return "not-an-outcome"

        reg = HandlerRegistry()
        reg.register("test", bad_return)
        outcome = reg.dispatch(_evt("e1"))
        assert outcome.success is False
        assert outcome.error_code == "handler_error"

    def test_mismatched_event_id_normalized(self):
        def wrong_id(event):
            return HandlerOutcome(
                event_id="wrong",
                success=True,
                follow_up_events=(),
                state_changes=(),
            )

        reg = HandlerRegistry()
        reg.register("test", wrong_id)
        outcome = reg.dispatch(_evt("e1"))
        assert outcome.success is False
        assert outcome.error_code == "handler_error"

    def test_input_event_not_mutated(self):
        reg = HandlerRegistry()
        reg.register("test", _ok_handler)
        event = _evt("e1")
        original_id = event.event_id
        reg.dispatch(event)
        assert event.event_id == original_id

    def test_follow_ups_not_scheduled_by_registry(self):
        reg = HandlerRegistry()

        def follow_up_handler(event):
            return HandlerOutcome(
                event_id=event.event_id,
                success=True,
                follow_up_events=(_evt("f1"), _evt("f2")),
                state_changes=(),
            )

        reg.register("test", follow_up_handler)
        outcome = reg.dispatch(_evt("e1"))
        assert len(outcome.follow_up_events) == 2
        # Registry returns them but does NOT schedule


# ──────────────────────────────────────────────
# Engine integration
# ──────────────────────────────────────────────

class TestEngineIntegration:
    def test_registry_satisfies_dispatcher_protocol(self):
        reg = HandlerRegistry()
        assert isinstance(reg, EventDispatcherProtocol)

    def test_engine_completes_with_successful_handler(self):
        reg = HandlerRegistry()
        reg.register("test", _ok_handler)
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize(initial_events=[_evt("boot")])
        snap = engine.step_event()
        assert snap.status == "completed"

    def test_unknown_event_causes_engine_failed(self):
        reg = HandlerRegistry()
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize(initial_events=[_evt("boot", event_type="unregistered")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "no_handler"

    def test_handler_exception_causes_engine_failed(self):
        def broken(_event):
            raise RuntimeError("crash")

        reg = HandlerRegistry()
        reg.register("test", broken)
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize(initial_events=[_evt("boot", event_type="test")])
        snap = engine.step_event()
        assert snap.status == "failed"
        assert snap.failure_error == "handler_error"

    def test_handler_follow_up_scheduled_by_engine(self):
        reg = HandlerRegistry()

        def multi_handler(event):
            return HandlerOutcome(
                event_id=event.event_id,
                success=True,
                follow_up_events=(
                    _evt("f1", simulation_time_s=1.0, event_type="step2"),
                    _evt("f2", simulation_time_s=1.0, event_type="step2"),
                ),
                state_changes=(),
            )

        step2_calls = []
        def step2_handler(event):
            step2_calls.append(event.event_id)
            return _ok_handler(event)

        reg.register("boot", multi_handler)
        reg.register("step2", step2_handler)
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize(initial_events=[_evt("boot", event_type="boot")])

        # First step dispatches boot → schedules f1, f2
        snap1 = engine.step_event()
        assert snap1.status == "ready"
        assert snap1.pending_events == 2

        # f1 dispatched
        engine.step_event()
        # f2 dispatched
        engine.step_event()
        assert step2_calls == ["f1", "f2"]

    def test_scheduler_ordering_authoritative(self):
        """Follow-ups obey scheduler time→priority→sequence; registry has no role."""
        dispatched = []
        reg = HandlerRegistry()

        def recording_handler(event):
            dispatched.append(event.event_id)
            return _ok_handler(event)

        reg.register("step", recording_handler)

        def boot_handler(event):
            return HandlerOutcome(
                event_id=event.event_id,
                success=True,
                follow_up_events=(
                    _evt("low", simulation_time_s=2.0, event_type="step"),
                    _evt("high", simulation_time_s=1.0, event_type="step"),
                ),
                state_changes=(),
            )

        reg.register("boot", boot_handler)
        engine = DiscreteSimulationEngine(_rc(), reg)
        engine.initialize(initial_events=[_evt("boot", event_type="boot")])
        engine.step_event()  # boot → schedules high(1.0), low(2.0)

        # Pop remaining events until complete
        while engine.status.value == "ready":
            engine.step_event()

        # high (t=1.0) before low (t=2.0)
        assert dispatched == ["high", "low"]

# --- M2-S02-C01: Contract hardening tests ---

class TestDispatchInputValidation:
    """dispatch() rejects non-ScheduledEvent input."""

    def test_dispatch_none_raises(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistryError, match="ScheduledEvent"):
            reg.dispatch(None)

    def test_dispatch_object_raises(self):
        reg = HandlerRegistry()
        with pytest.raises(HandlerRegistryError, match="ScheduledEvent"):
            reg.dispatch(object())


class TestEventHandlerFnExport:
    """EventHandlerFn is importable from the package."""

    def test_event_handler_fn_importable(self):
        from virtual_factory.discrete import EventHandlerFn as EHF
        from virtual_factory.discrete.handler_registry import EventHandlerFn as EHF2
        assert EHF is EHF2


class TestExceptionDetailNormalization:
    """Exception details are normalized: no newlines, bounded, no traceback."""

    def test_multiline_exception_normalized_to_one_line(self):
        def broken(_event):
            raise ValueError("line1\nline2\r\nline3")

        reg = HandlerRegistry()
        reg.register("test", broken)
        outcome = reg.dispatch(_evt("e1"))
        assert "\n" not in outcome.error_detail
        assert "\r" not in outcome.error_detail
        assert "line1 line2 line3" in outcome.error_detail

    def test_long_exception_detail_bounded(self):
        def broken(_event):
            raise RuntimeError("x" * 500)

        reg = HandlerRegistry()
        reg.register("test", broken)
        outcome = reg.dispatch(_evt("e1"))
        assert len(outcome.error_detail) <= 260  # 256 + "..."

    def test_keyboard_interrupt_still_not_caught(self):
        def interrupt(_event):
            raise KeyboardInterrupt()

        reg = HandlerRegistry()
        reg.register("test", interrupt)
        with pytest.raises(KeyboardInterrupt):
            reg.dispatch(_evt("e1"))

    def test_system_exit_still_not_caught(self):
        def exit_handler(_event):
            raise SystemExit(1)

        reg = HandlerRegistry()
        reg.register("test", exit_handler)
        with pytest.raises(SystemExit):
            reg.dispatch(_evt("e1"))
