"""SH-WTP functional simulation expansion (VF-vNEXT-G21).

A bounded, runnable multi-scope SH-WTP slice materially larger than the
T106 -> T108 proof. It reuses:

- G10/G11 readiness + G16 expansion-readiness classifications;
- T106 (LogicalOnly) and T108 (FirstOrder) accepted standalone runtimes;
- G18 scenario-assumed topology for the links PIM has NOT confirmed;
- G19's proven G4 coordinator + explicit_lagged orchestration pattern.

Selected slice (5 executable scopes, spanning intake -> treatment -> distribution):

    RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108

    RAW-INTAKE   LogicalOnly source (synthetic raw-water inflow)
    T100         LogicalOnly receiving junction (pass-through)
    T106         LogicalOnly filter (accepted G13B runtime, pass-through)
    T108         FirstOrder clean-water tank (accepted G13 runtime)
    DIST-P108    LogicalOnly distribution sink (scenario-assumed)

Only the T106 -> T108 link is PIM-authoritative (REL-SHW-F01 / G14A F01). The
other three links are VF_SCENARIO_ASSUMED_TOPOLOGY (explicit/versioned/
provenanced/reversible via G18) and never claim site truth. T110 is NOT used
(blocked pending evidence).

Frozen invariants preserved:

- assumed topology != PIM authoritative topology (distinct schema/provenance);
- every executable scope carries explicit fidelity/status;
- deterministic multi-window execution; explicit_lagged -> no same-window
  feed-through (participants emit from their COMMITTED state, one window behind);
- no mutable cross-scope state (detached immutable G4 transfers only);
- CompositionGraph != execution order (coordinator orders by structural identity);
- no site/runtime authority broadening (NOT_AUTHORIZED unchanged).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Sequence

from virtual_factory.composition import (
    BoundaryPort,
    BoundaryTransfer,
    CompositionBinding,
    CompositionGraph,
    Coordinator,
    PortCategory,
    PortDirection,
    PortRef,
    WindowOutcome,
)
from virtual_factory.connectivity.scenario_overlay import (
    AssumedTopologyEdge,
    ScenarioTopologyOverlay,
)
from virtual_factory.provenance import RunContextV2
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_SCOPE_PATH,
    T106Config,
    T106LogicalRuntime,
)
from virtual_factory.shwtp.projection import (
    SHWTP_F01_BINDING_ID,
    SHWTP_T106_OUT_PORT_ID,
    SHWTP_T108_IN_PORT_ID,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_SCOPE_PATH,
    T108Config,
    T108TankRuntime,
)
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

SHWTP_PLANT_SLICE_WORKSPACE_ID = "shwtp"
SHWTP_PLANT_SLICE_COUPLING_POLICY = "explicit_lagged"
SHWTP_PLANT_SLICE_PAYLOAD_KEY = "volumetric_flow_m3_s"
SHWTP_PLANT_SLICE_DEFAULT_RUN_ID = "run-shwtp-plant-slice"

RAW_INTAKE_SCOPE_PATH = StructuralPath(("shwtp", "raw_water", "raw_intake"))
T100_SCOPE_PATH = StructuralPath(("shwtp", "raw_water", "t100"))
DIST_P108_SCOPE_PATH = StructuralPath(("shwtp", "dist_p108"))

# Slice-local port ids (VF boundary identity, never PIM canonical ids).
RAW_OUT_PORT = "out"
T100_IN_PORT = "in"
T100_OUT_PORT = "out"
T106_IN_PORT = "in_flow"       # slice-local upstream input (NEW, not G14A)
T108_OUT_PORT = "out_flow"     # slice-local downstream output (NEW, not G14A)
DIST_IN_PORT = "in"

BIND_RAW_T100 = "BIND-SHW-RAW-T100"
BIND_T100_T106 = "BIND-SHW-T100-T106"
BIND_T108_DIST = "BIND-SHW-T108-DIST-P108"


class ShwtpExpansionError(ValueError):
    """Raised when a SH-WTP plant-slice invariant is violated (fail closed)."""


def _require_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShwtpExpansionError(f"{name} must be a finite number, got {value!r}")
    if not math.isfinite(float(value)):
        raise ShwtpExpansionError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShwtpExpansionError(f"{name} must be a non-empty str")
    return value


@dataclass(frozen=True, slots=True)
class PlantSliceScope:
    """One executable scope descriptor with explicit fidelity/status."""

    canonical_id: str          # PIM canonical semantic reference (read-only metadata)
    vf_path: str               # VF G1 StructuralPath string
    role: str
    fidelity: str              # "logical_only" | "first_order"
    status: str                # "accepted" | "scenario_assumed"
    inbound_link_assumed: bool  # whether the INBOUND link is assumed topology

    def to_dict(self) -> dict:
        return {
            "canonical_id": self.canonical_id,
            "vf_path": self.vf_path,
            "role": self.role,
            "fidelity": self.fidelity,
            "status": self.status,
            "inbound_link_assumed": self.inbound_link_assumed,
        }


PLANT_SLICE_SCOPES: tuple[PlantSliceScope, ...] = (
    PlantSliceScope(
        canonical_id="UNIT-SHW-RAW-INTAKE",
        vf_path=RAW_INTAKE_SCOPE_PATH.as_string(),
        role="source",
        fidelity="logical_only",
        status="scenario_assumed",
        inbound_link_assumed=False,
    ),
    PlantSliceScope(
        canonical_id="UNIT-SHW-T100",
        vf_path=T100_SCOPE_PATH.as_string(),
        role="junction",
        fidelity="logical_only",
        status="scenario_assumed",
        inbound_link_assumed=True,
    ),
    PlantSliceScope(
        canonical_id="UNIT-SHW-L1-T106",
        vf_path=SHWTP_T106_SCOPE_PATH.as_string(),
        role="filter",
        fidelity="logical_only",
        status="accepted",
        inbound_link_assumed=True,
    ),
    PlantSliceScope(
        canonical_id="UNIT-SHW-L1-T108",
        vf_path=SHWTP_T108_SCOPE_PATH.as_string(),
        role="clean_water_tank",
        fidelity="first_order",
        status="accepted",
        inbound_link_assumed=False,   # authoritative REL-SHW-F01
    ),
    PlantSliceScope(
        canonical_id="UNIT-SHW-DIST-P108",
        vf_path=DIST_P108_SCOPE_PATH.as_string(),
        role="distribution_sink",
        fidelity="logical_only",
        status="scenario_assumed",
        inbound_link_assumed=True,
    ),
)


def _scope_by_path(path: str) -> PlantSliceScope:
    for scope in PLANT_SLICE_SCOPES:
        if scope.vf_path == path:
            return scope
    raise ShwtpExpansionError(f"unknown slice scope path {path!r}")


class LogicalSourceParticipant:
    """LogicalOnly source scope (RAW-INTAKE): emits a synthetic raw-water inflow."""

    def __init__(
        self,
        scope_path: StructuralPath,
        workspace_id: str,
        run_id: str,
        out_port: PortRef,
        target_ref: PortRef,
        binding_id: str,
        initial_inflow_m3_s: float,
    ) -> None:
        self._scope_path = scope_path
        self._workspace_id = workspace_id
        self._run_id = run_id
        self._out_port = out_port
        self._target_ref = target_ref
        self._binding_id = binding_id
        self._inflow = _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
        self._time_s = 0.0
        self._window: str | None = None

    @property
    def scope_path(self) -> StructuralPath:
        return self._scope_path

    @property
    def current_time_s(self) -> float:
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        _require_nonempty(window_id, "window_id")
        self._window = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        if target_time_s < self._time_s:
            raise ShwtpExpansionError(
                f"cannot advance backward: {self._time_s!r} -> {target_time_s!r}"
            )
        self._time_s = float(target_time_s)
        return (
            BoundaryTransfer(
                transfer_id=f"{self._window}::{self._scope_path.as_string()}",
                source=self._out_port,
                target=self._target_ref,
                binding_id=self._binding_id,
                window_id=self._window or "",
                simulation_time_s=float(target_time_s),
                workspace_id=self._workspace_id,
                run_id=self._run_id,
                payload={SHWTP_PLANT_SLICE_PAYLOAD_KEY: self._inflow},
            ),
        )

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        if inbound:
            raise ShwtpExpansionError(
                f"pure source {self._scope_path.as_string()!r} received inbound"
            )


class LogicalJunctionParticipant:
    """LogicalOnly junction (T100): one-window-lag pass-through."""

    def __init__(
        self,
        scope_path: StructuralPath,
        workspace_id: str,
        run_id: str,
        in_port: PortRef,
        out_port: PortRef,
        target_ref: PortRef,
        binding_id: str,
        initial_inflow_m3_s: float,
    ) -> None:
        self._scope_path = scope_path
        self._workspace_id = workspace_id
        self._run_id = run_id
        self._in_port = in_port
        self._out_port = out_port
        self._target_ref = target_ref
        self._binding_id = binding_id
        self._inflow = _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
        self._time_s = 0.0
        self._window: str | None = None

    @property
    def scope_path(self) -> StructuralPath:
        return self._scope_path

    @property
    def current_time_s(self) -> float:
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        _require_nonempty(window_id, "window_id")
        self._window = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        if target_time_s < self._time_s:
            raise ShwtpExpansionError(
                f"cannot advance backward: {self._time_s!r} -> {target_time_s!r}"
            )
        self._time_s = float(target_time_s)
        return (
            BoundaryTransfer(
                transfer_id=f"{self._window}::{self._scope_path.as_string()}",
                source=self._out_port,
                target=self._target_ref,
                binding_id=self._binding_id,
                window_id=self._window or "",
                simulation_time_s=float(target_time_s),
                workspace_id=self._workspace_id,
                run_id=self._run_id,
                payload={SHWTP_PLANT_SLICE_PAYLOAD_KEY: self._inflow},
            ),
        )

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        value = _latest_inbound_flow(inbound, self._scope_path.as_string())
        self._inflow = value


class T106FilterParticipant:
    """Accepted T106 LogicalOnly filter runtime, fed from upstream (one-window lag)."""

    def __init__(
        self,
        runtime: T106LogicalRuntime,
        run_id: str,
        workspace_id: str,
        in_port: PortRef,
        out_port: PortRef,
        target_ref: PortRef,
        binding_id: str,
        initial_inflow_m3_s: float,
    ) -> None:
        if not isinstance(runtime, T106LogicalRuntime):
            raise ShwtpExpansionError(
                f"runtime must be T106LogicalRuntime, got {type(runtime).__name__}"
            )
        self._runtime = runtime
        self._run_id = run_id
        self._workspace_id = workspace_id
        self._in_port = in_port
        self._out_port = out_port
        self._target_ref = target_ref
        self._binding_id = binding_id
        self._inflow = _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
        self._window: str | None = None

    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T106_SCOPE_PATH

    @property
    def current_time_s(self) -> float:
        return self._runtime.state.time_s

    def prepare_window(self, window_id: str) -> None:
        _require_nonempty(window_id, "window_id")
        self._window = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        before = self._runtime.state.time_s
        if target_time_s < before:
            raise ShwtpExpansionError(
                f"cannot advance backward: {before!r} -> {target_time_s!r}"
            )
        step = self._runtime.step(self._inflow)
        if step.end_time_s != target_time_s:
            raise ShwtpExpansionError(
                f"T106 did not land on boundary {target_time_s!r}: "
                f"reported {step.end_time_s!r}"
            )
        return (
            BoundaryTransfer(
                transfer_id=f"{self._window}::{self.scope_path.as_string()}",
                source=self._out_port,
                target=self._target_ref,
                binding_id=self._binding_id,
                window_id=self._window or "",
                simulation_time_s=float(target_time_s),
                workspace_id=self._workspace_id,
                run_id=self._run_id,
                payload={SHWTP_PLANT_SLICE_PAYLOAD_KEY: step.output_flow_m3_s},
            ),
        )

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        self._inflow = _latest_inbound_flow(inbound, self.scope_path.as_string())


class T108TankParticipant:
    """Accepted T108 FirstOrder tank runtime, fed from upstream (one-window lag)."""

    def __init__(
        self,
        runtime: T108TankRuntime,
        run_id: str,
        workspace_id: str,
        in_port: PortRef,
        out_port: PortRef,
        target_ref: PortRef,
        binding_id: str,
        initial_inflow_m3_s: float,
        requested_outflow_m3_s: float,
    ) -> None:
        if not isinstance(runtime, T108TankRuntime):
            raise ShwtpExpansionError(
                f"runtime must be T108TankRuntime, got {type(runtime).__name__}"
            )
        self._runtime = runtime
        self._run_id = run_id
        self._workspace_id = workspace_id
        self._in_port = in_port
        self._out_port = out_port
        self._target_ref = target_ref
        self._binding_id = binding_id
        self._inflow = _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
        self._requested_outflow = _require_number(
            requested_outflow_m3_s, "requested_outflow_m3_s"
        )
        self._window: str | None = None

    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T108_SCOPE_PATH

    @property
    def current_time_s(self) -> float:
        return self._runtime.state.time_s

    def prepare_window(self, window_id: str) -> None:
        _require_nonempty(window_id, "window_id")
        self._window = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        before = self._runtime.state.time_s
        if target_time_s < before:
            raise ShwtpExpansionError(
                f"cannot advance backward: {before!r} -> {target_time_s!r}"
            )
        step = self._runtime.step(self._inflow, self._requested_outflow)
        if step.end_time_s != target_time_s:
            raise ShwtpExpansionError(
                f"T108 did not land on boundary {target_time_s!r}: "
                f"reported {step.end_time_s!r}"
            )
        return (
            BoundaryTransfer(
                transfer_id=f"{self._window}::{self.scope_path.as_string()}",
                source=self._out_port,
                target=self._target_ref,
                binding_id=self._binding_id,
                window_id=self._window or "",
                simulation_time_s=float(target_time_s),
                workspace_id=self._workspace_id,
                run_id=self._run_id,
                payload={SHWTP_PLANT_SLICE_PAYLOAD_KEY: step.applied_outflow_m3_s},
            ),
        )

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        self._inflow = _latest_inbound_flow(inbound, self.scope_path.as_string())


class LogicalSinkParticipant:
    """LogicalOnly distribution sink (DIST-P108): consumes inbound only."""

    def __init__(
        self,
        scope_path: StructuralPath,
        workspace_id: str,
        run_id: str,
        in_port: PortRef,
    ) -> None:
        self._scope_path = scope_path
        self._workspace_id = workspace_id
        self._run_id = run_id
        self._in_port = in_port
        self._time_s = 0.0
        self._received: list[float] = []

    @property
    def scope_path(self) -> StructuralPath:
        return self._scope_path

    @property
    def current_time_s(self) -> float:
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        _require_nonempty(window_id, "window_id")
        self._window = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        if target_time_s < self._time_s:
            raise ShwtpExpansionError(
                f"cannot advance backward: {self._time_s!r} -> {target_time_s!r}"
            )
        self._time_s = float(target_time_s)
        return ()

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        value = _latest_inbound_flow(inbound, self._scope_path.as_string())
        self._received.append(value)


def _latest_inbound_flow(
    inbound: Sequence[BoundaryTransfer], label: str
) -> float:
    if len(inbound) != 1:
        raise ShwtpExpansionError(
            f"{label} expected exactly one inbound transfer, got {len(inbound)}"
        )
    transfer = inbound[0]
    payload = transfer.payload
    if not isinstance(payload, Mapping) or SHWTP_PLANT_SLICE_PAYLOAD_KEY not in payload:
        raise ShwtpExpansionError(
            f"inbound transfer {transfer.transfer_id!r} payload missing "
            f"{SHWTP_PLANT_SLICE_PAYLOAD_KEY!r}"
        )
    value = _require_number(
        payload[SHWTP_PLANT_SLICE_PAYLOAD_KEY], "inbound volumetric_flow_m3_s"
    )
    if value < 0:
        raise ShwtpExpansionError("inbound volumetric_flow_m3_s must be >= 0")
    return value


@dataclass
class ShwtpPlantSlice:
    """A built runnable SH-WTP slice (workspace + graph + overlay + coordinator)."""

    workspace: Workspace
    graph: CompositionGraph
    overlay: ScenarioTopologyOverlay
    coordinator: Coordinator
    participants: dict[str, object]
    scopes: tuple[PlantSliceScope, ...]
    communication_step_s: float
    coupling_policy: str

    def run_window(self, window_id: str) -> WindowOutcome:
        for participant in self.participants.values():
            participant.prepare_window(window_id)
        target = self.communication_step_s * _window_number(window_id)
        return self.coordinator.run_window(window_id, target)


def _window_number(window_id: str) -> int:
    import re
    m = re.fullmatch(r"window-([1-9][0-9]*)", window_id)
    if not m:
        raise ShwtpExpansionError(
            f"invalid window id {window_id!r}; expected 'window-<n>' with n >= 1"
        )
    return int(m.group(1))


def build_shwtp_plant_slice(
    *,
    communication_step_s: float = 1.0,
    initial_inflow_m3_s: float = 2.0,
    t100_initial_inflow_m3_s: float = 2.0,
    t106_initial_inflow_m3_s: float = 2.0,
    t108_initial_inflow_m3_s: float = 0.0,
    t108_requested_outflow_m3_s: float = 1.5,
    t108_capacity_m3: float = 100.0,
    t108_tank_area_m2: float = 20.0,
    t108_initial_volume_m3: float = 50.0,
    run_id: str = SHWTP_PLANT_SLICE_DEFAULT_RUN_ID,
) -> ShwtpPlantSlice:
    """Build the 5-scope SH-WTP plant slice with explicit_lagged orchestration."""
    _require_number(communication_step_s, "communication_step_s")
    if communication_step_s <= 0:
        raise ShwtpExpansionError("communication_step_s must be > 0")
    _require_nonempty(run_id, "run_id")
    _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
    _require_number(t100_initial_inflow_m3_s, "t100_initial_inflow_m3_s")
    _require_number(t106_initial_inflow_m3_s, "t106_initial_inflow_m3_s")
    _require_number(t108_initial_inflow_m3_s, "t108_initial_inflow_m3_s")
    _require_number(t108_requested_outflow_m3_s, "t108_requested_outflow_m3_s")
    _require_number(t108_capacity_m3, "t108_capacity_m3")
    _require_number(t108_tank_area_m2, "t108_tank_area_m2")
    _require_number(t108_initial_volume_m3, "t108_initial_volume_m3")

    ws_id = SHWTP_PLANT_SLICE_WORKSPACE_ID
    # Bounded slice workspace: only the five executable scopes, with the same
    # containment paths as G11/G16 (raw_water/ and line1/ are containers).
    workspace = build_workspace(
        ws_id,
        [
            ScopeSpec(scope_id="raw_water", mode=ScopeMode.CONTAINER_ONLY),
            ScopeSpec(
                scope_id="raw_intake",
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=StructuralPath((ws_id, "raw_water")),
            ),
            ScopeSpec(
                scope_id="t100",
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=StructuralPath((ws_id, "raw_water")),
            ),
            ScopeSpec(scope_id="line1", mode=ScopeMode.CONTAINER_ONLY),
            ScopeSpec(
                scope_id="l1_t106",
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=StructuralPath((ws_id, "line1")),
            ),
            ScopeSpec(
                scope_id="l1_t108",
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=StructuralPath((ws_id, "line1")),
            ),
            ScopeSpec(scope_id="dist_p108", mode=ScopeMode.EXECUTABLE_CAPABLE),
        ],
    )

    raw_out = PortRef(RAW_INTAKE_SCOPE_PATH, RAW_OUT_PORT)
    t100_in = PortRef(T100_SCOPE_PATH, T100_IN_PORT)
    t100_out = PortRef(T100_SCOPE_PATH, T100_OUT_PORT)
    t106_in = PortRef(SHWTP_T106_SCOPE_PATH, T106_IN_PORT)
    t106_out = PortRef(SHWTP_T106_SCOPE_PATH, SHWTP_T106_OUT_PORT_ID)
    t108_in = PortRef(SHWTP_T108_SCOPE_PATH, SHWTP_T108_IN_PORT_ID)
    t108_out = PortRef(SHWTP_T108_SCOPE_PATH, T108_OUT_PORT)
    dist_in = PortRef(DIST_P108_SCOPE_PATH, DIST_IN_PORT)

    ports = [
        BoundaryPort(ref=raw_out, direction=PortDirection.OUT, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t100_in, direction=PortDirection.IN, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t100_out, direction=PortDirection.OUT, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t106_in, direction=PortDirection.IN, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t106_out, direction=PortDirection.OUT, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t108_in, direction=PortDirection.IN, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=t108_out, direction=PortDirection.OUT, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
        BoundaryPort(ref=dist_in, direction=PortDirection.IN, category=PortCategory.MATERIAL, unit="m3/s", descriptor="volumetric_flow"),
    ]

    bindings = [
        CompositionBinding(edge_id=BIND_RAW_T100, source=raw_out, target=t100_in),
        CompositionBinding(edge_id=BIND_T100_T106, source=t100_out, target=t106_in),
        CompositionBinding(edge_id=SHWTP_F01_BINDING_ID, source=t106_out, target=t108_in),
        CompositionBinding(edge_id=BIND_T108_DIST, source=t108_out, target=dist_in),
    ]

    graph = CompositionGraph(workspace_id=ws_id, bindings=bindings, ports=ports)

    # G18 scenario-assumed topology for the three links PIM has NOT confirmed.
    overlay = ScenarioTopologyOverlay(
        overlay_id="shwtp-plant-slice-assumed-topology",
        version="1",
        domain="shwtp",
        edges=(
            AssumedTopologyEdge(
                assumption_id="ASSUME-SHW-RAW-T100",
                version="1",
                source=RAW_INTAKE_SCOPE_PATH.as_string(),
                target=T100_SCOPE_PATH.as_string(),
                relation_type="ASSUMED_FLOWS_TO",
                rationale="scenario assumption: raw intake feeds receiving junction T100",
            ),
            AssumedTopologyEdge(
                assumption_id="ASSUME-SHW-T100-T106",
                version="1",
                source=T100_SCOPE_PATH.as_string(),
                target=SHWTP_T106_SCOPE_PATH.as_string(),
                relation_type="ASSUMED_FLOWS_TO",
                rationale="scenario assumption: junction T100 feeds filter T106",
            ),
            AssumedTopologyEdge(
                assumption_id="ASSUME-SHW-T108-DIST-P108",
                version="1",
                source=SHWTP_T108_SCOPE_PATH.as_string(),
                target=DIST_P108_SCOPE_PATH.as_string(),
                relation_type="ASSUMED_FLOWS_TO",
                rationale=(
                    "scenario assumption: T108 clean-water outlet feeds "
                    "distribution P108 (NOT PIM-confirmed; reversible)"
                ),
            ),
        ),
    )

    t106_runtime = T106LogicalRuntime(
        T106Config(dt_s=communication_step_s),
        RunContextV2(workspace_id=ws_id, run_id=run_id, scope_path=SHWTP_T106_SCOPE_PATH),
    )
    t108_runtime = T108TankRuntime(
        T108Config(
            capacity_m3=t108_capacity_m3,
            tank_area_m2=t108_tank_area_m2,
            initial_volume_m3=t108_initial_volume_m3,
            dt_s=communication_step_s,
        ),
        RunContextV2(workspace_id=ws_id, run_id=run_id, scope_path=SHWTP_T108_SCOPE_PATH),
    )

    participants: dict[str, object] = {}
    participants[RAW_INTAKE_SCOPE_PATH.as_string()] = LogicalSourceParticipant(
        RAW_INTAKE_SCOPE_PATH, ws_id, run_id, raw_out, t100_in, BIND_RAW_T100,
        initial_inflow_m3_s,
    )
    participants[T100_SCOPE_PATH.as_string()] = LogicalJunctionParticipant(
        T100_SCOPE_PATH, ws_id, run_id, t100_in, t100_out, t106_in, BIND_T100_T106,
        t100_initial_inflow_m3_s,
    )
    participants[SHWTP_T106_SCOPE_PATH.as_string()] = T106FilterParticipant(
        t106_runtime, run_id, ws_id, t106_in, t106_out, t108_in, SHWTP_F01_BINDING_ID,
        t106_initial_inflow_m3_s,
    )
    participants[SHWTP_T108_SCOPE_PATH.as_string()] = T108TankParticipant(
        t108_runtime, run_id, ws_id, t108_in, t108_out, dist_in, BIND_T108_DIST,
        t108_initial_inflow_m3_s, t108_requested_outflow_m3_s,
    )
    participants[DIST_P108_SCOPE_PATH.as_string()] = LogicalSinkParticipant(
        DIST_P108_SCOPE_PATH, ws_id, run_id, dist_in,
    )

    coordinator = Coordinator(workspace=workspace, graph=graph)
    for key in sorted(participants):
        coordinator.register(participants[key])

    return ShwtpPlantSlice(
        workspace=workspace,
        graph=graph,
        overlay=overlay,
        coordinator=coordinator,
        participants=participants,
        scopes=PLANT_SLICE_SCOPES,
        communication_step_s=communication_step_s,
        coupling_policy=SHWTP_PLANT_SLICE_COUPLING_POLICY,
    )
