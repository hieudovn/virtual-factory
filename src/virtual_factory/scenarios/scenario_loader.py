"""Scenario configuration loading helpers."""

from pathlib import Path

from virtual_factory.core.config_loader import load_yaml
from virtual_factory.core.schema import ScenarioConfig


def load_scenario(path: str | Path) -> ScenarioConfig:
    """Load and validate a standalone scenario YAML file."""
    return ScenarioConfig.model_validate(load_yaml(path))
