"""Base equipment abstraction."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BaseEquipment:
    """Base class for equipment that owns internal physical state and ports."""

    id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
