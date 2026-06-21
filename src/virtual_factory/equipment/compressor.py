"""Gas compressor with polytropic compression model.

Raises gas pressure from suction to discharge using a polytropic
compression curve:

    P_discharge = P_suction · (1 + (Q_rated − Q) / Q_rated · (PR_rated − 1))

where PR_rated is the rated pressure ratio at zero flow.

Parameters (from config)
------------------------
rated_power_kw : float
    Rated shaft power in kW (default 50).
rated_flow_m3_s : float
    Rated volumetric suction flow in m³/s (default 0.5).
rated_pressure_ratio : float
    Rated discharge/suction pressure ratio at rated flow (default 2.0).
max_pressure_kpa : float
    Maximum allowable discharge pressure in kPa (default 1000).

Truth variables (set during process dynamics)
----------------------------------------------
{id}.suction_pressure_kpa    — suction pressure
{id}.discharge_pressure_kpa  — computed discharge pressure
{id}.flow_true               — current flow rate
{id}.outlet.flow_true        — outlet flow (same as flow_true)
{id}.power_consumed_kw       — estimated power draw
"""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Compressor(BaseEquipment):
    """Gas compressor with polytropic compression characteristic."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create compressor truth placeholders."""
        state.set_truth(f"{self.id}.running", True)
        state.set_truth(f"{self.id}.suction_pressure_kpa", 101.325)  # atmospheric default
        state.set_truth(f"{self.id}.discharge_pressure_kpa", float(self.parameters.get("max_pressure_kpa", 1000.0)))
        state.set_truth(f"{self.id}.flow_true", 0.0)
        state.set_truth(f"{self.id}.outlet.flow_true", 0.0)
        state.set_truth(f"{self.id}.power_consumed_kw", 0.0)

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Compute compressor discharge pressure and power."""
        rated_power = float(self.parameters.get("rated_power_kw", 50.0))
        rated_q = float(self.parameters.get("rated_flow_m3_s", 0.5))
        rated_pr = float(self.parameters.get("rated_pressure_ratio", 2.0))
        max_p_kpa = float(self.parameters.get("max_pressure_kpa", 1000.0))
        running = bool(state.get_truth(f"{self.id}.running", True))
        q = float(state.get_truth(f"{self.id}.flow_true", 0.0))
        p_suction = float(state.get_truth(f"{self.id}.suction_pressure_kpa", 101.325))

        if not running or rated_q <= 0:
            p_discharge = p_suction
            power = 0.0
        else:
            frac = min(abs(q) / rated_q, 1.0)
            # Polytropic approx: PR decreases with flow
            pr_actual = 1.0 + (1.0 - frac) * (rated_pr - 1.0)
            p_discharge = p_suction * pr_actual
            power = rated_power * frac

        p_discharge = min(p_discharge, max_p_kpa)
        state.set_truth(f"{self.id}.discharge_pressure_kpa", round(p_discharge, 2))
        state.set_truth(f"{self.id}.power_consumed_kw", round(power, 2))
        state.set_truth(f"{self.id}.outlet.flow_true", q)
