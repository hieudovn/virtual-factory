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
from virtual_factory.assembly.station_contracts import (
    Capabilities,
    CompletionMode,
    StationCommand,
    StationContract,
    build_default_assy_contracts,
)
from virtual_factory.assembly.auto_timing import (
    AutoTimingProfile,
    TimingBehavior,
    TimingResolver,
    TimingSample,
    parse_timing_config,
)
from virtual_factory.assembly.operation_execution import (
    OperationExecution,
    OperationRegistry,
    OperationResult,
    OperationState,
)


# ═══════════════════════════════════════════════════════════════
# WIP State
# ═══════════════════════════════════════════════════════════════

class LineRunState(str, enum.Enum):
    """Operator-facing run state of one indexed line (B2).

    Deliberately distinct from ``ConveyorState``: ``STOPPED`` here is a
    controlled stop requested through the runtime control surface, and it is
    never a fault. ``FAULT`` is not a run state — a fault is a per-unit or
    per-station condition, so ``STOPPED != FAULT`` holds structurally.
    """
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class WipLifecycle(str, enum.Enum):
    """ASSY WIP lifecycle states (demo semantic names).

    ``IN_LINE`` (C01) is the domain-neutral entry state used by the generic line
    profile, so that a non-legacy workspace never publishes the legacy
    ``IN_ASSY`` semantic. The legacy profile keeps using ``IN_ASSY``.
    """
    CREATED = "created"
    IN_ASSY = "in_assy"
    IN_LINE = "in_line"
    AT_STATION = "at_station"
    COMPLETED_STATION = "completed_station"
    JOINED = "joined"
    RELEASED = "released"
    REJECTED = "rejected"


@dataclass(slots=True)
class AssyWipState:
    """Runtime state for one WIP in the ASSY line."""
    wip_id: str
    lifecycle: WipLifecycle = WipLifecycle.CREATED
    current_position: str = ""
    station_count: int = 0
    is_child_of_join: bool = False
    parent_wip_ids: tuple[str, ...] = field(default_factory=tuple)
    # M6-INT-01-C01: authoritative release occurrence time (set at RELEASE).
    released_at_sim_s: float = 0.0
    # B2 generic profile: unit metadata + per-unit outcome bookkeeping.
    unit_sequence: int = 0
    unit_type: str = ""
    product_code: str = ""
    rejected: bool = False
    counted_good: bool = False


@dataclass
class QualityStationSpec:
    """B2: a quality checkpoint declared by configuration, not by station id.

    The ASSY profile keeps its frozen AP06/AP08/AP11 mapping; a generic
    workspace declares its own checkpoint (for Bottled Water: the consolidated
    Inspection station) through this spec.
    """

    config_key: str = ""
    check_type: CheckType = CheckType.VISUAL_INSPECTION
    # "hold"   → retry / terminal hold semantics (ASSY behaviour, default)
    # "reject" → eject the unit at this station and continue the line
    on_fail: str = "hold"
    quality: StationQualityConfig = field(default_factory=StationQualityConfig)


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
    # AUTO-TIME-01B — runtime timing configuration (single source of truth)
    timing_behavior: TimingBehavior = TimingBehavior.DETERMINISTIC
    random_seed: int = 42
    auto_timing_profiles: dict[str, AutoTimingProfile] = field(default_factory=dict)

    # ── B2 generic single-line profile (additive; defaults preserve ASSY) ──
    line_id: str = ""
    line_label: str = ""
    plant_id: str = ""
    plant_name: str = ""
    # "assy"    → the frozen TIPA AP station semantics (default, unchanged)
    # "generic" → no station-id-specific domain behaviour; every station is a
    #             configured operation, plus optional configured quality checks
    line_profile: str = "assy"
    unit_id_prefix: str = "UNIT"
    unit_type: str = ""
    product_code: str = ""
    quality_stations: dict[str, QualityStationSpec] = field(default_factory=dict)

    @property
    def is_generic_profile(self) -> bool:
        """True when the config drives the generic (non-AP) station model."""
        return self.line_profile == "generic"


@dataclass(frozen=True, slots=True)
class DwellPerformance:
    """AUTO-TIME-01C — immutable last-executed-dwell performance metrics."""

    actual_dwell_s: float = 0.0
    dwell_overrun_s: float = 0.0
    bottleneck_station_id: str = ""
    bottleneck_duration_s: float = 0.0


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

    # ── B2 generic single-line profile (additive; absent => ASSY defaults) ──
    plant_data = data.get("plant", {})
    if plant_data:
        config.plant_id = str(plant_data.get("id", config.plant_id))
        config.plant_name = str(plant_data.get("name", config.plant_name))

    line_data = data.get("line", {})
    if line_data:
        config.line_id = str(line_data.get("id", config.line_id))
        config.line_label = str(line_data.get("label", config.line_label))
        config.line_profile = str(line_data.get("profile", config.line_profile))

    unit_data = data.get("unit", {})
    if unit_data:
        config.unit_id_prefix = str(unit_data.get("id_prefix", config.unit_id_prefix))
        config.unit_type = str(unit_data.get("unit_type", config.unit_type))
        config.product_code = str(unit_data.get("product_code", config.product_code))

    for station_id, spec_data in (data.get("quality_stations") or {}).items():
        spec_data = spec_data or {}
        spec = QualityStationSpec(
            config_key=str(spec_data.get("config_key", station_id)),
            check_type=CheckType(str(spec_data.get("check_type", "VISUAL_INSPECTION"))),
            on_fail=str(spec_data.get("on_fail", "hold")),
            quality=StationQualityConfig(
                max_attempts=int(spec_data.get("max_attempts", 1)),
                scenario=spec_data.get("scenario", "PASS"),
            ),
        )
        overrides = spec_data.get("overrides", {})
        if overrides:
            spec.quality.overrides = {int(k): list(v) for k, v in overrides.items()}
        config.quality_stations[str(station_id)] = spec

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

    # AUTO-TIME-01B: single runtime timing config path (uses validated parsing
    # from auto_timing.py — do not duplicate parsing logic here).
    timing_behavior, random_seed, profiles = parse_timing_config(data)
    config.timing_behavior = timing_behavior
    config.random_seed = random_seed
    config.auto_timing_profiles = profiles

    return config


# OPS-02 — normalized operation_result for quality-decision stations.
_QUALITY_OPERATION_RESULT: dict[str, "OperationResult"] = {
    "AP06": OperationResult.TEST_COMPLETE,
    "AP08": OperationResult.INSPECTION_COMPLETE,
    "AP11": OperationResult.RELEASED,
}

# OPS-02 — station → (quality config key, check type) for quality-decision stations.
_QUALITY_STATION_MAP: dict[str, tuple[str, "CheckType"]] = {
    "AP06": ("ap06", CheckType.TEST),
    "AP08": ("ap08", CheckType.VISUAL_INSPECTION),
    "AP11": ("ap11", CheckType.FINAL_QC),
}

