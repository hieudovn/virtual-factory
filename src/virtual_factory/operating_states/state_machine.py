"""Operating State Machine.

Explicit operating states with transitions, entry/exit conditions,
and benchmark truth export.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class OperatingState(str, Enum):
    """Explicit equipment/plant operating states."""
    STOPPED = "stopped"
    STARTUP = "startup"
    RAMP_UP = "ramp_up"
    STEADY_RUNNING = "steady_running"
    LOW_LOAD = "low_load"
    HIGH_LOAD = "high_load"
    RECYCLE_MODE = "recycle_mode"
    NEAR_SURGE = "near_surge"
    SHUTDOWN = "shutdown"
    TRIP = "trip"
    MAINTENANCE = "maintenance"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


# Ordered list for UI/reporting
OPERATING_STATES: list[OperatingState] = [
    OperatingState.STOPPED,
    OperatingState.STARTUP,
    OperatingState.RAMP_UP,
    OperatingState.STEADY_RUNNING,
    OperatingState.LOW_LOAD,
    OperatingState.HIGH_LOAD,
    OperatingState.RECYCLE_MODE,
    OperatingState.NEAR_SURGE,
    OperatingState.SHUTDOWN,
    OperatingState.TRIP,
    OperatingState.MAINTENANCE,
    OperatingState.RECOVERY,
]

# States where telemetry data is valid for analytics model training
VALID_TRAINING_STATES: set[OperatingState] = {
    OperatingState.STEADY_RUNNING,
    OperatingState.LOW_LOAD,
    OperatingState.HIGH_LOAD,
    OperatingState.RECYCLE_MODE,
}


@dataclass
class StateTransition:
    """Defines a possible transition between operating states.

    Attributes
    ----------
    from_state : OperatingState
        Source state.
    to_state : OperatingState
        Target state.
    condition : Callable | None
        Function(state, time_s) -> bool that must return True.
    description : str
        Human-readable trigger description.
    """
    from_state: OperatingState
    to_state: OperatingState
    description: str = ""
    condition: Callable[..., bool] | None = None

    def evaluate(self, state: dict[str, Any], time_s: float) -> bool:
        if self.condition is None:
            return True
        try:
            return bool(self.condition(state, time_s))
        except Exception:
            return False


@dataclass
class OperatingStateMachine:
    """State machine tracking operating state for an equipment asset.

    State transitions are evaluated each simulation step. When a
    transition fires, ``on_enter`` / ``on_exit`` callbacks are invoked.

    Usage::

        sm = OperatingStateMachine("COMP01", initial=OperatingState.STOPPED)
        sm.add_transition(StateTransition(
            OperatingState.STOPPED, OperatingState.STARTUP,
            condition=lambda s, t: s.get("COMP01.running"),
            description="Compressor start command",
        ))
        # Each step:
        sm.step(truth_state, current_time_s)
        current_state = sm.current  # OperatingState.STEADY_RUNNING
    """

    equipment_id: str
    initial: OperatingState = OperatingState.STOPPED

    # Runtime
    current: OperatingState = field(init=False)
    previous: OperatingState | None = field(init=False, default=None)
    time_in_state_s: float = field(init=False, default=0.0)
    state_history: list[dict[str, Any]] = field(default_factory=list)

    # Config
    transitions: list[StateTransition] = field(default_factory=list)
    on_enter_callbacks: dict[OperatingState, list[Callable[..., None]]] = field(default_factory=dict)
    on_exit_callbacks: dict[OperatingState, list[Callable[..., None]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.current = self.initial
        self.time_in_state_s = 0.0
        self.previous = None
        self.state_history = []

    def add_transition(self, transition: StateTransition) -> None:
        """Register a state transition rule."""
        self.transitions.append(transition)

    def on_enter(self, state: OperatingState, callback: Callable[..., None]) -> None:
        """Register a callback for when entering a state."""
        self.on_enter_callbacks.setdefault(state, []).append(callback)

    def on_exit(self, state: OperatingState, callback: Callable[..., None]) -> None:
        """Register a callback for when leaving a state."""
        self.on_exit_callbacks.setdefault(state, []).append(callback)

    def step(self, truth_state: dict[str, Any], dt_s: float = 1.0) -> OperatingState:
        """Evaluate transitions and advance state for one time step."""
        self.time_in_state_s += dt_s

        # Check all transitions from current state
        for trans in self.transitions:
            if trans.from_state != self.current:
                continue
            if trans.evaluate(truth_state, self.time_in_state_s):
                self._transition_to(trans.to_state, truth_state)
                break

        return self.current

    def force_state(self, new_state: OperatingState, truth_state: dict[str, Any]) -> None:
        """Force a state change regardless of transition rules."""
        self._transition_to(new_state, truth_state)

    def snapshot(self) -> dict[str, Any]:
        """Return current state as a dict for benchmark export."""
        return {
            "equipment_id": self.equipment_id,
            "current_state": self.current.value,
            "previous_state": self.previous.value if self.previous else None,
            "time_in_state_s": round(self.time_in_state_s, 2),
        }

    def _transition_to(self, new_state: OperatingState, truth_state: dict[str, Any]) -> None:
        """Execute a state transition with callbacks."""
        if new_state == self.current:
            return

        old_state = self.current

        # Exit callbacks
        for cb in self.on_exit_callbacks.get(old_state, []):
            try:
                cb(truth_state, old_state, new_state)
            except Exception:
                pass

        # Update state
        self.previous = old_state
        self.current = new_state
        self.time_in_state_s = 0.0

        # Record history
        self.state_history.append({
            "from": old_state.value,
            "to": new_state.value,
        })

        # Enter callbacks
        for cb in self.on_enter_callbacks.get(new_state, []):
            try:
                cb(truth_state, old_state, new_state)
            except Exception:
                pass
