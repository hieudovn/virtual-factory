"""Output policy enforcement for industrial telemetry."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.schema import OutputPolicyConfig, PlantConfig, SignalConfig


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
    def from_config(cls, config: PlantConfig | dict[str, Any]) -> "OutputPolicy":
        """Build a policy from plant configuration."""
        policy_config = config.output_policy if isinstance(config, PlantConfig) else config.get("output_policy", {})
        if isinstance(policy_config, OutputPolicyConfig):
            return cls(
                mode=policy_config.mode,
                allowed_categories=set(policy_config.publish_categories) or cls().allowed_categories,
            )
        return cls(
            mode=policy_config.get("mode", "industrial"),
            allowed_categories=set(policy_config.get("publish_categories", [])) or cls().allowed_categories,
        )

    def can_publish(self, signal_config: SignalConfig | dict[str, Any]) -> bool:
        """Return whether a signal may be published under this policy."""
        if isinstance(signal_config, SignalConfig):
            publish = signal_config.publish
            category = signal_config.category
        else:
            publish = signal_config.get("publish", False)
            category = signal_config.get("category")

        if not publish:
            return False
        if self.mode == "industrial" and category == "internal_truth":
            return False
        return category in self.allowed_categories
