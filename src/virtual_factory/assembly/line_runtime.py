"""ASSY indexed line runtime — synchronized stop-and-go production line.

M6-S02 / M6-S02-C01: Implements the authoritative TIPA ASSY runtime based on
the CLOSED M6-S01 baseline.

Key semantics (INV-CONV-01 through INV-CONV-09):
- ONE conveyor lane, stop-and-go indexed.
- Processing occurs ONLY while stopped.
- Multiple WIPs at different stations operate during the SAME dwell.
- INDEX is a line-level synchronization boundary.
- AP04 creates child MOTOR WIP with genealogy.
- WIP identity ≠ carrier identity.
- No conveyor physics. Deterministic synchronous execution.

M6-S02-C01 additions:
- Simulated time advances with dwell + index durations (C01-01).
- Station operation progress tracked; overrun when duration > dwell (C01-02).
- Lifecycle transitions are authoritative — no generic overwrite (C01-03).
- Dwell begins once per cycle — dwell_number increments in execute_dwell() (C01-04).
- Trace events emitted once — helpers return, caller appends (C01-05).
"""

from __future__ import annotations

import enum
import yaml
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.carrier import CarrierState
from virtual_factory.assembly.conveyor import (
    ConveyorConfig,
    ConveyorLine,
    ConveyorState,
)
from virtual_factory.assembly.genealogy import (
    GenealogyRecord,
    GenealogyStore,
)
from virtual_factory.assembly.upstream import (
    UpstreamConfig,
    UpstreamProducer,
    UpstreamWip,
)
from virtual_factory.assembly.quality_records import (
    QualityConfig,
    StationQualityConfig,
    QualityRecord,
    QualityHistory,
    QualityStatus,
    CheckType,
    MeasurementValue,
    resolve_quality_disposition,
)


# ═══════════════════════════════════════════════════════════════
# WIP State
# ═══════════════════════════════════════════════════════════════

class WipLifecycle(str, enum.Enum):
    """ASSY WIP lifecycle states (demo semantic names)."""
    CREATED = "created"
    IN_ASSY = "in_assy"
    AT_STATION = "at_station"
    COMPLETED_STATION = "completed_station"
    JOINED = "joined"
    RELEASED = "released"


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
    """Configuration for the ASSY indexed line. All values config-driven."""
    conveyor: ConveyorConfig = field(default_factory=ConveyorConfig)
    upstream: UpstreamConfig = field(default_factory=UpstreamConfig)
    station_durations: dict[str, float] = field(default_factory=lambda: {
        "PRE-ASSY": 30.0, "AP01": 60.0, "AP02": 75.0, "AP03": 45.0,
        "AP04": 60.0, "AP05": 90.0, "AP06": 60.0, "AP07": 30.0,
        "AP08": 30.0, "AP09": 45.0, "AP10": 45.0, "AP11": 30.0,
    })
    ap04_required_parent_sources: tuple[str, str] = ("SSO2", "RSO2")
    ap04_component_list: tuple[str, ...] = ()
    motor_wip_prefix: str = "MTR"
    simulation_time_multiplier: float = 1.0
    quality: QualityConfig = field(default_factory=QualityConfig)


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
# YAML Config Loader (M6-S02-C01)
# ═══════════════════════════════════════════════════════════════

