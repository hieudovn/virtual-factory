"""Actuator Engine — manages 12 Manipulated Variables with realistic actuation."""

from __future__ import annotations

import random
from typing import Any

from .models import MVConfig, clamp, seeded_rng


class Actuator:
    """Simulates a single actuator: SP → actual MV with slew rate + accuracy error."""

    def __init__(self, config: MVConfig) -> None:
        self.config = config
        self.current: float = config.default_sp
        self.setpoint: float = config.default_sp
        self._value: float = config.default_sp

    def set(self, sp: float) -> None:
        """Operator sets a new setpoint."""
        self.setpoint = clamp(sp, self.config.min_sp, self.config.max_sp)

    def update(self, dt_s: float, rng: random.Random) -> float:
        """Advance actuator by dt_s. Returns actual MV value."""
        if self.config.slew_rate <= 0 or self.config.min_sp == self.config.max_sp:
            # Binary (on/off) actuator
            self.current = self.setpoint
            self._value = self.setpoint
            return self._value

        # Slew rate limit
        max_delta = self.config.slew_rate * dt_s
        error = self.setpoint - self.current
        delta = clamp(error, -max_delta, max_delta)
        self.current += delta

        # Steady-state accuracy error
        accuracy_error = 1.0 + rng.gauss(0, self.config.accuracy_pct / 100.0)
        self._value = clamp(self.current * accuracy_error, self.config.min_sp, self.config.max_sp)
        return self._value

    @property
    def value(self) -> float:
        return self._value

    def status(self) -> dict[str, Any]:
        return {
            "signal_id": self.config.signal_id,
            "sp": round(self.setpoint, 2),
            "actual": round(self._value, 2),
            "unit": "L/min" if "flow" in self.config.signal_id else ("RPM" if "speed" in self.config.signal_id else ""),
            "range": [self.config.min_sp, self.config.max_sp],
        }


class ActuatorEngine:
    """Manages all 12 MV actuators."""

    def __init__(self, mv_configs: dict[str, MVConfig]) -> None:
        self.actuators: dict[str, Actuator] = {
            sid: Actuator(cfg) for sid, cfg in mv_configs.items()
        }

    def set_setpoint(self, signal_id: str, sp: float) -> Actuator | None:
        """Set a new setpoint for an MV. Returns the actuator or None."""
        actuator = self.actuators.get(signal_id)
        if actuator is None:
            return None
        actuator.set(sp)
        return actuator

    def step(self, dt_s: float, rng: random.Random | None = None) -> dict[str, float]:
        """Advance all actuators by dt_s. Returns {signal_id: actual_value}."""
        rng = rng or seeded_rng()
        results: dict[str, float] = {}
        for sid, act in self.actuators.items():
            results[sid] = act.update(dt_s, rng)
        return results

    def get_status(self) -> list[dict[str, Any]]:
        """Return current SP and actual for all MVs."""
        return [act.status() for act in self.actuators.values()]

    def get_actual(self, signal_id: str) -> float:
        """Get current actual value for an MV."""
        act = self.actuators.get(signal_id)
        return act.value if act else 0.0
