"""Simple time-based scenario action manager."""

from dataclasses import dataclass, field

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, ScenarioActionConfig, ScenarioConfig, endpoint_object_id


@dataclass(slots=True)
class ScenarioManager:
    """Applies configured scenario actions once when their scheduled time is due."""

    scenario: ScenarioConfig | None = None
    _executed_indices: set[int] = field(default_factory=set)

    def apply_due_actions(
        self,
        state: RuntimeState,
        config: PlantConfig,
        current_time_s: float,
    ) -> list[ScenarioActionConfig]:
        """Apply all scenario actions due at or before the current time."""
        if self.scenario is None:
            return []

        fired: list[ScenarioActionConfig] = []
        for index, action in enumerate(self.scenario.actions):
            if index in self._executed_indices or action.at_s > current_time_s:
                continue
            self._apply_action(action, state, config)
            self._executed_indices.add(index)
            fired.append(action)

        if fired:
            state.diagnostics.setdefault("scenario_actions", []).extend(
                {
                    "scenario_id": self.scenario.id,
                    "at_s": action.at_s,
                    "type": action.type,
                    "target": action.target,
                    "value": action.value,
                }
                for action in fired
            )
        return fired

    def _apply_action(self, action: ScenarioActionConfig, state: RuntimeState, config: PlantConfig) -> None:
        if action.type == "set_truth":
            _require_target(action)
            state.set_truth(action.target, action.value)
            return
        if action.type == "set_parameter":
            _set_parameter(config, action)
            return
        if action.type == "set_sensor_quality":
            _require_target(action)
            state.diagnostics[f"sensor_quality.{action.target}"] = str(action.value)
            return
        if action.type == "set_sensor_bias":
            _require_target(action)
            state.diagnostics[f"sensor_bias.{action.target}"] = float(action.value or 0.0)
            return
        if action.type == "set_sensor_drift":
            _require_target(action)
            state.diagnostics[f"sensor_drift.{action.target}"] = float(action.value or 0.0)
            return
        if action.type == "valve_stuck":
            _require_target(action)
            stuck_value = float(action.value or 0.0)
            state.diagnostics[f"fault.valve_stuck.{action.target}"] = stuck_value
            valve_id = _resolve_valve_id(config, action.target)
            if valve_id:
                state.diagnostics[f"fault.valve_stuck.{valve_id}"] = stuck_value
                state.set_truth(f"{valve_id}.opening_actual", stuck_value)
            return
        raise ValueError(f"Unsupported scenario action type: {action.type}")


def _require_target(action: ScenarioActionConfig) -> None:
    if not action.target:
        raise ValueError(f"Scenario action requires target: {action.type}")


def _set_parameter(config: PlantConfig, action: ScenarioActionConfig) -> None:
    _require_target(action)
    parts = action.target.split(".")
    if len(parts) != 3 or parts[0] != "equipment":
        raise ValueError(f"Unsupported set_parameter target: {action.target}")
    _, equipment_id, parameter_name = parts
    for equipment in config.equipment:
        if equipment.id == equipment_id:
            equipment.parameters[parameter_name] = action.value
            return
    raise ValueError(f"Unknown equipment for set_parameter: {equipment_id}")


def _resolve_valve_id(config: PlantConfig, target: str | None) -> str | None:
    if not target:
        return None
    for actuator in config.actuators:
        if actuator.id == target:
            return endpoint_object_id(actuator.actuates)
    if any(equipment.id == target and equipment.model_type == "control_valve_v1" for equipment in config.equipment):
        return target
    return None
