from pathlib import Path

from virtual_factory.actuation.valve_actuator import ValveActuator
from virtual_factory.control.pid_controller import PIDController
from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.runtime_factory import build_runtime
from virtual_factory.equipment.tank import Tank
from virtual_factory.instrumentation.level_transmitter import LevelTransmitter


def test_build_runtime_creates_objects_from_config() -> None:
    """Runtime object creation should be driven by model_type mappings."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    assembly = build_runtime(config)

    assert isinstance(assembly.equipment["T101"], Tank)
    assert isinstance(assembly.sensors["LT102"], LevelTransmitter)
    assert isinstance(assembly.controllers["LIC102"], PIDController)
    assert isinstance(assembly.actuators["VA101"], ValveActuator)


def test_build_runtime_uses_configured_ids() -> None:
    """Runtime assembly should not need engine constants for plant object IDs."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    assembly = build_runtime(config)

    assert set(assembly.equipment) == {item.id for item in config.equipment}
    assert set(assembly.sensors) == {item.id for item in config.sensors}
    assert set(assembly.controllers) == {item.id for item in config.controllers}
    assert set(assembly.actuators) == {item.id for item in config.actuators}
