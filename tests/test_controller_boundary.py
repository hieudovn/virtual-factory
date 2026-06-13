from pathlib import Path

import pytest
from pydantic import ValidationError

from virtual_factory.core.config_loader import load_plant_config, load_yaml
from virtual_factory.core.runtime_factory import build_runtime
from virtual_factory.core.schema import PlantConfig


def test_runtime_controller_uses_measured_signal() -> None:
    """The configured controller should consume LT102_LEVEL, not T102.level_true."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    assembly = build_runtime(config)

    controller = assembly.controllers["LIC102"]

    assert controller.pv_signal == "LT102_LEVEL"
    assert controller.pv_signal in config.signals


def test_controller_direct_truth_pv_fails_validation() -> None:
    """PlantConfig validation blocks direct physical truth controller inputs."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["controllers"][0]["pv_signal"] = "T102.level_true"

    with pytest.raises(ValidationError, match="must be a measured signal"):
        PlantConfig.model_validate(data)
