"""Base actuator abstraction."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BaseActuator:
    """Converts command signals into physical equipment actions."""

    id: str
    command_signal: str
    actuates: str
    parameters: dict[str, Any] = field(default_factory=dict)
