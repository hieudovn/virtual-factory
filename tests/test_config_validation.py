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


def test_alarm_source_cannot_reference_true_state() -> None:
    """Alarm source_signal must not be a true physical state path."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["alarms"][0]["source_signal"] = "T102.level_true"

    with pytest.raises(ValidationError, match="source_signal must be measured"):
        PlantConfig.model_validate(data)


def test_alarm_source_signal_cannot_be_internal_truth() -> None:
    """Alarm source_signal must not point at an internal_truth configured signal."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["alarms"][0]["source_signal"] = "T102_LEVEL_TRUE"

    with pytest.raises(ValidationError, match="source_signal cannot be internal_truth"):
        PlantConfig.model_validate(data)


def test_alarm_output_signal_must_be_industrial_event() -> None:
    """Alarm output signals must be configured as industrial_event."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["signals"]["T102_LOW_LEVEL_ALARM"]["category"] = "industrial_signal"

    with pytest.raises(ValidationError, match="output_signal must be industrial_event"):
        PlantConfig.model_validate(data)
