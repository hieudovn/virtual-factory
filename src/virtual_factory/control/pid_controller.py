"""PID controller with derivative term, low-pass filter, and anti-windup.

Features
--------
- Proportional, integral, and derivative gains (kp, ki, kd).
- Derivative on **measurement** (not on error) to avoid kick on setpoint
  changes.
- First-order IIR low-pass filter on derivative for noise attenuation.
- Integral anti-windup via clamping — integral does not accumulate when
  the output is saturated and the error is pushing further into saturation.
"""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.control.base_controller import BaseController
from virtual_factory.core.schema import SignalConfig

_OUTPUT_MIN = 0.0
_OUTPUT_MAX = 100.0


@dataclass(slots=True)
class PIDController(BaseController):
    """Full PID controller with derivative filter and anti-windup."""

    integral: float = 0.0
    last_pv: float | None = None
    last_derivative: float = 0.0

    def execute(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        signal_config: SignalConfig | None = None,
    ) -> None:
        """Run one PID scan with D-term, filter, and anti-windup."""
        pv = state.get_signal_numeric(self.pv_signal, 0.0)
        setpoint = float(self.config.setpoint or 0.0)
        dt = float(self.config.scan_time_s or 1.0)
        kp = float(self.parameters.get("kp", 0.0))
        ki = float(self.parameters.get("ki", 0.0))
        kd = float(self.parameters.get("kd", 0.0))

        error = setpoint - pv

        # --- P term ---
        p_out = kp * error

        # --- D term (derivative on measurement) ---
        d_out = 0.0
        if kd != 0.0 and self.last_pv is not None:
            derivative = (pv - self.last_pv) / max(dt, 1e-12)
            self.last_derivative = self._filter_derivative(derivative, dt)
            d_out = kd * self.last_derivative

        # --- I term with anti-windup ---
        # Compute tentative integral step to see if it pushes further into
        # saturation.  If the full output (P+I+D) would saturate and the
        # integral is pushing in the same direction, clamp the integral.
        integral_step = error * dt
        tentative_i = ki * (self.integral + integral_step)
        tentative_output = p_out + tentative_i + d_out

        if tentative_output > _OUTPUT_MAX and error > 0:
            pass  # skip integral — pushing further into saturation
        elif tentative_output < _OUTPUT_MIN and error < 0:
            pass  # skip integral — pushing further into saturation
        else:
            self.integral += integral_step
        i_out = ki * self.integral

        output = p_out + i_out + d_out
        clamped = max(_OUTPUT_MIN, min(_OUTPUT_MAX, output))

        self.last_pv = pv

        state.set_signal_value(
            self.output_signal,
            clamped,
            timestamp_s=timestamp_s,
            unit=signal_config.unit if signal_config else "percent",
            category=signal_config.category if signal_config else "controller_signal",
            quality="GOOD",
            source=signal_config.source if signal_config else self.id,
        )

    def _filter_derivative(self, raw: float, dt: float) -> float:
        """First-order IIR low-pass filter on the derivative."""
        tau = float(self.parameters.get("derivative_filter_tau_s", 0.0))
        if tau <= 0.0:
            tau = 2.0 * dt  # default: τf = 2 × scan time
        alpha = dt / (tau + dt)
        return alpha * raw + (1.0 - alpha) * self.last_derivative
