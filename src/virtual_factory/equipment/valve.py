"""Valve equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Valve(BaseEquipment):
    """Control valve placeholder for future opening and restriction behavior."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create initial valve opening and outlet flow truth values."""
        state.set_truth(f"{self.id}.opening_actual", 0.0)
        state.set_truth(f"{self.id}.outlet.flow_true", 0.0)
