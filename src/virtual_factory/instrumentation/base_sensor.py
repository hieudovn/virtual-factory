"""Base sensor abstraction."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import SensorConfig


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

    def sample(self, state: RuntimeState) -> None:
        """Read physical truth and write a measured signal."""
        # TODO: Add sensor fault, range, delay, and quality behavior.
        value = state.get_truth(self.measures, 0.0)
        state.set_signal(self.output_signal, value)
