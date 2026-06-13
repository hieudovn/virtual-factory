"""Pump equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Pump(BaseEquipment):
    """Pump model placeholder for future pressure and flow behavior."""
