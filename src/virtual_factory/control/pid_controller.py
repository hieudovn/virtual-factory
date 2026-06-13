"""PID controller skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.control.base_controller import BaseController


@dataclass(slots=True)
class PIDController(BaseController):
    """PID controller placeholder; tuning logic will be added later."""

    integral: float = 0.0

    def execute(self, state: RuntimeState) -> None:
        """Run a deterministic minimal PI/PID calculation."""
        pv = float(state.get_signal(self.pv_signal, 0.0))
        setpoint = float(self.config.setpoint or 0.0)
        dt = float(self.config.scan_time_s or 1.0)
        kp = float(self.parameters.get("kp", 0.0))
        ki = float(self.parameters.get("ki", 0.0))

        error = setpoint - pv
        self.integral += error * dt
        output = kp * error + ki * self.integral
        state.set_signal(self.output_signal, max(0.0, min(100.0, output)))
