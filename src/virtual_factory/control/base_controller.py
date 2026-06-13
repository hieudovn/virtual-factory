"""Base controller abstraction."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BaseController:
    """Consumes measured signals and produces controller output signals."""

    id: str
    pv_signal: str
    output_signal: str
    parameters: dict[str, Any] = field(default_factory=dict)
