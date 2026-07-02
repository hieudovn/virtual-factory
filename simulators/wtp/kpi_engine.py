"""KPI Engine — Stage 8: All 30 KPI signals including cost, quality, traceability.

Formulas from docs/wtp-simulation-model.md Stage 8 + Section 4.4 KPI table.
"""

from __future__ import annotations

import random
from typing import Any

from .models import SimulationState, clamp, seeded_rng


def ph_score(ph: float) -> float:
    """Compute pH quality score (1.0 = perfect, 0.0 = bad)."""
    if 7.0 <= ph <= 7.5:
        return 1.0
    if 6.8 <= ph < 7.0 or 7.5 < ph <= 7.8:
        return 0.8
    if 6.5 <= ph < 6.8 or 7.8 < ph <= 8.5:
        return 0.5
    return 0.0


def compute_all_kpis(
    pv_values: dict[str, float],
    dv_values: dict[str, float],
    mv_actuals: dict[str, float],
    state: SimulationState,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Compute all 30 KPI signals from current PV/DV/MV values.

    Returns dict mapping signal_id → value (float or bool).
    """
    rng = rng or seeded_rng()

    # --- Chemical KPIs ---
    coag_dose_rate = mv_actuals.get("COAG-PUMP-101.flow_rate", 12.0) * 2.08 + rng.gauss(0, 0.5)
    cl_dose_rate = mv_actuals.get("CHLORINE-PUMP-101.flow_rate", 8.0) * 0.375 + rng.gauss(0, 0.1)

    chemical_cost = coag_dose_rate * 30.0 + cl_dose_rate * 50.0

    # --- Clarifier efficiency ---
    raw_turbidity = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_turbidity", 45.0)
    settled_turbidity = pv_values.get("CLARIFIER-101.settled_turbidity", 10.0)
    clarifier_efficiency = (raw_turbidity - settled_turbidity) / max(raw_turbidity, 0.1) / 0.85
    clarifier_efficiency = clamp(clarifier_efficiency, 0.0, 1.0)

    # --- Energę KPIs ---
    rwp101_power = pv_values.get("RWP-101-MOTOR.power", 0.0)
    rwp102_power = pv_values.get("RWP-102-MOTOR.power", 0.0)
    hsp101_power = pv_values.get("HSP-101-MOTOR.power", 0.0)
    hsp102_power = pv_values.get("HSP-102-MOTOR.power", 0.0)
    total_power = rwp101_power + rwp102_power + hsp101_power + hsp102_power + 50.0
    total_flow_outlet = pv_values.get("OUTLET-MANIFOLD-101.manifold_flow", 640.0)
    spec_energy = total_power / max(0.1, total_flow_outlet)
    energy_cost = spec_energy * 2500.0

    # --- Outlet signals ---
    filtered_turbidity = pv_values.get("FILTER-QUALITY-STATION-101.filtered_turbidity", 0.3)
    outlet_turbidity = filtered_turbidity * 0.95 + rng.gauss(0, 0.01)
    outlet_turbidity = max(0.01, outlet_turbidity)

    filtered_ph = pv_values.get("FILTER-QUALITY-STATION-101.filtered_ph", 7.0)
    outlet_ph = filtered_ph + rng.gauss(0, 0.03)

    free_chlorine = pv_values.get("DISINFECTION-QUALITY-STATION-101.free_chlorine", 0.6)
    outlet_free_chlorine = free_chlorine * 0.9 + rng.gauss(0, 0.02)
    outlet_free_chlorine = max(0.0, outlet_free_chlorine)

    # --- Compliance check ---
    outlet_compliance = (
        outlet_turbidity <= 1.0
        and outlet_free_chlorine >= 0.2
        and 6.5 <= outlet_ph <= 8.5
    )

    # Update compliance rate
    state.compliance_frames += 1 if outlet_compliance else 0
    state.total_frames += 1
    compliance_rate = state.compliance_frames / max(state.total_frames, 1)

    # --- Energy cost ---
    # Peak demand (rolling 15-min max)
    peak_demand = max(total_power, state.kpi_values.get("ENERGY-MONITORING-STATION-101.peak_demand", total_power))

    # --- Water production ---
    water_production = state.total_water_m3
    total_intake = (
        mv_actuals.get("RWP-101.flow_rate", 0.0)
        + mv_actuals.get("RWP-102.flow_rate", 0.0)
    )
    waste = state.total_waste_m3
    treatment_yield = 100.0 - (waste / max(total_intake * state.time_s / 3600.0, 1.0)) * 100.0 if state.time_s > 0 else 99.0
    treatment_yield = clamp(treatment_yield, 80.0, 100.0)

    # --- Cost per m³ ---
    cost_per_m3 = energy_cost + chemical_cost + 1500.0

    # --- Outlet quality index ---
    outlet_quality_index = (
        0.35 * (1.0 - outlet_turbidity / 1.0)
        + 0.30 * (outlet_free_chlorine / 0.8)
        + 0.20 * ph_score(outlet_ph)
        + 0.15 * (1.0 - abs(cost_per_m3 - 3200.0) / 2000.0)
    )
    outlet_quality_index = clamp(outlet_quality_index, 0.0, 1.0)

    # --- COD and TOC ---
    cod = raw_turbidity * 0.3
    toc = raw_turbidity * 0.06

    # --- Traceability ---
    raw_ammonia = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_ammonia", 0.5)
    raw_algae = dv_values.get("RAW-WATER-QUALITY-STATION-101.raw_algae_index", 3.0)

    raw_water_impact = clamp(0.0, 10.0, raw_turbidity / 8.0 + raw_ammonia * 3.0 + raw_algae)

    optimal_coag_dose = 25.0
    optimal_cl_dose = 4.5
    chem_abnorm = clamp(
        0.0, 10.0,
        abs(coag_dose_rate - optimal_coag_dose) / 5.0
        + abs(cl_dose_rate - optimal_cl_dose) / 2.0
    )

    energy_abnorm = clamp(0.0, 10.0, (spec_energy - 0.38) / 0.03)

    risk_score = (
        0.4 * raw_water_impact
        + 0.3 * chem_abnorm
        + 0.2 * energy_abnorm
        + 0.1 * (1.0 - compliance_rate)
    )
    risk_score = clamp(risk_score, 0.0, 10.0)

    # Probable root cause code
    contributors = {
        "raw_water": raw_water_impact * 0.4,
        "chemical": chem_abnorm * 0.3,
        "energy": energy_abnorm * 0.2,
        "compliance": (1.0 - compliance_rate) * 0.1,
    }
    max_contrib = max(contributors.values())
    if max_contrib < 2.0:
        root_cause = 0
    elif contributors["raw_water"] == max_contrib:
        root_cause = 101  # raw water turbidity
    elif contributors["chemical"] == max_contrib:
        root_cause = 201  # chemical dosing
    elif contributors["energy"] == max_contrib:
        root_cause = 601  # pumping
    else:
        root_cause = 401  # filtration

    # Clear water quality index
    clear_water_turbidity = pv_values.get("CLEAR-WATER-QUALITY-STATION-101.clear_water_turbidity", 0.3)
    clear_quality = (
        0.4 * (1.0 - clear_water_turbidity / 1.0)
        + 0.3 * (free_chlorine / 0.8)
        + 0.3 * ph_score(pv_values.get("FILTER-QUALITY-STATION-101.filtered_ph", 7.0))
    )
    clear_quality = clamp(clear_quality, 0.0, 1.0)

    # Transformer KPIs
    tx_capacity = 1200.0  # kVA
    load_pct = total_power / tx_capacity * 100.0
    tx_winding_temp = pv_values.get("TRANSFORMER-101.winding_temp", 60.0)
    tx_oil_temp = tx_winding_temp - 10.0

    # Energy today (cumulative, updated in simulation loop)
    total_energy_today = state.total_energy_kwh * 1000.0  # convert to kWh

    # Compliance rate today
    compliance_rate_today = compliance_rate * 100.0

    # Build results dict
    kpis: dict[str, Any] = {
        # Stage 2 - Chemical
        "CHEMICAL-CONSUMPTION-STATION-101.coagulant_dose_rate": round(coag_dose_rate, 2),
        "CHEMICAL-CONSUMPTION-STATION-101.chlorine_dose_rate": round(cl_dose_rate, 2),
        "CHEMICAL-CONSUMPTION-STATION-101.chemical_cost_per_m3": round(chemical_cost, 0),
        # Stage 3 - Clarifier
        "CLARIFIER-QUALITY-STATION-101.clarifier_efficiency_index": round(clarifier_efficiency, 3),
        # Stage 4 - Filter
        "FILTER-QUALITY-STATION-101.filter_run_quality_index": round(
            pv_values.get("FILTER-QUALITY-STATION-101.filter_run_quality_index", 0.85), 3
        ),
        # Stage 6 - Clear Water
        "CLEAR-WATER-TANK-101.quality_index": round(clear_quality, 3),
        # Stage 7 - Outlet
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_turbidity": round(outlet_turbidity, 4),
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_ph": round(outlet_ph, 2),
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_free_chlorine": round(outlet_free_chlorine, 4),
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_compliance_status": bool(outlet_compliance),
        # Stage 8 - Energy
        "ENERGY-MONITORING-STATION-101.total_active_power": round(total_power, 2),
        "ENERGY-MONITORING-STATION-101.total_energy_today": round(total_energy_today, 1),
        "ENERGY-MONITORING-STATION-101.specific_energy_consumption": round(spec_energy, 4),
        "ENERGY-MONITORING-STATION-101.energy_cost_per_m3": round(energy_cost, 0),
        "ENERGY-MONITORING-STATION-101.peak_demand": round(peak_demand, 2),
        # Stage 8 - Transformer
        "TRANSFORMER-101.load_percent": round(load_pct, 1),
        "TRANSFORMER-101.oil_temp": round(tx_oil_temp, 1),
        # Stage 8 - Runtime
        "MCC-101.runtime_hours": round(state.time_s / 3600.0, 2),
        # Stage 8 - Lab
        "LAB-SAMPLING-STATION-101.cod": round(cod, 1),
        "LAB-SAMPLING-STATION-101.toc": round(toc, 2),
        # Stage 8 - Traceability
        "QUALITY-TRACEABILITY-ENGINE-101.raw_water_impact_score": round(raw_water_impact, 2),
        "QUALITY-TRACEABILITY-ENGINE-101.chemical_dosing_abnormality_score": round(chem_abnorm, 2),
        "QUALITY-TRACEABILITY-ENGINE-101.energy_abnormality_score": round(energy_abnorm, 2),
        "QUALITY-TRACEABILITY-ENGINE-101.outlet_quality_risk_score": round(risk_score, 2),
        "QUALITY-TRACEABILITY-ENGINE-101.probable_root_cause_code": root_cause,
        # Stage 8 - Plant KPIs
        "PLANT-KPI-101.water_production_today": round(water_production, 0),
        "PLANT-KPI-101.treatment_yield": round(treatment_yield, 1),
        "PLANT-KPI-101.outlet_quality_index": round(outlet_quality_index, 3),
        "PLANT-KPI-101.compliance_rate_today": round(compliance_rate_today, 1),
        "PLANT-KPI-101.cost_per_m3": round(cost_per_m3, 0),
    }

    return kpis
