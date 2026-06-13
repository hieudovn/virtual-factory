"""Base sensor abstraction."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BaseSensor:
    """Converts physical truth into measured industrial signals."""

    id: str
    measures: str
    output_signal: str
    parameters: dict[str, Any] = field(default_factory=dict)
