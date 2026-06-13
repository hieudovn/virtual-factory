"""Configuration loading helpers."""

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at top level of {config_path}")
    return data


def load_plant_config(path: str | Path) -> dict[str, Any]:
    """Load a plant configuration file.

    Full schema validation will be added after the skeleton is in place.
    """
    return load_yaml(path)