def load_assy_config_from_yaml(path: str) -> AssyLineConfig:
    """Load an AssyLineConfig from a TIPA ASSY demo YAML file.

    CONFIG_RUNTIME_STATUS: LOADED_AND_USED.
    The YAML is the authoritative source for the TIPA demo.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    config = AssyLineConfig()

    conv_data = data.get("conveyor", {})
    if conv_data:
        config.conveyor.nominal_line_dwell_time_s = float(
            conv_data.get("nominal_line_dwell_time_s", 120.0))
        config.conveyor.index_movement_duration_s = float(
            conv_data.get("index_movement_duration_s", 0.0))
        positions = conv_data.get("positions")
        if positions:
            config.conveyor.positions = tuple(positions)

    up_data = data.get("upstream", {})
    if up_data:
        config.upstream = UpstreamConfig(
            sso2_wip_prefix=up_data.get("sso2_wip_prefix", "SSO2"),
            rso2_wip_prefix=up_data.get("rso2_wip_prefix", "RSO2"),
            sso2_production_interval_s=float(up_data.get("sso2_production_interval_s", 120.0)),
            rso2_production_interval_s=float(up_data.get("rso2_production_interval_s", 120.0)),
            sso2_operation_type=up_data.get("sso2_operation_type", "shrink_fit"),
            rso2_operation_type=up_data.get("rso2_operation_type", "rotor_assembly"),
        )

    sd = data.get("station_durations", {})
    if sd:
        for key, val in sd.items():
            config.station_durations[key] = float(val)

    ap04 = data.get("ap04", {})
    if ap04:
        parents = ap04.get("required_parent_sources")
        if parents:
            config.ap04_required_parent_sources = tuple(parents)
        comps = ap04.get("component_list")
        if comps is not None:
            config.ap04_component_list = tuple(comps)

    ident = data.get("identity", {})
    if ident:
        config.motor_wip_prefix = ident.get("motor_wip_prefix", "MTR")

    sim = data.get("simulation", {})
    if sim:
        config.simulation_time_multiplier = float(sim.get("time_multiplier", 1.0))

    # Quality (M6-S03)
    quality_data = data.get("quality", {})
    if quality_data:
        for station_key in ("ap03", "ap06", "ap08", "ap11"):
            sq = quality_data.get(station_key.upper() if station_key.upper() in quality_data else station_key, {})
            if sq:
                sqc = StationQualityConfig(
                    max_attempts=int(sq.get("max_attempts", 1)),
                    scenario=sq.get("scenario", "PASS"),
                )
                overrides = sq.get("overrides", {})
                if overrides:
                    sqc.overrides = {int(k): list(v) for k, v in overrides.items()}
                setattr(config.quality, station_key, sqc)

    return config


# ═══════════════════════════════════════════════════════════════
# ASSY Line Runtime
# ═══════════════════════════════════════════════════════════════

@dataclass
class AssyLineRuntime:
    """Synchronized indexed ASSY line runtime.

    M6-S02-C01 execution model:

    execute_dwell():
      1. Conveyor STOPPED → OPERATING; dwell_number incremented ONCE.
      2. actual_dwell = max(nominal_dwell, max(remaining_station_time)).
      3. All occupied stations accumulate actual_dwell toward required duration.
      4. Stations completing are executed; stations not completing emit progress.
      5. simulation_time_s += actual_dwell.
      6. If all complete → READY_TO_INDEX; else stays OPERATING (overrun).

    index_line():
      1. READY_TO_INDEX → INDEXING → STOPPED.
      2. All carriers advance one position.
      3. simulation_time_s += index_movement_duration_s.
      4. dwell_number NOT incremented.
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
    _station_elapsed: dict[str, float] = field(default_factory=dict)
    _quality_histories: dict[str, QualityHistory] = field(default_factory=dict)
    _quality_seq: int = 0

    def __post_init__(self) -> None:
        self.conveyor = ConveyorLine(config=self.config.conveyor)
        self.upstream = UpstreamProducer(config=self.config.upstream)
        for pos in self.conveyor.positions:
            self._station_elapsed[pos] = 0.0

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

    @property
    def rso2_buffer_size(self) -> int:
        """Public: number of RSO2 WIPs available for AP04 join."""
        return len(self._rso2_wips)

    def get_quality_history(self, wip_id: str) -> Optional[QualityHistory]:
        """Public: quality history for a WIP."""
        return self._quality_histories.get(wip_id)

    def get_current_quality_status(self, wip_id: str) -> QualityStatus:
        """Public: current quality status for a WIP."""
        h = self._quality_histories.get(wip_id)
        return h.current_status if h else QualityStatus.CLEAR

    def _ensure_quality_history(self, wip_id: str) -> QualityHistory:
        if wip_id not in self._quality_histories:
            self._quality_histories[wip_id] = QualityHistory()
        return self._quality_histories[wip_id]

    def _next_quality_id(self) -> str:
        self._quality_seq += 1
        return f"QR-{self._quality_seq:04d}"

    # -- WIP registry --

    def get_wip(self, wip_id: str) -> Optional[AssyWipState]:
        return self._wips.get(wip_id)

    def _add_wip(self, wip_id: str, position: str = "") -> AssyWipState:
        ws = AssyWipState(wip_id=wip_id, lifecycle=WipLifecycle.CREATED,
                          current_position=position)
        self._wips[wip_id] = ws
        return ws

    # -- Upstream --

    def produce_sso2_wip(self) -> str:
        uw = self.upstream.produce_sso2(self._simulation_time_s)
        self._add_wip(uw.wip_id)
        self._emit("SSO2_PRODUCED", wip_id=uw.wip_id,
                   detail=f"source=SSO2")
        return uw.wip_id

    def produce_rso2_wip(self) -> str:
        uw = self.upstream.produce_rso2(self._simulation_time_s)
        self._rso2_wips[uw.wip_id] = uw
        self._emit("RSO2_PRODUCED", wip_id=uw.wip_id,
                   detail=f"source=RSO2")
        return uw.wip_id

    # -- Line entry --

    def introduce_to_assy(self, wip_id: str, carrier_id: str) -> None:
        ws = self._wips.get(wip_id)
        if ws is None:
            raise AssyLineError(f"Unknown WIP: {wip_id}")
        carrier = self.conveyor.get_carrier(carrier_id)
        if carrier is None:
            carrier = self.conveyor.create_carrier(carrier_id)
        self.conveyor.place_carrier(carrier, "PRE-ASSY", wip_id)
        ws.lifecycle = WipLifecycle.IN_ASSY
        ws.current_position = "PRE-ASSY"
        self._station_elapsed["PRE-ASSY"] = 0.0
        self._emit("LINE_ENTRY", position="PRE-ASSY", wip_id=wip_id,
                   detail=f"carrier={carrier_id}")

    # ═══════════════════════════════════════════════════════
    # DWELL (C01-02: progress + overrun; C01-04: single start)
    # ═══════════════════════════════════════════════════════

    def execute_dwell(self) -> list[LineEvent]:
        """Execute one dwell.  dwell_number increments HERE.

        C01-02: actual_dwell = max(nominal, max_remaining).
        Stations accumulate elapsed; complete when elapsed >= required.
        """
        all_events: list[LineEvent] = []

        if self.conveyor.state not in (ConveyorState.STOPPED, ConveyorState.OPERATING):
            raise AssyLineError(
                f"Cannot execute dwell: conveyor is {self.conveyor.state.value}"
            )

        # C01-04: SINGLE dwell start — dwell_number increments here
        # Only increment on first entry (STOPPED → OPERATING), not on retry
        if self.conveyor.state == ConveyorState.STOPPED:
            self.conveyor._dwell_number += 1
            all_events.append(self._dwell_event("DWELL_BEGIN"))
        else:
            all_events.append(self._dwell_event("DWELL_CONTINUE (retest/reinspect)"))
        self.conveyor.state = ConveyorState.OPERATING

        nominal = self.config.conveyor.nominal_line_dwell_time_s

        # Determine max remaining station time
        max_remaining = 0.0
        for pos in self.conveyor.occupied_positions():
            required = self.config.station_durations.get(pos, 60.0)
            elapsed = self._station_elapsed.get(pos, 0.0)
            remaining = max(0.0, required - elapsed)
            if remaining > max_remaining:
                max_remaining = remaining

        actual_dwell = max(nominal, max_remaining)

        # Apply dwell time to all occupied stations
        for pos in self.conveyor.occupied_positions():
            wip_id = self.conveyor.wip_at(pos)
            if wip_id is None:
                continue

            ws = self._wips.get(wip_id)
            if ws is None:
                continue

            required = self.config.station_durations.get(pos, 60.0)
            self._station_elapsed[pos] = self._station_elapsed.get(pos, 0.0) + actual_dwell

            ws.current_position = pos

            if self._station_elapsed[pos] >= required:
                # Station timer completed
                station_events = self._execute_station(pos, wip_id)
                all_events.extend(station_events)

                # M6-S03: quality HOLD prevents completion
                qstatus = self.get_current_quality_status(wip_id)
                if qstatus in (QualityStatus.RETEST_PENDING, QualityStatus.REINSPECT_PENDING,
                               QualityStatus.FAILED_FINAL):
                    # Keep station incomplete — line stays, retry next dwell
                    self._station_elapsed[pos] = 0.0  # restart timer for retest
                else:
                    self.conveyor.mark_position_complete(pos)
                    self._station_elapsed[pos] = 0.0
            else:
                all_events.append(self._make_event(
                    "STATION_PROGRESS", pos, wip_id,
                    f"elapsed={self._station_elapsed[pos]:.0f}s "
                    f"/ required={required:.0f}s"
                ))

        # C01-01: advance simulation time
        self._simulation_time_s += actual_dwell

        ready = self.conveyor.check_ready()
        if ready:
            all_events.append(self._dwell_event(
                f"DWELL_READY actual={actual_dwell:.0f}s"))
        else:
            all_events.append(self._dwell_event(
                f"DWELL_EXTENDED actual={actual_dwell:.0f}s overrun"))

        self._trace.extend(all_events)
        return all_events

    # ═══════════════════════════════════════════════════════
    # STATION EXECUTION (C01-03: authoritative lifecycle)
    # ═══════════════════════════════════════════════════════

    def _execute_station(self, position: str, wip_id: str) -> list[LineEvent]:
        """Execute station logic. Returns events; caller owns trace append.

        M6-S03: Quality stations (AP03, AP06, AP08, AP11) generate
        quality records and may set HOLD preventing completion.
        """
        events: list[LineEvent] = []

        if position == "PRE-ASSY":
            events.append(self._make_event("STATION_START", position, wip_id, "PRE-ASSY"))
            ws = self._wips.get(wip_id)
            if ws:
                ws.station_count += 1
                ws.lifecycle = WipLifecycle.COMPLETED_STATION
            events.append(self._make_event("STATION_COMPLETE", position, wip_id, "done"))

        elif position == "AP04":
            events.extend(self._execute_ap04_join(wip_id))

        elif position == "AP03":
            events.extend(self._execute_quality_station(position, wip_id, "ap03", CheckType.CHECKLIST))

        elif position == "AP06":
            events.extend(self._execute_quality_station(position, wip_id, "ap06", CheckType.TEST))

        elif position == "AP08":
            events.extend(self._execute_quality_station(position, wip_id, "ap08", CheckType.VISUAL_INSPECTION))

        elif position == "AP11":
            events.extend(self._execute_quality_station(position, wip_id, "ap11", CheckType.FINAL_QC))

        else:
            dur = self.config.station_durations.get(position, 60.0)
            events.append(self._make_event("STATION_START", position, wip_id,
                                           f"duration={dur:.0f}s"))
            ws = self._wips.get(wip_id)
            if ws:
                ws.station_count += 1
                ws.lifecycle = WipLifecycle.COMPLETED_STATION
            events.append(self._make_event("STATION_COMPLETE", position, wip_id, "done"))

        return events

    # ═══════════════════════════════════════════════════════
    # QUALITY STATION (M6-S03)
    # ═══════════════════════════════════════════════════════

    def _execute_quality_station(
        self, position: str, wip_id: str, station_key: str, check_type: CheckType,
    ) -> list[LineEvent]:
        """Execute a quality station (AP03, AP06, AP08, AP11).

        FAILED_FINAL is terminal: no further attempts, no new records.
        """
        events: list[LineEvent] = []

        # M6-S03-C01.1: FAILED_FINAL is idempotent — no further processing
        history = self._ensure_quality_history(wip_id)
        if history.current_status == QualityStatus.FAILED_FINAL:
            events.append(self._make_event(
                "QUALITY_WAITING_DISPOSITION", position, wip_id,
                "FAILED_FINAL — awaiting disposition"))
            return events

        qcfg = self.config.quality.get(station_key)
        attempt = history.attempt_count(station_key) + 1

        # Resolve disposition
        ws = self._wips.get(wip_id)
        motor_seq = self._motor_seq  # approximate: use current motor sequence
        # For child WIPs, use their motor number
        if ws and ws.is_child_of_join:
            # Extract motor number from ID like MTR-0003
            try:
                motor_seq = int(wip_id.split("-")[-1])
            except (ValueError, IndexError):
                pass

        disposition = resolve_quality_disposition(
            station_key, motor_seq, attempt, qcfg, check_type)

        events.append(self._make_event(
            "QUALITY_START", position, wip_id,
            f"type={check_type.value} attempt={attempt}"))

        # Build quality record
        measurements: list[MeasurementValue] = []
        checklist: list[str] = []

        if check_type == CheckType.TEST:
            # AP06: synthetic electrical measurements (DEMO_SYNTHETIC)
            measurements = [
                MeasurementValue("R_U-V", 0.45 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
                MeasurementValue("R_V-W", 0.47 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
                MeasurementValue("R_W-U", 0.44 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
            ]
        elif check_type == CheckType.CHECKLIST:
            checklist = ["mechanical_prep_ok", "visual_check_ok", "measurement_subset_ok"]
        elif check_type == CheckType.VISUAL_INSPECTION:
            checklist = ["surface_quality", "label_presence", "assembly_alignment"]
        elif check_type == CheckType.FINAL_QC:
            checklist = ["packaging_integrity", "label_correct", "documentation_complete"]

        # For FAIL/NG: measurement out of spec
        if disposition in ("FAIL", "NG") and measurements:
            # Make first measurement out of range (DEMO_SYNTHETIC)
            measurements = [MeasurementValue(
                m.name, m.expected_min - 0.1 if m.expected_min else 0.01,
                m.unit, m.expected_min, m.expected_max
            ) for m in measurements]

        record = QualityRecord(
            record_id=self._next_quality_id(),
            wip_id=wip_id,
            station_id=position,
            check_type=check_type,
            disposition=disposition,
            attempt_number=attempt,
            simulation_time_s=self._simulation_time_s + self._station_elapsed.get(position, 0.0),
            measurements=tuple(measurements),
            checklist_items=tuple(checklist),
        )
        history.add_record(record)

        events.append(self._make_event(
            "QUALITY_RESULT", position, wip_id,
            f"disposition={disposition} attempt={attempt}"))

        if disposition in ("FAIL", "NG"):
            # Quality HOLD — station NOT complete
            history.set_status(
                QualityStatus.RETEST_PENDING if check_type == CheckType.TEST
                else QualityStatus.REINSPECT_PENDING)
            events.append(self._make_event(
                "QUALITY_HOLD", position, wip_id,
                f"status={history.current_status.value}"))

            # Check max attempts
            if attempt >= qcfg.max_attempts:
                history.set_status(QualityStatus.FAILED_FINAL)
                events.append(self._make_event(
                    "QUALITY_FAILED_FINAL", position, wip_id,
                    f"max_attempts={qcfg.max_attempts} exhausted"))
                # FAILED_FINAL: station NOT marked complete (C01: blocks progression)
                # Conveyor stays stopped; WIP remains at this station

            # Station NOT marked complete — line stays, quality HOLD
        else:
            # PASS
            history.set_status(QualityStatus.CLEAR)
            if position == "AP11":
                ws = self._wips.get(wip_id)
                if ws:
                    ws.lifecycle = WipLifecycle.RELEASED
                    ws.station_count += 1
                events.append(self._make_event(
                    "STATION_COMPLETE", position, wip_id, "RELEASED"))
            else:
                ws = self._wips.get(wip_id)
                if ws:
                    ws.station_count += 1
                    ws.lifecycle = WipLifecycle.COMPLETED_STATION
                events.append(self._make_event(
                    "STATION_COMPLETE", position, wip_id, "PASS"))

        return events

    # ═══════════════════════════════════════════════════════
    # AP04 JOIN (C01-05: returns events; caller appends ONCE)
    # ═══════════════════════════════════════════════════════

    def _execute_ap04_join(self, parent_a_wip_id: str) -> list[LineEvent]:
        """AP04 JOIN. Returns events — does NOT append to self._trace."""
        events: list[LineEvent] = []
        events.append(self._make_event("STATION_START", "AP04", parent_a_wip_id,
                                       "JOIN begin"))

        if not self._rso2_wips:
            raise AssyLineError("AP04 JOIN: no RSO2 WIP available")

        rso2_key = next(iter(self._rso2_wips))
        rso2_wip = self._rso2_wips.pop(rso2_key)
        parent_b_wip_id = rso2_wip.wip_id

        self._motor_seq += 1
        child_id = f"{self.config.motor_wip_prefix}-{self._motor_seq:04d}"

        genealogy = GenealogyRecord(
            child_wip_id=child_id,
            parent_wip_ids=(parent_a_wip_id, parent_b_wip_id),
            component_ids=self.config.ap04_component_list,
            join_station="AP04",
            join_time_s=self._simulation_time_s,
            relationship_type="assembly_join",
        )
        self.genealogy.record(genealogy)

        child_ws = self._add_wip(child_id, position="AP04")
        child_ws.lifecycle = WipLifecycle.JOINED
        child_ws.is_child_of_join = True
        child_ws.parent_wip_ids = (parent_a_wip_id, parent_b_wip_id)
        child_ws.station_count += 1

        # C01-03: parent A → JOINED, not overwritten
        parent_ws = self._wips.get(parent_a_wip_id)
        if parent_ws:
            parent_ws.lifecycle = WipLifecycle.JOINED
            parent_ws.station_count += 1

        # Carrier handoff
        carrier = self.conveyor.carrier_at("AP04")
        if carrier and carrier.wip_id == parent_a_wip_id:
            carrier.clear()
            carrier.load(child_id)

        events.append(self._make_event("AP04_JOIN", "AP04", child_id,
                                       f"parents={parent_a_wip_id}+{parent_b_wip_id}"))
        events.append(self._make_event("STATION_COMPLETE", "AP04", child_id,
                                       "JOIN done"))

        return events  # C01-05: caller appends to trace ONCE

    # ═══════════════════════════════════════════════════════
    # LINE INDEX (C01-04: does NOT increment dwell_number)
    # ═══════════════════════════════════════════════════════

    def index_line(self) -> list[LineEvent]:
        """Advance all carriers one position.  dwell_number unchanged."""
        events: list[LineEvent] = []

        snapshot = self.conveyor.index()
        self._simulation_time_s += self.config.conveyor.index_movement_duration_s  # C01-01

        events.append(self._dwell_event("INDEX"))

        for pos, wip_id in snapshot.items():
            if wip_id:
                ws = self._wips.get(wip_id)
                if ws:
                    ws.current_position = pos
                    events.append(self._make_event("WIP_MOVED", pos, wip_id, f"→ {pos}"))
                self._station_elapsed[pos] = 0.0  # new WIP at position

        # C01-04: transition to STOPPED without incrementing dwell_number
        self.conveyor.state = ConveyorState.STOPPED

        self._trace.extend(events)
        return events

    # -- Full cycle --

    def run_dwell_cycle(self) -> list[LineEvent]:
        """Public API: one complete dwell + optional index."""
        all_events: list[LineEvent] = []
        all_events.extend(self.execute_dwell())
        if self.conveyor.state == ConveyorState.READY_TO_INDEX:
            all_events.extend(self.index_line())
        return all_events

    # -- Helpers --

    def _emit(self, event_type: str, position: str = "", wip_id: str = "",
              detail: str = "") -> None:
        self._trace.append(self._make_event(event_type, position, wip_id, detail))

    def _dwell_event(self, detail: str) -> LineEvent:
        return LineEvent(
            event_type="DWELL_META",
            simulation_time_s=self._simulation_time_s,
            dwell_number=self.conveyor.dwell_number,
            detail=detail,
        )

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

    def reset(self) -> None:
        self.conveyor.reset()
        self.upstream.reset()
        self.genealogy = GenealogyStore()
        self._wips.clear()
        self._rso2_wips.clear()
        self._trace.clear()
        self._motor_seq = 0
        self._simulation_time_s = 0.0
        self._station_elapsed = {p: 0.0 for p in self.conveyor.positions}
        self._quality_histories.clear()
        self._quality_seq = 0


class AssyLineError(RuntimeError):
    """Raised when an ASSY line invariant is violated."""
