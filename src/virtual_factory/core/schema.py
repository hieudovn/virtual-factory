"""Typed plant configuration schema and validation rules."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

INDUSTRIAL_PUBLISH_CATEGORIES = {
    "industrial_signal",
    "controller_signal",
    "actuator_feedback",
    "industrial_event",
}


def endpoint_object_id(endpoint: str) -> str:
    """Return the object id portion of an endpoint path.

    Example: ``T101.outlet`` becomes ``T101``.
    """
    return endpoint.split(".", maxsplit=1)[0]


class PlantMetadata(BaseModel):
    """Top-level plant identity and classification."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    description: str | None = None


class MediumConfig(BaseModel):
    """Physical medium metadata used by balance and equipment models."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    density_kg_m3: float
    viscosity_pa_s: float
    specific_heat_j_kg_k: float


class EquipmentConfig(BaseModel):
    """Configured equipment instance."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    model_type: str = Field(min_length=1)
    display_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ConnectionConfig(BaseModel):
    """Physical or logical connection between configured endpoints."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    type: str = Field(default="physical", min_length=1)
    from_endpoint: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    medium: str | None = None


class SensorConfig(BaseModel):
    """Configured sensor that converts physical truth into a measured signal."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    model_type: str = Field(min_length=1)
    measures: str = Field(min_length=1)
    output_signal: str = Field(min_length=1)
    display_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ControllerConfig(BaseModel):
    """Configured controller that consumes measured signals."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    model_type: str = Field(min_length=1)
    pv_signal: str = Field(min_length=1)
    output_signal: str = Field(min_length=1)
    display_name: str | None = None
    setpoint: float | int | str | None = None
    scan_time_s: float | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ActuatorConfig(BaseModel):
    """Configured actuator that maps command signals to equipment actions."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    model_type: str = Field(min_length=1)
    command_signal: str = Field(min_length=1)
    actuates: str = Field(min_length=1)
    feedback_signal: str | None = None
    display_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class SignalConfig(BaseModel):
    """Configured industrial, controller, actuator, event, or internal signal."""

    model_config = ConfigDict(extra="allow")

    category: str = Field(min_length=1)
    publish: bool
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)


class OutputPolicyConfig(BaseModel):
    """Configured output policy for protocol publication."""

    model_config = ConfigDict(extra="allow")

    mode: str = Field(min_length=1)
    publish_categories: list[str] = Field(default_factory=list)
    forbidden_categories: list[str] = Field(default_factory=list)
    rule: str | None = None


class ScenarioActionConfig(BaseModel):
    """One time-based scenario action."""

    model_config = ConfigDict(extra="allow")

    at_s: float
    type: str = Field(min_length=1)
    target: str | None = None
    value: float | int | str | bool | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioConfig(BaseModel):
    """Standalone scenario configuration."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    description: str | None = None
    actions: list[ScenarioActionConfig] = Field(default_factory=list)


class PlantConfig(BaseModel):
    """Validated plant configuration loaded from YAML/JSON."""

    model_config = ConfigDict(extra="allow")

    plant: PlantMetadata
    medium: MediumConfig
    equipment: list[EquipmentConfig]
    connections: list[ConnectionConfig]
    sensors: list[SensorConfig] = Field(default_factory=list)
    controllers: list[ControllerConfig] = Field(default_factory=list)
    actuators: list[ActuatorConfig] = Field(default_factory=list)
    signals: dict[str, SignalConfig]
    output_policy: OutputPolicyConfig

    @model_validator(mode="after")
    def validate_relationships(self) -> "PlantConfig":
        """Validate graph relationships and industrial publication boundaries."""
        self._validate_unique_object_ids()
        equipment_ids = {item.id for item in self.equipment}
        signal_names = set(self.signals)

        self._validate_connection_endpoints(equipment_ids)
        self._validate_sensor_links(equipment_ids, signal_names)
        self._validate_controller_links(signal_names)
        self._validate_actuator_links(equipment_ids, signal_names)
        self._validate_output_policy()

        return self

    def _validate_unique_object_ids(self) -> None:
        object_ids: list[str] = [
            *(item.id for item in self.equipment),
            *(item.id for item in self.sensors),
            *(item.id for item in self.controllers),
            *(item.id for item in self.actuators),
        ]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item_id in object_ids:
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate object ids are not allowed: {duplicate_list}")

    def _validate_connection_endpoints(self, equipment_ids: set[str]) -> None:
        for connection in self.connections:
            for endpoint in (connection.from_endpoint, connection.to):
                object_id = endpoint_object_id(endpoint)
                if object_id not in equipment_ids:
                    raise ValueError(f"Connection endpoint object does not exist: {endpoint}")

    def _validate_sensor_links(self, equipment_ids: set[str], signal_names: set[str]) -> None:
        for sensor in self.sensors:
            if sensor.output_signal not in signal_names:
                raise ValueError(f"Sensor {sensor.id} outputs unknown signal: {sensor.output_signal}")
            measured_object_id = endpoint_object_id(sensor.measures)
            if measured_object_id not in equipment_ids:
                raise ValueError(f"Sensor {sensor.id} measures unknown object: {sensor.measures}")

    def _validate_controller_links(self, signal_names: set[str]) -> None:
        for controller in self.controllers:
            if _looks_like_true_state(controller.pv_signal):
                raise ValueError(
                    f"Controller {controller.id} pv_signal must be a measured signal, "
                    f"not true physical state: {controller.pv_signal}"
                )
            if controller.pv_signal not in signal_names:
                raise ValueError(f"Controller {controller.id} references unknown pv_signal: {controller.pv_signal}")
            if controller.output_signal not in signal_names:
                raise ValueError(
                    f"Controller {controller.id} outputs unknown signal: {controller.output_signal}"
                )

    def _validate_actuator_links(self, equipment_ids: set[str], signal_names: set[str]) -> None:
        for actuator in self.actuators:
            if actuator.command_signal not in signal_names:
                raise ValueError(f"Actuator {actuator.id} references unknown command_signal: {actuator.command_signal}")
            if actuator.feedback_signal and actuator.feedback_signal not in signal_names:
                raise ValueError(f"Actuator {actuator.id} references unknown feedback_signal: {actuator.feedback_signal}")
            actuated_object_id = endpoint_object_id(actuator.actuates)
            if actuated_object_id not in equipment_ids:
                raise ValueError(f"Actuator {actuator.id} actuates unknown object: {actuator.actuates}")

    def _validate_output_policy(self) -> None:
        policy_categories = set(self.output_policy.publish_categories)
        if "internal_truth" in policy_categories:
            raise ValueError("internal_truth is not allowed in output_policy.publish_categories")

        if self.output_policy.mode == "industrial":
            invalid_categories = policy_categories - INDUSTRIAL_PUBLISH_CATEGORIES
            if invalid_categories:
                invalid_list = ", ".join(sorted(invalid_categories))
                raise ValueError(f"Industrial publish category is not allowed: {invalid_list}")

            for signal_name, signal in self.signals.items():
                if signal.category == "internal_truth" and signal.publish:
                    raise ValueError(f"Internal truth signal cannot be published in industrial mode: {signal_name}")
                if signal.publish and signal.category not in policy_categories:
                    raise ValueError(
                        f"Published signal {signal_name} category is not in output policy: {signal.category}"
                    )


def _looks_like_true_state(value: str) -> bool:
    """Return whether a controller input looks like a physical truth endpoint."""
    lowered = value.lower()
    return "." in value or lowered.endswith("_true") or "_true." in lowered
