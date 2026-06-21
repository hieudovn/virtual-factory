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
