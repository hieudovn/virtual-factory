"""Base controller abstraction."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import ControllerConfig


@dataclass(slots=True)
class BaseController:
    """Consumes measured signals and produces controller output signals."""

    config: ControllerConfig
    parameters: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.parameters = self.config.parameters

    @property
    def id(self) -> str:
        """Configured controller id."""
        return self.config.id

    @property
    def pv_signal(self) -> str:
        """Measured process variable signal consumed by the controller."""
        return self.config.pv_signal

    @property
    def output_signal(self) -> str:
        """Controller output signal name."""
        return self.config.output_signal

    def execute(self, state: RuntimeState) -> None:
        """Execute one controller scan."""
        raise NotImplementedError
