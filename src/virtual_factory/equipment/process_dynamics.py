"""Continuous-process dynamics with pump curve, valve Cv, pipe resistance.

Models a tank-pump-valve-tank path using:
- Centrifugal pump curve (quadratic head-vs-flow).
- Control-valve Cv equation (SI conversion from US Cv definition).
- Pipe resistance (simple K*Q² loss model).
- Source-tank depletion so pump suction conditions change over time.
- System solve to find the operating flow where pump head equals system head.

Future versions should generalise this into a graph-based hydraulic solver that
uses ports, units, equipment curves, and conservation checks across subgraphs.
"""

from dataclasses import dataclass

from virtual_factory.balance.stream import Stream
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig, PlantConfig, endpoint_object_id

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G_STANDARD = 9.81  # m/s²

# Cv (US definition): flow in US GPM at 1 psi ΔP for water.
#   Q_gpm = Cv · sqrt(ΔP_psi / SG)
# SI conversion helpers:
_GPM_TO_M3S = 6.309_019_64e-5  # 1 US GPM → m³/s
_PSI_TO_PA = 6_894.757  # 1 psi → Pa

# When a valve is fully closed (opening ≈ 0) we cap the effective opening
# fraction so the resistance does not become infinite.
_MIN_OPENING_FRACTION = 1e-6

# Default pipe resistance coefficient [Pa / (m³/s)²] for a short, straight
# connection when no explicit pipe data is configured.  Corresponds roughly
# to 10 m of DN 50 pipe with a friction factor of 0.02.
_DEFAULT_PIPE_RESISTANCE = 5.0e8


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContinuousPath:
    """Inferred single-path process section for MVP dynamics."""

    source_tank: EquipmentConfig
    pump: EquipmentConfig
    valve: EquipmentConfig
    destination_tank: EquipmentConfig


@dataclass(frozen=True, slots=True)
class _PumpCurve:
    """Quadratic centrifugal-pump curve: H(Q) = H_shutoff - β · Q²."""

    shutoff_head_m: float
    beta_s2_m5: float  # (H_shutoff - H_rated) / Q_rated²


@dataclass(frozen=True, slots=True)
class _ValveCv:
    """Convert US Cv and opening fraction into SI resistance K [Pa/(m³/s)²]."""

    cv_full: float
    density_kg_m3: float

    def resistance(self, opening_fraction: float) -> float:
        """K_valve [Pa/(m³/s)²] at the given opening fraction.

        Derivation
        ----------
        US definition:  Q_gpm = Cv · sqrt(ΔP_psi / SG)
        → ΔP_psi = (Q_gpm / Cv)² · SG
        → ΔP_Pa  = (Q_m3s / (Cv · k1))² · k2 · SG   where k1 = _GPM_TO_M3S,
                                                           k2 = _PSI_TO_PA
        → K = ΔP_Pa / Q_m3s² = k2 · SG / (Cv² · k1²)
        """
        sg = self.density_kg_m3 / 997.0  # specific gravity vs water at 25 °C
        k_full = _PSI_TO_PA * sg / (self.cv_full**2 * _GPM_TO_M3S**2)
        effective_fraction = max(opening_fraction, _MIN_OPENING_FRACTION)
        return k_full / (effective_fraction**2)


# ---------------------------------------------------------------------------
# Main update entry point
# ---------------------------------------------------------------------------


