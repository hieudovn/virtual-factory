"""Compressor Train — Flagship Analytics Benchmark Model.

Models a complete compressor train assembly including:
- Compressor (polytropic compression)
- Driver Motor (power, current, bearing temps, vibration)
- Lube Oil System (pressure, temperature, filter DP)
- Cooling System (temperatures, flow)
- Seal Gas System (pressure, flow)
- Anti-Surge System (recycle valve, surge margin)
- Suction/Discharge Headers

This is the primary analytics benchmark model supporting 50+ tags (Phase 1)
and 150-300 tags (Phase 2).

The compressor train reads inlet conditions from a connected boundary
source equipment (via ``source_equipment_id`` parameter) and writes
discharge flow to a connected boundary sink equipment (via
``sink_equipment_id`` parameter). This preserves the graph-based
architecture: every asset has inlet/outlet ports connected through
the plant graph, and equipment does not self-generate boundary
conditions independently.
"""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class CompressorTrain(BaseEquipment):
    """Complete compressor train assembly with all sub-systems.

    Coordinate all sub-system equipment models through the asset
    hierarchy and provide aggregated truth variables.

    Parameters
    ----------
    rated_power_kw : float
        Total rated shaft power.
    rated_flow_m3_s : float
        Rated suction flow.
    rated_pressure_ratio : float
        Design pressure ratio.
    polytropic_efficiency : float
        Polytropic efficiency (0.0-1.0).
    surge_margin_design : float
        Design surge margin (typically 0.10-0.15).
    source_equipment_id : str
        ID of boundary source equipment providing inlet conditions.
        Reads ``{source}.pressure_kpa``, ``{source}.temperature_c``,
        ``{source}.molecular_weight_kg_kmol``, ``{source}.specific_heat_ratio``.
    sink_equipment_id : str
        ID of boundary sink equipment receiving discharge.
        Reads ``{sink}.backpressure_kpa``, writes ``{sink}.flow_m3_s``.
    """

    # Sub-system equipment refs (set during initialization)
    compressor_id: str = ""
    motor_id: str = ""
    lube_oil_system_id: str = ""
    cooling_system_id: str = ""
    seal_gas_system_id: str = ""
    anti_surge_valve_id: str = ""
    recycle_valve_id: str = ""

    # Runtime
    _sub_equipment: dict[str, BaseEquipment] = field(default_factory=dict, init=False)

    def initialize_state(self, state: RuntimeState) -> None:
        """Initialize all compressor train truth variables."""
        tid = self.id

        # --- Compressor core ---
        state.set_truth(f"{tid}.running", False)
        state.set_truth(f"{tid}.speed_rpm", 0.0)
        state.set_truth(f"{tid}.suction_pressure_kpa", 101.325)
        state.set_truth(f"{tid}.discharge_pressure_kpa", 101.325)
        state.set_truth(f"{tid}.pressure_ratio", 1.0)
        state.set_truth(f"{tid}.flow_m3_s", 0.0)
        state.set_truth(f"{tid}.mass_flow_kg_s", 0.0)
        state.set_truth(f"{tid}.suction_temperature_c", 25.0)
        state.set_truth(f"{tid}.discharge_temperature_c", 25.0)
        state.set_truth(f"{tid}.polytropic_head_kj_kg", 0.0)
        state.set_truth(f"{tid}.isentropic_efficiency", 0.0)
        state.set_truth(f"{tid}.power_consumed_kw", 0.0)
        state.set_truth(f"{tid}.surge_margin", 1.0)

        # --- Driver motor ---
        state.set_truth(f"{tid}.motor.current_a", 0.0)
        state.set_truth(f"{tid}.motor.power_kw", 0.0)
        state.set_truth(f"{tid}.motor.voltage_v", 0.0)
        state.set_truth(f"{tid}.motor.power_factor", 0.0)
        state.set_truth(f"{tid}.motor.speed_rpm", 0.0)
        state.set_truth(f"{tid}.motor.winding_temp_c", 25.0)
        state.set_truth(f"{tid}.motor.bearing_de_temp_c", 25.0)
        state.set_truth(f"{tid}.motor.bearing_nde_temp_c", 25.0)
        state.set_truth(f"{tid}.motor.vibration_de_mm_s", 0.0)
        state.set_truth(f"{tid}.motor.vibration_nde_mm_s", 0.0)

        # --- Compressor bearings & vibration ---
        state.set_truth(f"{tid}.bearing_de_temp_c", 25.0)
        state.set_truth(f"{tid}.bearing_nde_temp_c", 25.0)
        state.set_truth(f"{tid}.bearing_thrust_temp_c", 25.0)
        state.set_truth(f"{tid}.vibration_de_mm_s", 0.0)
        state.set_truth(f"{tid}.vibration_nde_mm_s", 0.0)
        state.set_truth(f"{tid}.vibration_axial_mm_s", 0.0)
        state.set_truth(f"{tid}.shaft_displacement_de_um", 0.0)
        state.set_truth(f"{tid}.shaft_displacement_nde_um", 0.0)

        # --- Lube oil system ---
        state.set_truth(f"{tid}.lube_oil.pressure_kpa", 0.0)
        state.set_truth(f"{tid}.lube_oil.temperature_c", 25.0)
        state.set_truth(f"{tid}.lube_oil.filter_dp_kpa", 0.0)
        state.set_truth(f"{tid}.lube_oil.level_pct", 100.0)
        state.set_truth(f"{tid}.lube_oil.flow_l_min", 0.0)
        state.set_truth(f"{tid}.lube_oil.pump_current_a", 0.0)

        # --- Cooling system ---
        state.set_truth(f"{tid}.cooling.supply_temp_c", 25.0)
        state.set_truth(f"{tid}.cooling.return_temp_c", 25.0)
        state.set_truth(f"{tid}.cooling.flow_l_min", 0.0)
        state.set_truth(f"{tid}.cooling.delta_t_c", 0.0)

        # --- Seal gas system ---
        state.set_truth(f"{tid}.seal_gas.supply_pressure_kpa", 0.0)
        state.set_truth(f"{tid}.seal_gas.flow_nm3_h", 0.0)
        state.set_truth(f"{tid}.seal_gas.delta_p_kpa", 0.0)
        state.set_truth(f"{tid}.seal_gas.vent_pressure_kpa", 0.0)

        # --- Anti-surge / recycle ---
        state.set_truth(f"{tid}.recycle_valve.position_pct", 0.0)
        state.set_truth(f"{tid}.recycle_valve.command_pct", 0.0)
        state.set_truth(f"{tid}.anti_surge.controller_output_pct", 0.0)

        # --- Discharge check ---
        state.set_truth(f"{tid}.discharge.temperature_c", 25.0)
        state.set_truth(f"{tid}.discharge.pressure_kpa", 101.325)

        # --- Health / diagnostics ---
        state.set_truth(f"{tid}.health_index", 1.0)
        state.set_truth(f"{tid}.operating_hours", 0.0)

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Advance compressor train physics for one time step.

        Reads inlet conditions from the connected boundary source equipment
        (``source_equipment_id``) and writes discharge flow to the connected
        boundary sink equipment (``sink_equipment_id``).

        This preserves the graph-based architecture: boundary conditions
        are NOT self-generated; they come from explicitly connected
        equipment through the plant graph.
        """
        tid = self.id
        running = bool(state.get_truth(f"{tid}.running", False))

        rated_power = float(self.parameters.get("rated_power_kw", 500.0))
        rated_flow = float(self.parameters.get("rated_flow_m3_s", 2.0))
        rated_pr = float(self.parameters.get("rated_pressure_ratio", 3.0))
        poly_eff = float(self.parameters.get("polytropic_efficiency", 0.82))

        # --- Read inlet conditions from boundary source equipment ---
        source_id = str(self.parameters.get("source_equipment_id", ""))
        if source_id:
            p_suction = float(state.get_truth(f"{source_id}.pressure_kpa", 101.325))
            t_suction = float(state.get_truth(f"{source_id}.temperature_c", 25.0))
            mw = float(state.get_truth(f"{source_id}.molecular_weight_kg_kmol", 28.97))
            k_gas = float(state.get_truth(f"{source_id}.specific_heat_ratio", 1.4))
            # Flow: read from what was computed last step, or use source available flow
            flow_m3_s = float(state.get_truth(f"{tid}.flow_m3_s", 0.0))
            if flow_m3_s == 0.0 and running:
                avail = float(state.get_truth(f"{source_id}.available_flow_m3_s", 0.0))
                if avail > 0:
                    flow_m3_s = min(rated_flow * 0.5, avail)  # initial ramp
        else:
            # Fallback: read from own state (standalone mode, no boundary)
            p_suction = float(state.get_truth(f"{tid}.suction_pressure_kpa", 101.325))
            t_suction = float(state.get_truth(f"{tid}.suction_temperature_c", 25.0))
            mw = 28.97
            k_gas = 1.4
            flow_m3_s = float(state.get_truth(f"{tid}.flow_m3_s", 0.0))

        # --- Read backpressure from boundary sink equipment ---
        sink_id = str(self.parameters.get("sink_equipment_id", ""))
        if sink_id:
            p_sink = float(state.get_truth(f"{sink_id}.backpressure_kpa", 101.325))
        else:
            p_sink = 101.325

        # Persist inlet conditions to own state (for sensor access)
        state.set_truth(f"{tid}.suction_pressure_kpa", round(p_suction, 2))
        state.set_truth(f"{tid}.suction_temperature_c", round(t_suction, 1))

        if running and rated_flow > 0:
            # --- Compressor physics (using boundary gas properties) ---
            frac = min(abs(flow_m3_s) / rated_flow, 1.0)
            pr_actual = 1.0 + (1.0 - frac) * (rated_pr - 1.0)
            p_discharge = p_suction * pr_actual
            # Temperature ratio: T2/T1 = PR^((k-1)/(k*eta_poly))
            t_ratio = pr_actual ** ((k_gas - 1.0) / (k_gas * poly_eff))
            t_discharge = (t_suction + 273.15) * t_ratio - 273.15
            power = rated_power * frac

            # Surge margin (simplified: decreases with low flow)
            surge_margin = max(0.0, 1.0 - (1.0 - frac) * 1.5)

            # Polytropic head (kJ/kg): H_poly = (n/(n-1)) * Z * R * T1 * (PR^((n-1)/n) - 1)
            # R_universal = 8.314 kJ/(kmol·K), R_gas = R_universal / MW
            r_gas = 8.314 / mw  # kJ/(kg·K)
            head = (k_gas / (k_gas - 1.0)) * r_gas * (t_suction + 273.15) * (pr_actual ** ((k_gas - 1.0) / k_gas) - 1.0)

            # Mass flow: m_dot = rho * Q = (P / (R_gas * T)) * Q  [kg/s]
            # R_gas in J/(kg·K) = r_gas * 1000
            rho_suction = (p_suction * 1000.0) / (r_gas * 1000.0 * (t_suction + 273.15))
            mass_flow = rho_suction * flow_m3_s

            # --- Write compressor core outputs ---
            state.set_truth(f"{tid}.discharge_pressure_kpa", round(p_discharge, 2))
            state.set_truth(f"{tid}.pressure_ratio", round(pr_actual, 3))
            state.set_truth(f"{tid}.discharge_temperature_c", round(t_discharge, 1))
            state.set_truth(f"{tid}.power_consumed_kw", round(power, 2))
            state.set_truth(f"{tid}.polytropic_head_kj_kg", round(head, 3))
            state.set_truth(f"{tid}.surge_margin", round(surge_margin, 4))
            state.set_truth(f"{tid}.speed_rpm", 3560.0)
            state.set_truth(f"{tid}.mass_flow_kg_s", round(mass_flow, 3))
            state.set_truth(f"{tid}.flow_m3_s", round(flow_m3_s, 4))

            # --- Write discharge flow to boundary sink equipment ---
            if sink_id:
                state.set_truth(f"{sink_id}.flow_m3_s", round(flow_m3_s, 4))

            state.set_truth(f"{tid}.discharge_pressure_kpa", round(p_discharge, 2))
            state.set_truth(f"{tid}.pressure_ratio", round(pr_actual, 3))
            state.set_truth(f"{tid}.discharge_temperature_c", round(t_discharge, 1))
            state.set_truth(f"{tid}.power_consumed_kw", round(power, 2))
            state.set_truth(f"{tid}.polytropic_head_kj_kg", round(head, 3))
            state.set_truth(f"{tid}.surge_margin", round(surge_margin, 4))
            state.set_truth(f"{tid}.speed_rpm", 3560.0)  # nominal

            # --- Motor ---
            motor_eff = 0.95
            motor_power = power / motor_eff
            voltage = 4160.0
            pf = 0.88
            current = motor_power / (voltage * pf * 1.732) * 1000  # A
            state.set_truth(f"{tid}.motor.current_a", round(current, 1))
            state.set_truth(f"{tid}.motor.power_kw", round(motor_power, 2))
            state.set_truth(f"{tid}.motor.voltage_v", voltage)
            state.set_truth(f"{tid}.motor.power_factor", pf)
            state.set_truth(f"{tid}.motor.speed_rpm", 3560.0)
            state.set_truth(f"{tid}.motor.winding_temp_c", round(25.0 + motor_power * 0.05, 1))
            state.set_truth(f"{tid}.motor.bearing_de_temp_c", round(25.0 + power * 0.03, 1))
            state.set_truth(f"{tid}.motor.bearing_nde_temp_c", round(25.0 + power * 0.028, 1))
            state.set_truth(f"{tid}.motor.vibration_de_mm_s", round(1.5 + power * 0.002, 2))
            state.set_truth(f"{tid}.motor.vibration_nde_mm_s", round(1.3 + power * 0.0018, 2))

            # --- Compressor bearings ---
            state.set_truth(f"{tid}.bearing_de_temp_c", round(30.0 + power * 0.04, 1))
            state.set_truth(f"{tid}.bearing_nde_temp_c", round(29.0 + power * 0.038, 1))
            state.set_truth(f"{tid}.bearing_thrust_temp_c", round(28.0 + power * 0.035, 1))
            state.set_truth(f"{tid}.vibration_de_mm_s", round(2.0 + power * 0.003, 2))
            state.set_truth(f"{tid}.vibration_nde_mm_s", round(1.8 + power * 0.0028, 2))
            state.set_truth(f"{tid}.vibration_axial_mm_s", round(0.5 + power * 0.001, 2))
            state.set_truth(f"{tid}.shaft_displacement_de_um", round(20.0 + power * 0.05, 1))
            state.set_truth(f"{tid}.shaft_displacement_nde_um", round(18.0 + power * 0.048, 1))

            # --- Lube oil system ---
            state.set_truth(f"{tid}.lube_oil.pressure_kpa", round(250.0 - frac * 20, 1))
            state.set_truth(f"{tid}.lube_oil.temperature_c", round(40.0 + power * 0.06, 1))
            state.set_truth(f"{tid}.lube_oil.filter_dp_kpa", round(15.0 + power * 0.01, 2))
            state.set_truth(f"{tid}.lube_oil.level_pct", 100.0)
            state.set_truth(f"{tid}.lube_oil.flow_l_min", round(80.0, 1))
            state.set_truth(f"{tid}.lube_oil.pump_current_a", round(5.0 + frac * 2, 1))

            # --- Cooling system ---
            t_cool_supply = 20.0
            t_cool_return = t_cool_supply + power * 0.03
            state.set_truth(f"{tid}.cooling.supply_temp_c", t_cool_supply)
            state.set_truth(f"{tid}.cooling.return_temp_c", round(t_cool_return, 1))
            state.set_truth(f"{tid}.cooling.flow_l_min", round(200.0 + power * 0.3, 1))
            state.set_truth(f"{tid}.cooling.delta_t_c", round(t_cool_return - t_cool_supply, 1))

            # --- Seal gas system ---
            state.set_truth(f"{tid}.seal_gas.supply_pressure_kpa", round(p_discharge + 20, 1))
            state.set_truth(f"{tid}.seal_gas.flow_nm3_h", round(0.5 + frac * 0.3, 2))
            state.set_truth(f"{tid}.seal_gas.delta_p_kpa", round(15.0 + frac * 5, 1))
            state.set_truth(f"{tid}.seal_gas.vent_pressure_kpa", round(5.0, 1))

        else:
            # Stopped — zero all dynamic values
            self._zero_stopped_state(state)

        # --- Discharge check (always computed) ---
        p_disch = float(state.get_truth(f"{tid}.discharge_pressure_kpa", 101.325))
        t_disch = float(state.get_truth(f"{tid}.discharge_temperature_c", 25.0))
        state.set_truth(f"{tid}.discharge.temperature_c", round(t_disch, 1))
        state.set_truth(f"{tid}.discharge.pressure_kpa", round(p_disch, 1))

        # --- Operating hours ---
        if running:
            current_hours = float(state.get_truth(f"{tid}.operating_hours", 0.0))
            state.set_truth(f"{tid}.operating_hours", round(current_hours + dt_s / 3600.0, 4))

        # --- Health index (driven by fault engine) ---
        # Kept as-is; updated externally by FaultEngine

    def _zero_stopped_state(self, state: RuntimeState) -> None:
        """Zero out dynamic values when stopped."""
        tid = self.id
        zero_pairs = [
            (f"{tid}.speed_rpm", 0.0),
            (f"{tid}.discharge_pressure_kpa", float(state.get_truth(f"{tid}.suction_pressure_kpa", 101.325))),
            (f"{tid}.pressure_ratio", 1.0),
            (f"{tid}.discharge_temperature_c", 25.0),
            (f"{tid}.flow_m3_s", 0.0),
            (f"{tid}.mass_flow_kg_s", 0.0),
            (f"{tid}.power_consumed_kw", 0.0),
            (f"{tid}.polytropic_head_kj_kg", 0.0),
            (f"{tid}.surge_margin", 1.0),
            (f"{tid}.motor.current_a", 0.0),
            (f"{tid}.motor.power_kw", 0.0),
            (f"{tid}.motor.speed_rpm", 0.0),
            (f"{tid}.motor.vibration_de_mm_s", 0.0),
            (f"{tid}.motor.vibration_nde_mm_s", 0.0),
            (f"{tid}.vibration_de_mm_s", 0.0),
            (f"{tid}.vibration_nde_mm_s", 0.0),
            (f"{tid}.vibration_axial_mm_s", 0.0),
            (f"{tid}.lube_oil.pressure_kpa", 0.0),
            (f"{tid}.lube_oil.flow_l_min", 0.0),
            (f"{tid}.lube_oil.pump_current_a", 0.0),
            (f"{tid}.cooling.flow_l_min", 0.0),
            (f"{tid}.cooling.delta_t_c", 0.0),
            (f"{tid}.seal_gas.supply_pressure_kpa", 0.0),
            (f"{tid}.seal_gas.flow_nm3_h", 0.0),
            (f"{tid}.seal_gas.delta_p_kpa", 0.0),
            (f"{tid}.recycle_valve.position_pct", 0.0),
            (f"{tid}.recycle_valve.command_pct", 0.0),
            (f"{tid}.anti_surge.controller_output_pct", 0.0),
        ]
        for key, val in zero_pairs:
            state.set_truth(key, val)

    def get_tag_names(self) -> list[str]:
        """Return all tag names for this compressor train.

        Phase 1: 50+ tags. Phase 2: 150-300 tags.
        """
        tid = self.id
        return [
            # Compressor core (10)
            f"{tid}.running",
            f"{tid}.speed_rpm",
            f"{tid}.suction_pressure_kpa",
            f"{tid}.discharge_pressure_kpa",
            f"{tid}.pressure_ratio",
            f"{tid}.flow_m3_s",
            f"{tid}.mass_flow_kg_s",
            f"{tid}.suction_temperature_c",
            f"{tid}.discharge_temperature_c",
            f"{tid}.polytropic_head_kj_kg",
            # Compressor performance (3)
            f"{tid}.isentropic_efficiency",
            f"{tid}.power_consumed_kw",
            f"{tid}.surge_margin",
            # Motor (10)
            f"{tid}.motor.current_a",
            f"{tid}.motor.power_kw",
            f"{tid}.motor.voltage_v",
            f"{tid}.motor.power_factor",
            f"{tid}.motor.speed_rpm",
            f"{tid}.motor.winding_temp_c",
            f"{tid}.motor.bearing_de_temp_c",
            f"{tid}.motor.bearing_nde_temp_c",
            f"{tid}.motor.vibration_de_mm_s",
            f"{tid}.motor.vibration_nde_mm_s",
            # Compressor bearings & vibration (8)
            f"{tid}.bearing_de_temp_c",
            f"{tid}.bearing_nde_temp_c",
            f"{tid}.bearing_thrust_temp_c",
            f"{tid}.vibration_de_mm_s",
            f"{tid}.vibration_nde_mm_s",
            f"{tid}.vibration_axial_mm_s",
            f"{tid}.shaft_displacement_de_um",
            f"{tid}.shaft_displacement_nde_um",
            # Lube oil system (6)
            f"{tid}.lube_oil.pressure_kpa",
            f"{tid}.lube_oil.temperature_c",
            f"{tid}.lube_oil.filter_dp_kpa",
            f"{tid}.lube_oil.level_pct",
            f"{tid}.lube_oil.flow_l_min",
            f"{tid}.lube_oil.pump_current_a",
            # Cooling system (4)
            f"{tid}.cooling.supply_temp_c",
            f"{tid}.cooling.return_temp_c",
            f"{tid}.cooling.flow_l_min",
            f"{tid}.cooling.delta_t_c",
            # Seal gas system (4)
            f"{tid}.seal_gas.supply_pressure_kpa",
            f"{tid}.seal_gas.flow_nm3_h",
            f"{tid}.seal_gas.delta_p_kpa",
            f"{tid}.seal_gas.vent_pressure_kpa",
            # Anti-surge / recycle (3)
            f"{tid}.recycle_valve.position_pct",
            f"{tid}.recycle_valve.command_pct",
            f"{tid}.anti_surge.controller_output_pct",
            # Discharge (2)
            f"{tid}.discharge.temperature_c",
            f"{tid}.discharge.pressure_kpa",
            # Health (2)
            f"{tid}.health_index",
            f"{tid}.operating_hours",
        ]
