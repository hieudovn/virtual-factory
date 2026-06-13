"""Runtime object factory for validated plant configurations."""

from dataclasses import dataclass

from virtual_factory.actuation.base_actuator import BaseActuator
from virtual_factory.actuation.valve_actuator import ValveActuator
from virtual_factory.control.base_controller import BaseController
from virtual_factory.control.pid_controller import PIDController
from virtual_factory.core.plant_graph import PlantGraph
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig
from virtual_factory.equipment.base_equipment import BaseEquipment
from virtual_factory.equipment.pump import Pump
from virtual_factory.equipment.tank import Tank
from virtual_factory.equipment.valve import Valve
from virtual_factory.instrumentation.base_sensor import BaseSensor
from virtual_factory.instrumentation.flow_transmitter import FlowTransmitter
from virtual_factory.instrumentation.level_transmitter import LevelTransmitter
from virtual_factory.instrumentation.pressure_transmitter import PressureTransmitter
from virtual_factory.telemetry.output_policy import OutputPolicy

EQUIPMENT_TYPES: dict[str, type[BaseEquipment]] = {
    "tank_v1": Tank,
    "centrifugal_pump_v1": Pump,
    "control_valve_v1": Valve,
}

SENSOR_TYPES: dict[str, type[BaseSensor]] = {
    "level_transmitter_v1": LevelTransmitter,
    "flow_transmitter_v1": FlowTransmitter,
    "pressure_transmitter_v1": PressureTransmitter,
}

CONTROLLER_TYPES: dict[str, type[BaseController]] = {
    "pid_controller_v1": PIDController,
}

ACTUATOR_TYPES: dict[str, type[BaseActuator]] = {
    "valve_actuator_v1": ValveActuator,
}


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
    output_policy: OutputPolicy


def build_runtime(config: PlantConfig) -> RuntimeAssembly:
    """Instantiate runtime objects from a validated plant configuration."""
    graph = PlantGraph.from_config(config)
    state = RuntimeState()

    equipment = {
        item.id: _build_object(EQUIPMENT_TYPES, item.model_type, item)
        for item in config.equipment
    }
    sensors = {
        item.id: _build_object(SENSOR_TYPES, item.model_type, item)
        for item in config.sensors
    }
    controllers = {
        item.id: _build_object(CONTROLLER_TYPES, item.model_type, item)
        for item in config.controllers
    }
    actuators = {
        item.id: _build_object(ACTUATOR_TYPES, item.model_type, item)
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
        output_policy=OutputPolicy.from_config(config),
    )


def _build_object(registry: dict[str, type], model_type: str, config: object) -> object:
    if model_type not in registry:
        raise ValueError(f"Unsupported model_type: {model_type}")
    return registry[model_type](config)
