"""Pydantic models for VF-2 simulation package entities.

These models match the PIM-generated package schema exactly (schema_version "1.0").
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ======================================================================
# Utilities
# ======================================================================


def clamp(value: float, lo: float, hi: float) -> float:
    """Constrain *value* to the inclusive range ``[lo, hi]``."""
    return max(lo, min(value, hi))


# ======================================================================
# Enums
# ======================================================================

class VF2ObjectType(str, Enum):
    CENTRIFUGAL_PUMP = "centrifugal_pump"
    STORAGE_TANK = "storage_tank"
    CONTROL_VALVE = "control_valve"
    GATE_VALVE = "gate_valve"
    CHECK_VALVE = "check_valve"
    ELECTRIC_MOTOR = "electric_motor"
    CENTRIFUGAL_COMPRESSOR = "centrifugal_compressor"
    HEAT_EXCHANGER = "heat_exchanger"
    FILTER_UNIT = "filter_unit"
    MIXER = "mixer"
    FAN = "fan"
    CONVEYOR = "conveyor"
    SKID_PACKAGE = "skid_package"
    PACKAGE_UNIT = "package_unit"
    GENERIC_EQUIPMENT = "generic_equipment"
    PIPE_LINE = "pipe_line"
    HEADER = "header"
    MCC_BOARD = "mcc_board"
    FEEDER_CIRCUIT = "feeder_circuit"
    TRANSFORMER = "transformer"


class VF2PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class VF2SignalDirection(str, Enum):
    VF2_INPUT = "VF2_INPUT"
    VF2_OUTPUT = "VF2_OUTPUT"


class VF2SignalType(str, Enum):
    STATUS = "status"
    MEASUREMENT = "measurement"
    ALARM = "alarm"
    SETPOINT = "setpoint"
    FEEDBACK = "feedback"


# ======================================================================
# Source / Provenance
# ======================================================================

class VF2ObjectSource(BaseModel):
    generated_from: str = "PIM_KG"
    model_version: str = "PIM-PH04-v0.1"
    canonical_id: str


class VF2SignalSource(BaseModel):
    generated_from: str = "PIM_KG"
    model_version: str = "PIM-PH04-v0.1"


# ======================================================================
# Ports
# ======================================================================

class VF2Port(BaseModel):
    port_id: str
    direction: VF2PortDirection
    connected_to_canonical_id: Optional[str] = None
    relation_type: Optional[str] = None
    relationship_id: Optional[str] = None
    note: Optional[str] = None


# ======================================================================
# Objects
# ======================================================================

class VF2SimulationObject(BaseModel):
    simulation_object_id: str = Field(..., pattern=r"^VF2-[A-Z0-9-]+$")
    canonical_id: str
    object_type: VF2ObjectType
    name: str
    unit_id: str
    status: str = "active"
    ports: list[VF2Port] = Field(default_factory=list)
    parameters: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    source: VF2ObjectSource


# ======================================================================
# Signals
# ======================================================================

class VF2SignalBehavior(BaseModel):
    signal_type: VF2SignalType
    update_rate_ms: int = 100
    initial_value: Optional[float | bool] = None


class VF2SimulationSignal(BaseModel):
    simulation_signal_id: str = Field(..., pattern=r"^VF2(\.[A-Z0-9_]+){2,8}$")
    canonical_tag_id: Optional[str] = None
    canonical_instrument_id: Optional[str] = None
    canonical_asset_id: str
    name: str
    data_type: str = "float64"
    engineering_unit: Optional[str] = None
    direction: VF2SignalDirection
    behavior: VF2SignalBehavior
    source: VF2SignalSource = Field(default_factory=lambda: VF2SignalSource())


# ======================================================================
# Topology
# ======================================================================

class VF2ProcessEdge(BaseModel):
    from_simulation_object_id: str = Field(..., alias="from")
    to_simulation_object_id: str = Field(..., alias="to")
    relation_type: str
    relationship_id: Optional[str] = None
    projection_only: bool = False
    note: Optional[str] = None

    model_config = {"populate_by_name": True}


class VF2Topology(BaseModel):
    process_edges: list[VF2ProcessEdge] = Field(default_factory=list)
    electrical_edges: list[VF2ProcessEdge] = Field(default_factory=list)


# ======================================================================
# Scenarios
# ======================================================================

class VF2ExpectedEffect(BaseModel):
    signal_id: str = ""
    expected_change: str = ""


class VF2Scenario(BaseModel):
    scenario_id: str
    scenario_type: str
    description: Optional[str] = ""
    trigger_asset_id: Optional[str] = None
    trigger_simulation_object_id: Optional[str] = None
    affected_assets: list[str] = Field(default_factory=list)
    affected_signals: list[str] = Field(default_factory=list)
    affected_simulation_object_ids: list[str] = Field(default_factory=list)
    affected_simulation_signal_ids: list[str] = Field(default_factory=list)
    expected_effects: list[VF2ExpectedEffect] = Field(default_factory=list)
    impact_path_source: Optional[str] = None
    impact_path_length: int = 0


# ======================================================================
# Validation Rules
# ======================================================================

class VF2ValidationRule(BaseModel):
    rule_id: str
    rule_name: str
    description: Optional[str] = ""
    severity: str = "error"
    applies_to: str = ""


# ======================================================================
# Source Model
# ======================================================================

class VF2SourceModel(BaseModel):
    system: str = "PIM"
    model_version: str = "PIM-PH04-v0.1"
    generated_at: str
    unit_id: str
    unit_name: str


# ======================================================================
# Top-Level Package
# ======================================================================

class VF2Package(BaseModel):
    package_id: str
    package_type: str = "vf2_simulation_package"
    schema_version: str = "1.0"
    source_model: VF2SourceModel
    objects: list[VF2SimulationObject]
    signals: list[VF2SimulationSignal]
    topology: VF2Topology
    scenarios: list[VF2Scenario]
    validation_rules: list[VF2ValidationRule] = Field(default_factory=list)
