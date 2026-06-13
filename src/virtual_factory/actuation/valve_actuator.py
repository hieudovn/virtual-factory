"""Valve actuator skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import SignalConfig
from virtual_factory.actuation.base_actuator import BaseActuator


@dataclass(slots=True)
class ValveActuator(BaseActuator):
    """Placeholder for mapping controller output to valve opening."""

    def update(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        feedback_signal_config: SignalConfig | None = None,
    ) -> None:
        """Move valve opening truth toward the controller command."""
        command = state.get_signal_numeric(self.command_signal, 0.0)
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
            state.set_signal_value(
                self.feedback_signal,
                next_value,
                timestamp_s=timestamp_s,
                unit=feedback_signal_config.unit if feedback_signal_config else "percent",
                category=feedback_signal_config.category if feedback_signal_config else "actuator_feedback",
                quality="GOOD",
                source=feedback_signal_config.source if feedback_signal_config else self.id,
            )
