"""Carrier/pallet identity and state for the ASSY indexed line.

M6-S02: Carrier is separate from WIP identity (INV-CONV-07).
PROVISIONAL_FOR_DEMO: Same carrier remains associated through ASSY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class CarrierId:
    """Immutable carrier/pallet identity.

    Distinct from WipId — a carrier carries a WIP but is not the WIP.
    """

    id: str

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"CarrierId({self.id!r})"


@dataclass(slots=True)
class CarrierState:
    """Mutable runtime state for a single carrier/pallet.

    Tracks which WIP (if any) is currently on this carrier.
    Carrier may be empty (no WIP assigned).
    """

    carrier_id: CarrierId
    wip_id: Optional[str] = None  # WipId.id string, or None if empty

    @property
    def is_occupied(self) -> bool:
        return self.wip_id is not None

    def load(self, wip_id: str) -> None:
        """Assign a WIP to this carrier."""
        if self.wip_id is not None:
            raise CarrierError(
                f"Cannot load WIP {wip_id} onto {self.carrier_id}: "
                f"already occupied by {self.wip_id}"
            )
        self.wip_id = wip_id

    def unload(self) -> str:
        """Remove and return the current WIP ID."""
        if self.wip_id is None:
            raise CarrierError(
                f"Cannot unload {self.carrier_id}: carrier is empty"
            )
        wip = self.wip_id
        self.wip_id = None
        return wip

    def clear(self) -> None:
        """Clear the carrier (release after product completion)."""
        self.wip_id = None


class CarrierError(ValueError):
    """Raised when a carrier invariant is violated."""
