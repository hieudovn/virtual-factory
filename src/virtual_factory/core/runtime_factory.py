"""Runtime object factory for validated plant configurations.

Uses ``ModelRegistry`` to instantiate equipment, sensors, controllers,
and actuators from the model types declared in the plant config.
"""

from dataclasses import dataclass
from pathlib import Path

from virtual_factory.actuation.base_actuator import BaseActuator
from virtual_factory.control.base_controller import BaseController
from virtual_factory.core.model_registry import ModelRegistry
from virtual_factory.core.plant_graph import PlantGraph
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig
from virtual_factory.equipment.base_equipment import BaseEquipment
from virtual_factory.instrumentation.base_sensor import BaseSensor
from virtual_factory.telemetry.alarm_manager import AlarmManager
from virtual_factory.telemetry.output_policy import OutputPolicy
from virtual_factory.telemetry.ring_buffer import RingBufferTelemetryStore

# Default directory searched for model-type YAML files.
_DEFAULT_MODEL_TYPES_DIR = Path("configs/model_types")


@dataclass(slots=True)
class RuntimeAssembly:
    """Instantiated runtime objects and shared state for one plant config."""

    config: PlantConfig
    graph: PlantGraph
    state: RuntimeState
    equipment: dict[str, BaseEquipment]
    sensors: dict[str, BaseSensor]
    controllers: dict[str, BaseController]
    actuators: dict[str, BaseActuator]
    alarm_manager: AlarmManager
    output_policy: OutputPolicy
    telemetry_store: RingBufferTelemetryStore


def build_runtime(
    config: PlantConfig,
    model_types_dir: str | Path = _DEFAULT_MODEL_TYPES_DIR,
) -> RuntimeAssembly:
    """Instantiate runtime objects from a validated plant configuration.

    Model types are discovered in *model_types_dir* (``configs/model_types``
    by default).  Each ``.yaml`` file declares a ``python_class`` that tells
    the registry which Python class to create.
    """
    registry = ModelRegistry.from_directory(model_types_dir)

    graph = PlantGraph.from_config(config)
    state = RuntimeState()

    equipment = {
        item.id: registry.build(item.model_type, item)
        for item in config.equipment
    }
    sensors = {
        item.id: registry.build(item.model_type, item)
        for item in config.sensors
    }
    controllers = {
        item.id: registry.build(item.model_type, item)
        for item in config.controllers
    }
    actuators = {
        item.id: registry.build(item.model_type, item)
        for item in config.actuators
    }

    return RuntimeAssembly(
        config=config,
        graph=graph,
        state=state,
        equipment=equipment,
        sensors=sensors,
        controllers=controllers,
        actuators=actuators,
        alarm_manager=AlarmManager(config.alarms),
        output_policy=OutputPolicy.from_config(config),
        telemetry_store=RingBufferTelemetryStore(),
    )
