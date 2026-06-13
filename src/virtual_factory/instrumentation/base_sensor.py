"""Base sensor abstraction."""

import random
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import SensorConfig, SignalConfig


@dataclass(slots=True)
class BaseSensor:
    """Converts physical truth into measured industrial signals."""

    config: SensorConfig
    parameters: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.parameters = self.config.parameters

    @property
    def id(self) -> str:
        """Configured sensor id."""
        return self.config.id

    @property
    def measures(self) -> str:
        """Internal truth endpoint measured by this sensor."""
        return self.config.measures

    @property
    def output_signal(self) -> str:
        """Measured signal produced by this sensor."""
        return self.config.output_signal

    def sample(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        signal_config: SignalConfig | None = None,
    ) -> None:
        """Read physical truth and write a measured signal."""
        # TODO: Add delay buffer and sensor fault behavior.
        value = state.get_truth(self.measures, 0.0)
        value = self._apply_noise(value)
        value = self._apply_bias(value, state)
        value = self._apply_resolution(value)
        quality = self._quality(state)
        state.set_signal_value(
            self.output_signal,
            value,
            timestamp_s=timestamp_s,
            unit=signal_config.unit if signal_config else None,
            category=signal_config.category if signal_config else "industrial_signal",
            quality=quality,
            source=signal_config.source if signal_config else self.id,
        )

    def _apply_noise(self, value: Any) -> Any:
        noise_std = float(self.parameters.get("noise_std", 0.0))
        if noise_std <= 0 or not isinstance(value, int | float):
            return value
        return float(value) + random.gauss(0.0, noise_std)

    def _apply_resolution(self, value: Any) -> Any:
        resolution = self.parameters.get("resolution")
        if resolution is None or not isinstance(value, int | float):
            return value
        resolution_value = float(resolution)
        if resolution_value <= 0:
            return value
        return round(round(float(value) / resolution_value) * resolution_value, 12)

    def _apply_bias(self, value: Any, state: RuntimeState) -> Any:
        """Apply deterministic sensor bias before resolution quantization."""
        if not isinstance(value, int | float):
            return value
        bias = float(state.diagnostics.get(f"sensor_bias.{self.id}", 0.0))
        return float(value) + bias

    def _quality(self, state: RuntimeState) -> str:
        return str(
            state.diagnostics.get(
                f"sensor_quality.{self.id}",
                state.diagnostics.get(f"sensor_quality.{self.output_signal}", self.parameters.get("quality", "GOOD")),
            )
        )
