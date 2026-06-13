"""Tank equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Tank(BaseEquipment):
    """Tank model placeholder for future inventory and level dynamics."""
