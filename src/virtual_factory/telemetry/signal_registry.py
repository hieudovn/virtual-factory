"""Signal registry for configured industrial and internal signals."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SignalRegistry:
    """Stores signal metadata declared by plant configuration."""

    signals: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "SignalRegistry":
        """Create a registry from the top-level `signals` mapping."""
        return cls(signals=dict(config.get("signals", {})))
