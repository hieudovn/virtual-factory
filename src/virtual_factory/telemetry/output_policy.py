"""Output policy enforcement for industrial telemetry."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OutputPolicy:
    """Determines whether configured signals may be published."""

    mode: str = "industrial"
    allowed_categories: set[str] = field(
        default_factory=lambda: {
            "industrial_signal",
            "controller_signal",
            "actuator_feedback",
            "industrial_event",
        }
    )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "OutputPolicy":
        """Build a policy from plant configuration."""
        policy_config = config.get("output_policy", {})
        return cls(
            mode=policy_config.get("mode", "industrial"),
            allowed_categories=set(policy_config.get("publish_categories", [])) or cls().allowed_categories,
        )

    def can_publish(self, signal_config: dict[str, Any]) -> bool:
        """Return whether a signal may be published under this policy."""
        if not signal_config.get("publish", False):
            return False
        category = signal_config.get("category")
        if self.mode == "industrial" and category == "internal_truth":
            return False
        return category in self.allowed_categories