def update_continuous_process(config: PlantConfig, state: RuntimeState, dt_s: float) -> None:
    """Advance a tank-pump-valve-tank continuous process by dt_s seconds."""
    path = _infer_single_path(config)
    if path is None:
        state.diagnostics["process_dynamics"] = "No tank-pump-valve-tank path inferred."
        return

    density = float(config.medium.density_kg_m3)
    pump_running = bool(state.get_truth(f"{path.pump.id}.running", True))
    opening_percent = float(state.get_truth(f"{path.valve.id}.opening_actual", 0.0))
    opening_fraction = _clamp(opening_percent / 100.0, 0.0, 1.0)

    # --- apply degradation / fault modifiers ---
    pump_deg_pct = _fault_float(state, f"fault.pump_degradation.{path.pump.id}", None)
    valve_cv_loss_pct = _fault_float(state, f"fault.valve_cv_loss.{path.valve.id}", None)
    pipe_fouling_factor = _fault_float(state, f"fault.pipe_fouling.{path.pump.id}", None)
    # Sensor drift is handled in base_sensor.py, not here

    # --- build component models (with degradation applied) ---
    pump = _build_pump_curve(path.pump, degradation_pct=pump_deg_pct)
    cv_nominal = float(path.valve.parameters.get("cv", 1.0))
    if valve_cv_loss_pct is not None:
        cv_nominal *= _clamp(1.0 - valve_cv_loss_pct / 100.0, 0.0, 1.0)
    valve_cv = _ValveCv(cv_full=cv_nominal, density_kg_m3=density)
    pipe_k = float(path.pump.parameters.get("pipe_resistance", _DEFAULT_PIPE_RESISTANCE))
    if pipe_fouling_factor is not None:
        pipe_k *= max(pipe_fouling_factor, 1.0)

    # --- source tank current state ---
    src_capacity = float(path.source_tank.parameters.get("capacity_m3", 0.0))
    src_volume = float(state.get_truth(f"{path.source_tank.id}.volume_true", 0.0))
    src_level = float(state.get_truth(f"{path.source_tank.id}.level_true", 0.0))

    # --- destination tank current state ---
    dst_capacity = float(path.destination_tank.parameters.get("capacity_m3", 0.0))
    dst_volume = float(state.get_truth(f"{path.destination_tank.id}.volume_true", 0.0))
    qout_m3_s = _tank_outlet_demand(path.destination_tank)

    # --- static head (source → destination elevation difference) ---
    # Positive means the pump must lift fluid; negative means gravity assists.
    static_head_m = _tank_level(path.destination_tank, dst_volume) - src_level

    # --- solve operating flow ---
    if not pump_running or src_volume <= 0.0:
        flow_m3_s = 0.0
        discharge_pressure_kpa = 0.0
    else:
        flow_m3_s = _solve_flow(pump, valve_cv, pipe_k, opening_fraction, density, static_head_m)
        # Pump discharge pressure at operating point
        pump_head_m = pump.shutoff_head_m - pump.beta_s2_m5 * flow_m3_s**2
        discharge_pressure_kpa = max(0.0, pump_head_m * G_STANDARD * density / 1000.0)

    # --- source tank depletion ---
    src_next_volume = _clamp(src_volume - flow_m3_s * dt_s, 0.0, src_capacity)
    src_next_level = _tank_level(path.source_tank, src_next_volume)
    # If pump is running but source is dry, pump cavitates → no flow
    if src_volume <= 0.0 and pump_running:
        flow_m3_s = 0.0
        discharge_pressure_kpa = 0.0

    # --- destination tank fill ---
    dst_next_volume = _clamp(dst_volume + (flow_m3_s - qout_m3_s) * dt_s, 0.0, dst_capacity)
    dst_next_level = _tank_level(path.destination_tank, dst_next_volume)

    # --- write truth ---
    state.set_truth(f"{path.source_tank.id}.volume_true", src_next_volume)
    state.set_truth(f"{path.source_tank.id}.level_true", src_next_level)
    state.set_truth(f"{path.source_tank.id}.outflow_true", flow_m3_s)
    state.set_truth(f"{path.pump.id}.discharge_pressure_true", discharge_pressure_kpa)
    state.set_truth(f"{path.valve.id}.outlet.flow_true", flow_m3_s)
    state.set_truth(f"{path.valve.id}.outlet.mass_flow_true", flow_m3_s * density)
    state.set_truth(f"{path.destination_tank.id}.inflow_true", flow_m3_s)
    state.set_truth(f"{path.destination_tank.id}.outflow_true", qout_m3_s)
    state.set_truth(f"{path.destination_tank.id}.volume_true", dst_next_volume)
    state.set_truth(f"{path.destination_tank.id}.level_true", dst_next_level)

    # --- write material streams (one per physical connection) ---
    medium_id = config.medium.id
    for connection in config.connections:
        if connection.type != "physical":
            continue
        conn_id = connection.id
        # Determine flow on this connection from the path
        if conn_id is None:
            continue
        # C001: T101→P101, C002: P101→V101, C003: V101→T102
        # All carry the same flow in single-path MVP
        state.set_stream(conn_id, Stream(
            medium_id=medium_id,
            flow_rate_m3_s=flow_m3_s,
            density_kg_m3=density,
        ))

    state.diagnostics["process_dynamics"] = "tank_pump_valve_tank_with_pump_curve_and_cv"