# B2 — fallback operation_result by check type for configured (non-AP) checkpoints.
_QUALITY_CHECKTYPE_RESULT: dict["CheckType", "OperationResult"] = {
    CheckType.TEST: OperationResult.TEST_COMPLETE,
    CheckType.VISUAL_INSPECTION: OperationResult.INSPECTION_COMPLETE,
    CheckType.FINAL_QC: OperationResult.CONFIRMED,
    CheckType.CHECKLIST: OperationResult.CONFIRMED,
}


def build_line_station_contracts(
    config: AssyLineConfig,
) -> dict[str, StationContract]:
    """Build the station contracts implied by a line configuration.

    ASSY profile → the frozen AP contracts (unchanged behaviour).
    Generic profile → one execution contract per configured position, plus a
    quality-decision capability for positions that declare a quality station.
    No station id is special-cased.
    """
    if not config.is_generic_profile:
        return build_default_assy_contracts(dict(config.station_durations))

    contracts: dict[str, StationContract] = {}
    for position in config.conveyor.positions:
        duration = float(config.station_durations.get(position, 60.0))
        if position in config.quality_stations:
            contracts[position] = StationContract(
                station_id=position,
                capabilities=Capabilities(execution=True, measurement=True,
                                          quality_decision=True),
                normal_action=StationCommand.CONFIRM,
                required_action=StationCommand.CONFIRM,
                work_duration_s=duration,
                decision_actions=("PASS", "FAIL", "NG"),
            )
        else:
            contracts[position] = StationContract(
                station_id=position,
                capabilities=Capabilities(execution=True),
                normal_action=StationCommand.DONE,
                required_action=StationCommand.DONE,
                work_duration_s=duration,
            )
    return contracts


