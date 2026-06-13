from pathlib import Path

import pytest
from pydantic import ValidationError

from virtual_factory.core.config_loader import load_yaml
from virtual_factory.core.schema import PlantConfig


def test_duplicate_ids_fail_validation() -> None:
    """IDs must be unique across equipment, sensors, controllers, and actuators."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["sensors"][0]["id"] = "T101"

    with pytest.raises(ValidationError, match="Duplicate object ids"):
        PlantConfig.model_validate(data)


def test_missing_controller_pv_signal_fails_validation() -> None:
    """Controller PV signals must refer to configured signals."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["controllers"][0]["pv_signal"] = "MISSING_LEVEL"

    with pytest.raises(ValidationError, match="unknown pv_signal"):
        PlantConfig.model_validate(data)


def test_controller_pv_signal_cannot_reference_true_state() -> None:
    """Controllers must consume measured signals, not true physical state endpoints."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["controllers"][0]["pv_signal"] = "T102.level_true"

    with pytest.raises(ValidationError, match="must be a measured signal"):
        PlantConfig.model_validate(data)
