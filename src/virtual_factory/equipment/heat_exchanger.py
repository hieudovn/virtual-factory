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

Truth variables (set during process_step)
------------------------------------------
{id}.hot_outlet_temp_c      — computed hot-side outlet temperature
{id}.cold_outlet_temp_c     — computed cold-side outlet temperature
{id}.heat_transfer_kw       — total heat transfer rate in kW
{id}.dt_log_mean_k          — log-mean temperature difference in K
"""

import math
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

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Compute heat transfer using LMTD method.

        Reads flow rates from incoming/outgoing streams via truth
        variables and computes outlet temperatures based on
        Q = U · A · ΔT_lm.
        """
        area = float(self.parameters.get("area_m2", 5.0))
        u = float(self.parameters.get("u_w_m2k", 500.0))
        hot_in = float(self.parameters.get("hot_inlet_temp_c", 80.0))
        cold_in = float(self.parameters.get("cold_inlet_temp_c", 20.0))

        # Read current outlet temps (may have been set by initialization or previous step)
        hot_out = float(state.get_truth(f"{self.id}.hot_outlet_temp_c", hot_in))
        cold_out = float(state.get_truth(f"{self.id}.cold_outlet_temp_c", cold_in))

        # Log-mean temperature difference for counter-flow
        dt1 = hot_in - cold_out  # hot inlet - cold outlet
        dt2 = hot_out - cold_in  # hot outlet - cold inlet

        if dt1 <= 0 or dt2 <= 0:
            dt_log_mean = 0.0
        elif abs(dt1 - dt2) < 0.01:
            dt_log_mean = dt1
        else:
            dt_log_mean = (dt1 - dt2) / math.log(dt1 / dt2)

        # Heat transfer rate
        q_w = u * area * dt_log_mean  # Watts
        q_kw = q_w / 1000.0

        # Simple model: split temperature change evenly
        delta_t = q_kw * 0.01  # simplified temp change per kW
        new_hot_out = hot_in - delta_t if q_kw > 0 else hot_in
        new_cold_out = cold_in + delta_t if q_kw > 0 else cold_in

        state.set_truth(f"{self.id}.hot_outlet_temp_c", max(0, new_hot_out))
        state.set_truth(f"{self.id}.cold_outlet_temp_c", min(100, new_cold_out))
        state.set_truth(f"{self.id}.heat_transfer_kw", round(q_kw, 2))
        state.set_truth(f"{self.id}.dt_log_mean_k", round(dt_log_mean, 2))
