"""ASSY indexed line runtime — synchronized stop-and-go production line.

M6-S02: Implements the authoritative TIPA ASSY runtime based on the
CLOSED M6-S01 baseline.

Key semantics (INV-CONV-01 through INV-CONV-09):
- ONE conveyor lane, stop-and-go indexed.
- Processing occurs ONLY while stopped.
- Multiple WIPs at different stations operate during the SAME dwell.
- INDEX is a line-level synchronization boundary.
- AP04 creates child MOTOR WIP with genealogy.
- WIP identity ≠ carrier identity.
- No conveyor physics. Deterministic synchronous execution.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.carrier import CarrierId, CarrierState, CarrierError
from virtual_factory.assembly.conveyor import (
    ConveyorConfig,
    ConveyorLine,
    ConveyorState,
    ConveyorError,
)
from virtual_factory.assembly.genealogy import (
    GenealogyRecord,
    GenealogyStore,
    GenealogyError,
)
from virtual_factory.assembly.upstream import (
    UpstreamConfig,
    UpstreamProducer,
    UpstreamWip,
)


# ═══════════════════════════════════════════════════════════════
# WIP State (separate from existing assembly.wip for ASSY line)
# ═══════════════════════════════════════════════════════════════

class WipLifecycle(str, enum.Enum):
    """ASSY WIP lifecycle states (demo semantic names)."""
    CREATED = "created"
    IN_ASSY = "in_assy"
    AT_STATION = "at_station"
    COMPLETED_STATION = "completed_station"
    JOINED = "joined"         # After AP04: child created, parents archived
    RELEASED = "released"     # Passed AP11 final QC


@dataclass(slots=True)
class AssyWipState:
    """Runtime state for one WIP in the ASSY line."""

    wip_id: str
    lifecycle: WipLifecycle = WipLifecycle.CREATED
    current_position: str = ""
    station_count: int = 0
    is_child_of_join: bool = False
    parent_wip_ids: tuple[str, ...] = field(default_factory=tuple)


# ═══════════════════════════════════════════════════════════════
# Line Configuration
# ═══════════════════════════════════════════════════════════════

@dataclass
class AssyLineConfig:
    """Configuration for the ASSY indexed line.

    All values configuration-driven per M6-S01 baseline.
    """

    # Conveyor
    conveyor: ConveyorConfig = field(default_factory=ConveyorConfig)

    # Upstream
    upstream: UpstreamConfig = field(default_factory=UpstreamConfig)

    # Station operation durations (per station, seconds)
    station_durations: dict[str, float] = field(default_factory=lambda: {
        "PRE-ASSY": 30.0,
        "AP01": 60.0,
        "AP02": 75.0,
        "AP03": 45.0,
        "AP04": 60.0,
        "AP05": 90.0,
        "AP06": 60.0,
        "AP07": 30.0,
        "AP08": 30.0,
        "AP09": 45.0,
        "AP10": 45.0,
        "AP11": 30.0,
    })

    # AP04 join
    ap04_required_parent_sources: tuple[str, str] = ("SSO2", "RSO2")
    ap04_component_list: tuple[str, ...] = ()  # empty placeholder (PTC-05)

    # Identity
    motor_wip_prefix: str = "MTR"

    # Simulation
    simulation_time_multiplier: float = 1.0


# ═══════════════════════════════════════════════════════════════
# Trace / Event
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class LineEvent:
    """A trace event from the ASSY line runtime."""

    event_type: str
    simulation_time_s: float
    dwell_number: int
    position: str = ""
    wip_id: str = ""
    detail: str = ""

    def __str__(self) -> str:
        parts = [f"[t={self.simulation_time_s:.1f}s]", f"dwell={self.dwell_number}"]
        if self.position:
            parts.append(self.position)
        parts.append(self.event_type)
        if self.wip_id:
            parts.append(self.wip_id)
        if self.detail:
            parts.append(f"({self.detail})")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════
# ASSY Line Runtime
# ═══════════════════════════════════════════════════════════════

@dataclass
class AssyLineRuntime:
    """Synchronized indexed ASSY line runtime.

    Owns the conveyor, upstream producer, WIP registry, genealogy store,
    and trace buffer.

    Execution model (per dwell):
    1. Conveyor is STOPPED.
    2. All occupied positions execute station logic (sequential eval, same dwell).
    3. All stations complete → READY_TO_INDEX.
    4. INDEX: all carriers advance one position (line-level sync boundary).
    """

    config: AssyLineConfig = field(default_factory=AssyLineConfig)
    conveyor: ConveyorLine = field(init=False)
    upstream: UpstreamProducer = field(init=False)
    genealogy: GenealogyStore = field(default_factory=GenealogyStore)
    _wips: dict[str, AssyWipState] = field(default_factory=dict)
    _rso2_wips: dict[str, UpstreamWip] = field(default_factory=dict)
    _trace: list[LineEvent] = field(default_factory=list)
    _motor_seq: int = 0
    _simulation_time_s: float = 0.0

    def __post_init__(self) -> None:
        self.conveyor = ConveyorLine(config=self.config.conveyor)
        self.upstream = UpstreamProducer(config=self.config.upstream)

    # -- Properties --

    @property
    def simulation_time_s(self) -> float:
        return self._simulation_time_s

    @property
    def trace(self) -> tuple[LineEvent, ...]:
        return tuple(self._trace)

    @property
    def wip_count(self) -> int:
        return len(self._wips)

    @property
    def motor_count(self) -> int:
        return self._motor_seq

    # -- WIP registry --

    def get_wip(self, wip_id: str) -> Optional[AssyWipState]:
        return self._wips.get(wip_id)

    def _add_wip(self, wip_id: str, position: str = "") -> AssyWipState:
        ws = AssyWipState(wip_id=wip_id, lifecycle=WipLifecycle.CREATED,
                          current_position=position)
        self._wips[wip_id] = ws
        return ws

    # -- Upstream production --

    def produce_sso2_wip(self) -> str:
        """Create SSO2 WIP and register it. Returns wip_id."""
        uw = self.upstream.produce_sso2(self._simulation_time_s)
        self._add_wip(uw.wip_id)
        self._emit("SSO2_PRODUCED", wip_id=uw.wip_id,
                   detail=f"source=SSO2, op={self.config.upstream.sso2_operation_type}")
        return uw.wip_id

    def produce_rso2_wip(self) -> str:
        """Create RSO2 WIP and store in RSO2 buffer. Returns wip_id."""
        uw = self.upstream.produce_rso2(self._simulation_time_s)
        self._rso2_wips[uw.wip_id] = uw
        self._emit("RSO2_PRODUCED", wip_id=uw.wip_id,
                   detail=f"source=RSO2, op={self.config.upstream.rso2_operation_type}")
        return uw.wip_id

    # -- Line entry --

    def introduce_to_assy(self, wip_id: str, carrier_id: str) -> None:
        """Place a WIP on a carrier at PRE-ASSY."""
        ws = self._wips.get(wip_id)
        if ws is None:
            raise AssyLineError(f"Unknown WIP: {wip_id}")

        # Create carrier if needed
        carrier = self.conveyor.get_carrier(carrier_id)
        if carrier is None:
            carrier = self.conveyor.create_carrier(carrier_id)

        self.conveyor.place_carrier(carrier, "PRE-ASSY", wip_id)
        ws.lifecycle = WipLifecycle.IN_ASSY
        ws.current_position = "PRE-ASSY"
        self._emit("LINE_ENTRY", position="PRE-ASSY", wip_id=wip_id,
                   detail=f"carrier={carrier_id}")

    # -- Dwell execution --

    def execute_dwell(self) -> list[LineEvent]:
        """Execute one complete dwell cycle: STOP → OPERATE → READY.

        All occupied positions are processed within the SAME dwell window.
        Station evaluation order is deterministic (position order).

        INV-CONV-09: Sequential evaluation inside one dwell — manufacturing
        semantics of concurrent operation, NOT CPU concurrency.
        """
        events: list[LineEvent] = []

        # Begin dwell
        dwell_time = self.config.conveyor.nominal_line_dwell_time_s
        self.conveyor.begin_dwell(dwell_time)
        self._emit_dwell_event("DWELL_BEGIN", events)

        # Begin operating
        self.conveyor.begin_operating()

        # Process each occupied position
        for pos in self.conveyor.occupied_positions():
            carrier = self.conveyor.carrier_at(pos)
            if carrier is None or carrier.wip_id is None:
                continue

            wip_id = carrier.wip_id
            ws = self._wips.get(wip_id)
            if ws is None:
                continue

            ws.lifecycle = WipLifecycle.AT_STATION
            ws.current_position = pos

            # Execute station logic
            station_events = self._execute_station(pos, wip_id)
            events.extend(station_events)

            # Mark position complete
            self.conveyor.mark_position_complete(pos)
            ws.station_count += 1
            ws.lifecycle = WipLifecycle.COMPLETED_STATION

        # Check ready
        ready = self.conveyor.check_ready()
        if ready:
            self._emit_dwell_event("DWELL_READY", events)
        else:
            # Overrun: stay stopped (PROVISIONAL_FOR_DEMO)
            self._emit_dwell_event("DWELL_EXTENDED", events)

        self._trace.extend(events)
        return events

    def _execute_station(self, position: str, wip_id: str) -> list[LineEvent]:
        """Execute station logic for one position during a dwell.

        Returns trace events.
        """
        events: list[LineEvent] = []

        if position == "PRE-ASSY":
            events.append(self._make_event("STATION_START", position, wip_id,
                                           "PRE-ASSY operation"))
            events.append(self._make_event("STATION_COMPLETE", position, wip_id,
                                           "PRE-ASSY done"))

        elif position == "AP04":
            # JOIN: the core M6-S02 feature
            join_events = self._execute_ap04_join(wip_id)
            events.extend(join_events)

        elif position == "AP11":
            # Final QC / release
            events.append(self._make_event("STATION_START", position, wip_id,
                                           "final QC"))
            ws = self._wips.get(wip_id)
            if ws:
                ws.lifecycle = WipLifecycle.RELEASED
            events.append(self._make_event("STATION_COMPLETE", position, wip_id,
                                           "released finished good"))

        else:
            # Generic station
            duration = self.config.station_durations.get(position, 60.0)
            events.append(self._make_event("STATION_START", position, wip_id,
                                           f"duration={duration}s"))
            events.append(self._make_event("STATION_COMPLETE", position, wip_id,
                                           "done"))

        return events

    def _execute_ap04_join(self, parent_a_wip_id: str) -> list[LineEvent]:
        """Execute AP04 JOIN: Parent A + Parent B → Child MOTOR.

        Parent A = SSO2-derived WIP currently at AP04.
        Parent B = next available RSO2 WIP from buffer.
        """
        events: list[LineEvent] = []
        events.append(self._make_event("STATION_START", "AP04", parent_a_wip_id,
                                       "JOIN begin"))

        # Consume next RSO2 WIP
        if not self._rso2_wips:
            raise AssyLineError("AP04 JOIN: no RSO2 WIP available in buffer")

        # FIFO: take the earliest RSO2 WIP
        rso2_key = next(iter(self._rso2_wips))
        rso2_wip = self._rso2_wips.pop(rso2_key)
        parent_b_wip_id = rso2_wip.wip_id

        # Create child MOTOR WIP
        self._motor_seq += 1
        child_id = f"{self.config.motor_wip_prefix}-{self._motor_seq:04d}"

        # Create genealogy
        genealogy = GenealogyRecord(
            child_wip_id=child_id,
            parent_wip_ids=(parent_a_wip_id, parent_b_wip_id),
            component_ids=self.config.ap04_component_list,
            join_station="AP04",
            join_time_s=self._simulation_time_s,
            relationship_type="assembly_join",
        )
        self.genealogy.record(genealogy)

        # Register child WIP
        child_ws = self._add_wip(child_id, position="AP04")
        child_ws.lifecycle = WipLifecycle.JOINED
        child_ws.is_child_of_join = True
        child_ws.parent_wip_ids = (parent_a_wip_id, parent_b_wip_id)

        # Archive parent A (mark as joined)
        parent_ws = self._wips.get(parent_a_wip_id)
        if parent_ws:
            parent_ws.lifecycle = WipLifecycle.JOINED

        # Update the carrier at AP04: replace parent WIP with child WIP
        carrier = self.conveyor.carrier_at("AP04")
        if carrier and carrier.wip_id == parent_a_wip_id:
            carrier.clear()
            carrier.load(child_id)

        events.append(self._make_event("AP04_JOIN", "AP04", child_id,
                                       f"parents={parent_a_wip_id}+{parent_b_wip_id}, "
                                       f"components={list(self.config.ap04_component_list)}"))
        events.append(self._make_event("STATION_COMPLETE", "AP04", child_id,
                                       "JOIN done"))

        # Emit to trace
        self._trace.extend(events)

        return events

    # -- Line index --

    def index_line(self) -> list[LineEvent]:
        """Advance the conveyor by one index.

        All carriers move one position downstream (INV-CONV-09:
        line-level synchronization boundary).
        """
        events: list[LineEvent] = []
        snapshot = self.conveyor.index()

        self._emit_dwell_event("INDEX", events)

        # Update WIP positions after index
        for pos, wip_id in snapshot.items():
            if wip_id:
                ws = self._wips.get(wip_id)
                if ws:
                    ws.current_position = pos
                    events.append(self._make_event(
                        "WIP_MOVED", pos, wip_id,
                        f"→ {pos}"
                    ))

            # Check for exit (last position became empty after index)
            # The carrier that was at AP11 is now off the line
            last_pos = self.config.conveyor.positions[-1]
            if pos == last_pos:
                prev_carrier_wip = self.conveyor.wip_at(last_pos)
                # The previous AP11 carrier already moved out
                # Mark the WIP that was at AP11 as released
                # (We track this via the genealogy store or WIP state)

        # After index, transition to STOPPED
        self.conveyor.begin_dwell(self.config.conveyor.nominal_line_dwell_time_s)
        self._emit_dwell_event("DWELL_BEGIN", events)

        self._trace.extend(events)
        return events

    # -- Full cycle --

    def run_dwell_cycle(self) -> list[LineEvent]:
        """Run one complete dwell + index cycle.

        Returns all trace events for this cycle.
        """
        all_events: list[LineEvent] = []

        dwell_events = self.execute_dwell()
        all_events.extend(dwell_events)

        if self.conveyor.state == ConveyorState.READY_TO_INDEX:
            idx_events = self.index_line()
            all_events.extend(idx_events)

        return all_events

    # -- Helpers --

    def _emit(self, event_type: str, position: str = "", wip_id: str = "",
              detail: str = "") -> None:
        self._trace.append(self._make_event(event_type, position, wip_id, detail))

    def _emit_dwell_event(self, event_type: str, events: list[LineEvent]) -> None:
        events.append(LineEvent(
            event_type=event_type,
            simulation_time_s=self._simulation_time_s,
            dwell_number=self.conveyor.dwell_number,
            detail=f"state={self.conveyor.state.value}",
        ))

    def _make_event(self, event_type: str, position: str, wip_id: str,
                    detail: str) -> LineEvent:
        return LineEvent(
            event_type=event_type,
            simulation_time_s=self._simulation_time_s,
            dwell_number=self.conveyor.dwell_number,
            position=position,
            wip_id=wip_id,
            detail=detail,
        )

    # -- Reset --

    def reset(self) -> None:
        """Reset the entire line to initial state."""
        self.conveyor.reset()
        self.upstream.reset()
        self.genealogy = GenealogyStore()
        self._wips.clear()
        self._rso2_wips.clear()
        self._trace.clear()
        self._motor_seq = 0
        self._simulation_time_s = 0.0


class AssyLineError(RuntimeError):
    """Raised when an ASSY line invariant is violated."""
