"""Valve equipment skeleton."""

from dataclasses import dataclass

from virtual_factory.equipment.base_equipment import BaseEquipment


@dataclass(slots=True)
class Valve(BaseEquipment):
    """Control valve placeholder for future opening and restriction behavior."""