# ---------------------------------------------------------------------------
# Hydraulic sub-models
# ---------------------------------------------------------------------------


def _build_pump_curve(pump: EquipmentConfig, degradation_pct: float | None = None) -> _PumpCurve:
    """Build quadratic pump curve from rated duty point.

    If *degradation_pct* is provided, the rated head is reduced by that
    percentage to simulate wear, cavitation damage, or speed reduction.

    Shutoff head is estimated at 1.25 × rated head, a typical value for
    end-suction centrifugal pumps.
    """
    q_rated = float(pump.parameters.get("rated_flow_m3_s", 0.01))
    h_rated = float(pump.parameters.get("rated_head_m", 20.0))
    if degradation_pct is not None:
        h_rated *= _clamp(1.0 - degradation_pct / 100.0, 0.0, 1.0)
    shutoff = 1.25 * h_rated
    beta = (shutoff - h_rated) / (q_rated**2) if q_rated > 0 else 0.0
    return _PumpCurve(shutoff_head_m=shutoff, beta_s2_m5=beta)


def _solve_flow(
    pump: _PumpCurve,
    valve_cv: _ValveCv,
    pipe_k: float,
    opening_fraction: float,
    density: float,
    static_head_m: float,
) -> float:
    """Solve for operating flow where pump head equals system head.

    Pump:     ρ·g·H_pump(Q) = ρ·g·(H_shutoff - β·Q²)
    System:   ρ·g·H_static + K_total·Q²
             where K_total = K_valve(opening) + K_pipe

    Equating and solving for Q:
        Q = sqrt(ρ·g·(H_shutoff - H_static) / (ρ·g·β + K_total))

    Returns 0 when pump cannot overcome static head.
    """
    if pump.shutoff_head_m <= static_head_m:
        return 0.0

    rho_g = density * G_STANDARD
    k_valve = valve_cv.resistance(opening_fraction)
    k_total = k_valve + pipe_k
    numerator = rho_g * (pump.shutoff_head_m - static_head_m)
    denominator = rho_g * pump.beta_s2_m5 + k_total

    if denominator <= 0.0:
        return 0.0

    return (numerator / denominator) ** 0.5


# ---------------------------------------------------------------------------
# Graph inference
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tank helpers
# ---------------------------------------------------------------------------


def _tank_outlet_demand(tank: EquipmentConfig) -> float:
    if "outlet_demand_m3_s" in tank.parameters:
        return float(tank.parameters["outlet_demand_m3_s"])
    if "outlet_demand_m3h" in tank.parameters:
        return float(tank.parameters["outlet_demand_m3h"]) / 3600.0
    return 0.006


def _tank_level(tank: EquipmentConfig, volume_m3: float) -> float:
    """Return level in metres for a given volume."""
    if "tank_area_m2" in tank.parameters:
        area = float(tank.parameters["tank_area_m2"])
        return volume_m3 / area if area > 0 else 0.0
    capacity = float(tank.parameters.get("capacity_m3", 0.0))
    max_level = float(tank.parameters.get("max_level_m", 5.0))
    return (volume_m3 / capacity * max_level) if capacity > 0 else 0.0


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _fault_float(state: RuntimeState, key: str, default: float | None = None) -> float | None:
    """Read a numeric fault/diagnostic value from state.

    Returns ``default`` if the key is absent or not convertible to float.
    """
    raw = state.diagnostics.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default
