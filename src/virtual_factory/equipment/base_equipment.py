"""Base equipment abstraction."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig


@dataclass(slots=True)
class BaseEquipment:
    """Base class for equipment that owns internal physical state and ports."""

    config: EquipmentConfig
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Configured equipment id."""
        return self.config.id

    @property
    def parameters(self) -> dict[str, Any]:
        """Configured equipment parameters."""
        return self.config.parameters

    def initialize_state(self, state: RuntimeState) -> None:
        """Initialize equipment truth values in runtime state."""
