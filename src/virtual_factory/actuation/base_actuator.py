"""Base actuator abstraction."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import ActuatorConfig, SignalConfig


@dataclass(slots=True)
class BaseActuator:
    """Converts command signals into physical equipment actions."""

    config: ActuatorConfig
    parameters: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.parameters = self.config.parameters

    @property
    def id(self) -> str:
        """Configured actuator id."""
        return self.config.id

    @property
    def command_signal(self) -> str:
        """Command signal consumed by this actuator."""
        return self.config.command_signal

    @property
    def actuates(self) -> str:
        """Internal truth target written by this actuator."""
        return self.config.actuates

    @property
    def feedback_signal(self) -> str | None:
        """Optional actuator feedback signal produced by this actuator."""
        return self.config.feedback_signal

    def update(
        self,
        state: RuntimeState,
        timestamp_s: float = 0.0,
        feedback_signal_config: SignalConfig | None = None,
    ) -> None:
        """Apply the command signal to the physical target."""
        raise NotImplementedError
