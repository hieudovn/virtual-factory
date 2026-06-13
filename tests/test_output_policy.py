from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.telemetry.output_policy import OutputPolicy


def test_industrial_policy_blocks_internal_truth() -> None:
    """Industrial mode must not publish internal_truth signals."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    policy = OutputPolicy.from_config(config)

    assert policy.can_publish(config["signals"]["LT102_LEVEL"]) is True
    assert policy.can_publish(config["signals"]["T102_LEVEL_TRUE"]) is False