def _validate_checklist_completion(
    items, contract: StationContract,
) -> list[dict]:
    """OPS-03-C01: validate the COMPLETE required checklist set (fail-closed).

    The authoritative required item set is ``contract.checklist_items``. The
    submitted payload must contain exactly those ids (each once) with
    ``completed == True``. Fails closed on missing / empty / partial subset /
    unknown id / duplicate / malformed item / ``completed != True``.
    """
    required = list(contract.checklist_items)
    if not required:
        raise AssyLineError(
            "Checklist gate: action requires a checklist but the contract "
            "defines no required items"
        )
    if not isinstance(items, (list, tuple)) or not items:
        raise AssyLineError(
            "Checklist gate: requires a non-empty checklist "
            "(payload['checklist'] missing or empty)"
        )
    seen: dict[str, bool] = {}
    for it in items:
        if not isinstance(it, dict):
            raise AssyLineError(
                "Checklist gate: each checklist item must be an object "
                "{item_id, completed}"
            )
        item_id = it.get("item_id")
        completed = it.get("completed")
        if not isinstance(item_id, str) or not item_id:
            raise AssyLineError(
                "Checklist gate: checklist item missing a non-empty 'item_id'"
            )
        if completed is not True:
            raise AssyLineError(
                f"Checklist gate: item '{item_id}' is not completed "
                f"(completed={completed!r}) - item exists != item completed"
            )
        if item_id not in required:
            raise AssyLineError(
                f"Checklist gate: unknown checklist item '{item_id}' "
                f"(required: {required})"
            )
        if item_id in seen:
            raise AssyLineError(
                f"Checklist gate: duplicate checklist item '{item_id}'"
            )
        seen[item_id] = True
    missing = [rid for rid in required if rid not in seen]
    if missing:
        raise AssyLineError(
            f"Checklist gate: incomplete checklist — missing {missing}"
        )
    return [{"item_id": rid, "completed": True} for rid in required]


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

    # B2 — generic single-line profile state (unused by the ASSY profile)
    _run_state: "LineRunState" = LineRunState.STOPPED
    _unit_seq: int = 0
    _carrier_seq: int = 0
    _total_count: int = 0
    _good_count: int = 0
    _reject_count: int = 0

    # OPS-02 — OperationExecution foundation
    station_contracts: dict[str, StationContract] = field(default_factory=dict)
    operation_registry: OperationRegistry = field(default_factory=OperationRegistry)
    global_run_mode: CompletionMode = CompletionMode.AUTO

    # AUTO-TIME-01B — isolated timing resolver (seeded, no global random)
    _timing_resolver: Optional[TimingResolver] = field(init=False, default=None)

    # AUTO-TIME-01C — last executed dwell performance metrics
    _dwell_performance: DwellPerformance = field(
        init=False, default_factory=DwellPerformance)

    def __post_init__(self) -> None:
        self.conveyor = ConveyorLine(config=self.config.conveyor)
        self.upstream = UpstreamProducer(config=self.config.upstream)
        for pos in self.conveyor.positions:
            self._station_elapsed[pos] = 0.0
        if not self.station_contracts:
            self.station_contracts = build_line_station_contracts(self.config)
        self._timing_resolver = TimingResolver(seed=self.config.random_seed)

    # -- Properties --

    @property
    def simulation_time_s(self) -> float:
        return self._simulation_time_s

    @property
    def dwell_performance(self) -> DwellPerformance:
        """AUTO-TIME-01C: last executed dwell performance (immutable)."""
        return self._dwell_performance

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

    @property
    def wip_ids(self) -> tuple[str, ...]:
        """Public: all registered WIP IDs (for snapshot/projection)."""
        return tuple(self._wips.keys())

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

    def _quality_spec(self, pos: str) -> QualityStationSpec:
        """Resolve the quality checkpoint definition for a station (B2).

        A configured spec wins (generic workspaces declare their own
        checkpoints). Otherwise the frozen ASSY AP06/AP08/AP11 mapping is used
        with unchanged hold/retry behaviour.
        """
        spec = self.config.quality_stations.get(pos)
        if spec is not None:
            return spec
        station_key, check_type = _QUALITY_STATION_MAP[pos]
        return QualityStationSpec(
            config_key=station_key,
            check_type=check_type,
            on_fail="hold",
            quality=self.config.quality.get(station_key),
        )

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
    # GENERIC UNIT FLOW (B2) — used by non-AP line profiles
    # ═══════════════════════════════════════════════════════

    def produce_unit(self) -> str:
        """Create one generic unit with the configured metadata.

        Returns the new unit id. Replaces the SSO2/RSO2 upstream for workspaces
        that have a single material entry, e.g. Bottled Water bottles.
        """
        self._unit_seq += 1
        unit_id = f"{self.config.unit_id_prefix}-{self._unit_seq:06d}"
        ws = self._add_wip(unit_id)
        ws.unit_sequence = self._unit_seq
        ws.unit_type = self.config.unit_type
        ws.product_code = self.config.product_code
        self._total_count += 1
        return unit_id

    def introduce_unit(self, wip_id: str, carrier_id: str,
                       position: str = "") -> list[LineEvent]:
        """Introduce a unit at a conveyor position (default: line entry).

        Returns events — does NOT append to ``self._trace``; the caller owns the
        single append (same convention as ``_execute_ap04_join``).
        """
        ws = self._wips.get(wip_id)
        if ws is None:
            raise AssyLineError(f"Unknown unit: {wip_id}")
        entry = position or self.conveyor.positions[0]
        carrier = self.conveyor.get_carrier(carrier_id)
        if carrier is None:
            carrier = self.conveyor.create_carrier(carrier_id)
        self.conveyor.place_carrier(carrier, entry, wip_id)
        # C01-A: the generic route must stay domain-neutral — the legacy
        # IN_ASSY lifecycle is not published for a non-legacy workspace.
        ws.lifecycle = WipLifecycle.IN_LINE
        ws.current_position = entry
        self._station_elapsed[entry] = 0.0
        return [self._make_event(
            "UNIT_ENTERED", entry, wip_id,
            f"carrier={carrier_id} unit_type={ws.unit_type} "
            f"product_code={ws.product_code}")]

    def _reject_unit(self, pos: str, wip_id: str,
                     op: OperationExecution) -> list[LineEvent]:
        """Eject a rejected unit and keep the line moving (B2).

        Used only by configured ``on_fail: reject`` checkpoints. The unit leaves
        the carrier (the empty carrier continues downstream), the reject count
        increments once, and the station completes so the line never blocks.
        """
        events: list[LineEvent] = []
        ws = self._wips.get(wip_id)
        if ws is not None:
            if not ws.rejected:
                ws.rejected = True
                self._reject_count += 1
            ws.lifecycle = WipLifecycle.REJECTED
        carrier = self.conveyor.carrier_at(pos)
        if carrier is not None and carrier.wip_id == wip_id:
            carrier.clear()
        op.routing_action = "REJECTED"
        op.terminal = True
        op.transition(OperationState.COMPLETED)
        events.append(self._make_event(
            "REJECT", pos, wip_id, f"reason={op.quality_result or 'FAIL'}"))
        return events

    def _count_completed_unit(self) -> list[LineEvent]:
        """Count a generic-profile unit that finished the last station (B2).

        Called from ``index_line``: the unit is about to index off the line, so
        its route is complete. Rejected and already-counted units are skipped,
        which keeps ``good_count + reject_count <= total_count``.
        """
        if not self.config.is_generic_profile:
            return []
        last_pos = self.conveyor.positions[-1]
        wip_id = self.conveyor.wip_at(last_pos)
        if not wip_id or not self.conveyor.is_position_complete(last_pos):
            return []
        ws = self._wips.get(wip_id)
        if ws is None or ws.rejected or ws.counted_good:
            return []
        ws.counted_good = True
        ws.lifecycle = WipLifecycle.RELEASED
        self._good_count += 1
        return [self._make_event(
            "UNIT_COMPLETED", last_pos, wip_id,
            f"route_complete total={self._total_count} "
            f"good={self._good_count} reject={self._reject_count}")]

    # ═══════════════════════════════════════════════════════
    # RUN CONTROLS + RAW FACTS (B2)
    # ═══════════════════════════════════════════════════════

    @property
    def run_state(self) -> "LineRunState":
        return self._run_state

    def start(self) -> "LineRunState":
        """START — begin automatic progression."""
        if self._run_state != LineRunState.RUNNING:
            self._run_state = LineRunState.RUNNING
            self._emit("LINE_RUN_STATE", detail="state=RUNNING")
        return self._run_state

    def pause(self) -> "LineRunState":
        """PAUSE — freeze progression, preserving every bit of state."""
        if self._run_state == LineRunState.RUNNING:
            self._run_state = LineRunState.PAUSED
            self._emit("LINE_RUN_STATE", detail="state=PAUSED")
        return self._run_state

    def resume(self) -> "LineRunState":
        """RESUME — continue from the preserved state."""
        if self._run_state == LineRunState.PAUSED:
            self._run_state = LineRunState.RUNNING
            self._emit("LINE_RUN_STATE", detail="state=RUNNING")
        return self._run_state

    def stop(self) -> "LineRunState":
        """STOP — controlled stop. Never a fault."""
        if self._run_state != LineRunState.STOPPED:
            self._run_state = LineRunState.STOPPED
            self._emit("LINE_RUN_STATE", detail="state=STOPPED")
        return self._run_state

    def advance_cycle(self) -> list[LineEvent]:
        """One deterministic production cycle: feed → dwell → index.

        Only RUNNING advances the line. PAUSED / STOPPED return no events and
        leave all state (including simulation time) untouched, so RESUME
        continues from exactly the same position.
        """
        if self._run_state != LineRunState.RUNNING:
            return []
        events = self._feed_next_unit()
        if events:
            self._trace.extend(events)
        events.extend(self.execute_dwell())
        if self.conveyor.state == ConveyorState.READY_TO_INDEX:
            events.extend(self.index_line())
        return events

    def _feed_next_unit(self) -> list[LineEvent]:
        """Release the next unit at line entry when the entry is free.

        The line takt (dwell + station durations) governs the release cadence;
        no wall-clock and no random source is involved.
        """
        entry = self.conveyor.positions[0]
        if self.conveyor.wip_at(entry) is not None:
            return []
        unit_id = self.produce_unit()
        self._carrier_seq += 1
        return self.introduce_unit(unit_id, f"CAR-{self._carrier_seq:04d}")

    @property
    def total_count(self) -> int:
        return self._total_count

    @property
    def good_count(self) -> int:
        return self._good_count

    @property
    def reject_count(self) -> int:
        return self._reject_count

    def unit_counts(self) -> dict[str, int]:
        """Raw production counts (no KPI is derived here)."""
        return {
            "total_count": self._total_count,
            "good_count": self._good_count,
            "reject_count": self._reject_count,
        }

    def units_on_line(self) -> int:
        """Units physically on the line (empty carriers excluded)."""
        return sum(
            1 for pos in self.conveyor.occupied_positions()
            if self.conveyor.wip_at(pos) is not None
        )

    def operating_state(self) -> str:
        """RUNNING / IDLE / STOPPED raw operating state.

        Deliberately not FAULT and not DOWNTIME: those are not produced by B2,
        and keeping them out of the enum keeps ``STOPPED != FAULT`` and
        ``IDLE != DOWNTIME`` true by construction.
        """
        if self._run_state == LineRunState.STOPPED:
            return "STOPPED"
        if self.units_on_line() == 0:
            return "IDLE"
        return "RUNNING"

    def line_facts(self) -> dict:
        """Outward raw-fact view of the line (B2).

        Raw operational facts only. No OEE / availability / performance /
        quality% / energy-per-unit / utilization / health score is calculated.
        """
        positions = []
        for pos in self.conveyor.positions:
            wip_id = self.conveyor.wip_at(pos)
            ws = self._wips.get(wip_id) if wip_id else None
            positions.append({
                "position_id": pos,
                "unit_id": wip_id or "",
                "unit_type": ws.unit_type if ws else "",
                "product_code": ws.product_code if ws else "",
                "manufacturing_status": ws.lifecycle.value if ws else "",
                "is_occupied": bool(wip_id),
            })
        facts = {
            "plant_id": self.config.plant_id,
            "line_id": self.config.line_id,
            "line_label": self.config.line_label,
            "line_profile": self.config.line_profile,
            "unit_type": self.config.unit_type,
            "product_code": self.config.product_code,
            "run_state": self._run_state.value,
            "operating_state": self.operating_state(),
            "simulation_time_s": self._simulation_time_s,
            "dwell_number": self.conveyor.dwell_number,
            "nominal_dwell_s": self.config.conveyor.nominal_line_dwell_time_s,
            "route": list(self.conveyor.positions),
            "positions": positions,
            "units_on_line": self.units_on_line(),
        }
        facts.update(self.unit_counts())
        return facts

    def last_quality_disposition(self, position: str) -> str:
        """Most recent inspection/quality disposition observed at a station."""
        for record in reversed(self._trace):
            if record.event_type == "QUALITY_RESULT" and record.position == position:
                return record.detail.split("disposition=")[-1].split(" ")[0]
        return ""

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

        # AUTO-TIME-01B (SA invariant): the active OperationExecution and its
        # frozen effective timing MUST exist before max_remaining / actual_dwell
        # is calculated. No domain action executes here.
        for pos in self.conveyor.occupied_positions():
            if self.conveyor.is_position_complete(pos):
                continue
            wip_id = self.conveyor.wip_at(pos)
            if wip_id is None:
                continue
            if self._wips.get(wip_id) is None:
                continue
            self._ensure_operation_for_position(pos, wip_id)

        # Determine max remaining station time from FROZEN op duration,
        # scanning in configured conveyor position order so tie-breaking is
        # deterministic (first position with the max remaining drives).
        # (completed stations are done for this dwell and must not extend it.)
        max_remaining = 0.0
        driver_pos = ""
        driver_duration = 0.0
        occupied = set(self.conveyor.occupied_positions())
        for pos in self.conveyor.positions:
            if pos not in occupied or self.conveyor.is_position_complete(pos):
                continue
            wip_id = self.conveyor.wip_at(pos)
            if wip_id is None:
                continue
            op = self.operation_registry.active_for(pos, wip_id)
            required = (
                op.work_duration_s
                if op is not None
                else self.config.station_durations.get(pos, 60.0)
            )
            elapsed = self._station_elapsed.get(pos, 0.0)
            remaining = max(0.0, required - elapsed)
            if remaining > max_remaining:
                max_remaining = remaining
                driver_pos = pos
                driver_duration = required

        actual_dwell = max(nominal, max_remaining)

        # AUTO-TIME-01C — persist last-dwell performance metrics.
        overrun = max(0.0, actual_dwell - nominal)
        if max_remaining > nominal:
            bottleneck_station_id = driver_pos
            bottleneck_duration_s = driver_duration
        else:
            bottleneck_station_id = ""
            bottleneck_duration_s = 0.0
        self._dwell_performance = DwellPerformance(
            actual_dwell_s=actual_dwell,
            dwell_overrun_s=overrun,
            bottleneck_station_id=bottleneck_station_id,
            bottleneck_duration_s=bottleneck_duration_s,
        )

        # Apply dwell time to all occupied stations
        for pos in self.conveyor.occupied_positions():
            if self.conveyor.is_position_complete(pos):
                # OPS-04-C01: a station already complete this dwell (e.g. AP04
                # child waiting for the rest of the line) must NOT be
                # re-processed before the next index.
                continue
            wip_id = self.conveyor.wip_at(pos)
            if wip_id is None:
                # B2: an empty carrier (unit already completed/rejected) does no
                # work. Complete it so it can never stall an indexed line.
                self.conveyor.mark_position_complete(pos)
                continue

            ws = self._wips.get(wip_id)
            if ws is None:
                continue

            self._station_elapsed[pos] = self._station_elapsed.get(pos, 0.0) + actual_dwell
            ws.current_position = pos

            all_events.extend(self._advance_operation(pos, wip_id))

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
    # OPS-02 — OperationExecution foundation
    # ═══════════════════════════════════════════════════════

    def _resolve_mode(self, contract: StationContract) -> CompletionMode:
        """Effective completion mode (OPS-01 §5 precedence).

        station.mode_override (if configured) → global_run_mode (if set)
        → station.default_mode.
        """
        if contract.mode_override is not None:
            return contract.mode_override
        if self.global_run_mode is not None:
            return self.global_run_mode
        return contract.default_mode

    def active_operations(self) -> list[OperationExecution]:
        """Public: active (non-indexed) operation executions."""
        return self.operation_registry.active_operations()

    def _should_auto_submit(
        self, contract: StationContract, mode: CompletionMode,
    ) -> bool:
        """Whether the simulator may auto-issue the required command (C01-02).

        AUTO → yes. MANUAL → no. ASSISTED → wait for explicit confirmation on
        checklist / quality-decision / final-disposition / identity-transformation
        contracts; pure execution may auto-submit. Fail-safe: wait if unclear.
        """
        if mode == CompletionMode.AUTO:
            return True
        if mode == CompletionMode.MANUAL:
            return False
        if mode == CompletionMode.ASSISTED:
            if (contract.capabilities.checklist
                    or contract.capabilities.quality_decision
                    or contract.capabilities.final_disposition
                    or contract.capabilities.identity_transformation):
                return False
            return True  # pure execution: system prepares/defaults
        return False  # fail-safe

    def _execute_ap03_checklist(
        self, wip_id: str, checklist_items: list[dict],
    ) -> list[LineEvent]:
        """AP03 checklist gate completion (C01-01 / C02). No quality record."""
        events: list[LineEvent] = []
        events.append(self._make_event("STATION_START", "AP03", wip_id, "checklist gate"))
        ws = self._wips.get(wip_id)
        if ws:
            ws.station_count += 1
            ws.lifecycle = WipLifecycle.COMPLETED_STATION
        completed = sum(1 for it in checklist_items if it.get("completed") is True)
        events.append(self._make_event(
            "STATION_COMPLETE", "AP03", wip_id,
            f"checklist complete items={completed}"))
        return events

    def _ensure_operation_for_position(
        self, pos: str, wip_id: str,
    ) -> OperationExecution:
        """Ensure an active OperationExecution exists BEFORE dwell sizing.

        AUTO-TIME-01B (SA invariant): the active OperationExecution and its
        frozen effective timing must exist before ``max_remaining`` /
        ``actual_dwell`` is calculated.

        - resolves effective completion mode exactly once;
        - for AUTO, resolves the station timing profile exactly once and
          freezes the ``TimingSample`` + effective ``work_duration_s``;
        - for MANUAL / ASSISTED (and AUTO without a profile), freezes the
          legacy fixed contract duration;
        - performs NO domain action; state stays READY until
          ``_advance_operation``.
        """
        contract = self.station_contracts.get(pos)
        if contract is None:
            contract = StationContract(
                station_id=pos,
                normal_action=StationCommand.DONE,
                required_action=StationCommand.DONE,
            )

        op = self.operation_registry.active_for(pos, wip_id)
        if op is not None:
            return op

        mode = self._resolve_mode(contract)
        legacy = (
            contract.work_duration_s
            if contract.work_duration_s is not None
            else self.config.station_durations.get(pos, 60.0)
        )

        timing: Optional[TimingSample] = None
        effective = legacy
        if mode == CompletionMode.AUTO:
            profile = self.config.auto_timing_profiles.get(pos)
            if profile is not None:
                timing = self._timing_resolver.resolve(
                    profile, self.config.timing_behavior)
                effective = timing.effective_duration_s

        op = self.operation_registry.start(
            pos, wip_id, contract, mode, self._simulation_time_s)
        op.work_duration_s = effective
        op.timing = timing
        return op

    def _advance_operation(
        self, pos: str, wip_id: str,
    ) -> list[LineEvent]:
        """Advance the OperationExecution for one occupied station this dwell."""
        contract = self.station_contracts.get(pos)
        if contract is None:
            contract = StationContract(
                station_id=pos,
                normal_action=StationCommand.DONE,
                required_action=StationCommand.DONE,
            )
        elapsed = self._station_elapsed.get(pos, 0.0)

        # AUTO-TIME-01B: op already exists (created before dwell sizing) with
        # frozen effective timing. Single source of truth = op.work_duration_s.
        op = self._ensure_operation_for_position(pos, wip_id)
        if op.state == OperationState.READY:
            op.transition(OperationState.WORKING)

        required = op.work_duration_s
        work_done = elapsed >= required

        if op.state == OperationState.WORKING and work_done:
            if contract.capabilities.quality_decision:
                op.transition(OperationState.AWAITING_DECISION)
            else:
                op.transition(OperationState.AWAITING_COMPLETION)

        # OPS-04-C01 (D): generate observations (measurements + proposal) the
        # moment the operation enters AWAITING_DECISION — BEFORE any decision is
        # applied. Idempotent per attempt.
        obs_events: list[LineEvent] = []
        if (op.state == OperationState.AWAITING_DECISION
                and contract.capabilities.quality_decision
                and op.proposed_quality_result is None):
            obs_events = self._prepare_quality_observation(op, pos, wip_id, contract)

        # Gating uses the FROZEN op.completion_mode (C01-03).
        if op.state in (OperationState.AWAITING_COMPLETION, OperationState.AWAITING_DECISION):
            if self._should_auto_submit(contract, op.completion_mode):
                # OPS-04-C01 (F): state-aware command — quality decision first
                # (normal action), final disposition afterwards (required action).
                if op.state == OperationState.AWAITING_DECISION:
                    command = contract.normal_action or contract.required_action or StationCommand.DONE
                else:
                    command = contract.required_action or contract.normal_action or StationCommand.DONE
                payload = None
                if (contract.checklist_required_for_action is not None
                        and contract.checklist_required_for_action == command):
                    payload = {"checklist": [
                        {"item_id": item_id, "completed": True}
                        for item_id in contract.checklist_items
                    ]}
                return obs_events + self.submit_operation_command(pos, wip_id, command, payload)
            action = contract.required_action.value if contract.required_action else "?"
            return obs_events + [self._make_event(
                "OPERATION_WAITING_COMMAND", pos, wip_id,
                f"mode={op.completion_mode.value} state={op.state.value} action={action}")]

        # Post-outcome handling for carried-over states.
        events: list[LineEvent] = []
        if op.state == OperationState.COMPLETED:
            # M6-INT-01: capture authoritative completion timestamp (domain truth).
            if op.completed_at_sim_s is None:
                op.completed_at_sim_s = (
                    self._simulation_time_s + self._station_elapsed.get(pos, 0.0))
            op.transition(OperationState.ELIGIBLE_TO_INDEX)
            self.conveyor.mark_position_complete(pos)
            self._station_elapsed[pos] = 0.0
        elif op.state == OperationState.FAILED:
            self._station_elapsed[pos] = 0.0
            if op.terminal:
                events.append(self._make_event(
                    "OPERATION_TERMINAL", pos, wip_id,
                    "FAILED_FINAL — no recovery, not HELD"))
            else:
                # OPS-04-C01: fresh observation for the next attempt.
                self._reset_quality_observation(op)
                op.transition(OperationState.AWAITING_DECISION)
                events.append(self._make_event(
                    "OPERATION_RETRY", pos, wip_id,
                    f"attempt={op.attempt_number} new attempt pending"))
        elif op.state == OperationState.WORKING:
            events.append(self._make_event(
                "STATION_PROGRESS", pos, wip_id,
                f"elapsed={elapsed:.0f}s / required={required:.0f}s"))
        return events

    def submit_operation_command(
        self,
        station_id: str,
        wip_id: str,
        command: StationCommand | str,
        payload: Optional[dict] = None,
    ) -> list[LineEvent]:
        """Runtime command surface (OPS-03 will bind UI to this).

        Validates active-operation identity, station contract, current state,
        and allowed command. Fails closed on invalid/stale command.
        """
        op = self.operation_registry.active_for(station_id, wip_id)
        if op is None:
            raise AssyLineError(
                f"No active operation for station={station_id} wip={wip_id}")

        contract = self.station_contracts.get(station_id)
        if contract is None:
            raise AssyLineError(f"No station contract for {station_id}")

        cmd = command if isinstance(command, StationCommand) else StationCommand(str(command))
        if cmd not in contract.allowed_commands:
            raise AssyLineError(
                f"Command {cmd.value} not allowed at {station_id} "
                f"(allowed: {[c.value for c in contract.allowed_commands]})")

        if op.state not in (OperationState.AWAITING_COMPLETION, OperationState.AWAITING_DECISION):
            raise AssyLineError(
                f"Operation {op.execution_id} not awaiting action "
                f"(state={op.state.value})")

        # OPS-03-C01: checklist gate — validate the COMPLETE required set.
        if (contract.checklist_required_for_action is not None
                and cmd == contract.checklist_required_for_action):
            checklist = (payload or {}).get("checklist", []) if payload else []
            op.checklist = _validate_checklist_completion(checklist, contract)

        # OPS-03-C02 / OPS-04-C01 (F): operator-supplied quality decision
        # (PASS/FAIL/NG). Only applies to the quality-decision command (normal
        # action); a distinct final-disposition command (RELEASE) must NOT
        # require or accept a quality decision.
        decision = (payload or {}).get("decision") if payload else None
        quality_command = (contract.normal_action or contract.required_action
                           or StationCommand.DONE)
        if contract.capabilities.quality_decision and cmd == quality_command:
            if contract.decision_actions:
                if decision is not None and decision not in contract.decision_actions:
                    raise AssyLineError(
                        f"Invalid quality decision {decision!r} at {station_id} "
                        f"(allowed: {list(contract.decision_actions)})")
                if op.completion_mode == CompletionMode.MANUAL and decision is None:
                    raise AssyLineError(
                        f"Manual quality decision required at {station_id}: "
                        f"choose one of {list(contract.decision_actions)}")

        events = self._run_operation_domain(
            station_id, wip_id, op, contract, decision=decision, command=cmd)

        # OPS-04-C01-R2: commit accepted command/input only after the domain
        # resolves. A rejected action must not look accepted.
        op.command = cmd
        if payload is not None:
            op.inputs.update(payload)

        # Resolve post-domain outcome
        if op.state == OperationState.COMPLETED:
            # M6-INT-01: capture authoritative completion timestamp (domain truth).
            if op.completed_at_sim_s is None:
                op.completed_at_sim_s = (
                    self._simulation_time_s + self._station_elapsed.get(station_id, 0.0))
            op.transition(OperationState.ELIGIBLE_TO_INDEX)
            self.conveyor.mark_position_complete(station_id)
            self._station_elapsed[station_id] = 0.0
        elif op.state == OperationState.FAILED:
            self._station_elapsed[station_id] = 0.0
            if op.terminal:
                pass  # FAILED + FAILED_FINAL: terminal, no recovery
            else:
                # OPS-04-C01: fresh observation for the next attempt.
                self._reset_quality_observation(op)
                op.transition(OperationState.AWAITING_DECISION)  # new attempt next dwell
        return events

    def submit_station_action(
        self, station_id: str, wip_id: str, action: str,
    ) -> list[LineEvent]:
        """OPS-03-C02 / OPS-04-C01 (A): station-level action surface.

        HOLD  → first-class HELD state + STAY_AT_STATION containment.
        RESUME → generic recovery from HELD back to the pending action.
        Other actions fail closed until their physical semantics are confirmed.
        """
        op = self.operation_registry.active_for(station_id, wip_id)
        if op is None:
            raise AssyLineError(
                f"No active operation for station={station_id} wip={wip_id}")
        contract = self.station_contracts.get(station_id)
        if contract is None:
            raise AssyLineError(f"No station contract for {station_id}")

        if action == "RESUME":
            # OPS-04-C01 (A): generic recovery from HELD → the exact state that
            # was held (AWAITING_DECISION or AWAITING_COMPLETION).
            if op.state != OperationState.HELD:
                raise AssyLineError(
                    f"RESUME requires HELD operation (state={op.state.value})")
            if op.pre_hold_state in (OperationState.AWAITING_DECISION,
                                     OperationState.AWAITING_COMPLETION):
                target = op.pre_hold_state
            elif contract.capabilities.quality_decision:
                target = OperationState.AWAITING_DECISION
            else:
                target = OperationState.AWAITING_COMPLETION
            op.pre_hold_state = None
            op.transition(target)
            op.routing_action = None
            return [self._make_event(
                "STATION_ACTION", station_id, wip_id,
                f"action=RESUME state={op.state.value}")]

        allowed = (set(contract.exception_actions)
                   | set(contract.final_disposition_actions))
        if action not in allowed:
            raise AssyLineError(
                f"Station action {action!r} not allowed at {station_id} "
                f"(allowed: {sorted(allowed)})")
        if action == "HOLD":
            if op.state not in (OperationState.AWAITING_COMPLETION,
                                OperationState.AWAITING_DECISION):
                raise AssyLineError(
                    f"HOLD requires an awaiting operation (state={op.state.value})")
            op.routing_action = "STAY_AT_STATION"
            op.pre_hold_state = op.state  # OPS-04-C01: remember for RESUME
            op.transition(OperationState.HELD)
            return [self._make_event(
                "STATION_ACTION", station_id, wip_id,
                f"action=HOLD state={op.state.value} routing={op.routing_action}")]
        raise AssyLineError(
            f"Station action {action!r} is not safely representable "
            f"in the current runtime (no physical routing confirmed)")

    def _run_operation_domain(
        self,
        pos: str,
        wip_id: str,
        op: OperationExecution,
        contract: StationContract,
        decision: Optional[str] = None,
        command: Optional[StationCommand] = None,
    ) -> list[LineEvent]:
        """Execute station domain work and map the outcome onto the operation.

        Capability-driven dispatch (C01-01), command-aware (OPS-04-C01):
        identity transformation → final disposition (RELEASE) → quality
        decision → checklist gate → pure execution.
        """
        cmd = command or contract.required_action or contract.normal_action or StationCommand.DONE

        if contract.capabilities.identity_transformation:
            events = self._execute_ap04_join(wip_id)
            op.operation_result = OperationResult.JOIN_COMPLETE
            op.quality_result = None
            op.routing_action = "CONTINUE"
            op.transition(OperationState.COMPLETED)
        elif (contract.capabilities.final_disposition
                and cmd == StationCommand.RELEASE):
            # OPS-04-C01 (F): RELEASE is a distinct final disposition, allowed
            # only after final QC resolved PASS (CLEAR).
            events = self._execute_release_disposition(pos, wip_id, op)
        elif contract.capabilities.quality_decision:
            spec = self._quality_spec(pos)
            # OPS-03-C02: in AUTO the simulator/scenario decides; operator
            # decision only overrides in MANUAL/ASSISTED.
            eff_decision = decision if op.completion_mode != CompletionMode.AUTO else None
            events = self._apply_quality_decision(
                pos, wip_id, op, spec, decision=eff_decision)
            qstatus = self.get_current_quality_status(wip_id)
            qh = self.get_quality_history(wip_id)
            op.quality_result = qh.last_disposition(pos) if qh else None
            op.attempt_number = qh.attempt_count(pos) if qh else 0
            if spec.on_fail == "reject" and op.quality_result in ("FAIL", "NG"):
                # B2 generic profile: a rejected unit is ejected and the line
                # keeps running — no retry, no hold, no blocked station.
                events.extend(self._reject_unit(pos, wip_id, op))
            elif qstatus == QualityStatus.CLEAR:
                if contract.capabilities.final_disposition:
                    # OPS-04-C01 (F): final QC passed — now await RELEASE.
                    op.operation_result = OperationResult.CONFIRMED
                    op.transition(OperationState.AWAITING_COMPLETION)
                else:
                    op.operation_result = (
                        _QUALITY_OPERATION_RESULT.get(pos)
                        or _QUALITY_CHECKTYPE_RESULT.get(
                            spec.check_type, OperationResult.TEST_COMPLETE))
                    op.routing_action = "CONTINUE"
                    self._mark_station_complete(wip_id, pos)
                    op.transition(OperationState.COMPLETED)
            elif qstatus == QualityStatus.FAILED_FINAL:
                op.terminal = True
                op.routing_action = "STAY_AT_STATION"
                op.transition(OperationState.FAILED)
            else:  # RETEST_PENDING / REINSPECT_PENDING
                op.routing_action = "STAY_AT_STATION"
                op.transition(OperationState.FAILED)
        elif contract.capabilities.checklist:
            # C01-01: AP03 checklist gate — no quality record, no PASS/FAIL/NG.
            events = self._execute_ap03_checklist(wip_id, op.checklist)
            op.operation_result = OperationResult.CONFIRMED
            op.quality_result = None
            op.routing_action = "CONTINUE"
            op.transition(OperationState.COMPLETED)
        else:
            events = self._execute_station(pos, wip_id)
            op.operation_result = OperationResult.DONE
            op.quality_result = None
            op.routing_action = "CONTINUE"
            op.transition(OperationState.COMPLETED)
        return events

    # ═══════════════════════════════════════════════════════
    # STATION EXECUTION (C01-03: authoritative lifecycle)
    # ═══════════════════════════════════════════════════════

    def _execute_station(self, position: str, wip_id: str) -> list[LineEvent]:
        """Execute station logic. Returns events; caller owns trace append.

        Pure-execution stations (PRE-ASSY, AP01, AP02, AP05, AP07, AP09, AP10)
        are handled here. AP04 JOIN, AP06/AP08 quality, AP11 final QC, and
        AP03 checklist are dispatched capability-first in `_run_operation_domain`.
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
    # QUALITY STATION (M6-S03) — OPS-04-C01 observation/decision split
    # ═══════════════════════════════════════════════════════

    def _mark_station_complete(self, wip_id: str, position: str) -> None:
        """OPS-04-C01: set WIP lifecycle + station count for a completed station."""
        ws = self._wips.get(wip_id)
        if ws:
            ws.station_count += 1
            ws.lifecycle = WipLifecycle.COMPLETED_STATION

    def _reset_quality_observation(self, op: OperationExecution) -> None:
        """OPS-04-C01 (D): clear pending observation so the next attempt
        regenerates fresh measurements + proposal + reason."""
        op.proposed_quality_result = None
        op.proposed_quality_reason = None
        op.measurements = []
        op.observations = []

    def _quality_checklist(self, check_type: CheckType) -> list[str]:
        """OPS-04-C01-R1: neutral DEMO_SYNTHETIC observation identifiers.

        No unconfirmed TIPA domain facts are hard-coded in the runtime.
        """
        if check_type == CheckType.VISUAL_INSPECTION:
            return ["demo_visual_observation_1", "demo_visual_observation_2",
                    "demo_visual_observation_3"]
        if check_type == CheckType.FINAL_QC:
            return ["demo_final_qc_observation_1", "demo_final_qc_observation_2",
                    "demo_final_qc_observation_3"]
        if check_type == CheckType.CHECKLIST:
            return ["demo_checklist_observation_1", "demo_checklist_observation_2",
                    "demo_checklist_observation_3"]
        return []

    def _prepare_quality_observation(
        self,
        op: OperationExecution,
        pos: str,
        wip_id: str,
        contract: StationContract,
    ) -> list[LineEvent]:
        """OPS-04-C01 (C/D): observe BEFORE deciding.

        Generates the synthetic measurements (TEST) and the scenario-derived
        proposal, stored on the operation. No QualityRecord is created yet, and
        measurements are NEVER rewritten based on the eventual disposition.
        """
        events: list[LineEvent] = []
        history = self._ensure_quality_history(wip_id)
        if history.current_status == QualityStatus.FAILED_FINAL:
            return events  # idempotent terminal hold — no new observation

        spec = self._quality_spec(pos)
        station_key = spec.config_key
        check_type = spec.check_type
        qcfg = spec.quality
        attempt = history.attempt_count(station_key) + 1

        ws = self._wips.get(wip_id)
        motor_seq = self._motor_seq
        if ws and ws.is_child_of_join:
            try:
                motor_seq = int(wip_id.split("-")[-1])
            except (ValueError, IndexError):
                pass
        elif ws and ws.unit_sequence:
            # B2: generic units use their own sequence number so per-unit
            # quality overrides stay deterministic. ASSY WIPs keep 0.
            motor_seq = ws.unit_sequence

        proposal = resolve_quality_disposition(
            station_key, motor_seq, attempt, qcfg, check_type)

        measurements: list[MeasurementValue] = []
        observations: list[dict] = []
        reason: Optional[dict] = None

        if check_type == CheckType.TEST:
            # AP06: synthetic electrical measurements (DEMO_SYNTHETIC).
            measurements = [
                MeasurementValue("R_U-V", 0.45 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
                MeasurementValue("R_V-W", 0.47 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
                MeasurementValue("R_W-U", 0.44 + (motor_seq * 0.01), "Ω", 0.30, 0.60),
            ]
            if proposal in ("FAIL", "NG"):
                # OPS-04-C01-R1: deterministic synthetic anomaly BEFORE decision.
                measurements[0] = MeasurementValue("R_U-V", 0.29, "Ω", 0.30, 0.60)
                reason = {"code": "DEMO_OUT_OF_RANGE", "source": "simulated_test"}
            else:
                reason = {"code": "DEMO_IN_RANGE", "source": "simulated_test"}
        elif check_type == CheckType.VISUAL_INSPECTION:
            anomaly = proposal in ("FAIL", "NG")
            observations = [
                {"observation_id": "demo_visual_observation_1",
                 "result": "anomaly" if anomaly else "ok"},
                {"observation_id": "demo_visual_observation_2", "result": "ok"},
                {"observation_id": "demo_visual_observation_3", "result": "ok"},
            ]
            reason = {"code": "demo_visual_rule_1", "source": "simulated_vision"}
        elif check_type == CheckType.FINAL_QC:
            observations = [
                {"observation_id": "demo_final_qc_observation_1", "result": "ok"},
                {"observation_id": "demo_final_qc_observation_2", "result": "ok"},
                {"observation_id": "demo_final_qc_observation_3", "result": "ok"},
            ]
            reason = {"code": "demo_final_qc_rule_1", "source": "simulated_final_qc"}
        elif check_type == CheckType.CHECKLIST:
            observations = [
                {"observation_id": "demo_checklist_observation_1", "result": "ok"},
                {"observation_id": "demo_checklist_observation_2", "result": "ok"},
                {"observation_id": "demo_checklist_observation_3", "result": "ok"},
            ]
            reason = {"code": "demo_checklist_rule_1", "source": "simulated_checklist"}

        op.measurements = [m.to_dict() for m in measurements]
        op.observations = observations
        op.proposed_quality_result = proposal
        op.proposed_quality_reason = reason
        events.append(self._make_event(
            "QUALITY_OBSERVED", pos, wip_id,
            f"type={check_type.value} attempt={attempt} proposal={proposal}"))
        return events

    def _apply_quality_decision(
        self,
        pos: str,
        wip_id: str,
        op: OperationExecution,
        spec: QualityStationSpec,
        decision: Optional[str] = None,
    ) -> list[LineEvent]:
        """OPS-04-C01 (C): apply the FINAL disposition to the OBSERVED data.

        Creates the QualityRecord from `op.measurements` (as observed) and the
        final disposition (operator decision, or the stored proposal). No
        backwards rewriting of measurements for FAIL/NG.
        """
        events: list[LineEvent] = []
        history = self._ensure_quality_history(wip_id)
        if history.current_status == QualityStatus.FAILED_FINAL:
            events.append(self._make_event(
                "QUALITY_WAITING_DISPOSITION", pos, wip_id,
                "FAILED_FINAL — awaiting disposition"))
            return events

        station_key = spec.config_key
        check_type = spec.check_type
        qcfg = spec.quality
        attempt = history.attempt_count(station_key) + 1

        disposition = op.proposed_quality_result or "PASS"
        if decision is not None:
            disposition = decision

        # OPS-04-C01-R2: reject unrepresentable final-QC negative BEFORE any
        # authoritative mutation — no QualityRecord, no status change, no
        # attempt increment, no events.
        if check_type == CheckType.FINAL_QC and disposition in ("FAIL", "NG"):
            raise AssyLineError(
                f"Final QC negative disposition {disposition!r} is unconfirmed; "
                f"fails closed (no REINSPECT/REWORK/SCRAP routing)")

        events.append(self._make_event(
            "QUALITY_START", pos, wip_id,
            f"type={check_type.value} attempt={attempt}"))

        measurements = tuple(MeasurementValue(**m) for m in op.measurements)
        checklist = self._quality_checklist(check_type)
        # VF-CONTRACT-FINALITY-01: stamp the authoritative terminal decision
        # (attempts exhausted -> FAILED_FINAL) on this record, using the SAME
        # condition as the existing FAILED_FINAL transition below.  Additive,
        # atomic, never reconstructed downstream; no transition-logic change.
        terminal = disposition in ("FAIL", "NG") and attempt >= qcfg.max_attempts
        record = QualityRecord(
            record_id=self._next_quality_id(),
            wip_id=wip_id,
            station_id=pos,
            check_type=check_type,
            disposition=disposition,
            attempt_number=attempt,
            simulation_time_s=self._simulation_time_s + self._station_elapsed.get(pos, 0.0),
            measurements=measurements,
            checklist_items=tuple(checklist),
            terminal=terminal,
            observations=tuple(op.observations),
            proposed_quality_result=op.proposed_quality_result or "",
            proposed_quality_reason=dict(op.proposed_quality_reason)
            if op.proposed_quality_reason else None,
        )
        history.add_record(record)

        events.append(self._make_event(
            "QUALITY_RESULT", pos, wip_id,
            f"disposition={disposition} attempt={attempt}"))

        if disposition in ("FAIL", "NG"):
            history.set_status(
                QualityStatus.RETEST_PENDING if check_type == CheckType.TEST
                else QualityStatus.REINSPECT_PENDING)
            op.routing_action = "STAY_AT_STATION"
            events.append(self._make_event(
                "QUALITY_HOLD", pos, wip_id,
                f"status={history.current_status.value}"))
            if attempt >= qcfg.max_attempts:
                history.set_status(QualityStatus.FAILED_FINAL)
                events.append(self._make_event(
                    "QUALITY_FAILED_FINAL", pos, wip_id,
                    f"max_attempts={qcfg.max_attempts} exhausted"))
        else:
            history.set_status(QualityStatus.CLEAR)
            op.routing_action = "CONTINUE"
        return events

    def _execute_release_disposition(
        self, pos: str, wip_id: str, op: OperationExecution,
    ) -> list[LineEvent]:
        """OPS-04-C01 (F): RELEASE as a distinct final disposition.

        Allowed ONLY after final QC resolved PASS (quality status CLEAR).
        Fails closed otherwise; HELD blocks release.
        """
        events: list[LineEvent] = []
        qstatus = self.get_current_quality_status(wip_id)
        qh = self.get_quality_history(wip_id)
        last = qh.last_disposition(pos) if qh else None
        if op.state == OperationState.HELD:
            raise AssyLineError("RELEASE blocked: operation is HELD (RESUME first)")
        if qstatus != QualityStatus.CLEAR or last != "PASS":
            raise AssyLineError(
                f"RELEASE blocked at {pos}: final QC not PASS "
                f"(status={qstatus.value}, disposition={last!r})")
        ws = self._wips.get(wip_id)
        if ws:
            ws.lifecycle = WipLifecycle.RELEASED
            ws.station_count += 1
            # M6-INT-01-C01: capture the authoritative release occurrence time
            # (consistent with QualityRecord timestamp convention).
            ws.released_at_sim_s = (
                self._simulation_time_s + self._station_elapsed.get(pos, 0.0))
        events.append(self._make_event("STATION_START", pos, wip_id, "RELEASE"))
        events.append(self._make_event("STATION_COMPLETE", pos, wip_id, "RELEASED"))
        op.operation_result = OperationResult.RELEASED
        op.routing_action = "CONTINUE"
        op.transition(OperationState.COMPLETED)
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

        events.extend(self._count_completed_unit())

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
        self.operation_registry.clear()
        # B2: restore the generic-profile run state and production counters.
        self._run_state = LineRunState.STOPPED
        self._unit_seq = 0
        self._carrier_seq = 0
        self._total_count = 0
        self._good_count = 0
        self._reject_count = 0
        # AUTO-TIME-01B: restore deterministic timing stream on reset.
        self._timing_resolver = TimingResolver(seed=self.config.random_seed)
        # AUTO-TIME-01C: restore neutral dwell metrics on reset.
        self._dwell_performance = DwellPerformance()


class AssyLineError(RuntimeError):
    """Raised when an ASSY line invariant is violated."""
