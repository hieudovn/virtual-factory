"""Fan / blower equipment with quadratic pressure-rise characteristic.

Provides a pressure boost to a gas flow stream.  The fan curve follows a
quadratic model similar to the centrifugal pump but for compressible media:

    ΔP = rated_pressure_rise_pa · (1 − (Q / rated_flow_m3_s)²)

Parameters (from config)
------------------------
rated_pressure_rise_pa : float
    Maximum pressure rise at zero flow in Pa (default 500).
rated_flow_m3_s : float
    Rated volumetric flow at zero pressure rise in m³/s (default 1.0).

Truth variables (set during process_step)
------------------------------------------
{id}.pressure_rise_pa   — actual pressure rise at current flow
{id}.flow_true          — current flow rate through the fan
"""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Fan(BaseEquipment):
    """Fan / blower with quadratic pressure-rise curve."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create fan truth placeholders."""
        state.set_truth(f"{self.id}.running", True)
        state.set_truth(f"{self.id}.pressure_rise_pa", float(self.parameters.get("rated_pressure_rise_pa", 500.0)))
        state.set_truth(f"{self.id}.flow_true", 0.0)
        state.set_truth(f"{self.id}.outlet.flow_true", 0.0)

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Compute fan pressure rise based on quadratic curve."""
        rated_pr = float(self.parameters.get("rated_pressure_rise_pa", 500.0))
        rated_q = float(self.parameters.get("rated_flow_m3_s", 1.0))
        running = bool(state.get_truth(f"{self.id}.running", True))
        q = float(state.get_truth(f"{self.id}.flow_true", 0.0))
        if not running or rated_q <= 0:
            pr = 0.0
        else:
            frac = min(abs(q) / rated_q, 1.0)
            pr = rated_pr * (1.0 - frac**2)
        state.set_truth(f"{self.id}.pressure_rise_pa", max(0.0, pr))
        state.set_truth(f"{self.id}.outlet.flow_true", q)
