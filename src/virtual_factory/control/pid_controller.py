"""PID controller skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.control.base_controller import BaseController
from virtual_factory.core.schema import SignalConfig


@dataclass(slots=True)
class PIDController(BaseController):
    """PID controller placeholder; tuning logic will be added later."""

    integral: float = 0.0

    def execute(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        signal_config: SignalConfig | None = None,
    ) -> None:
        """Run a deterministic minimal PI/PID calculation."""
        pv = state.get_signal_numeric(self.pv_signal, 0.0)
        setpoint = float(self.config.setpoint or 0.0)
        dt = float(self.config.scan_time_s or 1.0)
        kp = float(self.parameters.get("kp", 0.0))
        ki = float(self.parameters.get("ki", 0.0))

        error = setpoint - pv
        self.integral += error * dt
        output = kp * error + ki * self.integral
        state.set_signal_value(
            self.output_signal,
            max(0.0, min(100.0, output)),
            timestamp_s=timestamp_s,
            unit=signal_config.unit if signal_config else "percent",
            category=signal_config.category if signal_config else "controller_signal",
            quality="GOOD",
            source=signal_config.source if signal_config else self.id,
        )
