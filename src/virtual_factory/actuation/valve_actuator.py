"""Valve actuator skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.actuation.base_actuator import BaseActuator


@dataclass(slots=True)
class ValveActuator(BaseActuator):
    """Placeholder for mapping controller output to valve opening."""

    def update(self, state: RuntimeState) -> None:
        """Move valve opening truth toward the controller command."""
        command = float(state.get_signal(self.command_signal, 0.0))
        current = float(state.get_truth(self.actuates, 0.0))
        max_rate = self.parameters.get("max_rate")

        if max_rate is None:
            next_value = command
        else:
            delta = max(-float(max_rate), min(float(max_rate), command - current))
            next_value = current + delta

        next_value = max(0.0, min(100.0, next_value))
        state.set_truth(self.actuates, next_value)
        if self.feedback_signal:
            state.set_signal(self.feedback_signal, next_value)
