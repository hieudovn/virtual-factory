from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config


def test_mvp_config_can_be_loaded() -> None:
    """Config loader should load the MVP YAML into a mapping."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))

    assert config["plant"]["id"] == "continuous_mvp_01"
    assert config["equipment"]
    assert config["signals"]["LT102_LEVEL"]["publish"] is True
