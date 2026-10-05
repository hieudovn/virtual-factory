"""DDAY-B4 — Bottled Water whole-factory composition.

This module is a *small aggregate layer* around the unchanged detailed
Filling & Packaging line runtime delivered by B2/B3. It composes the existing
discrete line runtime (``AssyLineRuntime`` through ``DemoController``) and adds
only:

* a deterministic factory clock driven from the server (never from a browser);
* aggregate Water Treatment / Bottle Preparation / Utilities / Warehouse models
  that publish conservation-consistent raw facts;
* a hierarchy + taxonomy projection read from the frozen B1 topology contract.

It is deliberately *not* a second simulation engine, not a telemetry framework,
not a scenario engine, not a protocol gateway, not a historian and not a
persistence subsystem. No calculated KPI (OEE / availability / performance /
quality % / energy per unit / utilization / health score) is produced here —
those belong to FactoriX IIoT / PlantOS.

Raw-fact boundary
-----------------
Every published fact is a simulated raw fact attributable to a hierarchy source
ID. Configured constants are published with ``provenance = CONFIGURED_TARGET``
where a B1 dictionary entry calls for it.

Control interpretation (documented, see B4 evidence)
----------------------------------------------------
``PAUSE`` freezes the simulation clock completely: no simulated time passes, so
no tank, energy, utility or warehouse progression occurs. ``STOP`` is a
controlled stop (never a fault) that halts *production* while the plant stays
energized: the clock keeps advancing and only explicitly modelled standby/base
load accrues energy, which keeps cumulative energy monotonic and coherent with
equipment state.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.line_runtime import LineRunState
from virtual_factory.workspaces.capper_degradation import (
    CapperDegradationScenario,
    load_runtime_config,
)
from virtual_factory.workspaces.compressor_pressure import (
    CompressorPressureScenario,
    load_compressor_runtime,
)
from virtual_factory.workspaces.plantos_export import (
    ExportSessionCursor,
    PlantosLocalIngestion,
    export_bundle,
    map_snapshot,
)

WORKSPACE_ID = "bottled-water-dday"

ENTITY_PLANT = "plant"
ENTITY_AREA = "area"
ENTITY_ASSET = "asset"

PROVENANCE_RAW = "SIMULATED_RAW"
PROVENANCE_CONFIGURED = "CONFIGURED_TARGET"

_QUALITY_GOOD = "GOOD"

#: Equipment class per B1 asset role. ``role`` describes what an asset does in
#: this process; ``equipment_class`` describes what kind of equipment it is, so
#: two different roles may share a class.
EQUIPMENT_CLASS_BY_ROLE = {
    "feed": "pump",
    "treatment": "ro_skid",
    "storage": "storage_tank",
    "blower_infeed": "blower",
    "rinser": "rinser",
    "filler": "filler",
    "capper": "capper",
    "quality_inspection": "inspector",
    "labeler": "labeler",
    "case_packer": "case_packer",
    "palletizer": "palletizer",
    "compressed_air": "compressor",
    "cooling": "chiller",
    "pump": "pump",
    "power_meter": "power_meter",
    "finished_goods": "fg_interface",
}

#: Line stations whose completion count drives a packaging material counter.
STATION_KEYS = ("fill", "cap", "label", "case_pack", "palletize")

MAX_FACTORY_EVENTS = 48

HIDDEN_TRUTH_KEYS = (
    "degradation_factor",
    "injected_fault_strength",
    "scenario_internal_phase_timer",
    "phase_timer",
    "fault_strength",
    "_factor",
    "_phase_elapsed_s",
    "_bearing_temp_c",
    "sag_factor",
    "injected_sag_strength",
)

FORBIDDEN_KPI_KEYS = (
    "oee",
    "availability",
    "performance",
    "quality_percentage",
    "quality_pct",
    "energy_per_unit",
    "energy_per",
    "health_score",
    "asset_health",
    "anomaly_score",
    "anomaly",
    "rul",
    "remaining_useful",
    "predictive",
)

#: Float tolerance for tank-level limit comparisons (volume, m3).
_TANK_EPSILON_M3 = 1e-12


def _get(data: dict, path: str, default: Any) -> Any:
    """Read ``a.b.c`` from nested mappings, returning ``default`` when absent."""
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


# ═══════════════════════════════════════════════════════════════
# Frozen B1 hierarchy / taxonomy
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class HierarchyNode:
    """One node of the frozen B1 plant hierarchy with its minimal taxonomy."""

    source_id: str
    name: str
    entity_type: str
    parent_source_id: Optional[str]
    role: str
    equipment_class: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "parent_source_id": self.parent_source_id,
            "role": self.role,
            "equipment_class": self.equipment_class,
            "workspace_id": WORKSPACE_ID,
        }


def load_hierarchy(topology_path: str | Path) -> tuple[dict, list[HierarchyNode]]:
    """Load the frozen B1 topology contract into flat taxonomy nodes.

    Order is plant → areas → that area's assets, which keeps the projection
    stable and readable. No node is invented here and no FactoriX platform
    canonical ID is created: VF owns source IDs only.
    """
    data = yaml.safe_load(Path(topology_path).read_text(encoding="utf-8")) or {}
    plant = data.get("plant") or {}
    plant_id = plant.get("id")
    if not plant_id:
        raise ValueError(f"topology contract declares no plant id: {topology_path}")

    nodes: list[HierarchyNode] = [
        HierarchyNode(
            source_id=plant_id,
            name=plant.get("name", plant_id),
            entity_type=ENTITY_PLANT,
            parent_source_id=None,
            role="plant",
            equipment_class=None,
        )
    ]
    for area in data.get("areas", ()) or ():
        area_id = area["id"]
        nodes.append(
            HierarchyNode(
                source_id=area_id,
                name=area.get("name", area_id),
                entity_type=ENTITY_AREA,
                parent_source_id=plant_id,
                role=area.get("role", ""),
                equipment_class=None,
            )
        )
        for asset in area.get("assets", ()) or ():
            role = asset.get("role", "")
            nodes.append(
                HierarchyNode(
                    source_id=asset["id"],
                    name=asset.get("name", asset["id"]),
                    entity_type=ENTITY_ASSET,
                    parent_source_id=area_id,
                    role=role,
                    equipment_class=EQUIPMENT_CLASS_BY_ROLE.get(role),
                )
            )
    return data, nodes


# ═══════════════════════════════════════════════════════════════
# Aggregate simulation parameters
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class FactoryConfig:
    """Aggregate-simulation parameters (no process physics, no KPI)."""

    workspace_id: str
    step_dt_s: float
    integration_step_s: float
    tick_interval_s: float

    raw_water_flow_m3h: float
    recovery_factor: float
    tank_capacity_m3: float
    tank_initial_volume_m3: float
    tank_high_level_pct: float
    tank_low_level_pct: float
    feed_standby_kw: float
    feed_running_kw: float
    ro_standby_kw: float
    ro_running_kw: float

    stations: dict[str, str]
    bottle_volume_m3: float
    process_efficiency: float
    bottles_per_case: int
    cases_per_pallet: int

    line_loads: dict[str, tuple[float, float]]

    air_setpoint_bar: float
    air_production_sag_bar: float
    air_min_bar: float
    air_max_bar: float
    air_rise_bar_per_s: float
    air_fall_bar_per_s: float
    air_loading_tolerance_bar: float
    air_running_kw: float
    air_standby_kw: float
    chiller_running_kw: float
    chiller_standby_kw: float
    pump_running_kw: float
    pump_standby_kw: float

    dispatch_rate_per_min: float
    base_load_kw: float


def load_factory_config(
    factory_config_path: str | Path,
    route: Iterable[str] = (),
) -> FactoryConfig:
    """Load the aggregate-simulation parameters for the workspace."""
    data = yaml.safe_load(
        Path(factory_config_path).read_text(encoding="utf-8")
    ) or {}

    route_ids = list(route)
    declared_loads = _get(data, "line_loads", {}) or {}
    unknown = sorted(set(declared_loads) - set(route_ids))
    if unknown:
        raise ValueError(
            "factory configuration declares loads for stations that are not on "
            f"the line route: {unknown}"
        )

    stations = dict(_get(data, "line.stations", {}) or {})
    missing = [key for key in STATION_KEYS if key not in stations]
    if missing:
        raise ValueError(
            f"factory configuration is missing line station bindings: {missing}"
        )
    off_route = sorted(sid for sid in stations.values() if sid not in route_ids)
    if off_route:
        raise ValueError(
            f"factory configuration binds line stations not on the route: {off_route}"
        )

    tank_capacity = float(_get(data, "water_treatment.tank_capacity_m3", 0.4))
    fill_fraction = float(
        _get(data, "water_treatment.tank_initial_fill_fraction", 0.7)
    )

    line_loads: dict[str, tuple[float, float]] = {}
    for station_id in route_ids:
        entry = declared_loads.get(station_id) or {}
        line_loads[station_id] = (
            float(entry.get("standby_kw", 0.0)),
            float(entry.get("running_kw", 0.0)),
        )

    return FactoryConfig(
        workspace_id=_get(data, "workspace_id", WORKSPACE_ID),
        step_dt_s=float(_get(data, "clock.dt_s", 1.0)),
        integration_step_s=float(_get(data, "clock.integration_step_s", 1.0)),
        tick_interval_s=float(_get(data, "clock.tick_interval_s", 0.25)),
        raw_water_flow_m3h=float(
            _get(data, "water_treatment.raw_water_flow_m3h", 1.2)
        ),
        recovery_factor=float(_get(data, "water_treatment.recovery_factor", 0.75)),
        tank_capacity_m3=tank_capacity,
        tank_initial_volume_m3=tank_capacity * fill_fraction,
        tank_high_level_pct=float(
            _get(data, "water_treatment.tank_high_level_pct", 85.0)
        ),
        tank_low_level_pct=float(
            _get(data, "water_treatment.tank_low_level_pct", 60.0)
        ),
        feed_standby_kw=float(_get(data, "water_treatment.feed_standby_kw", 0.5)),
        feed_running_kw=float(_get(data, "water_treatment.feed_running_kw", 3.0)),
        ro_standby_kw=float(_get(data, "water_treatment.ro_standby_kw", 0.3)),
        ro_running_kw=float(_get(data, "water_treatment.ro_running_kw", 6.0)),
        stations=stations,
        bottle_volume_m3=float(_get(data, "line.bottle_volume_m3", 0.0005)),
        process_efficiency=float(_get(data, "line.process_efficiency", 0.94)),
        bottles_per_case=int(_get(data, "packaging.bottles_per_case", 6)),
        cases_per_pallet=int(_get(data, "packaging.cases_per_pallet", 2)),
        line_loads=line_loads,
        air_setpoint_bar=float(_get(data, "utilities.compressed_air.setpoint_bar", 7.0)),
        air_production_sag_bar=float(
            _get(data, "utilities.compressed_air.production_sag_bar", 0.6)
        ),
        air_min_bar=float(
            _get(data, "utilities.compressed_air.min_pressure_bar", 5.5)
        ),
        air_max_bar=float(
            _get(data, "utilities.compressed_air.max_pressure_bar", 7.2)
        ),
        air_rise_bar_per_s=float(
            _get(data, "utilities.compressed_air.rise_bar_per_s", 0.05)
        ),
        air_fall_bar_per_s=float(
            _get(data, "utilities.compressed_air.fall_bar_per_s", 0.02)
        ),
        air_loading_tolerance_bar=float(
            _get(data, "utilities.compressed_air.loading_tolerance_bar", 0.05)
        ),
        air_running_kw=float(_get(data, "utilities.compressed_air.running_kw", 15.0)),
        air_standby_kw=float(_get(data, "utilities.compressed_air.standby_kw", 2.0)),
        chiller_running_kw=float(_get(data, "utilities.chiller.running_kw", 11.0)),
        chiller_standby_kw=float(_get(data, "utilities.chiller.standby_kw", 1.5)),
        pump_running_kw=float(_get(data, "utilities.pump.running_kw", 4.0)),
        pump_standby_kw=float(_get(data, "utilities.pump.standby_kw", 0.8)),
        dispatch_rate_per_min=float(
            _get(data, "warehouse.dispatch_rate_per_min", 4.0)
        ),
        base_load_kw=float(_get(data, "plant.base_load_kw", 6.0)),
    )


def load_workspace(
    factory_config_path: str | Path,
) -> tuple[FactoryConfig, list[HierarchyNode]]:
    """Load the aggregate parameters and the frozen hierarchy of a workspace.

    The hierarchy source is declared by the factory configuration
    (``hierarchy_source``) and resolved relative to it, so the B1 topology stays
    the single hierarchy source of truth.
    """
    factory_path = Path(factory_config_path)
    data = yaml.safe_load(factory_path.read_text(encoding="utf-8")) or {}
    hierarchy_ref = _get(data, "hierarchy_source", "topology.yaml")
    topology_path = (factory_path.parent / str(hierarchy_ref)).resolve()
    if not topology_path.is_file():
        # Fall back to the workspace directory packaged with the repository.
        topology_path = (
            Path(__file__).resolve().parents[3]
            / "configs" / "workspaces" / WORKSPACE_ID / str(hierarchy_ref)
        )
    _topology, nodes = load_hierarchy(topology_path)
    return data, nodes


# ═══════════════════════════════════════════════════════════════
# Target-line projection (B2/B3 facts, reused unchanged)
# ═══════════════════════════════════════════════════════════════


def project_target_line(ctrl: DemoController, limit: int = 60) -> dict:
    """Domain-neutral outward projection of the B2 generic line runtime.

    Reads only public runtime surfaces. Counts and states are raw facts; no KPI
    is derived and no hidden scenario truth is exposed. This is the B3
    projection, kept as the single implementation and reused by the
    whole-factory projection.
    """
    line = ctrl.line
    facts = ctrl.line_facts()
    checkpoints = [
        station_id
        for station_id, contract in line.station_contracts.items()
        if contract.capabilities.quality_decision
    ]

    stations = []
    for sequence, entry in enumerate(facts["positions"]):
        station_id = entry["position_id"]
        stations.append({
            "sequence": sequence,
            "station_id": station_id,
            "unit_id": entry["unit_id"],
            "unit_type": entry["unit_type"],
            "product_code": entry["product_code"],
            "unit_status": entry["manufacturing_status"],
            "is_occupied": entry["is_occupied"],
            "is_quality_checkpoint": station_id in checkpoints,
            "last_disposition": line.last_quality_disposition(station_id),
        })

    events = [
        {
            "event_type": event.event_type,
            "station_id": event.position,
            "unit_id": event.wip_id,
            "detail": event.detail,
            "simulation_time_s": event.simulation_time_s,
            "dwell_number": event.dwell_number,
        }
        for event in line.trace[-limit:]
    ]

    return {
        "workspace_id": WORKSPACE_ID,
        "plant_id": facts["plant_id"],
        "line_id": facts["line_id"],
        "line_label": facts["line_label"],
        "run_state": facts["run_state"],
        "operating_state": facts["operating_state"],
        "simulation_time_s": facts["simulation_time_s"],
        "dwell_number": facts["dwell_number"],
        "nominal_dwell_s": facts["nominal_dwell_s"],
        "unit_type": facts["unit_type"],
        "product_code": facts["product_code"],
        "route": facts["route"],
        "stations": stations,
        "counts": {
            "total": facts["total_count"],
            "good": facts["good_count"],
            "reject": facts["reject_count"],
        },
        "units_on_line": facts["units_on_line"],
        "quality_checkpoints": checkpoints,
        "last_reject": next(
            (e["unit_id"] for e in reversed(events)
             if e["event_type"] == "REJECT"), ""),
        "recent_events": events,
    }


def _scenario_files(
    workspace_dir: Path,
    packaged: Path,
    stem: str,
) -> tuple[Path, Path]:
    """Resolve a workspace scenario pair, falling back to the packaged copy."""
    contract_path = workspace_dir / "scenarios" / f"{stem}.contract.yaml"
    runtime_path = workspace_dir / "scenarios" / f"{stem}.runtime.yaml"
    if not contract_path.is_file():
        contract_path = packaged / f"{stem}.contract.yaml"
    if not runtime_path.is_file():
        runtime_path = packaged / f"{stem}.runtime.yaml"
    return contract_path, runtime_path


# ═══════════════════════════════════════════════════════════════
# Whole-factory composition
# ═══════════════════════════════════════════════════════════════


class BottledWaterFactory:
    """Deterministic whole-factory composition for the Bottled Water workspace.

    Owns exactly one ``DemoController`` (the reused discrete line runtime) plus
    the aggregate area/utility/warehouse models. Callers drive it with
    ``step(dt_s)``; the HTTP layer is only an observer and a control surface.
    """

    def __init__(
        self,
        line_config_path: str | Path,
        factory_config_path: str | Path,
        *,
        enable_capper: bool = True,
        enable_compressor: bool = True,
        compressor: Optional[CompressorPressureScenario] = None,
    ) -> None:
        self.line_config_path = str(line_config_path)
        self.factory_config_path = str(factory_config_path)
        self._lock = threading.RLock()

        self.controller = DemoController(config_path=self.line_config_path)
        self.controller.initialize()
        if not self.controller.is_generic_line:
            raise RuntimeError(
                "Bottled Water workspace requires a generic single-line "
                "configuration"
            )

        route = list(self.controller.line.config.conveyor.positions)
        data, nodes = load_workspace(factory_config_path)
        self._config = load_factory_config(factory_config_path, route=route)
        self.tick_interval_s = self._config.tick_interval_s
        self.workspace_id = self._config.workspace_id

        self._hierarchy = nodes
        self._nodes_by_id = {node.source_id: node for node in nodes}
        if len(self._nodes_by_id) != len(nodes):
            raise ValueError("topology contract contains duplicate source ids")
        self._route = route
        self._topology = data
        self._plant_source_id = next(
            node.source_id for node in nodes if node.entity_type == ENTITY_PLANT
        )

        # Asset ids used by the aggregate models, resolved through the frozen
        # hierarchy so nothing is hard-coded to a particular plant layout.
        self._load_nodes = [
            node.source_id
            for node in nodes
            if node.entity_type == ENTITY_ASSET
            and (node.source_id in self._config.line_loads
                 or node.role in ("feed", "treatment", "compressed_air",
                                  "cooling", "pump"))
        ]
        self._feed_node = self._node_by_role("feed")
        self._ro_node = self._node_by_role("treatment")
        self._tank_node = self._node_by_role("storage")
        self._meter_node = self._node_by_role("power_meter")
        self._fg_node = self._node_by_role("finished_goods")
        self._compressor_node = self._node_by_role("compressed_air")
        self._chiller_node = self._node_by_role("cooling")
        self._pump_node = self._node_by_role_any("pump", exclude=("feed",))
        self._prep_area = self._node_by_role("preparation_area")
        self._line_area = self._node_by_role("production_line")
        self._cap_node = self._config.stations.get("cap") or self._node_by_role(
            "capper"
        )

        workspace_dir = Path(self.factory_config_path).resolve().parent
        packaged = (
            Path(__file__).resolve().parents[3]
            / "configs" / "workspaces" / WORKSPACE_ID / "scenarios"
        )
        capper_contract, capper_runtime = _scenario_files(
            workspace_dir, packaged, "capper_degradation"
        )
        self._scenario = CapperDegradationScenario(
            load_runtime_config(capper_runtime, capper_contract)
        )
        self._capper_enabled = bool(enable_capper)

        if compressor is not None:
            self._compressor = compressor
        else:
            cmp_contract, cmp_runtime = _scenario_files(
                workspace_dir, packaged, "compressor_pressure"
            )
            self._compressor = CompressorPressureScenario(
                load_compressor_runtime(cmp_runtime, cmp_contract)
            )
        self._compressor_enabled = bool(enable_compressor)

        # B6 local ingestion sink: a view of this factory, not a second runtime.
        self._export_sink = PlantosLocalIngestion()
        self._export_cursor = ExportSessionCursor()
        self._initialise_state()

    @property
    def export_cursor(self) -> ExportSessionCursor:
        """Per-run transport watermark. RESET / new run clears it."""
        return self._export_cursor

    # --- hierarchy helpers ---

    def _node_by_role(self, role: str) -> Optional[str]:
        for node in self._hierarchy:
            if node.role == role:
                return node.source_id
        return None

    def _node_by_role_any(self, role: str, exclude: tuple[str, ...]) -> Optional[str]:
        for node in self._hierarchy:
            if node.role == role and node.source_id not in exclude:
                return node.source_id
        return None

    # --- state ---

    def _initialise_state(self) -> None:
        cfg = self._config
        line = self.controller.line
        self._clock_s = 0.0
        self._production_elapsed_s = 0.0
        self._dwell_acc_s = 0.0
        self._nominal_dwell_s = float(line.config.conveyor.nominal_line_dwell_time_s)

        self._tank_volume_m3 = cfg.tank_initial_volume_m3
        self._feed_enabled = True
        self._raw_water_total_m3 = 0.0
        self._treated_water_total_m3 = 0.0
        self._reject_water_total_m3 = 0.0
        self._water_draw_total_m3 = 0.0
        self._pending_draw_m3 = 0.0
        self._product_water_total_m3 = 0.0
        self._last_raw_flow_m3h = 0.0

        self._air_pressure_bar = cfg.air_setpoint_bar

        self._station_units: dict[str, set[str]] = {
            station_id: set() for station_id in self._route
        }
        self._filled_counted = 0
        self._trace_cursor = 0

        self._node_energy_kwh: dict[str, float] = {
            node_id: 0.0 for node_id in self._load_nodes
        }
        self._plant_energy_total_kwh = 0.0

        self._dispatch_acc = 0.0
        self._dispatch_count = 0

        self._events: deque = deque(maxlen=MAX_FACTORY_EVENTS)
        self._last_noted_state = LineRunState.STOPPED.value
        self._scenario.reset()
        self._compressor.reset()
        if self._capper_enabled:
            self._record_scenario_events(self._scenario.advance(0.0, 0.0))
        if self._compressor_enabled:
            self._record_scenario_events(self._compressor.advance(0.0, 0.0))
        if getattr(self, "_export_cursor", None) is not None:
            self._export_cursor.reset()
        if getattr(self, "_export_sink", None) is not None:
            self._export_sink.clear()
            self._publish_export()

    def _publish_export(self) -> None:
        """Map the current snapshot into the local PlantOS-compatible sink."""
        if getattr(self, "_export_sink", None) is None:
            return
        self._export_sink.ingest(map_snapshot(self.snapshot()))

    def plantos_export(self) -> dict:
        """Debug/verification bundle over the single factory snapshot."""
        with self._lock:
            return export_bundle(self.snapshot(), self._export_sink)

    def _reset(self) -> None:
        self.controller.reset()
        self._initialise_state()

    # --- control (server-side semantics) ---

    def _note_run_state(self) -> None:
        """Record a plant-level raw MACHINE_STATE_CHANGED fact.

        Idempotent: only a real transition is recorded, so RESET restores exactly
        the initial state (including an empty recent-event window).
        """
        state = self.controller.run_state.value
        if state == self._last_noted_state:
            return
        self._last_noted_state = state
        self._events.append({
            "event_type": "MACHINE_STATE_CHANGED",
            "source_id": self._plant_source_id,
            "detail": f"run_state={state}",
            "simulation_time_s": _round(self._clock_s, 3),
            "quality": _QUALITY_GOOD,
            "provenance": PROVENANCE_RAW,
        })

    def _plant_id(self) -> str:
        return self._plant_source_id

    def start(self) -> str:
        with self._lock:
            self.controller.start()
            self._note_run_state()
            self._publish_export()
            return self.controller.run_state.value

    def pause(self) -> str:
        with self._lock:
            self.controller.pause()
            self._note_run_state()
            self._publish_export()
            return self.controller.run_state.value

    def resume(self) -> str:
        with self._lock:
            self.controller.resume()
            self._note_run_state()
            self._publish_export()
            return self.controller.run_state.value

    def stop(self) -> str:
        with self._lock:
            self.controller.stop()
            self._note_run_state()
            self._publish_export()
            return self.controller.run_state.value

    def reset(self) -> str:
        with self._lock:
            self._reset()
            self._note_run_state()
            self._publish_export()
            return self.controller.run_state.value

    def classify(self, kind: str, code: str, target: str | None = None) -> dict:
        """Enrich existing/pending abnormal context. Never steps the model."""
        with self._lock:
            destination = self._classify_destination(target)
            if destination == "compressor":
                result = self._compressor.classify(kind, code)
            else:
                result = self._scenario.classify(kind, code)
            self._apply_classification_to_recent_events()
            self._publish_export()
            return result

    def _classify_destination(self, target: str | None) -> str:
        cleaned = str(target or "").strip()
        if cleaned in ("", "capper", "BW-FP-CAP01", "BW-CAP-DEG-01"):
            return "capper"
        if cleaned in ("compressor", "BW-UT-CMP01", "BW-CMP-SAG-01"):
            return "compressor"
        raise ValueError(f"unsupported classification target: {target!r}")

    def _apply_classification_to_recent_events(self) -> None:
        capper_codes = self._scenario.classification()
        compressor_codes = self._compressor.classification()
        for event in self._events:
            if event.get("event_type") in ("DOWNTIME_START", "DOWNTIME_END"):
                self._stamp_codes(event, capper_codes)
            elif self._compressor.accepts_classification(event):
                self._stamp_codes(event, compressor_codes)

    def _record_scenario_event(self, event: dict) -> None:
        payload = dict(event)
        if payload.get("event_type") in ("DOWNTIME_START", "DOWNTIME_END"):
            self._stamp_codes(payload, self._scenario.classification())
        elif self._compressor.accepts_classification(payload):
            self._stamp_codes(payload, self._compressor.classification())
        self._events.append(payload)

    @staticmethod
    def _stamp_codes(event: dict, codes: dict) -> None:
        if codes.get("downtime_code"):
            event["downtime_code"] = codes["downtime_code"]
        if codes.get("failure_code"):
            event["failure_code"] = codes["failure_code"]

    def _record_scenario_events(self, events: list[dict]) -> None:
        for event in events:
            self._record_scenario_event(event)

    def advance_debug_cycle(self) -> float:
        """Manual/debug seam: force exactly one line cycle.

        Not the D-Day operating path and not a visible operator action — the
        autonomous server-side clock is. The factory clock and the aggregate
        models are advanced by exactly the simulated time the line advanced, so
        aggregates never drift from the line when this seam is used.
        """
        with self._lock:
            before = self.controller.line.simulation_time_s
            self._produce_one_cycle()
            delta = self.controller.line.simulation_time_s - before
            if delta > 0.0:
                self._dwell_acc_s = 0.0
                self._integrate_elapsed(delta)
                if self.controller.run_state is LineRunState.RUNNING:
                    self._advance_scenarios(delta)
                self._apply_draw()
            self._publish_export()
            return delta

    # --- deterministic clock ---

    def step(self, dt_s: Optional[float] = None) -> None:
        """Advance the factory by ``dt_s`` simulated seconds (default config)."""
        delta = self._config.step_dt_s if dt_s is None else float(dt_s)
        if delta <= 0.0:
            return
        with self._lock:
            sub_step = max(self._config.integration_step_s, 1e-6)
            remaining = delta
            while remaining > 1e-9:
                chunk = min(remaining, sub_step)
                self._sub_step(chunk)
                remaining -= chunk
            self._publish_export()

    def _sub_step(self, dt: float) -> None:
        run_state = self.controller.run_state
        if run_state is LineRunState.PAUSED:
            # PAUSE freezes simulated progression entirely: no clock, no tank,
            # no utility, no warehouse and no energy movement.
            return

        self._integrate_elapsed(dt)

        if run_state is LineRunState.RUNNING:
            self._advance_scenarios(dt)
            if self._production_inhibited():
                self._dwell_acc_s = 0.0
            else:
                self._dwell_acc_s += dt
                effective = self._effective_dwell_s()
                if self._dwell_acc_s >= effective - 1e-9:
                    self._dwell_acc_s -= effective
                    self._produce_one_cycle()

        self._apply_draw()

    def _currently_running(self) -> bool:
        return self.controller.run_state is LineRunState.RUNNING

    def _integrate_elapsed(self, dt: float) -> None:
        """Integrate clock and aggregate models over ``dt`` simulated seconds."""
        running = self._currently_running()
        self._clock_s += dt
        if running:
            self._production_elapsed_s += dt

        self._update_feed_state(running)
        self._integrate_water(dt)
        self._integrate_air(dt)
        self._integrate_energy(dt, running)
        self._integrate_dispatch(dt)

    def _update_feed_state(self, running: bool) -> None:
        """Tank-level hysteresis latch for the water-treatment feed.

        The latch is only updated while the plant is producing; while it is not,
        the feed is inactive because ``_feed_active()`` also requires the run
        state. That keeps the latch meaningful across a STOP/RESUME cycle
        instead of latching to 'off' and never restarting.
        """
        cfg = self._config
        if not running:
            return
        high_volume_m3 = self._tank_high_volume_m3()
        low_volume_m3 = cfg.tank_capacity_m3 * cfg.tank_low_level_pct / 100.0
        if self._tank_volume_m3 >= high_volume_m3 - _TANK_EPSILON_M3:
            self._feed_enabled = False
        elif self._tank_volume_m3 <= low_volume_m3 + _TANK_EPSILON_M3:
            self._feed_enabled = True

    def _tank_high_volume_m3(self) -> float:
        cfg = self._config
        return cfg.tank_capacity_m3 * cfg.tank_high_level_pct / 100.0

    def _feed_active(self) -> bool:
        """True when the treatment feed is actually running right now."""
        return self._feed_enabled and self._currently_running()

    def _integrate_water(self, dt: float) -> None:
        """Water balance with a bounded tank and a modulating high-level limit.

        ``treated = raw x recovery`` and the feed ramps down as the tank reaches
        its high-level volume, so the tank can never be pushed past the high
        limit (and therefore never past capacity). The published instantaneous
        flow is the flow actually taken during the last step.
        """
        cfg = self._config
        if not self._feed_active() or dt <= 0.0:
            self._last_raw_flow_m3h = 0.0
            return

        high_volume_m3 = self._tank_high_volume_m3()
        headroom_m3 = high_volume_m3 - self._tank_volume_m3
        if headroom_m3 <= _TANK_EPSILON_M3:
            self._last_raw_flow_m3h = 0.0
            return

        raw_m3 = cfg.raw_water_flow_m3h / 3600.0 * dt
        treated_m3 = raw_m3 * cfg.recovery_factor
        if treated_m3 >= headroom_m3:
            # Saturate exactly at the configured high-level volume.
            treated_m3 = headroom_m3
            raw_m3 = treated_m3 / cfg.recovery_factor
            self._tank_volume_m3 = high_volume_m3
        else:
            self._tank_volume_m3 += treated_m3

        self._last_raw_flow_m3h = raw_m3 / dt * 3600.0
        self._raw_water_total_m3 += raw_m3
        self._treated_water_total_m3 += treated_m3
        self._reject_water_total_m3 += raw_m3 - treated_m3

    def _advance_scenarios(self, dt: float) -> None:
        """Advance enabled scenario helpers by ``dt`` simulated seconds."""
        if self._capper_enabled:
            self._record_scenario_events(
                self._scenario.advance(dt, self._clock_s)
            )
        if self._compressor_enabled:
            self._record_scenario_events(
                self._compressor.observe_pressure(
                    self._air_pressure_bar, self._clock_s
                )
            )
            self._record_scenario_events(
                self._compressor.advance(dt, self._clock_s)
            )

    def _production_inhibited(self) -> bool:
        capper = self._capper_enabled and self._scenario.production_inhibited()
        compressor = (
            self._compressor_enabled and self._compressor.production_inhibited()
        )
        return capper or compressor

    def _effective_dwell_s(self) -> float:
        dwell = self._nominal_dwell_s
        if self._capper_enabled:
            dwell = self._scenario.effective_dwell_s(self._nominal_dwell_s)
        if self._compressor_enabled:
            dwell = max(
                dwell, self._compressor.effective_dwell_s(self._nominal_dwell_s)
            )
        return dwell

    def _integrate_air(self, dt: float) -> None:
        cfg = self._config
        if (
            self._compressor_enabled
            and self._compressor.overrides_pressure()
        ):
            pressure = self._compressor.step_pressure(self._air_pressure_bar, dt)
            self._air_pressure_bar = max(
                cfg.air_min_bar, min(cfg.air_max_bar, pressure)
            )
            return

        target = cfg.air_setpoint_bar
        if self._currently_running():
            target -= cfg.air_production_sag_bar
        target = max(cfg.air_min_bar, min(cfg.air_max_bar, target))

        pressure = self._air_pressure_bar
        if pressure < target:
            pressure = min(target, pressure + cfg.air_rise_bar_per_s * dt)
        elif pressure > target:
            pressure = max(target, pressure - cfg.air_fall_bar_per_s * dt)
        self._air_pressure_bar = max(
            cfg.air_min_bar, min(cfg.air_max_bar, pressure)
        )

    def _integrate_energy(self, dt: float, running: bool) -> None:
        dt_h = dt / 3600.0
        loads = self._active_loads(running)
        for node_id, kw in loads.items():
            if kw:
                self._node_energy_kwh[node_id] = (
                    self._node_energy_kwh.get(node_id, 0.0) + kw * dt_h
                )
        self._plant_energy_total_kwh += (
            sum(loads.values()) + self._config.base_load_kw
        ) * dt_h

    def _integrate_dispatch(self, dt: float) -> None:
        cfg = self._config
        if self._finished_goods_inventory() <= 0:
            return
        self._dispatch_acc += cfg.dispatch_rate_per_min / 60.0 * dt
        while self._dispatch_acc >= 1.0 and self._finished_goods_inventory() > 0:
            self._dispatch_acc -= 1.0
            self._dispatch_count += 1

    # --- production coupling ---

    def _produce_one_cycle(self) -> None:
        self.controller.advance()
        self._consume_trace()

    def _consume_trace(self) -> None:
        """Derive material consumption from real line progress.

        Per-station completion is counted by unit id, so a rejected unit still
        consumes every material it already had when it was rejected.
        """
        trace = self.controller.line.trace
        while self._trace_cursor < len(trace):
            event = trace[self._trace_cursor]
            self._trace_cursor += 1
            if event.event_type != "STATION_COMPLETE":
                continue
            bucket = self._station_units.get(event.position)
            if bucket is not None:
                bucket.add(event.wip_id)

        filled = self._station_completions(self._config.stations["fill"])
        new_filled = filled - self._filled_counted
        if new_filled > 0:
            self._filled_counted = filled
            product_m3 = new_filled * self._config.bottle_volume_m3
            self._product_water_total_m3 += product_m3
            self._pending_draw_m3 += product_m3 / self._config.process_efficiency

    def _apply_draw(self) -> None:
        """Take as much pending Filler demand as the tank can supply.

        Unmet demand stays on the pending ledger. Silently zeroing the
        remainder would destroy conservation under low-water conditions.
        """
        if self._pending_draw_m3 <= 0.0:
            return
        available = max(0.0, self._tank_volume_m3)
        drawn = min(self._pending_draw_m3, available)
        self._tank_volume_m3 = available - drawn
        self._water_draw_total_m3 += drawn
        self._pending_draw_m3 -= drawn

    def _water_request_total_m3(self) -> float:
        """Cumulative Filler demand: water actually drawn plus still unmet."""
        return self._water_draw_total_m3 + self._pending_draw_m3

    def _station_completions(self, station_id: Optional[str]) -> int:
        if not station_id:
            return 0
        return len(self._station_units.get(station_id, ()))

    # --- aggregate facts ---

    def _tank_level_pct(self) -> float:
        cfg = self._config
        if cfg.tank_capacity_m3 <= 0.0:
            return 0.0
        return self._tank_volume_m3 / cfg.tank_capacity_m3 * 100.0

    def _compressor_loading(self) -> bool:
        cfg = self._config
        return (
            self._air_pressure_bar
            < cfg.air_setpoint_bar - cfg.air_loading_tolerance_bar
        )

    def _active_loads(self, running: Optional[bool] = None) -> dict[str, float]:
        """Instantaneous active power per load-bearing asset (kW)."""
        cfg = self._config
        if running is None:
            running = self._currently_running()

        loads: dict[str, float] = {}
        feed_active = self._feed_active()
        run_state = self.controller.run_state.value
        for station_id, (standby, running_kw) in cfg.line_loads.items():
            if station_id == self._cap_node and self._capper_enabled:
                loads[station_id] = self._scenario.capper_active_power_kw(
                    run_state, standby, running_kw
                )
            else:
                loads[station_id] = running_kw if running else standby
        if self._feed_node:
            loads[self._feed_node] = (
                cfg.feed_running_kw if feed_active else cfg.feed_standby_kw
            )
        if self._ro_node:
            loads[self._ro_node] = (
                cfg.ro_running_kw if feed_active else cfg.ro_standby_kw
            )
        if self._compressor_node:
            loaded = self._compressor_loading()
            if self._compressor_enabled:
                loads[self._compressor_node] = (
                    self._compressor.compressor_active_power_kw(
                        cfg.air_standby_kw, cfg.air_running_kw, loaded
                    )
                )
            else:
                loads[self._compressor_node] = (
                    cfg.air_running_kw if loaded else cfg.air_standby_kw
                )
        if self._chiller_node:
            loads[self._chiller_node] = (
                cfg.chiller_running_kw if running else cfg.chiller_standby_kw
            )
        if self._pump_node:
            loads[self._pump_node] = (
                cfg.pump_running_kw if (feed_active or running)
                else cfg.pump_standby_kw
            )
        return loads

    def _finished_goods_receipts(self) -> int:
        return int(self.controller.line.good_count)

    def _finished_goods_inventory(self) -> int:
        return self._finished_goods_receipts() - self._dispatch_count

    def _operating_state(self, active: bool, support_equipment: bool = False) -> str:
        """B1 operating_state from equipment activity and the factory run state.

        FAULT and UNKNOWN are never produced by B4 — no abnormal condition is
        modelled before B5 — so ``STOPPED != FAULT`` holds by construction. A
        PAUSED factory reports IDLE because nothing is producing, while
        ``run_state`` carries PAUSED explicitly.

        Process equipment of a stopped plant reports STOPPED. Support equipment
        (utilities) stays energized and reports its own load state, so a
        controlled stop reduces utility demand instead of hiding it behind a
        blanket STOPPED.
        """
        if (not support_equipment
                and self.controller.run_state is LineRunState.STOPPED):
            return "STOPPED"
        return "RUNNING" if active else "IDLE"

    def _signal(
        self,
        value: Any,
        unit: str,
        provenance: str = PROVENANCE_RAW,
    ) -> dict:
        return {
            "value": value,
            "unit": unit,
            "quality": _QUALITY_GOOD,
            "provenance": provenance,
            "simulation_time_s": _round(self._clock_s, 3),
        }

    def _node_signals(self) -> dict[str, dict[str, dict]]:
        running = self._currently_running()
        cfg = self._config
        loads = self._active_loads(running)
        stations = cfg.stations

        filled = self._station_completions(stations["fill"])
        caps = self._station_completions(stations["cap"])
        labels = self._station_completions(stations["label"])
        packed = self._station_completions(stations["case_pack"])
        palletized = self._station_completions(stations["palletize"])
        good = self._finished_goods_receipts()

        production_min = self._production_elapsed_s / 60.0
        fill_rate = filled / production_min if production_min > 0 else 0.0

        nodes: dict[str, dict[str, dict]] = {}

        def put(node_id: Optional[str], signal_id: str, value: Any, unit: str,
                provenance: str = PROVENANCE_RAW) -> None:
            if not node_id or node_id not in self._nodes_by_id:
                return
            nodes.setdefault(node_id, {})[signal_id] = self._signal(
                value, unit, provenance
            )

        # Plant node — factory-level run state only.
        put(self._plant_id(), "run_state", self.controller.run_state.value, "-")
        put(self._plant_id(), "operating_state",
            self._operating_state(running), "-")

        # Water treatment.
        feed_active = self._feed_active()
        put(self._feed_node, "operating_state",
            self._operating_state(feed_active), "-")
        put(self._feed_node, "water_flow",
            _round(self._last_raw_flow_m3h, 6), "m3/h")
        put(self._feed_node, "raw_water_total_m3",
            self._raw_water_total_m3, "m3")
        put(self._ro_node, "operating_state",
            self._operating_state(feed_active), "-")
        put(self._ro_node, "production_flow",
            _round(self._last_raw_flow_m3h * cfg.recovery_factor, 6), "m3/h")
        put(self._ro_node, "treated_water_total_m3",
            self._treated_water_total_m3, "m3")
        put(self._ro_node, "reject_water_total_m3",
            self._reject_water_total_m3, "m3")
        put(self._tank_node, "level", _round(self._tank_level_pct(), 3), "%")
        put(self._tank_node, "volume_m3", self._tank_volume_m3, "m3")

        # Bottle preparation — logical area, no duplicate physical asset.
        put(self._prep_area, "operating_state", self._operating_state(running), "-")
        put(self._prep_area, "preform_count", int(self.controller.line.total_count),
            "preform")

        # Filling & packaging line area and its stations.
        put(self._line_area, "operating_state", self._operating_state(running), "-")
        put(self._line_area, "total_count",
            int(self.controller.line.total_count), "bottle")
        put(self._line_area, "good_count", good, "bottle")
        put(self._line_area, "reject_count",
            int(self.controller.line.reject_count), "bottle")

        run_state_value = self.controller.run_state.value
        for station_id in self._route:
            if station_id == self._cap_node and self._capper_enabled:
                put(
                    station_id,
                    "operating_state",
                    self._scenario.capper_operating_state(run_state_value),
                    "-",
                )
            else:
                put(station_id, "operating_state",
                    self._operating_state(running), "-")

        if self._capper_enabled:
            for signal_id, (value, unit) in self._scenario.published_signals(
                run_state_value
            ).items():
                if signal_id == "operating_state":
                    continue
                put(self._cap_node, signal_id, value, unit)

        put(stations["fill"], "fill_rate", _round(fill_rate, 3), "bottle/min")
        put(stations["fill"], "product_water_total_m3",
            self._product_water_total_m3, "m3")
        put(stations["fill"], "water_draw_total_m3",
            self._water_draw_total_m3, "m3")
        put(stations["cap"], "cap_count", caps, "cap")
        put(stations["label"], "label_count", labels, "label")
        put(stations["case_pack"], "case_count",
            packed // cfg.bottles_per_case, "case")
        put(stations["palletize"], "pallet_count",
            (packed // cfg.bottles_per_case) // cfg.cases_per_pallet, "pallet")

        # Consolidated automated quality checkpoint configured for this line.
        # The result is published only once the line has produced one, so no
        # disposition is ever invented.
        quality_stations = dict(self.controller.line.config.quality_stations)
        for station_id in self._route:
            if station_id not in quality_stations:
                continue
            disposition = self.controller.line.last_quality_disposition(station_id)
            if disposition:
                put(station_id, "inspection_result", disposition, "-")

        # Utilities — support equipment keeps following demand while STOPPED.
        put(self._compressor_node, "operating_state",
            self._operating_state(self._compressor_loading(), True), "-")
        put(self._compressor_node, "air_pressure",
            _round(self._air_pressure_bar, 3), "bar")
        put(self._chiller_node, "operating_state",
            self._operating_state(running, True), "-")
        put(self._pump_node, "operating_state",
            self._operating_state(feed_active or running, True), "-")
        put(self._meter_node, "plant_active_power",
            _round(sum(loads.values()) + cfg.base_load_kw, 3), "kW",
            PROVENANCE_RAW)
        put(self._meter_node, "plant_energy_total",
            self._plant_energy_total_kwh, "kWh")

        # Warehouse / dispatch: activity tracks whether finished goods are
        # available to drain.
        put(self._fg_node, "operating_state",
            self._operating_state(self._finished_goods_inventory() > 0), "-")
        put(self._fg_node, "receipt_count", good, "bottle")
        put(self._fg_node, "dispatch_count", self._dispatch_count, "bottle")
        put(self._fg_node, "inventory_count",
            self._finished_goods_inventory(), "bottle")

        # Per-asset electrical load / energy where the asset consumes power.
        for node_id, kw in loads.items():
            put(node_id, "active_power", _round(kw, 3), "kW")
            put(node_id, "energy_total",
                self._node_energy_kwh.get(node_id, 0.0), "kWh")

        return nodes

    # --- projection ---

    def snapshot(self, event_limit: int = 60) -> dict:
        """One authoritative whole-factory raw projection."""
        with self._lock:
            cfg = self._config
            running = self._currently_running()
            loads = self._active_loads(running)
            nodes = self._node_signals()

            node_tree: dict[str, dict] = {}
            for node in self._hierarchy:
                entry = node.as_dict()
                entry["signals"] = nodes.get(node.source_id, {})
                node_tree[node.source_id] = entry

            balances = {
                # Conservation quantities are published at full precision so the
                # balances stay exactly checkable (rounding them would break the
                # mass/energy identities at small magnitudes).
                "water": {
                    "raw_water_feed_total_m3": self._raw_water_total_m3,
                    "treated_water_total_m3": self._treated_water_total_m3,
                    "ro_reject_total_m3": self._reject_water_total_m3,
                    "recovery_factor": cfg.recovery_factor,
                    "tank_initial_volume_m3": cfg.tank_initial_volume_m3,
                    "tank_volume_m3": self._tank_volume_m3,
                    "tank_capacity_m3": cfg.tank_capacity_m3,
                    "tank_high_volume_m3": (
                        cfg.tank_capacity_m3
                        * cfg.tank_high_level_pct / 100.0
                    ),
                    "tank_low_volume_m3": (
                        cfg.tank_capacity_m3
                        * cfg.tank_low_level_pct / 100.0
                    ),
                    "tank_level_pct": self._tank_level_pct(),
                    "product_water_total_m3": self._product_water_total_m3,
                    "water_draw_total_m3": self._water_draw_total_m3,
                    "unmet_water_demand_m3": self._pending_draw_m3,
                    "water_request_total_m3": self._water_request_total_m3(),
                    "other_loss_total_m3": max(
                        0.0,
                        self._water_draw_total_m3
                        - self._product_water_total_m3,
                    ),
                },
                "materials": {
                    "preform_count": int(self.controller.line.total_count),
                    "cap_count": self._station_completions(cfg.stations["cap"]),
                    "label_count": self._station_completions(cfg.stations["label"]),
                    "case_count": self._station_completions(
                        cfg.stations["case_pack"]) // cfg.bottles_per_case,
                    "pallet_count": (
                        self._station_completions(cfg.stations["case_pack"])
                        // cfg.bottles_per_case
                    ) // cfg.cases_per_pallet,
                },
                "energy": {
                    "plant_active_power_kw": _round(
                        sum(loads.values()) + cfg.base_load_kw, 3),
                    "plant_energy_total_kwh": self._plant_energy_total_kwh,
                    "base_load_kw": cfg.base_load_kw,
                },
                "finished_goods": {
                    "receipt_count": self._finished_goods_receipts(),
                    "dispatch_count": self._dispatch_count,
                    "inventory_count": self._finished_goods_inventory(),
                },
            }

            target_line = self.overlay_line_projection(
                project_target_line(self.controller, limit=event_limit)
            )
            return {
                "workspace_id": self.workspace_id,
                "plant_id": self._plant_id(),
                "plant_name": self._nodes_by_id[self._plant_id()].name,
                "factory": {
                    "run_state": self.controller.run_state.value,
                    "operating_state": self._operating_state(running),
                    "simulation_time_s": _round(self._clock_s),
                    "production_elapsed_s":
                        _round(self._production_elapsed_s),
                    "dwell_number": self.controller.line.conveyor.dwell_number,
                },
                "scenario": self._scenario.public_context(),
                "compressor_scenario": {
                    **self._compressor.public_context(),
                    "air_pressure_bar": _round(self._air_pressure_bar, 3),
                },
                "classification": self._scenario.classification(),
                "hierarchy": [node.as_dict() for node in self._hierarchy],
                "nodes": node_tree,
                "balances": balances,
                "target_line": target_line,
                "recent_events": list(self._events),
            }

    def overlay_line_projection(self, projection: dict) -> dict:
        """Attach scenario context and Capper raw facts to the B3 line view.

        Used by both ``/state`` and the factory ``target_line`` so they stay
        the same object. Hidden ground truth is not copied here.
        """
        overlaid = dict(projection)
        overlaid["scenario"] = self._scenario.public_context()
        overlaid["compressor_scenario"] = {
            **self._compressor.public_context(),
            "air_pressure_bar": _round(self._air_pressure_bar, 3),
        }
        overlaid["classification"] = self._scenario.classification()
        run_state = self.controller.run_state.value
        signals = {}
        if self._capper_enabled:
            for signal_id, (value, unit) in self._scenario.published_signals(
                run_state
            ).items():
                signals[signal_id] = self._signal(value, unit)
        asset_signals = {self._cap_node: signals} if signals else {}
        if self._compressor_node:
            asset_signals[self._compressor_node] = {
                "operating_state": self._signal(
                    self._operating_state(self._compressor_loading(), True),
                    "-",
                ),
                "air_pressure": self._signal(
                    _round(self._air_pressure_bar, 3), "bar"
                ),
            }
        overlaid["asset_signals"] = asset_signals
        overlaid["scenario_events"] = [
            {
                "event_type": event["event_type"],
                "station_id": event.get("station_id") or event.get("source_id"),
                "unit_id": event.get("unit_id", ""),
                "detail": event.get("detail", ""),
                "simulation_time_s": event.get("simulation_time_s"),
                "dwell_number": event.get("dwell_number", 0),
                "downtime_code": event.get("downtime_code"),
                "failure_code": event.get("failure_code"),
            }
            for event in self._events
            if event.get("event_type") in (
                "SCENARIO_PHASE_CHANGED",
                "ALARM_RAISED",
                "ALARM_CLEARED",
                "DOWNTIME_START",
                "DOWNTIME_END",
            )
        ]
        return overlaid

    def hierarchy(self) -> list[HierarchyNode]:
        return list(self._hierarchy)

    def iter_node_signals(self, snapshot: Optional[dict] = None):
        """Yield ``(source_id, signal_id, signal)`` for every exposed fact."""
        data = self.snapshot() if snapshot is None else snapshot
        for source_id, entry in data["nodes"].items():
            for signal_id, signal in (entry.get("signals") or {}).items():
                yield source_id, signal_id, signal
