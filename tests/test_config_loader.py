from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.schema import PlantConfig


def test_mvp_config_can_be_loaded() -> None:
    """Config loader should load the MVP YAML into a validated PlantConfig."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))

    assert isinstance(config, PlantConfig)
    assert config.plant.id == "continuous_mvp_01"
    assert config.signals["LT102_LEVEL"].publish is True


def test_mvp_equipment_ids_come_from_config() -> None:
    """MVP equipment IDs should be present in configuration, not engine constants."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    equipment_ids = {item.id for item in config.equipment}

    assert {"T101", "P101", "V101", "T102"} <= equipment_ids
