"""Gas-liquid separator with level dynamics.

Separates a mixed inlet stream into gas overhead and liquid bottoms.
Liquid level follows a simple mass balance:

    d(level)/dt = (Q_in_liquid − Q_out_liquid) / area

Parameters (from config)
------------------------
diameter_m : float
    Vessel internal diameter in metres (default 1.0).
height_m : float
    Vessel tangent-to-tangent height in metres (default 3.0).
initial_level_m : float
    Initial liquid level in metres (default 0.5).
max_level_m : float
    High-level alarm threshold in metres (default 2.5).

Truth variables (set during process dynamics)
----------------------------------------------
{id}.level_true            — liquid level in metres
{id}.pressure_kpa          — vessel pressure
{id}.gas_outflow_true      — overhead gas flow
{id}.liquid_outflow_true   — bottoms liquid flow
"""

from dataclasses import dataclass
import math

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Separator(BaseEquipment):
    """Gas-liquid separator vessel with level dynamics."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create separator truth placeholders."""
        level = float(self.parameters.get("initial_level_m", 0.5))
        state.set_truth(f"{self.id}.level_true", level)
        state.set_truth(f"{self.id}.pressure_kpa", 500.0)
        state.set_truth(f"{self.id}.gas_outflow_true", 0.0)
        state.set_truth(f"{self.id}.liquid_outflow_true", 0.0)

    def process_step(self, state: RuntimeState, dt_s: float) -> None:
        """Advance separator liquid level via mass balance."""
        diameter = float(self.parameters.get("diameter_m", 1.0))
        max_level = float(self.parameters.get("max_level_m", 2.5))

        area = math.pi * (diameter / 2.0) ** 2
        if area <= 0:
            return

        level = float(state.get_truth(f"{self.id}.level_true", 0.5))

        # Estimate net inflow from connected equipment
        # Use connected tank level difference as proxy for liquid flow
        q_in = float(state.get_truth(f"{self.id}.inlet.flow_true", 0.0))
        q_gas_out = float(state.get_truth(f"{self.id}.gas_outflow_true", 0.0))
        q_liq_out = float(state.get_truth(f"{self.id}.liquid_outflow_true", 0.0))

        q_net = q_in * 0.5 - q_liq_out  # assume 50% liquid fraction
        new_level = level + (q_net * dt_s) / area
        new_level = max(0.0, min(new_level, max_level))

        state.set_truth(f"{self.id}.level_true", round(new_level, 4))
