"""Base sensor with delay buffer, drift, and stuck-fault behaviour.

Extends the original noise/bias/resolution/quality handling with:
- **Transport delay** — configurable ``delay_s`` using an internal ring buffer.
- **Drift** — accumulator that grows each sample (controlled by scenario).
- **Stuck fault** — returns the last good value when quality is ``STUCK``.
"""

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import SensorConfig, SignalConfig


@dataclass(slots=True)
class BaseSensor:
    """Converts physical truth into measured industrial signals.

    Parameters (from config)
    ------------------------
    sample_time_s : float
        Sampling interval in seconds (informational).
    noise_std : float
        Standard deviation of Gaussian noise added to the reading.
    resolution : float
        Quantisation step applied after noise and bias.
    delay_s : float
        Transport delay — sensor output is a past value ``delay_s``
        seconds old.  Internal buffer size = ``ceil(delay_s / dt)``.
    quality : str
        Default signal quality (``GOOD``, ``BAD``, ``UNCERTAIN``, …).

    Faults (driven by ``RuntimeState.diagnostics``)
    ------------------------------------------------
    ``sensor_quality.{id}`` — override quality (e.g. ``BAD``, ``STUCK``).
        When ``STUCK`` the sensor returns the **last good value**.
    ``sensor_bias.{id}`` — constant additive bias (float).
    ``sensor_drift.{id}`` — per-sample drift increment (float).
    """

    config: SensorConfig
    parameters: dict[str, Any] = field(init=False)
    _delay_buffer: deque[float] = field(init=False)
    _last_good_value: float = 0.0
    _drift_acc: float = 0.0

    def __post_init__(self) -> None:
        self.parameters = self.config.parameters
        self._delay_buffer = deque(maxlen=self._delay_buffer_len())

    def _delay_buffer_len(self) -> int:
        dt = float(self.parameters.get("sample_time_s", 1.0))
        delay = float(self.parameters.get("delay_s", 0.0))
        if delay <= 0.0 or dt <= 0.0:
            return 1
        return max(1, math.ceil(delay / dt))

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def measures(self) -> str:
        return self.config.measures

    @property
    def output_signal(self) -> str:
        return self.config.output_signal

    # ------------------------------------------------------------------
    # Public sampling entry point
    # ------------------------------------------------------------------

    def sample(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        signal_config: SignalConfig | None = None,
    ) -> None:
        """Read physical truth, apply processing chain, write the signal."""
        unit = signal_config.unit if signal_config else None
        category = signal_config.category if signal_config else "industrial_signal"
        source = signal_config.source if signal_config else self.id

        quality = self._resolve_quality(state)

        # Stuck fault: reuse last good value, skip pipeline
        if quality == "STUCK":
            value = self._last_good_value
            state.set_signal_value(self.output_signal, value, timestamp_s, unit, category, quality, source)
            return

        # Normal pipeline
        value = state.get_truth(self.measures, 0.0)
        value = self._apply_noise(value)
        value = self._apply_bias(value, state)
        self._apply_drift(state)
        value = value + self._drift_acc
        value = self._apply_resolution(value)

        # Delay buffer
        self._push_delay(value)
        value = self._output_delayed(value)

        self._last_good_value = value
        state.set_signal_value(self.output_signal, value, timestamp_s, unit, category, quality, source)

    # ------------------------------------------------------------------
    # Processing chain (each step is optional)
    # ------------------------------------------------------------------

    def _apply_noise(self, value: Any) -> Any:
        noise_std = float(self.parameters.get("noise_std", 0.0))
        if noise_std <= 0 or not isinstance(value, int | float):
            return value
        return float(value) + random.gauss(0.0, noise_std)

    def _apply_bias(self, value: Any, state: RuntimeState) -> Any:
        if not isinstance(value, int | float):
            return value
        bias = float(state.diagnostics.get(f"sensor_bias.{self.id}", 0.0))
        return float(value) + bias

    def _apply_drift(self, state: RuntimeState) -> None:
        """Increment drift accumulator (called for side-effect).

        Drift accumulates from two sources:
        - ``drift_scale`` parameter in config (always-on).
        - ``sensor_drift.{id}`` in diagnostics (set by scenario action).
        """
        config_drift = float(self.parameters.get("drift_scale", 0.0))
        scenario_drift = float(state.diagnostics.get(f"sensor_drift.{self.id}", 0.0))
        self._drift_acc += config_drift + scenario_drift

    def _apply_resolution(self, value: Any) -> Any:
        resolution = self.parameters.get("resolution")
        if resolution is None or not isinstance(value, int | float):
            return value
        r = float(resolution)
        if r <= 0:
            return value
        return round(round(float(value) / r) * r, 12)

    # ------------------------------------------------------------------
    # Delay buffer
    # ------------------------------------------------------------------

    def _push_delay(self, value: float) -> None:
        self._delay_buffer.append(value)

    def _output_delayed(self, latest: float) -> float:
        """Return the oldest buffered value (transport delay)."""
        return self._delay_buffer[0]

    # ------------------------------------------------------------------
    # Quality
    # ------------------------------------------------------------------

    def _resolve_quality(self, state: RuntimeState) -> str:
        quality = state.diagnostics.get(f"sensor_quality.{self.id}")
        if quality is not None:
            return str(quality)
        return str(self.parameters.get("quality", "GOOD"))
