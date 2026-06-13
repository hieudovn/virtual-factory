"""Registry for reusable model types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ModelRegistry:
    """Stores model type metadata loaded from configuration files."""

    model_types: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register(self, model_type: dict[str, Any]) -> None:
        """Register one model type definition."""
        model_id = model_type["id"]
        self.model_types[model_id] = model_type

    def get(self, model_id: str) -> dict[str, Any]:
        """Return a registered model type definition."""
        return self.model_types[model_id]
