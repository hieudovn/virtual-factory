"""Minimal continuous-process dynamics for early MVP validation.

This module intentionally implements only a simple single-path approximation.
Future versions should replace this with a graph-based hydraulic solver that
uses ports, units, equipment curves, and conservation checks across subgraphs.
"""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig, PlantConfig, endpoint_object_id


@dataclass(frozen=True, slots=True)
class ContinuousPath:
    """Inferred single-path process section for the MVP dynamics approximation."""

    source_tank: EquipmentConfig
    pump: EquipmentConfig
    valve: EquipmentConfig
    destination_tank: EquipmentConfig


def update_continuous_process(config: PlantConfig, state: RuntimeState, dt_s: float) -> None:
    """Update a minimal tank-pump-valve-tank continuous process."""
    path = _infer_single_path(config)
    if path is None:
        state.diagnostics["process_dynamics"] = "No tank-pump-valve-tank path inferred."
        return

    density = float(config.medium.density_kg_m3)
    pump_running = bool(state.get_truth(f"{path.pump.id}.running", True))
    rated_flow = float(path.pump.parameters.get("rated_flow_m3_s", 0.0))
    rated_head = float(path.pump.parameters.get("rated_head_m", 0.0))

    if pump_running:
        discharge_pressure_kpa = rated_head * 9.81 * density / 1000.0
        available_flow_m3_s = rated_flow
    else:
        discharge_pressure_kpa = 0.0
        available_flow_m3_s = 0.0

    opening_percent = float(state.get_truth(f"{path.valve.id}.opening_actual", 0.0))
    opening_fraction = _clamp(opening_percent / 100.0, 0.0, 1.0)
    flow_m3_s = available_flow_m3_s * opening_fraction

    qout_m3_s = _tank_outlet_demand(path.destination_tank)
    capacity_m3 = float(path.destination_tank.parameters.get("capacity_m3", 0.0))
    previous_volume = float(state.get_truth(f"{path.destination_tank.id}.volume_true", 0.0))
    next_volume = _clamp(previous_volume + (flow_m3_s - qout_m3_s) * dt_s, 0.0, capacity_m3)
    next_level = _volume_to_level(path.destination_tank, next_volume)

    state.set_truth(f"{path.pump.id}.discharge_pressure_true", discharge_pressure_kpa)
    state.set_truth(f"{path.valve.id}.outlet.flow_true", flow_m3_s)
    state.set_truth(f"{path.valve.id}.outlet.mass_flow_true", flow_m3_s * density)
    state.set_truth(f"{path.destination_tank.id}.volume_true", next_volume)
    state.set_truth(f"{path.destination_tank.id}.level_true", next_level)
    state.diagnostics["process_dynamics"] = "single_path_tank_pump_valve_tank"


def _infer_single_path(config: PlantConfig) -> ContinuousPath | None:
    equipment_by_id = {item.id: item for item in config.equipment}
    model_by_id = {item.id: item.model_type for item in config.equipment}
    physical_edges = [
        (endpoint_object_id(connection.from_endpoint), endpoint_object_id(connection.to))
        for connection in config.connections
        if connection.type == "physical"
    ]

    pumps = [item for item in config.equipment if item.model_type == "centrifugal_pump_v1"]
    valves = [item for item in config.equipment if item.model_type == "control_valve_v1"]
    if not pumps or not valves:
        return None

    for pump in pumps:
        upstream_tanks = [
            equipment_by_id[source_id]
            for source_id, target_id in physical_edges
            if target_id == pump.id and model_by_id.get(source_id) == "tank_v1"
        ]
        downstream_valves = [
            equipment_by_id[target_id]
            for source_id, target_id in physical_edges
            if source_id == pump.id and model_by_id.get(target_id) == "control_valve_v1"
        ]
        for valve in downstream_valves:
            destination_tanks = [
                equipment_by_id[target_id]
                for source_id, target_id in physical_edges
                if source_id == valve.id and model_by_id.get(target_id) == "tank_v1"
            ]
            if upstream_tanks and destination_tanks:
                return ContinuousPath(
                    source_tank=upstream_tanks[0],
                    pump=pump,
                    valve=valve,
                    destination_tank=destination_tanks[0],
                )

    if len(pumps) == 1 and len(valves) == 1:
        tanks = [item for item in config.equipment if item.model_type == "tank_v1"]
        if len(tanks) >= 2:
            return ContinuousPath(source_tank=tanks[0], pump=pumps[0], valve=valves[0], destination_tank=tanks[-1])
    return None


def _tank_outlet_demand(tank: EquipmentConfig) -> float:
    if "outlet_demand_m3_s" in tank.parameters:
        return float(tank.parameters["outlet_demand_m3_s"])
    if "outlet_demand_m3h" in tank.parameters:
        return float(tank.parameters["outlet_demand_m3h"]) / 3600.0
    return 0.006


def _volume_to_level(tank: EquipmentConfig, volume_m3: float) -> float:
    if "tank_area_m2" in tank.parameters:
        area = float(tank.parameters["tank_area_m2"])
        return volume_m3 / area if area > 0 else 0.0
    capacity = float(tank.parameters.get("capacity_m3", 0.0))
    max_level = float(tank.parameters.get("max_level_m", 5.0))
    return (volume_m3 / capacity * max_level) if capacity > 0 else 0.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
