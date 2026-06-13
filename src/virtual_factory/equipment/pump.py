"""Pump equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Pump(BaseEquipment):
    """Pump model placeholder for future pressure and flow behavior."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create simple pump truth placeholders without process physics."""
        state.set_truth(f"{self.id}.running", True)
        state.set_truth(f"{self.id}.discharge_pressure_true", 0.0)
        state.set_truth(f"{self.id}.outlet.flow_true", 0.0)
