"""Simulation Loop — 8-stage orchestrator for the WTP Simulator.

Follows the exact MV→PV→KPI flow from docs/wtp-simulation-model.md.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from .actuator_engine import ActuatorEngine
from .clarification_engine import compute_stage3_clarification
from .disinfection_engine import compute_stage5_disinfection
from .disturbance_engine import DisturbanceEngine
from .energy_engine import compute_energy
from .filtration_engine import compute_stage4_filtration
from .kpi_engine import compute_all_kpis
from .models import Measurement, SimulationState, clamp, compute_quality, seeded_rng
from .signal_registry import SignalRegistry


class WtpSimulationLoop:
    """Orchestrates one simulation tick through all 8 stages."""

    def __init__(
        self,
        registry: SignalRegistry,
        disturbance_engine: DisturbanceEngine,
        actuator_engine: ActuatorEngine,
        state: SimulationState | None = None,
    ) -> None:
        self.registry = registry
        self.disturbance_engine = disturbance_engine
        self.actuator_engine = actuator_engine
        self.state = state or SimulationState()
        self.rng = seeded_rng()

    def _compute_pv(self, pv_id: str, default: float = 0.0) -> float:
        return self.state.pv_values.get(pv_id, default)

    def step(self, dt_s: float = 1.0) -> list[Measurement]:
        """Execute one full simulation tick. Returns list of 92 Measurement objects."""
        rng = self.rng
        state = self.state
        state.time_s += dt_s
        state.step_count += 1

        # --- PHASE 0: UPDATE DISTURBANCES (7 DVs) ---
        dv_values = self.disturbance_engine.step(dt_s, rng)
        state.dv_values.update(dv_values)

        # --- PHASE 1: UPDATE ACTUATORS (12 MVs) ---
        mv_actuals = self.actuator_engine.step(dt_s, rng)
        state.mv_values.update(mv_actuals)

        # Extract key values for easier access
        raw_turbidity = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_turbidity", 45.0)
        raw_ph = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_ph", 7.15)
        raw_conductivity = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_conductivity", 350.0)
        raw_temperature = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_temperature", 28.0)
        raw_ammonia = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_ammonia", 0.5)
        raw_algae = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_algae_index", 3.0)
        raw_water_level = dv_values.get("INTAKE-STRUCTURE-101.raw_water_level", 3.5)

        rwp101_flow = mv_actuals.get("RWP-101.flow_rate", 450.0)
        rwp102_flow = mv_actuals.get("RWP-102.flow_rate", 440.0)
        hsp101_flow = mv_actuals.get("HSP-101.flow_rate", 320.0)
        hsp102_flow = mv_actuals.get("HSP-102.flow_rate", 320.0)
        coag_pump_flow = mv_actuals.get("COAG-PUMP-101.flow_rate", 12.0)
        cl_pump_flow = mv_actuals.get("CHLORINE-PUMP-101.flow_rate", 8.0)
        ph_pump_flow = mv_actuals.get("PH-PUMP-101.flow_rate", 5.0)
        mixer_speed = mv_actuals.get("FLASH-MIXER-101.mixer_speed", 300.0)
        floc_speed = mv_actuals.get("FLOCCULATOR-101.flocculator_speed", 40.0)
        screen_running = mv_actuals.get("SCREEN-101.running_status", 1.0)
        scraper_running = mv_actuals.get("CLARIFIER-SCRAPER-101.running_status", 1.0)
        sludge_running = mv_actuals.get("SLUDGE-PUMP-101.running_status", 0.0)

        pv: dict[str, float] = {}
        kpi: dict[str, Any] = {}

        # ========== STAGE 1: INTAKE ==========
        total_rwp_flow = rwp101_flow + rwp102_flow

        pv["INTAKE-STRUCTURE-101.screen_dp"] = round(10.0 + 5.0 * (raw_turbidity / 45.0) + rng.gauss(0, 1), 2)
        pv["INTAKE-STRUCTURE-101.inlet_valve_position"] = round(clamp(60.0 + 10.0 * (raw_water_level - 3.0), 0, 100), 1)
        pv["RAW-WATER-PUMP-STATION-101.discharge_pressure"] = round(200.0 + 50.0 * (total_rwp_flow / 900.0) + rng.gauss(0, 3), 1)
        pv["RWP-101.running_status"] = 1.0 if rwp101_flow > 0 else 0.0
        pv["RAW-WATER-MANIFOLD-101.manifold_pressure"] = round(200.0 + 50.0 * (total_rwp_flow / 900.0) + rng.gauss(0, 3), 1)

        manifold_press = pv["RAW-WATER-MANIFOLD-101.manifold_pressure"]

        # RWP-101 motor
        pv["RWP-101-MOTOR.motor_current"] = round(95.0 * (rwp101_flow / 450.0) + rng.gauss(0, 1), 1)
        pv["RWP-101-MOTOR.power"] = round(45.0 * (rwp101_flow / 450.0) * (manifold_press / 250.0) + rng.gauss(0, 1), 2)
        state.rwp101_vibration_accum += 0.001 * dt_s
        pv["RWP-101-MOTOR.vibration_de"] = round(state.rwp101_vibration_accum + rng.gauss(0, 0.05), 2)

        # RWP-102 motor
        pv["RWP-102-MOTOR.motor_current"] = round(95.0 * (rwp102_flow / 450.0) + rng.gauss(0, 1), 1)

        # ========== STAGE 2: CHEMICAL DOSING ==========
        coag_dose_rate = coag_pump_flow * 2.08 + rng.gauss(0, 0.5)
        cl_dose_rate = cl_pump_flow * 0.375 + rng.gauss(0, 0.1)

        pv["COAG-TANK-101.level"] = round(clamp(60.0 - 0.5 * (coag_pump_flow - 12.0), 20, 90), 1)
        pv["COAG-TANK-101.temperature"] = round(raw_temperature + rng.gauss(0, 0.5), 1)
        pv["CHLORINE-TANK-101.level"] = round(clamp(55.0 - 0.5 * (cl_pump_flow - 8.0), 20, 90), 1)

        streaming_current = -5.0 + 0.3 * (coag_pump_flow - 25.0) + rng.gauss(0, 0.2)
        pv["COAGULATION-CONTROL-STATION-101.streaming_current"] = round(streaming_current, 2)

        # ========== STAGE 3: CLARIFICATION ==========
        clar_result = compute_stage3_clarification(
            raw_turbidity=raw_turbidity,
            raw_ph=raw_ph,
            coag_dose_rate=coag_dose_rate,
            ph_pump_flow=ph_pump_flow,
            mixer_speed=mixer_speed,
            flocculator_speed=floc_speed,
            raw_algae_index=raw_algae,
            rng=rng,
        )

        pv["CLARIFIER-101.settled_turbidity"] = clar_result["settled_turbidity"]
        pv["CLARIFIER-101.settled_ph"] = clar_result["settled_ph"]
        pv["COAGULATION-CONTROL-STATION-101.floc_size_index"] = clar_result["floc_size_index"]

        # ========== STAGE 4: FILTRATION ==========
        # Filter effluent flows (proportional to intake)
        filter_101_flow = rwp101_flow * 0.5
        filter_102_flow = rwp102_flow * 0.5
        pv["FILTER-101.effluent_flow"] = round(filter_101_flow, 1)
        pv["FILTER-102.effluent_flow"] = round(filter_102_flow, 1)

        filt_result = compute_stage4_filtration(
            settled_turbidity=clar_result["settled_turbidity"],
            settled_ph=clar_result["settled_ph"],
            raw_algae_index=raw_algae,
            filter_101_effluent_flow=filter_101_flow,
            filter_102_effluent_flow=filter_102_flow,
            filter_101_dp_accum=state.filter_dp_101_accum,
            filter_102_dp_accum=state.filter_dp_102_accum,
            backwash_101_remaining=state.backwash_101_remaining,
            backwash_102_remaining=state.backwash_102_remaining,
            dt_s=dt_s,
            rng=rng,
        )

        state.filter_dp_101_accum = filt_result["filter_101_dp_accum"]
        state.filter_dp_102_accum = filt_result["filter_102_dp_accum"]
        state.backwash_101_remaining = filt_result["backwash_101_remaining"]
        state.backwash_102_remaining = filt_result["backwash_102_remaining"]

        pv["FILTER-101.filter_dp"] = filt_result["filter_101_dp_accum"]
        pv["FILTER-102.filter_dp"] = filt_result["filter_102_dp_accum"]
        pv["FILTER-101.filter_level"] = filt_result["filter_level_101"]
        pv["FILTER-102.filter_level"] = filt_result["filter_level_102"]
        pv["BACKWASH-PUMP-101.running_status"] = 1.0 if state.backwash_101_remaining > 0 or state.backwash_102_remaining > 0 else 0.0
        pv["FILTER-QUALITY-STATION-101.filtered_turbidity"] = filt_result["filtered_turbidity"]
        pv["FILTER-QUALITY-STATION-101.filtered_ph"] = filt_result["filtered_ph"]
        pv["FILTER-QUALITY-STATION-101.particle_count_proxy"] = filt_result["particle_count_proxy"]
        pv["FILTER-QUALITY-STATION-101.filter_run_quality_index"] = filt_result["filter_run_quality_index"]

        # ========== STAGE 5: DISINFECTION ==========
        # Contact time depends on tank level and flow
        contact_tank_inflow = filter_101_flow + filter_102_flow
        contact_tank_level = clamp(65.0 + 0.5 * (contact_tank_inflow - 400.0) / 100.0, 30, 90)
        contact_time = 30.0 * (contact_tank_level / 65.0) * (contact_tank_inflow / 400.0) + rng.gauss(0, 1)
        contact_time = max(5.0, contact_time)
        pv["CONTACT-TANK-101.level"] = round(contact_tank_level, 1)
        pv["CONTACT-TANK-101.contact_time"] = round(contact_time, 1)

        disinf_result = compute_stage5_disinfection(
            chlorine_dose_rate=cl_dose_rate,
            raw_ammonia=raw_ammonia,
            raw_algae_index=raw_algae,
            contact_time=contact_time,
            rng=rng,
        )

        pv["DISINFECTION-QUALITY-STATION-101.free_chlorine"] = disinf_result["free_chlorine"]
        pv["DISINFECTION-QUALITY-STATION-101.total_chlorine"] = disinf_result["total_chlorine"]
        pv["DISINFECTION-QUALITY-STATION-101.orp"] = disinf_result["orp"]

        free_chlorine = disinf_result["free_chlorine"]

        # ========== STAGE 6: CLEAR WATER ==========
        filtered_turb = filt_result["filtered_turbidity"]
        clear_water_turb = filtered_turb * 0.95 + rng.gauss(0, 0.01)
        clear_water_turb = max(0.01, clear_water_turb)
        pv["CLEAR-WATER-QUALITY-STATION-101.clear_water_turbidity"] = round(clear_water_turb, 4)

        cwt_level = clamp(70.0 + 0.5 * (contact_tank_inflow - hsp101_flow - hsp102_flow) / 100.0, 40, 95)
        pv["CLEAR-WATER-TANK-101.level"] = round(cwt_level, 1)
        pv["TRANSFER-PUMP-101.running_status"] = 1.0 if cwt_level > 20.0 else 0.0

        # ========== STAGE 7: DISTRIBUTION ==========
        total_hsp_flow = hsp101_flow + hsp102_flow
        discharge_press = 350.0 + 0.5 * total_hsp_flow + rng.gauss(0, 5)
        outlet_manifold_press = discharge_press - 0.02 * (total_hsp_flow ** 2) + rng.gauss(0, 3)
        outlet_manifold_flow = total_hsp_flow + rng.gauss(0, 3)

        pv["HIGH-SERVICE-PUMP-STATION-101.discharge_pressure"] = round(discharge_press, 1)
        pv["OUTLET-MANIFOLD-101.manifold_pressure"] = round(outlet_manifold_press, 1)
        pv["OUTLET-MANIFOLD-101.manifold_flow"] = round(outlet_manifold_flow, 1)

        # HSP-101 motor
        pv["HSP-101-MOTOR.motor_current"] = round(180.0 * (hsp101_flow / 320.0) * (discharge_press / 400.0) + rng.gauss(0, 2), 1)
        hsp101_power = 110.0 * (hsp101_flow / 320.0) * (discharge_press / 400.0) + rng.gauss(0, 1)
        pv["HSP-101-MOTOR.power"] = round(max(0, hsp101_power), 2)
        # Winding temperature with degradation
        hsp101_current = pv["HSP-101-MOTOR.motor_current"]
        state.hsp101_winding_accum += 0.01 * dt_s / 3600.0
        pv["HSP-101-MOTOR.winding_temp"] = round(75.0 + 20.0 * (hsp101_current - 180.0) / 30.0 + state.hsp101_winding_accum + rng.gauss(0, 0.5), 1)

        # HSP-102 motor
        pv["HSP-102-MOTOR.motor_current"] = round(180.0 * (hsp102_flow / 320.0) * (discharge_press / 400.0) + rng.gauss(0, 2), 1)
        hsp102_power = 110.0 * (hsp102_flow / 320.0) * (discharge_press / 400.0) + rng.gauss(0, 1)
        pv["HSP-102-MOTOR.power"] = round(max(0, hsp102_power), 2)

        # ========== STAGE 8: KPI & ENERGY ==========
        energy_result = compute_energy(
            rwp101_flow=rwp101_flow,
            rwp102_flow=rwp102_flow,
            hsp101_flow=hsp101_flow,
            hsp102_flow=hsp102_flow,
            manifold_pressure=manifold_press,
            outlet_pressure=discharge_press,
            total_flow_outlet=outlet_manifold_flow,
            rng=rng,
        )

        # Update cumulative totals
        state.total_energy_kwh += energy_result["total_active_power"] * dt_s / 3600.0
        state.total_water_m3 += outlet_manifold_flow * dt_s / 3600.0

        # Waste water (sludge + backwash)
        sludge_active = 1.0 if sludge_running > 0 else 0.0
        bw_active = 1.0 if pv["BACKWASH-PUMP-101.running_status"] > 0 else 0.0
        state.total_waste_m3 += (sludge_active * 5.0 + bw_active * 15.0) * dt_s / 3600.0

        # Transformer winding temp
        total_power_kva = energy_result["total_active_power"] / 0.9  # approx
        pv["TRANSFORMER-101.winding_temp"] = round(50.0 + 0.05 * total_power_kva + rng.gauss(0, 1), 1)

        # Save all PVs
        state.pv_values.update(pv)
        state.pv_values["RWP-101-MOTOR.power"] = pv["RWP-101-MOTOR.power"]
        state.pv_values["CLARIFIER-101.settled_turbidity"] = clar_result["settled_turbidity"]

        # Compute all KPIs
        kpi_result = compute_all_kpis(
            pv_values=state.pv_values,
            dv_values=dv_values,
            mv_actuals=mv_actuals,
            state=state,
            rng=rng,
        )
        state.kpi_values.update(kpi_result)

        # Build measurements
        measurements = self._build_measurements(dv_values, mv_actuals, pv, kpi_result)
        return measurements

    def _build_measurements(
        self,
        dv: dict[str, float],
        mv: dict[str, float],
        pv: dict[str, float],
        kpi: dict[str, Any],
    ) -> list[Measurement]:
        """Build list of 92 Measurement objects from current values."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond:06d}Z"

        all_values: dict[str, tuple[float, str, float, float]] = {}

        # DVs
        for sid, cfg in self.registry.DV_CONFIGS.items():
            val = dv.get(sid, cfg.baseline)
            all_values[sid] = (val, "GOOD", cfg.bounds_min, cfg.bounds_max)

        # MVs
        for sid, cfg in self.registry.MV_CONFIGS.items():
            val = mv.get(sid, cfg.default_sp)
            all_values[sid] = (val, "GOOD", cfg.min_sp, cfg.max_sp)

        # PVs
        for sid in self.registry.PV_SIGNALS:
            val = pv.get(sid, 0.0)
            all_values[sid] = (val, "GOOD", 0.0, 100.0)

        # KPIs
        for sid in self.registry.KPI_SIGNALS:
            val = kpi.get(sid, 0.0)
            if isinstance(val, bool):
                val = 1.0 if val else 0.0
            all_values[sid] = (val, "GOOD", 0.0, 100.0)

        # Compute quality for each signal
        measurements: list[Measurement] = []
        for sid, (val, _, lo, hi) in all_values.items():
            quality = compute_quality(val, lo, hi)
            measurements.append(
                Measurement(
                    timestamp=timestamp,
                    signal_id=sid,
                    value=val,
                    quality=quality,
                    source="wtp-sim-01",
                )
            )

        return measurements

    def get_all_values(self) -> dict[str, float]:
        """Return current value for all 92 signals."""
        result: dict[str, float] = {}
        for m in self.get_latest_measurements():
            result[m.signal_id] = m.value if not isinstance(m.value, bool) else (1.0 if m.value else 0.0)
        return result

    def get_latest_measurements(self) -> list[Measurement]:
        """Return the current 92-signal measurement frame without advancing time."""
        return self._build_measurements(
            self.state.dv_values,
            self.state.mv_values,
            self.state.pv_values,
            self.state.kpi_values,
        )

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self.state = SimulationState()
        self.rng = seeded_rng()
