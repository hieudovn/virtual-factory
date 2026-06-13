from pathlib import Path

import pytest
from pydantic import ValidationError

from virtual_factory.core.config_loader import load_plant_config, load_yaml
from virtual_factory.core.schema import PlantConfig
from virtual_factory.telemetry.output_policy import OutputPolicy


def test_industrial_policy_allows_measured_signal() -> None:
    """Industrial mode should allow configured measurable signals."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    policy = OutputPolicy.from_config(config)

    assert policy.can_publish(config.signals["LT102_LEVEL"]) is True


def test_industrial_policy_blocks_internal_truth() -> None:
    """Industrial mode must not publish internal_truth signals."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    policy = OutputPolicy.from_config(config)

    assert policy.can_publish(config.signals["T102_LEVEL_TRUE"]) is False


def test_validation_fails_when_internal_truth_is_published() -> None:
    """Config validation should reject published internal truth in industrial mode."""
    data = load_yaml(Path("configs/plants/continuous_mvp_01.yaml"))
    data["signals"]["T102_LEVEL_TRUE"]["publish"] = True

    with pytest.raises(ValidationError, match="Internal truth signal cannot be published"):
        PlantConfig.model_validate(data)
