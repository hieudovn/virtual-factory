"""Valve actuator skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import SignalConfig, endpoint_object_id
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
        stuck_value = self._stuck_value(state)
        if stuck_value is not None:
            self._write_opening(state, stuck_value, timestamp_s, feedback_signal_config)
            return

        command = state.get_signal_numeric(self.command_signal, 0.0)
        current = float(state.get_truth(self.actuates, 0.0))
        max_rate = self.parameters.get("max_rate")

        if max_rate is None:
            next_value = command
        else:
            delta = max(-float(max_rate), min(float(max_rate), command - current))
            next_value = current + delta

        self._write_opening(state, next_value, timestamp_s, feedback_signal_config)

    def _stuck_value(self, state: RuntimeState) -> float | None:
        valve_id = endpoint_object_id(self.actuates)
        actuator_key = f"fault.valve_stuck.{self.id}"
        valve_key = f"fault.valve_stuck.{valve_id}"
        if actuator_key in state.diagnostics:
            return float(state.diagnostics[actuator_key])
        if valve_key in state.diagnostics:
            return float(state.diagnostics[valve_key])
        return None

    def _write_opening(
        self,
        state: RuntimeState,
        value: float,
        timestamp_s: float,
        feedback_signal_config: SignalConfig | None,
    ) -> None:
        next_value = max(0.0, min(100.0, value))
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
