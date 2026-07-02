"""Signal Registry — classifies all 92 signals by taxonomy role."""

from __future__ import annotations

from .models import DVConfig, MVConfig, SignalType


class SignalRegistry:
    """Maps each signal_id to its simulation role (MV/DV/PV/KPI)."""

    # --- 7 Disturbance Variables ---
    DV_CONFIGS: dict[str, DVConfig] = {
        "RAW-WATER-QUALITY-STATION-101.raw_turbidity": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_turbidity",
            pattern="random_walk", baseline=45.0, amplitude=15.0,
            noise_std=2.0, bounds_min=10.0, bounds_max=120.0,
        ),
        "RAW-WATER-QUALITY-STATION-101.raw_ph": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_ph",
            pattern="random_walk", baseline=7.15, amplitude=0.3,
            noise_std=0.05, bounds_min=6.5, bounds_max=9.0,
        ),
        "RAW-WATER-QUALITY-STATION-101.raw_conductivity": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_conductivity",
            pattern="random_walk", baseline=350.0, amplitude=80.0,
            noise_std=10.0, bounds_min=200.0, bounds_max=600.0,
        ),
        "RAW-WATER-QUALITY-STATION-101.raw_temperature": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_temperature",
            pattern="sine", baseline=28.0, amplitude=4.0,
            noise_std=0.3, bounds_min=20.0, bounds_max=35.0,
            frequency_hz=1.0 / (365 * 86400),  # seasonal
        ),
        "RAW-WATER-QUALITY-STATION-101.raw_ammonia": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_ammonia",
            pattern="random_walk", baseline=0.25, amplitude=0.1,
            noise_std=0.03, bounds_min=0.05, bounds_max=0.6,
        ),
        "RAW-WATER-QUALITY-STATION-101.raw_algae_index": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_algae_index",
            pattern="random_walk", baseline=3.0, amplitude=1.0,
            noise_std=0.2, bounds_min=0.5, bounds_max=10.0,
        ),
        "INTAKE-STRUCTURE-101.raw_water_level": DVConfig(
            signal_id="INTAKE-STRUCTURE-101.raw_water_level",
            pattern="sine", baseline=3.5, amplitude=0.5,
            noise_std=0.05, bounds_min=2.0, bounds_max=5.0,
            frequency_hz=1.0 / (365 * 86400),
        ),
    }

    # --- 12 Manipulated Variables ---
    MV_CONFIGS: dict[str, MVConfig] = {
        "COAG-PUMP-101.flow_rate": MVConfig(
            signal_id="COAG-PUMP-101.flow_rate",
            default_sp=12.0, min_sp=5.0, max_sp=25.0,
            slew_rate=2.0, accuracy_pct=2.0,
        ),
        "CHLORINE-PUMP-101.flow_rate": MVConfig(
            signal_id="CHLORINE-PUMP-101.flow_rate",
            default_sp=11.0, min_sp=2.0, max_sp=18.0,
            slew_rate=1.0, accuracy_pct=2.0,
        ),
        "PH-PUMP-101.flow_rate": MVConfig(
            signal_id="PH-PUMP-101.flow_rate",
            default_sp=5.0, min_sp=1.0, max_sp=12.0,
            slew_rate=1.0, accuracy_pct=2.0,
        ),
        "RWP-101.flow_rate": MVConfig(
            signal_id="RWP-101.flow_rate",
            default_sp=450.0, min_sp=200.0, max_sp=550.0,
            slew_rate=50.0, accuracy_pct=1.0,
        ),
        "RWP-102.flow_rate": MVConfig(
            signal_id="RWP-102.flow_rate",
            default_sp=440.0, min_sp=0.0, max_sp=500.0,
            slew_rate=50.0, accuracy_pct=1.0,
        ),
        "HSP-101.flow_rate": MVConfig(
            signal_id="HSP-101.flow_rate",
            default_sp=320.0, min_sp=100.0, max_sp=400.0,
            slew_rate=50.0, accuracy_pct=1.0,
        ),
        "HSP-102.flow_rate": MVConfig(
            signal_id="HSP-102.flow_rate",
            default_sp=320.0, min_sp=0.0, max_sp=450.0,
            slew_rate=50.0, accuracy_pct=1.0,
        ),
        "FLASH-MIXER-101.mixer_speed": MVConfig(
            signal_id="FLASH-MIXER-101.mixer_speed",
            default_sp=300.0, min_sp=150.0, max_sp=500.0,
            slew_rate=50.0, accuracy_pct=2.0,
        ),
        "FLOCCULATOR-101.flocculator_speed": MVConfig(
            signal_id="FLOCCULATOR-101.flocculator_speed",
            default_sp=40.0, min_sp=10.0, max_sp=80.0,
            slew_rate=10.0, accuracy_pct=2.0,
        ),
        "SCREEN-101.running_status": MVConfig(
            signal_id="SCREEN-101.running_status",
            default_sp=1.0, min_sp=0.0, max_sp=1.0,
            slew_rate=0.0, accuracy_pct=0.0,
        ),
        "CLARIFIER-SCRAPER-101.running_status": MVConfig(
            signal_id="CLARIFIER-SCRAPER-101.running_status",
            default_sp=1.0, min_sp=0.0, max_sp=1.0,
            slew_rate=0.0, accuracy_pct=0.0,
        ),
        "SLUDGE-PUMP-101.running_status": MVConfig(
            signal_id="SLUDGE-PUMP-101.running_status",
            default_sp=0.0, min_sp=0.0, max_sp=1.0,
            slew_rate=0.0, accuracy_pct=0.0,
        ),
    }

    # --- PV signal IDs (43 signals) ---
    PV_SIGNALS: list[str] = [
        "INTAKE-STRUCTURE-101.screen_dp",
        "INTAKE-STRUCTURE-101.inlet_valve_position",
        "RAW-WATER-PUMP-STATION-101.discharge_pressure",
        "RWP-101.running_status",
        "RWP-101-MOTOR.motor_current",
        "RWP-101-MOTOR.power",
        "RWP-101-MOTOR.vibration_de",
        "RWP-102-MOTOR.motor_current",
        "RAW-WATER-MANIFOLD-101.manifold_pressure",
        "COAG-TANK-101.level",
        "COAG-TANK-101.temperature",
        "COAGULATION-CONTROL-STATION-101.streaming_current",
        "COAGULATION-CONTROL-STATION-101.floc_size_index",
        "CHLORINE-TANK-101.level",
        "CLARIFIER-101.settled_turbidity",
        "CLARIFIER-101.settled_ph",
        "FILTER-101.filter_dp",
        "FILTER-101.effluent_flow",
        "FILTER-101.filter_level",
        "FILTER-102.filter_dp",
        "FILTER-102.effluent_flow",
        "FILTER-102.filter_level",
        "BACKWASH-PUMP-101.running_status",
        "FILTER-QUALITY-STATION-101.filtered_turbidity",
        "FILTER-QUALITY-STATION-101.filtered_ph",
        "FILTER-QUALITY-STATION-101.particle_count_proxy",
        "CONTACT-TANK-101.level",
        "CONTACT-TANK-101.contact_time",
        "DISINFECTION-QUALITY-STATION-101.free_chlorine",
        "DISINFECTION-QUALITY-STATION-101.total_chlorine",
        "DISINFECTION-QUALITY-STATION-101.orp",
        "CLEAR-WATER-TANK-101.level",
        "CLEAR-WATER-QUALITY-STATION-101.clear_water_turbidity",
        "TRANSFER-PUMP-101.running_status",
        "HIGH-SERVICE-PUMP-STATION-101.discharge_pressure",
        "HSP-101-MOTOR.motor_current",
        "HSP-101-MOTOR.power",
        "HSP-101-MOTOR.winding_temp",
        "HSP-102-MOTOR.motor_current",
        "HSP-102-MOTOR.power",
        "OUTLET-MANIFOLD-101.manifold_pressure",
        "OUTLET-MANIFOLD-101.manifold_flow",
        "TRANSFORMER-101.winding_temp",
    ]

    # --- KPI signal IDs (30 signals) ---
    KPI_SIGNALS: list[str] = [
        "CHEMICAL-CONSUMPTION-STATION-101.coagulant_dose_rate",
        "CHEMICAL-CONSUMPTION-STATION-101.chlorine_dose_rate",
        "CHEMICAL-CONSUMPTION-STATION-101.chemical_cost_per_m3",
        "CLARIFIER-QUALITY-STATION-101.clarifier_efficiency_index",
        "FILTER-QUALITY-STATION-101.filter_run_quality_index",
        "CLEAR-WATER-TANK-101.quality_index",
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_turbidity",
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_ph",
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_free_chlorine",
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_compliance_status",
        "TRANSFORMER-101.load_percent",
        "TRANSFORMER-101.oil_temp",
        "ENERGY-MONITORING-STATION-101.total_active_power",
        "ENERGY-MONITORING-STATION-101.total_energy_today",
        "ENERGY-MONITORING-STATION-101.specific_energy_consumption",
        "ENERGY-MONITORING-STATION-101.energy_cost_per_m3",
        "ENERGY-MONITORING-STATION-101.peak_demand",
        "MCC-101.runtime_hours",
        "LAB-SAMPLING-STATION-101.cod",
        "LAB-SAMPLING-STATION-101.toc",
        "QUALITY-TRACEABILITY-ENGINE-101.raw_water_impact_score",
        "QUALITY-TRACEABILITY-ENGINE-101.chemical_dosing_abnormality_score",
        "QUALITY-TRACEABILITY-ENGINE-101.energy_abnormality_score",
        "QUALITY-TRACEABILITY-ENGINE-101.outlet_quality_risk_score",
        "QUALITY-TRACEABILITY-ENGINE-101.probable_root_cause_code",
        "PLANT-KPI-101.water_production_today",
        "PLANT-KPI-101.treatment_yield",
        "PLANT-KPI-101.outlet_quality_index",
        "PLANT-KPI-101.compliance_rate_today",
        "PLANT-KPI-101.cost_per_m3",
    ]

    @property
    def all_signal_ids(self) -> list[str]:
        return (
            list(self.DV_CONFIGS.keys())
            + list(self.MV_CONFIGS.keys())
            + self.PV_SIGNALS
            + self.KPI_SIGNALS
        )

    def get_signal_type(self, signal_id: str) -> SignalType | None:
        if signal_id in self.DV_CONFIGS:
            return SignalType.DV
        if signal_id in self.MV_CONFIGS:
            return SignalType.MV
        if signal_id in self.PV_SIGNALS:
            return SignalType.PV
        if signal_id in self.KPI_SIGNALS:
            return SignalType.KPI
        return None

    def get_mv_config(self, signal_id: str) -> MVConfig | None:
        return self.MV_CONFIGS.get(signal_id)

    def get_dv_config(self, signal_id: str) -> DVConfig | None:
        return self.DV_CONFIGS.get(signal_id)

    def is_mv(self, signal_id: str) -> bool:
        return signal_id in self.MV_CONFIGS

    def is_dv(self, signal_id: str) -> bool:
        return signal_id in self.DV_CONFIGS
