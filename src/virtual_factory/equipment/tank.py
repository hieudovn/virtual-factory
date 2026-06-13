"""Tank equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Tank(BaseEquipment):
    """Tank model placeholder for future inventory and level dynamics."""

    def initialize_state(self, state: RuntimeState) -> None:
        """Create initial tank level and volume truth values."""
        level = float(self.parameters.get("initial_level_m", 0.0))
        state.set_truth(f"{self.id}.level_true", level)
        state.set_truth(f"{self.id}.volume_true", level)
