"""Validation direction for plant and model configuration."""

from typing import Any


def validate_required_keys(config: dict[str, Any], required_keys: list[str]) -> list[str]:
    """Return missing top-level keys without enforcing a full schema yet."""
    return [key for key in required_keys if key not in config]


def validate_plant_config_shape(config: dict[str, Any]) -> list[str]:
    """Perform minimal shape checks for early configuration feedback."""
    return validate_required_keys(config, ["plant", "medium", "equipment", "connections", "signals", "output_policy"])
