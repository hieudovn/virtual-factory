"""Data models for the WTP Simulator."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SignalType(Enum):
    MV = "manipulated_variable"
    DV = "disturbance_variable"
    PV = "process_variable"
    KPI = "key_performance_indicator"


@dataclass
class SignalMeta:
    signal_id: str
    signal_name: str
    display_name: str
    asset_id: str
    area_id: str
    signal_type: SignalType
    data_type: str  # float | bool | int | string
    engineering_unit: str
    default_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 100.0
    depends_on: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class MVConfig:
    signal_id: str
    default_sp: float
    min_sp: float
    max_sp: float
    slew_rate: float
    accuracy_pct: float


@dataclass
class DVConfig:
    signal_id: str
    pattern: str  # "random_walk" | "sine"
    baseline: float
    amplitude: float
    noise_std: float
    bounds_min: float
    bounds_max: float
    frequency_hz: float = 0.001


@dataclass
class Measurement:
    timestamp: str
    signal_id: str
    value: float | bool | int
    quality: str  # "GOOD" | "UNCERTAIN" | "BAD"
    source: str = "wtp-sim-01"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "signal_id": self.signal_id,
            "value": self.value,
            "quality": self.quality,
            "source": self.source,
        }


@dataclass
class SimulationState:
    time_s: float = 0.0
    step_count: int = 0
    mv_values: dict[str, float] = field(default_factory=dict)
    dv_values: dict[str, float] = field(default_factory=dict)
    pv_values: dict[str, float] = field(default_factory=dict)
    kpi_values: dict[str, float | bool] = field(default_factory=dict)
    dv_state: dict[str, dict] = field(default_factory=dict)
    mv_actuator_state: dict[str, float] = field(default_factory=dict)

    # Filter state
    filter_dp_101_accum: float = 20.0
    filter_dp_102_accum: float = 15.0
    backwash_101_remaining: float = 0.0
    backwash_102_remaining: float = 0.0

    # Cumulative totals
    total_energy_kwh: float = 0.0
    total_water_m3: float = 0.0
    total_waste_m3: float = 0.0
    compliance_frames: int = 0
    total_frames: int = 0
    outlet_compliance_previous: bool = False
    compliance_rate: float = 1.0

    # Degradation tracking
    rwp101_vibration_accum: float = 0.5
    rwp102_vibration_accum: float = 0.3
    hsp101_winding_accum: float = 25.0
    hsp102_winding_accum: float = 25.0
    hsp101_bearing_vib_accum: float = 0.5
    hsp102_bearing_vib_accum: float = 0.3


def compute_quality(value: float, min_val: float, max_val: float, margin: float = 0.1) -> str:
    """Compute quality flag based on bounds proximity."""
    if value < min_val or value > max_val:
        return "BAD"
    range_size = max_val - min_val
    if range_size > 0:
        near_min = value < min_val + margin * range_size
        near_max = value > max_val - margin * range_size
        if near_min or near_max:
            return "UNCERTAIN"
    return "GOOD"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


_shared_rng = random.Random()


def seeded_rng(seed: int | None = None) -> random.Random:
    if seed is not None:
        return random.Random(seed)
    return _shared_rng
