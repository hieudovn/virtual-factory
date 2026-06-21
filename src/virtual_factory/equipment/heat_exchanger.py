"""Shell-and-tube heat exchanger with counter-flow heat transfer.

A two-port heat exchanger that transfers thermal energy between a hot
fluid stream (tube side) and a cold fluid stream (shell side).
Heat transfer follows the log-mean temperature difference (LMTD) method:

    Q = U · A · ΔT_lm

where ΔT_lm is the log-mean temperature difference accounting for
counter-flow geometry.

Parameters (from config)
------------------------
area_m2 : float
    Total heat transfer surface area in square metres (default 5.0).
u_w_m2k : float
    Overall heat transfer coefficient in W/(m²·K) (default 500).
hot_inlet_temp_c : float
    Nominal hot-side inlet temperature in °C (default 80, informational).
cold_inlet_temp_c : float
    Nominal cold-side inlet temperature in °C (default 20, informational).

Truth variables (set during process dynamics)
----------------------------------------------
{id}.hot_outlet_temp_c      — computed hot-side outlet temperature
{id}.cold_outlet_temp_c     — computed cold-side outlet temperature
{id}.heat_transfer_kw       — total heat transfer rate in kW
{id}.dt_log_mean_k          — log-mean temperature difference in K
"""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class HeatExchanger(BaseEquipment):
    """Shell-and-tube counter-flow heat exchanger."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create heat exchanger truth placeholders."""
        state.set_truth(f"{self.id}.hot_outlet_temp_c", float(self.parameters.get("hot_inlet_temp_c", 80.0)))
        state.set_truth(f"{self.id}.cold_outlet_temp_c", float(self.parameters.get("cold_inlet_temp_c", 20.0)))
        state.set_truth(f"{self.id}.heat_transfer_kw", 0.0)
        state.set_truth(f"{self.id}.dt_log_mean_k", 0.0)
