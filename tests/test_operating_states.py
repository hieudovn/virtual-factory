"""Tests for the Operating State Machine."""

import pytest

from virtual_factory.operating_states.state_machine import (
    OperatingState,
    OperatingStateMachine,
    StateTransition,
)


class TestOperatingStateMachine:
    def test_initial_state(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        assert sm.current == OperatingState.STOPPED
        assert sm.previous is None

    def test_transition_fires(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: s.get("EQ01.running", False),
            description="Start command",
        ))

        # No transition when condition false
        sm.step({"EQ01.running": False})
        assert sm.current == OperatingState.STOPPED

        # Transition fires when condition true
        sm.step({"EQ01.running": True})
        assert sm.current == OperatingState.STARTUP

    def test_transition_chain(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: s.get("running"),
        ))
        sm.add_transition(StateTransition(
            OperatingState.STARTUP, OperatingState.STEADY_RUNNING,
            condition=lambda s, t: t > 30.0,
        ))

        sm.step({"running": True})
        assert sm.current == OperatingState.STARTUP

        # Not enough time
        sm.step({"running": True})
        assert sm.current == OperatingState.STARTUP

        # After 30s cumulative
        for _ in range(30):
            sm.step({"running": True})
        assert sm.current == OperatingState.STEADY_RUNNING

    def test_force_state(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.force_state(OperatingState.TRIP, {})
        assert sm.current == OperatingState.TRIP
        assert sm.previous == OperatingState.STOPPED

    def test_snapshot(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STEADY_RUNNING)
        snap = sm.snapshot()
        assert snap["equipment_id"] == "EQ01"
        assert snap["current_state"] == "steady_running"
        assert "time_in_state_s" in snap

    def test_state_history(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: True,
        ))
        sm.step({})
        assert len(sm.state_history) == 1
        assert sm.state_history[0]["from"] == "stopped"
        assert sm.state_history[0]["to"] == "startup"

    def test_callbacks(self):
        entered = []
        exited = []

        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.on_enter(OperatingState.STARTUP, lambda s, old, new: entered.append(new.value))
        sm.on_exit(OperatingState.STOPPED, lambda s, old, new: exited.append(old.value))
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: True,
        ))
        sm.step({})
        assert "startup" in entered
        assert "stopped" in exited

    def test_time_in_state_resets_on_transition(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: t > 10.0,
        ))
        # Stay in STOPPED for 15 seconds
        for _ in range(15):
            sm.step({})
        assert sm.current == OperatingState.STARTUP
        # Time should have been reset
        assert sm.time_in_state_s < 5.0

    def test_no_transition_to_same_state(self):
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STARTUP)
        sm.add_transition(StateTransition(
            OperatingState.STARTUP, OperatingState.STARTUP,
            condition=lambda s, t: True,
        ))
        sm.step({})
        # Should remain STARTUP (no self-transition)
        assert sm.current == OperatingState.STARTUP
        assert len(sm.state_history) == 0
