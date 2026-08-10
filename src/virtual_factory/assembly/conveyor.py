"""Indexed conveyor state machine for the ASSY line.

M6-S02: Implements INV-CONV-01 through INV-CONV-09.
Single lane, stop-and-go, line-level synchronization boundary.

The conveyor owns:
- A sequence of position IDs (PRE-ASSY, AP01..AP11)
- A mapping of position → carrier occupying it
- Current conveyor state (INDEXING, STOPPED, OPERATING, READY_TO_INDEX)
- Dwell/index timing configuration

Processing occurs ONLY during STOPPED state.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.carrier import CarrierId, CarrierState


class ConveyorState(str, enum.Enum):
    """Conveyor lifecycle state.

    INDEXING      — pallets are physically moving to next position.
    STOPPED        — conveyor halted; stations may begin operating.
    OPERATING      — at least one station is executing required work.
    READY_TO_INDEX — all required work complete; eligible to advance.
    """

    INDEXING = "indexing"
    STOPPED = "stopped"
    OPERATING = "operating"
    READY_TO_INDEX = "ready_to_index"


@dataclass
class ConveyorConfig:
    """Configuration for the indexed conveyor.

    All values are configuration-driven (INV-CONV-04).
    """

    nominal_line_dwell_time_s: float = 120.0
    index_movement_duration_s: float = 0.0  # demo: instantaneous index
    positions: tuple[str, ...] = field(default_factory=lambda: (
        "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
        "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
    ))


@dataclass
class ConveyorLine:
    """Single-lane indexed conveyor (INV-CONV-01, INV-CONV-02).

    Manages:
    - Position → carrier occupancy
    - Conveyor state transitions
    - Synchronized index advancement
    - Dwell completion tracking per position

    All conveyor-bound work must occur while STOPPED (INV-CONV-03).
    """

    config: ConveyorConfig
    state: ConveyorState = ConveyorState.STOPPED
    _occupancy: dict[str, Optional[CarrierState]] = field(default_factory=dict)
    _position_complete: dict[str, bool] = field(default_factory=dict)
    _carriers: dict[str, CarrierState] = field(default_factory=dict)
    _dwell_number: int = 0
    _current_dwell_time_s: float = 0.0

    def __post_init__(self) -> None:
        # Initialize all positions as empty
        for pos in self.config.positions:
            self._occupancy[pos] = None
            self._position_complete[pos] = False

    # -- Read-only properties --

    @property
    def dwell_number(self) -> int:
        return self._dwell_number

    @property
    def current_dwell_time_s(self) -> float:
        return self._current_dwell_time_s

    @property
    def positions(self) -> tuple[str, ...]:
        return self.config.positions

    # -- Position queries --

    def carrier_at(self, position: str) -> Optional[CarrierState]:
        """Return the carrier at a position, or None if empty."""
        return self._occupancy.get(position)

    def wip_at(self, position: str) -> Optional[str]:
        """Return the WIP ID at a position, or None."""
        c = self._occupancy.get(position)
        return c.wip_id if c else None

    def occupied_positions(self) -> list[str]:
        """Return all positions that currently have a carrier."""
        return [p for p, c in self._occupancy.items() if c is not None]

    def get_carrier(self, carrier_id: str) -> Optional[CarrierState]:
        """Look up a carrier by ID."""
        return self._carriers.get(carrier_id)

    # -- Carrier management --

    def create_carrier(self, carrier_id: str) -> CarrierState:
        """Create a new carrier."""
        if carrier_id in self._carriers:
            raise ConveyorError(f"Carrier {carrier_id} already exists")
        cid = CarrierId(carrier_id)
        cs = CarrierState(carrier_id=cid)
        self._carriers[carrier_id] = cs
        return cs

    def place_carrier(self, carrier: CarrierState, position: str, wip_id: str) -> None:
        """Place a carrier (with WIP) at a specific position."""
        if position not in self._occupancy:
            raise ConveyorError(f"Unknown position: {position}")
        if self._occupancy[position] is not None:
            raise ConveyorError(
                f"Position {position} already occupied by "
                f"{self._occupancy[position].carrier_id}"
            )
        carrier.load(wip_id)
        self._occupancy[position] = carrier
        self._position_complete[position] = False

    def place_empty_carrier(self, carrier: CarrierState, position: str) -> None:
        """Place an empty carrier at a position (for line entry)."""
        if position not in self._occupancy:
            raise ConveyorError(f"Unknown position: {position}")
        if self._occupancy[position] is not None:
            raise ConveyorError(
                f"Position {position} already occupied"
            )
        self._occupancy[position] = carrier
        self._position_complete[position] = False

    # -- Dwell / completion --

    def mark_position_complete(self, position: str) -> None:
        """Mark that a station has completed its work for this dwell."""
        if position not in self._occupancy:
            raise ConveyorError(f"Unknown position: {position}")
        self._position_complete[position] = True

    def all_occupied_complete(self) -> bool:
        """Check if all occupied positions have completed work."""
        for pos in self.occupied_positions():
            if not self._position_complete[pos]:
                return False
        return True

    def is_position_complete(self, position: str) -> bool:
        return self._position_complete.get(position, False)

    # -- State transitions --

    def begin_dwell(self, dwell_time_s: float) -> None:
        """Transition: INDEXING → STOPPED.

        Called after the conveyor finishes indexing.
        Resets completion flags for all occupied positions.
        """
        if self.state not in (ConveyorState.INDEXING, ConveyorState.STOPPED):
            raise ConveyorError(
                f"Cannot begin dwell from state {self.state.value}"
            )
        self.state = ConveyorState.STOPPED
        self._dwell_number += 1
        self._current_dwell_time_s = dwell_time_s
        for pos in self.occupied_positions():
            self._position_complete[pos] = False

    def begin_operating(self) -> None:
        """Transition: STOPPED → OPERATING.

        Called when stations start processing their WIPs.
        """
        if self.state != ConveyorState.STOPPED:
            raise ConveyorError(
                f"Cannot begin operating from state {self.state.value}"
            )
        self.state = ConveyorState.OPERATING

    def check_ready(self) -> bool:
        """Check if all occupied positions are complete.
        If so, transition OPERATING → READY_TO_INDEX.
        Returns True if ready.
        """
        if self.state != ConveyorState.OPERATING:
            return self.state == ConveyorState.READY_TO_INDEX
        if self.all_occupied_complete():
            self.state = ConveyorState.READY_TO_INDEX
            return True
        return False

    def index(self) -> dict[str, Optional[str]]:
        """Transition: READY_TO_INDEX → INDEXING → STOPPED.

        Performs ONE synchronized line-level index:
        All carriers advance one position downstream.

        Returns a mapping of position → wip_id snapshot AFTER index,
        for trace purposes.

        INV-CONV-09: This is a LINE-LEVEL synchronization boundary.
        All carriers move together.
        """
        if self.state != ConveyorState.READY_TO_INDEX:
            raise ConveyorError(
                f"Cannot index from state {self.state.value}"
            )
        self.state = ConveyorState.INDEXING

        # Build new occupancy: shift everything one position downstream
        pos_list = list(self.config.positions)
        new_occupancy: dict[str, Optional[CarrierState]] = {}
        for i, pos in enumerate(pos_list):
            if i == 0:
                # First position (PRE-ASSY): clear after carrier advances
                new_occupancy[pos] = None
            else:
                # Position i gets the carrier from position i-1
                prev_carrier = self._occupancy[pos_list[i - 1]]
                new_occupancy[pos] = prev_carrier

        # Last position: carrier exits (for finished goods)
        # No need to track it; it's released

        self._occupancy = new_occupancy
        for pos in pos_list:
            self._position_complete[pos] = False

        # Return post-index snapshot
        snapshot: dict[str, Optional[str]] = {}
        for pos in pos_list:
            c = self._occupancy[pos]
            snapshot[pos] = c.wip_id if c else None

        return snapshot

    def reset(self) -> None:
        """Reset the conveyor to initial state."""
        self.state = ConveyorState.STOPPED
        self._dwell_number = 0
        self._current_dwell_time_s = 0.0
        for pos in self.config.positions:
            self._occupancy[pos] = None
            self._position_complete[pos] = False
        self._carriers.clear()


class ConveyorError(ValueError):
    """Raised when a conveyor invariant is violated."""
