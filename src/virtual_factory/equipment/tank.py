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
        capacity = float(self.parameters.get("capacity_m3", 0.0))
        if "tank_area_m2" in self.parameters:
            volume = level * float(self.parameters["tank_area_m2"])
        else:
            max_level = float(self.parameters.get("max_level_m", 5.0))
            volume = capacity * level / max_level if max_level > 0 else 0.0
        volume = max(0.0, min(capacity, volume))
        state.set_truth(f"{self.id}.level_true", level)
        state.set_truth(f"{self.id}.volume_true", volume)
