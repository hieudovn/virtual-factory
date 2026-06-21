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
