"""SH-WTP X2 whole-plant shallow runnable model (VF-SHW-X2).

Turns the frozen X1 contract layer into an executable deterministic
synthetic/reference whole-plant model with C1 functional control. It is built
ONLY from:

- ``configs/vnext/shwtp/shwtp_whole_plant_graph_v1.json`` (topology/provenance),
- ``configs/vnext/shwtp/shwtp_process_contracts_v1.json`` (per-scope behaviour),
- ``configs/vnext/shwtp/shwtp_control_contracts_v1.json`` (C1 functional control),
- ``configs/vnext/shwtp/shwtp_x2_admission_manifest_v1.json`` (admission boundary),
- ``src/virtual_factory/shwtp/contracts.py`` (the fail-closed loader).

Frozen invariants honoured here:

- exactly the 16 admitted executable scopes participate; ELEC-MCC / AUTO-PLC /
  T107 and the LINE2 internals never execute;
- exactly the 9 X2-active C1 controls evaluate; no C2 equation is ever
  evaluated (the C2 facts used are only ``x2_status``/``x2_replacement``);
- the coordinator coupling is ``explicit_lagged``: every participant emits from
  its COMMITTED state, so no same-window feed-through exists;
- every transfer payload carries its graph-edge provenance (``pim_relation_id``
  for PIM-known edges, ``assumption_id`` for assumed edges) and stays
  ``site_truth=False`` / ``simulation_truth=synthetic_reference``;
- all states are bounded, flows/volumes non-negative, invalid states fail closed
  with labelled VF synthetic alarms;
- deterministic: window-index driven, no wall clock, no unordered iteration.

This module constructs no runtime/session/lifecycle authority of its own: it is
a model driven by the existing canonical ``ShwtpExecutionBridge`` /
``RunLifecycleService`` / ``RuntimeSession`` seam.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

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
from virtual_factory.shwtp.contracts import WholePlantContracts, load_whole_plant_contracts
from virtual_factory.shwtp.x2_controls import C1ControllerSet, build_c1_controllers
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

SHWTP_WHOLE_PLANT_WORKSPACE_ID = "shwtp"
SHWTP_WHOLE_PLANT_COUPLING_POLICY = "explicit_lagged"
SHWTP_WHOLE_PLANT_DEFAULT_RUN_ID = "run-shwtp-whole-plant-x2"
SHWTP_WHOLE_PLANT_DEFAULT_STEP_S = 60.0
WHOLE_PLANT_X2_SCHEMA = "vf.shwtp.x2.whole_plant_runtime.v1"

#: Mandatory X2 truth/authorization labels carried by EVERY runtime output.
SITE_TRUTH = False
SIMULATION_TRUTH = "synthetic_reference"
VF_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"
SITE_AUTHORIZED_EXECUTION = "NOT_AUTHORIZED"
#: Implementation state is kept SEPARATE from authorization state.
WHOLE_PLANT_RUNTIME_IMPLEMENTATION = "IMPLEMENTED_SYNTHETIC_REFERENCE"
WHOLE_PLANT_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"

AUTHORITY_LABELS: Mapping[str, Any] = {
    "site_truth": SITE_TRUTH,
    "simulation_truth": SIMULATION_TRUTH,
    "vf_runtime_authorization": VF_RUNTIME_AUTHORIZATION,
    "site_authorized_execution": SITE_AUTHORIZED_EXECUTION,
}


def authority_labels() -> dict:
    """The four mandatory labels (detached copy; read-only projection)."""
    return dict(AUTHORITY_LABELS)


def require_authority_labels(record: Mapping[str, Any], *, where: str) -> None:
    """Fail closed when a runtime output drifts from the mandatory labels."""
    for key, expected in AUTHORITY_LABELS.items():
        if key not in record:
            raise WholePlantX2Error(f"{where} is missing the mandatory label {key!r}")
        if record[key] != expected:
            raise WholePlantX2Error(
                f"{where} declares {key}={record[key]!r}; the mandatory value is {expected!r}"
            )

#: VF-local scope path segments (G1 StructuralPath) per admitted PIM id.
SCOPE_PATHS: dict[str, tuple[str, ...]] = {
    "vf-shw-node-raw-source": ("raw_water", "raw_source"),
    "vf-shw-node-raw-intake": ("raw_water", "raw_intake"),
    "vf-shw-node-t100": ("raw_water", "t100"),
    "vf-shw-node-t101": ("line1", "l1_t101"),
    "vf-shw-node-t102": ("line1", "l1_t102"),
    "vf-shw-node-t103": ("line1", "l1_t103"),
    "vf-shw-node-t104": ("line1", "l1_t104"),
    "vf-shw-node-t105": ("line1", "l1_t105"),
    "vf-shw-node-t106": ("line1", "l1_t106"),
    "vf-shw-node-t108": ("line1", "l1_t108"),
    "vf-shw-node-wash-t110": ("line1", "wash_t110"),
    "vf-shw-node-chem-dosing": ("chemical", "chem_dosing"),
    "vf-shw-node-sludge-t201": ("sludge", "sludge_t201"),
    "vf-shw-node-dist-p108": ("dist_p108",),
    "vf-shw-node-line2-aggregate": ("line2", "line2_aggregate"),
    "vf-shw-node-network-demand": ("network_demand",),
}

#: Container scopes (never executable, never registered) for structural parity.
CONTAINER_PATHS: tuple[tuple[str, ...], ...] = (("raw_water",), ("line1",), ("chemical",), ("sludge",), ("line2",))

#: The 15 assumed edges + 3 PIM-known edges that carry material/flow in X2.
X2_FLOW_EDGE_IDS: tuple[str, ...] = (
    "vf-shw-edge-raw-source-intake",
    "vf-shw-edge-intake-t100",
    "vf-shw-edge-t100-l1",
    "vf-shw-edge-t100-line2",
    "vf-shw-edge-t101-t102",
    "vf-shw-edge-t102-t103",
    "vf-shw-edge-t103-t104",
    "vf-shw-edge-t104-t105",
    "vf-shw-edge-t105-t106",
    "vf-shw-edge-t105-sludge",
    "vf-shw-edge-t106-t108",
    "vf-shw-edge-t106-wash",
    "vf-shw-edge-wash-t106",
    "vf-shw-edge-t108-dist",
    "vf-shw-edge-dist-demand",
    "vf-shw-edge-line2-dist",
    "vf-shw-edge-chem-t102",
    "vf-shw-edge-chem-t103",
)

#: Contract-declared process input relations between process nodes (information).
X2_INFORMATION_EDGE_IDS: tuple[str, ...] = (
    "vf-shw-info-t101-demand-t100",
    "vf-shw-info-line2-split-t100",
    "vf-shw-info-t100-plant-flow-chem",
)

#: Bindings that carry raw-source AVAILABILITY outside the plant control volume:
#: the pumped-intake boundary starts at the intake discharge, so water the intake
#: does not pump never enters the plant and must not enter the inventory (C02-3).
OUTSIDE_BOUNDARY_BINDINGS: frozenset[str] = frozenset({"vf-shw-edge-raw-source-intake"})

#: The plant control volume: IN at the pumped-intake discharge, OUT at the
#: network discharge (plus the sludge tank outflow, which emits no transfer).
INTAKE_BINDING_ID = "vf-shw-edge-intake-t100"
NETWORK_BINDING_ID = "vf-shw-edge-dist-demand"
LINE2_FEED_BINDING_ID = "vf-shw-edge-t100-line2"
LINE2_DELIVERY_BINDING_ID = "vf-shw-edge-line2-dist"
#: Boundary role per binding (everything else is internal): ``entry`` water
#: enters the control volume, ``exit`` water has left it.
BOUNDARY_ROLE: Mapping[str, str] = {
    INTAKE_BINDING_ID: "entry",
    NETWORK_BINDING_ID: "exit",
}

#: Documented NUMERICAL (float rounding) tolerance for the ledger reconciliation.
#: This is not a model-approximation allowance: the ledger must close to rounding
#: error, and any modelled loss is an explicit (alarmed) ledger term instead.
PLANT_WATER_TOLERANCE_RELATIVE = 1e-9
PLANT_WATER_TOLERANCE_ABSOLUTE_M3 = 1e-9

#: Justified ROUNDING tolerance for artificially CREATED water (a negative volume
#: clamped back to zero, VF-SHW-X2-C03). Any material creation invalidates physical
#: conservation: the amount is reported as a diagnostic but is NEVER used to
#: reconcile the balance.
CREATED_WATER_TOLERANCE_M3 = 1e-9

#: Rounding tolerance of the declared LINE2 process-loss audit.
PROCESS_LOSS_TOLERANCE_M3 = 1e-9


def audit_line2_process_loss(
    *,
    feed_m3h: float,
    delivered_m3h: float,
    loss_fraction: float,
    capacity_m3h: float,
) -> dict:
    """Prove a LINE2 transfer's loss equals the DECLARED law + modelled spill (C03-4).

    The declared law is ``delivery = max(0, min(feed * (1 - loss_fraction), capacity))``,
    so an admissible loss is exactly ``feed * loss_fraction`` (the declared process
    loss) plus ``max(0, feed * (1 - loss_fraction) - capacity)`` (the explicitly
    modelled capacity spill). An arbitrary dropped delivery is NOT a valid process
    loss and makes ``valid`` False.
    """
    feed = _nonneg(feed_m3h, "feed_m3h")
    delivered = _nonneg(delivered_m3h, "delivered_m3h")
    fraction = _num(loss_fraction, "loss_fraction")
    if not 0.0 <= fraction <= 1.0:
        raise WholePlantX2Error("loss_fraction must be within [0, 1]")
    capacity = _nonneg(capacity_m3h, "capacity_m3h")
    after_loss = feed * (1.0 - fraction)
    declared_loss = feed * fraction
    capacity_spill = max(0.0, after_loss - capacity)
    expected_delivery = min(after_loss, capacity)
    observed_loss = feed - delivered
    delivery_matches_law = abs(delivered - expected_delivery) <= PROCESS_LOSS_TOLERANCE_M3
    loss_matches_law = abs(observed_loss - (declared_loss + capacity_spill)) <= PROCESS_LOSS_TOLERANCE_M3
    return {
        "feed_m3h": round(feed, 12),
        "delivered_m3h": round(delivered, 12),
        "declared_loss_m3h": round(declared_loss, 12),
        "capacity_spill_m3h": round(capacity_spill, 12),
        "expected_delivery_m3h": round(expected_delivery, 12),
        "observed_loss_m3h": round(observed_loss, 12),
        "delivery_matches_declared_law": delivery_matches_law,
        "loss_equals_declared_plus_spill": loss_matches_law,
        "valid": bool(delivery_matches_law and loss_matches_law),
    }


def _empty_water_ledger() -> dict:
    return {
        "plant_in_m3": 0.0,
        "plant_out_m3": 0.0,
        "process_loss_m3": 0.0,
        "process_loss_observed_m3": 0.0,
        "process_loss_audit_failures": 0,
        "overflow_m3": 0.0,
        "shortfall_m3": 0.0,
        "in_transit_m3": 0.0,
        "information_m3": 0.0,
        "source_availability_m3": 0.0,
    }


class WholePlantX2Error(ValueError):
    """Raised when an X2 whole-plant invariant is violated (fail closed)."""


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WholePlantX2Error(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise WholePlantX2Error(f"{name} must be a finite number, got {value!r}")
    return out


def _nonneg(value: Any, name: str) -> float:
    out = _num(value, name)
    if out < 0:
        raise WholePlantX2Error(f"{name} must be >= 0, got {out!r}")
    return out


def scope_path(scope_id: str) -> StructuralPath:
    segments = SCOPE_PATHS.get(scope_id)
    if segments is None:
        raise WholePlantX2Error(f"no VF scope path is declared for scope {scope_id!r}")
    return StructuralPath((SHWTP_WHOLE_PLANT_WORKSPACE_ID, *segments))


# ── scenario (deterministic synthetic/reference plant parameters) ─────────

@dataclass(frozen=True, slots=True)
class WholePlantScenario:
    """Deterministic synthetic scenario parameters (provenance synthetic_reference)."""

    name: str = "x2-synthetic-reference-default"
    communication_step_s: float = SHWTP_WHOLE_PLANT_DEFAULT_STEP_S
    raw_flow_sp_m3h: float = 45.0
    raw_turbidity_ntu: float = 12.0
    raw_ph: float = 7.2
    line1_demand_m3h: float = 36.0
    line2_split_fraction: float = 0.2
    network_demand_m3h: float = 40.0
    pump_rated_flow_m3h: float = 60.0
    screen_dp_gain_kpa_per_m3h: float = 0.06
    intake_screen_dp_limit_kpa: float = 50.0
    t100_area_m2: float = 20.0
    t100_capacity_m3: float = 200.0
    t100_initial_volume_m3: float = 60.0
    t100_level_band_m: tuple[float, float, float, float] = (0.5, 0.8, 3.5, 4.0)
    t101_contact_volume_m3: float = 30.0
    t104_floc_volume_m3: float = 30.0
    t102_dose_efficiency: float = 0.05
    t103_dose_efficiency: float = 0.08
    t105_settling_efficiency: float = 0.85
    t105_capacity_m3: float = 150.0
    t105_initial_volume_m3: float = 60.0
    t105_area_m2: float = 30.0
    t105_sludge_withdrawal_m3h: float = 2.0
    t105_settled_volume_high_m3: float = 120.0
    t106_dp_initial_kpa: float = 25.0
    t106_dp_growth_kpa_per_s: float = 0.02
    t106_filter_efficiency: float = 0.96
    t106_backwash_wash_flow_m3h: float = 5.0
    t106_capacity_m3: float = 40.0
    t106_initial_volume_m3: float = 10.0
    wash_t110_capacity_m3: float = 30.0
    wash_t110_area_m2: float = 15.0
    wash_t110_return_flow_m3h: float = 4.0
    wash_t110_level_sufficient_m: float = 0.4
    t108_area_m2: float = 20.0
    t108_capacity_m3: float = 100.0
    t108_initial_volume_m3: float = 50.0
    t108_level_band_m: tuple[float, float, float, float] = (1.0, 1.4, 4.0, 4.6)
    t108_transfer_rated_flow_m3h: float = 60.0
    dist_curve_head_bar: float = 4.0
    dist_manifold_loss_bar_per_m3h2: float = 0.0006
    dist_pressure_ceiling_bar: float = 8.0
    chem_pac_dose_mg_l: float = 2.0
    chem_coag_dose_mg_l: float = 1.0
    chem_tank_capacity_l: float = 5000.0
    sludge_t201_capacity_m3: float = 80.0
    sludge_t201_initial_volume_m3: float = 10.0
    sludge_t201_area_m2: float = 20.0
    sludge_t201_high_m3: float = 70.0
    sludge_processed_flow_m3h: float = 2.0
    line2_loss_fraction: float = 0.01
    line2_quality_proxy_ntu: float = 0.4
    line2_capacity_m3h: float = 20.0

    def __post_init__(self) -> None:
        step = _num(self.communication_step_s, "communication_step_s")
        if step <= 0:
            raise WholePlantX2Error("communication_step_s must be > 0")
        for name in (
            "raw_flow_sp_m3h", "raw_turbidity_ntu", "raw_ph", "line1_demand_m3h",
            "line2_split_fraction", "network_demand_m3h", "pump_rated_flow_m3h",
            "screen_dp_gain_kpa_per_m3h", "intake_screen_dp_limit_kpa", "t100_area_m2",
            "t100_capacity_m3", "t100_initial_volume_m3", "t101_contact_volume_m3",
            "t104_floc_volume_m3",
            "t102_dose_efficiency", "t103_dose_efficiency", "t105_settling_efficiency",
            "t105_capacity_m3", "t105_initial_volume_m3", "t105_area_m2",
            "t105_sludge_withdrawal_m3h", "t105_settled_volume_high_m3",
            "t106_dp_initial_kpa", "t106_dp_growth_kpa_per_s", "t106_filter_efficiency",
            "t106_backwash_wash_flow_m3h", "t106_capacity_m3", "t106_initial_volume_m3",
            "wash_t110_capacity_m3", "wash_t110_area_m2", "wash_t110_return_flow_m3h",
            "wash_t110_level_sufficient_m", "t108_area_m2", "t108_capacity_m3",
            "t108_initial_volume_m3", "t108_transfer_rated_flow_m3h", "dist_curve_head_bar",
            "dist_manifold_loss_bar_per_m3h2", "dist_pressure_ceiling_bar",
            "chem_pac_dose_mg_l", "chem_coag_dose_mg_l", "chem_tank_capacity_l",
            "sludge_t201_capacity_m3", "sludge_t201_initial_volume_m3",
            "sludge_t201_area_m2", "sludge_t201_high_m3", "sludge_processed_flow_m3h",
            "line2_loss_fraction", "line2_quality_proxy_ntu", "line2_capacity_m3h",
        ):
            _nonneg(getattr(self, name), name)
        if not 0.0 <= self.line2_split_fraction <= 1.0:
            raise WholePlantX2Error("line2_split_fraction must be within [0, 1]")
        for name in ("t100_level_band_m", "t108_level_band_m"):
            band = getattr(self, name)
            if len(band) != 4 or list(band) != sorted(band):
                raise WholePlantX2Error(f"{name} must be four ascending thresholds")
        for name in ("t100_initial_volume_m3", "t108_initial_volume_m3"):
            value = getattr(self, name)
            capacity = self.t100_capacity_m3 if name.startswith("t100") else self.t108_capacity_m3
            if value > capacity:
                raise WholePlantX2Error(f"{name} exceeds its capacity")


@dataclass(frozen=True, slots=True)
class ScopeRuntimeInfo:
    """Read-only X2 runtime metadata for one admitted scope (contract-derived)."""

    scope_id: str
    canonical_id: str | None
    vf_path: str
    process_role: str
    fidelity_class: str
    update_rule_family: str
    conservation_kind: str
    control_ids: tuple[str, ...]
    x2_admitted: bool

    def to_dict(self) -> dict:
        return {
            "scope_id": self.scope_id,
            "canonical_id": self.canonical_id,
            "vf_path": self.vf_path,
            "process_role": self.process_role,
            "fidelity_class": self.fidelity_class,
            "update_rule_family": self.update_rule_family,
            "conservation_kind": self.conservation_kind,
            "control_ids": list(self.control_ids),
            "x2_admitted": self.x2_admitted,
            **AUTHORITY_LABELS,
        }


# ── participants ─────────────────────────────────────────────────────────

class ScopeParticipant:
    """Base participant: one admitted scope, explicit_lagged, contract-derived."""

    family_fidelity = "synthetic_reference"
    storage = False

    def __init__(
        self,
        contract: Mapping[str, Any],
        *,
        workspace_id: str,
        run_id: str,
        scenario: WholePlantScenario,
    ) -> None:
        self.contract = contract
        self.scope_id = str(contract["scope_id"])
        self.scope_path = scope_path(self.scope_id)
        self.workspace_id = workspace_id
        self.run_id = run_id
        self.scenario = scenario
        self._time_s = 0.0
        self._window: str | None = None
        self._commands: Mapping[str, Any] = {}
        #: COMMITTED process inputs (delivered by the previous window) - kept
        #: separate from the transient controller commands in ``_commands`` so a
        #: ``prepare_window`` can never discard them before consumption (C02-2).
        self._process_input: dict[str, Any] = {}
        self._inbound: list[BoundaryTransfer] = []
        self._alarms: set[str] = set()
        self._volume_in_m3 = 0.0
        self._volume_out_m3 = 0.0
        self._initial_volume_m3 = 0.0
        #: explicitly ACCOUNTED volume clamps (never silent, never tolerated):
        #: water that had to leave a full tank, and water created by clamping a
        #: negative volume to zero.
        self._overflow_m3 = 0.0
        self._shortfall_m3 = 0.0
        self.reset()

    # lifecycle -----------------------------------------------------------
    def reset(self) -> None:
        self._time_s = 0.0
        self._window = None
        self._commands = {}
        self._process_input = {}
        self._inbound = []
        self._alarms = set()
        self._volume_in_m3 = 0.0
        self._volume_out_m3 = 0.0
        self._overflow_m3 = 0.0
        self._shortfall_m3 = 0.0
        self._reset_state()

    def _reset_state(self) -> None:
        """Scope-specific deterministic initial state."""

    @property
    def current_time_s(self) -> float:
        return self._time_s

    def prepare_window(
        self, window_id: str, commands: Mapping[str, Any], feedback: Mapping[str, Any]
    ) -> None:
        if not isinstance(window_id, str) or not window_id.strip():
            raise WholePlantX2Error("window_id must be a non-empty str")
        self._window = window_id
        # ``commands`` is THIS window's transient controller command set.
        # Committed process inputs live in ``self._process_input`` and are
        # deliberately NOT cleared here: they carry the previous window's
        # committed process data (the correct explicit_lagged lag, C02-2).
        self._commands = dict(commands)
        self._feedback = dict(feedback)

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        target = _num(target_time_s, "target_time_s")
        if target < self._time_s:
            raise WholePlantX2Error(f"{self.scope_id}: cannot advance backward {self._time_s} -> {target}")
        dt_s = target - self._time_s
        outputs = self._step(dt_s)
        self._time_s = target
        return outputs

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        self._inbound = list(inbound)
        self._commit(list(inbound))

    # domain hooks --------------------------------------------------------
    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        raise NotImplementedError

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        raise NotImplementedError

    # helpers -------------------------------------------------------------
    def _inbound_flow(self, port_id: str, key: str = "flow_m3h") -> float:
        for transfer in self._inbound:
            if transfer.target.port_id == port_id:
                value = transfer.payload.get(key)
                if value is None:
                    raise WholePlantX2Error(
                        f"{self.scope_id}: inbound {transfer.transfer_id!r} payload lacks {key!r}"
                    )
                return _nonneg(value, f"{self.scope_id}.{key}")
        return 0.0

    def _inbound_payload(self, port_id: str) -> Mapping[str, Any]:
        for transfer in self._inbound:
            if transfer.target.port_id == port_id:
                return transfer.payload
        return {}

    def _inbound_count(self) -> int:
        return len(self._inbound)

    def _command(self, signal: str, default: Any = None) -> Any:
        return self._commands.get(signal, default)

    def _consume_process_input(self, signal: str, default: Any = None) -> Any:
        """Consume a COMMITTED process input exactly once (correct lag).

        ``_commands`` holds the CURRENT window's transient controller commands
        and is replaced by every ``prepare_window``. A committed process datum
        (e.g. a physical inflow delivered at the end of the previous window)
        must survive that replacement and be consumed exactly once by the next
        step: it lives in ``self._process_input`` (C02-2).
        """
        if signal in self._process_input:
            return self._process_input.pop(signal)
        return default

    def _consume_process_flow(self, signal: str, default: float = 0.0) -> float:
        value = self._consume_process_input(signal, None)
        if value is None:
            return default
        return _nonneg(value, signal)

    def _bound_volume(self, volume: float, capacity: float | None) -> float:
        """Bound a storage volume, ACCOUNTING every clamp (no silent loss).

        A negative volume would CREATE water and an overflow would DESTROY it;
        both are recorded (``_shortfall_m3`` / ``_overflow_m3``) and alarmed so
        the plant water ledger can reconcile them explicitly (C02-3).

        C03: the created amount is a DIAGNOSTIC, not a reconciliation term - a
        material shortfall invalidates physical conservation (see
        ``balance_report``). Callers must bound real outflows with
        ``_available_outflow_rate`` so this clamp only ever absorbs float noise.
        """
        if volume < 0.0:
            self._shortfall_m3 += -volume
            self._alarm("negative_volume_clamped")
            volume = 0.0
        if capacity is not None and volume > capacity:
            self._overflow_m3 += volume - capacity
            self._alarm("capacity_clamped")
            volume = capacity
        return volume

    def _available_outflow_rate(self, dt_s: float, inflow_m3h: float = 0.0) -> float:
        """Maximum admissible OUTFLOW rate: water actually held (+ inflow).

        VF-SHW-X2-C03: a scope must never EMIT water it does not have and then
        have the storage repaired by clamping a negative volume. Every real
        withdrawal / backwash discharge is bounded by this rate; if the
        requested rate exceeds it, the emitted flow is limited and the
        limitation is alarmed (explicit diagnostics, never invented water).
        """
        dt_h = dt_s / 3600.0
        held = (self._storage_volume() / dt_h) if dt_h > 0 else 0.0
        return held + max(0.0, inflow_m3h)

    def _emit(
        self,
        target_scope_id: str,
        target_port: str,
        source_port: str,
        binding_id: str,
        flow_m3h: float,
        **signals: Any,
    ) -> BoundaryTransfer:
        window = self._window or ""
        payload = {
            "flow_m3h": round(_nonneg(flow_m3h, "flow_m3h"), 9),
            "scope_id": self.scope_id,
            "fidelity_class": self.family_fidelity,
            **AUTHORITY_LABELS,
            **{key: value for key, value in sorted(signals.items()) if value is not None},
        }
        require_authority_labels(payload, where=f"transfer payload from {self.scope_id!r}")
        return BoundaryTransfer(
            transfer_id=f"{window}::{binding_id}",
            source=PortRef(self.scope_path, source_port),
            target=PortRef(scope_path(target_scope_id), target_port),
            binding_id=binding_id,
            window_id=window,
            simulation_time_s=self._time_s,
            workspace_id=self.workspace_id,
            run_id=self.run_id,
            payload=payload,
        )

    def _alarm(self, name: str) -> None:
        self._alarms.add(name)

    def _clamp(self, value: float, low: float, high: float, alarm: str) -> float:
        if value < low:
            self._alarm(alarm)
            return low
        if value > high:
            self._alarm(alarm)
            return high
        return value

    @property
    def open_alarms(self) -> tuple[str, ...]:
        return tuple(sorted(self._alarms))

    def monitor_values(self) -> dict:
        return {"time_s": round(self._time_s, 6), **AUTHORITY_LABELS}

    def balance(self) -> dict:
        return {
            "scope_id": self.scope_id,
            "storage": self.storage,
            "volume_in_m3": round(self._volume_in_m3, 9),
            "volume_out_m3": round(self._volume_out_m3, 9),
            "volume_delta_m3": round(self._storage_volume() - self._initial_volume_m3, 9),
            "overflow_m3": round(self._overflow_m3, 9),
            "shortfall_m3": round(self._shortfall_m3, 9),
            "residual_m3": round(
                (self._storage_volume() - self._initial_volume_m3) - (self._volume_in_m3 - self._volume_out_m3),
                9,
            ),
            "conservation_kind": str(self.contract["conservation"]["kind"]),
        }

    def _storage_volume(self) -> float:
        return 0.0


# ── the 16 admitted scopes ───────────────────────────────────────────────

class RawSourceParticipant(ScopeParticipant):
    """boundary_condition_v1: synthetic raw-water boundary source."""

    family_fidelity = "synthetic_reference"

    def _reset_state(self) -> None:
        self._flow_m3h = self.scenario.raw_flow_sp_m3h
        self._turbidity_ntu = self.scenario.raw_turbidity_ntu
        self._ph = self.scenario.raw_ph

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        band = self.contract["parameters"]
        lower = next((p["value"] for p in band if p["name"] == "flow_band_min"), 0.0)
        upper = next((p["value"] for p in band if p["name"] == "flow_band_max"), None)
        upper_bound = self.scenario.pump_rated_flow_m3h if not isinstance(upper, (int, float)) else float(upper)
        self._flow_m3h = self._clamp(
            _num(self._commands.get("scenario_raw_flow_sp", self.scenario.raw_flow_sp_m3h), "raw_flow_sp"),
            float(lower),
            upper_bound,
            "raw_flow_out_of_band",
        )
        return (
            self._emit(
                "vf-shw-node-raw-intake",
                "raw_in",
                "raw_out",
                "vf-shw-edge-raw-source-intake",
                self._flow_m3h,
                turbidity_ntu=self._turbidity_ntu,
                raw_ph=self._ph,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        if inbound:
            raise WholePlantX2Error("raw-source must not receive inbound transfers")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "raw_flow_m3h": round(self._flow_m3h, 6),
            "raw_turbidity_ntu": round(self._turbidity_ntu, 6),
            "raw_ph": round(self._ph, 6),
        }


class RawIntakeParticipant(ScopeParticipant):
    """pump_flow_algebraic_v1: duty/standby pump with the frozen X2 fixed speed."""

    family_fidelity = "first_order"

    def _reset_state(self) -> None:
        self._raw_flow_m3h = 0.0
        self._pump_speed_pct = 0.0
        self._intake_flow_m3h = 0.0
        self._screen_dp_kpa = 0.0
        self._run_hours = 0.0
        self._turbidity_ntu = 0.0

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        speed = _nonneg(self._command("pump_speed_cmd", 0.0), "pump_speed_cmd")
        permit = bool(self._command("intake_enable", True))
        availability = bool(self._command("raw_source_available", self._raw_flow_m3h > 0))
        self._pump_speed_pct = self._clamp(speed, 0.0, 100.0, "pump_speed_out_of_range")

        if not permit or not availability:
            self._intake_flow_m3h = 0.0
        else:
            target = self._raw_flow_m3h * (self._pump_speed_pct / 100.0)
            self._intake_flow_m3h = round(min(target, self.scenario.pump_rated_flow_m3h), 9)
        if self._intake_flow_m3h > 0.0 and self._pump_speed_pct <= 0.0:
            self._alarm("dry_run_flow")
        self._screen_dp_kpa = round(
            min(
                self.scenario.screen_dp_gain_kpa_per_m3h * self._intake_flow_m3h,
                self.scenario.intake_screen_dp_limit_kpa,
            ),
            9,
        )
        if self._pump_speed_pct > 0.0:
            self._run_hours += dt_s / 3600.0
        return (
            self._emit(
                "vf-shw-node-t100",
                "intake_in",
                "intake_out",
                "vf-shw-edge-intake-t100",
                self._intake_flow_m3h,
                screen_dp_kpa=self._screen_dp_kpa,
                pump_speed_pct=self._pump_speed_pct,
                turbidity_ntu=self._turbidity_ntu,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "raw_in":
                self._raw_flow_m3h = _nonneg(transfer.payload["flow_m3h"], "raw_flow_m3h")
                self._turbidity_ntu = _nonneg(transfer.payload.get("turbidity_ntu", 0.0), "turbidity_ntu")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "raw_flow_m3h": round(self._raw_flow_m3h, 6),
            "intake_flow_m3h": round(self._intake_flow_m3h, 6),
            "pump_speed_pct": round(self._pump_speed_pct, 6),
            "screen_dp_kpa": round(self._screen_dp_kpa, 6),
            "run_hours": round(self._run_hours, 6),
        }


class StorageTankParticipant(ScopeParticipant):
    """volume_balance_first_order_v1 (T100 / T108) with the frozen permissives."""

    family_fidelity = "first_order"
    storage = True
    upstream_scope_id = ""
    downstream_scope_ids: tuple[str, ...] = ()
    area_m2 = 1.0
    capacity_m3 = 1.0
    initial_volume_m3 = 0.0
    level_band: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def _reset_state(self) -> None:
        self._volume_m3 = self.initial_volume_m3
        self._initial_volume_m3 = self.initial_volume_m3
        self._inflow_m3h = 0.0
        self._withdrawal_m3h = 0.0
        self._outflows: dict[str, float] = {scope: 0.0 for scope in self.downstream_scope_ids}
        self._level_m = round(self._volume_m3 / self.area_m2, 9)
        self._inflow_permitted = True
        self._turbidity_ntu = 0.0

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        raise NotImplementedError

    def _storage_volume(self) -> float:
        return self._volume_m3

    def _integrate(self, dt_s: float, inflow_m3h: float, outflow_m3h: float) -> None:
        dt_h = dt_s / 3600.0
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (inflow_m3h - outflow_m3h) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += inflow_m3h * dt_h
        self._volume_out_m3 += outflow_m3h * dt_h
        self._level_m = round(self._volume_m3 / self.area_m2, 9)

    def _band_alarms(self, level_m: float) -> None:
        lall, lal, lah, lahh = self.level_band
        if level_m <= lall:
            self._alarm("level_LALL")
        if level_m >= lah:
            self._alarm("level_LAH")
        if level_m >= lahh:
            self._alarm("level_LAHH")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "volume_m3": round(self._volume_m3, 6),
            "level_m": round(self._level_m, 6),
            "inflow_m3h": round(self._inflow_m3h, 6),
            "withdrawal_m3h": round(self._withdrawal_m3h, 6),
            "outflows_m3h": {key: round(value, 6) for key, value in sorted(self._outflows.items())},
            "inflow_permitted": self._inflow_permitted,
        }


class T100Participant(StorageTankParticipant):
    upstream_scope_id = "vf-shw-node-raw-intake"
    downstream_scope_ids = ("vf-shw-node-t101", "vf-shw-node-line2-aggregate")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.area_m2 = kwargs.pop("area_m2")
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3")
        self.level_band = kwargs.pop("level_band")
        super().__init__(*args, **kwargs)

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        outlet_enabled = bool(self._command("outlet_enable", True))
        # committed declared process inputs are consumed exactly once per window
        # and only then fall back to the transient controller command/scenario
        committed_demand = self._consume_process_input("line1_demand_m3h", None)
        committed_split = self._consume_process_input("line2_split_fraction", None)
        demand_command = self._command("line1_demand_m3h")
        split_command = self._command("line2_split_fraction")
        demand = _nonneg(
            demand_command
            if demand_command is not None
            else (committed_demand if committed_demand is not None else self.scenario.line1_demand_m3h),
            "line1_demand",
        )
        split_fraction = _num(
            split_command
            if split_command is not None
            else (committed_split if committed_split is not None else 0.0),
            "line2_split_fraction",
        )
        if not 0.0 <= split_fraction <= 1.0:
            self._alarm("split_fraction_out_of_range")
            split_fraction = min(1.0, max(0.0, split_fraction))

        available_m3 = self._volume_m3
        dt_h = dt_s / 3600.0 if dt_s > 0 else 0.0
        available_rate = (available_m3 / dt_h) if dt_h > 0 else 0.0

        # C02-4 audit: the level permissive does NOT delete water that has
        # already been received. The frozen ownership routes the high-level
        # inhibit to the UPSTREAM intake actuator (``intake_enable``), which the
        # raw-intake participant honours at the source; this flag is only the
        # reporting/alarm state.
        self._inflow_permitted = self._level_m < self.level_band[2]
        intake = self._inflow_m3h

        l1_feed = 0.0
        l2_feed = 0.0
        if outlet_enabled:
            l1_feed = min(demand, available_rate + intake)
            l2_feed = min(split_fraction * l1_feed, max(0.0, available_rate + intake - l1_feed))
            l1_feed = max(0.0, l1_feed)
            l2_feed = max(0.0, l2_feed)
        self._outflows = {"vf-shw-node-t101": l1_feed, "vf-shw-node-line2-aggregate": l2_feed}
        self._withdrawal_m3h = l1_feed + l2_feed

        self._integrate(dt_s, intake, self._withdrawal_m3h)
        self._band_alarms(self._level_m)
        if self._level_m >= self.level_band[3]:
            self._alarm("inhibit_upstream_intake")
        return (
            self._emit(
                "vf-shw-node-t101", "feed_in", "l1_out", "vf-shw-edge-t100-l1", l1_feed,
                t100_level_m=self._level_m,
                turbidity_ntu=self._turbidity_ntu,
            ),
            self._emit(
                "vf-shw-node-line2-aggregate", "l2_feed_in", "l2_out", "vf-shw-edge-t100-line2", l2_feed,
                t100_level_m=self._level_m,
                turbidity_ntu=self._turbidity_ntu,
            ),
            self._emit(
                "vf-shw-node-chem-dosing", "plant_flow_in", "plant_flow_out",
                "vf-shw-info-t100-plant-flow-chem", self._withdrawal_m3h,
                plant_flow_m3h=self._withdrawal_m3h,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "intake_in":
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "intake_flow_m3h")
                self._turbidity_ntu = _nonneg(transfer.payload.get("turbidity_ntu", 0.0), "turbidity_ntu")
            elif transfer.target.port_id == "l1_demand_in":
                self._process_input["line1_demand_m3h"] = transfer.payload.get("l1_demand_m3h", 0.0)
            elif transfer.target.port_id == "l2_split_in":
                self._process_input["line2_split_fraction"] = transfer.payload.get("split_fraction", 0.0)


class ResidenceParticipant(ScopeParticipant):
    """residence_accumulator_v1 (T101 / T104): accumulating basin with a
    residence index (volume / inflow) and an OUTLET interlock.

    The C1 residence contract inhibits the scope OUTLET (its own downstream
    feed) while the residence index is below the frozen minimum; the upstream
    supply keeps filling the basin (that is what makes the index grow).
    """

    family_fidelity = "logical_only"
    storage = True
    index_key = "contact_time_s"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3", 0.0)
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._volume_m3 = self.initial_volume_m3
        self._initial_volume_m3 = self.initial_volume_m3
        self._inflow_m3h = 0.0
        self._outflow_m3h = 0.0
        self._index_s = 0.0
        self._index_max_s = 0.0
        self._outlet_inhibited = True
        self._turbidity_ntu = 0.0
        self._turbidity_out_ntu = 0.0

    def _storage_volume(self) -> float:
        return self._volume_m3

    @property
    def _outlet_enable_signal(self) -> str:
        return "t101_outlet_enable"

    def _emit_extra(self) -> tuple[BoundaryTransfer, ...]:
        return ()

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        outlet_enabled = bool(self._command(self._outlet_enable_signal, True))
        self._outlet_inhibited = not outlet_enabled
        if self._outlet_inhibited:
            self._alarm("outlet_inhibited_by_residence_interlock")
        self._outflow_m3h = self._inflow_m3h if outlet_enabled else 0.0
        dt_h = dt_s / 3600.0
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (self._inflow_m3h - self._outflow_m3h) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += self._inflow_m3h * dt_h
        self._volume_out_m3 += self._outflow_m3h * dt_h
        if self._inflow_m3h > 1e-9:
            self._index_s = round(min(86_400.0, 3600.0 * self._volume_m3 / self._inflow_m3h), 6)
        elif self._outflow_m3h <= 0.0:
            self._index_s = round(self._index_s + dt_s, 6)
        self._index_max_s = max(self._index_max_s, self._index_s)
        self._turbidity_out_ntu = self._turbidity_ntu
        return (
            self._emit(
                self._next_scope_id, self._next_port, "flow_out", self._edge_id, self._outflow_m3h,
                **{self.index_key: self._index_s},
                turbidity_ntu=self._turbidity_out_ntu,
            ),
            *self._emit_extra(),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id in ("feed_in", "flow_in"):
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "inflow_m3h")
                self._turbidity_ntu = _nonneg(transfer.payload.get("turbidity_ntu", self._turbidity_ntu), "turbidity_ntu")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "volume_m3": round(self._volume_m3, 6),
            "inflow_m3h": round(self._inflow_m3h, 6),
            "outflow_m3h": round(self._outflow_m3h, 6),
            self.index_key: round(self._index_s, 6),
            "outlet_enabled": not self._outlet_inhibited,
            "turbidity_ntu": round(self._turbidity_out_ntu, 6),
        }


class T101Participant(ResidenceParticipant):
    _next_scope_id = "vf-shw-node-t102"
    _next_port = "flow_in"
    _edge_id = "vf-shw-edge-t101-t102"
    index_key = "contact_time_s"

    def _emit_extra(self) -> tuple[BoundaryTransfer, ...]:
        return (
            self._emit(
                "vf-shw-node-t100", "l1_demand_in", "demand_out",
                "vf-shw-info-t101-demand-t100", self._inflow_m3h,
                l1_demand_m3h=self.scenario.line1_demand_m3h,
                contact_time_s=self._index_s,
            ),
        )


class T104Participant(ResidenceParticipant):
    _next_scope_id = "vf-shw-node-t105"
    _next_port = "flow_in"
    _edge_id = "vf-shw-edge-t104-t105"
    index_key = "floc_time_index_s"

    @property
    def _outlet_enable_signal(self) -> str:
        # T104 has no X2-active C1 control: its outlet is always enabled; the
        # flocculation index is a monitoring index (contract-declared output).
        return "t104_outlet_enable"

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        return super()._step(dt_s)


class DoseContactParticipant(ScopeParticipant):
    """dose_ratio_proxy_v1 (T102 / T103): contact + applied dose effect."""

    family_fidelity = "logical_only"
    dose_signal = "pac_dose"
    dose_efficiency = 0.0
    next_scope_id = ""
    next_port = "flow_in"
    edge_id = ""

    def _reset_state(self) -> None:
        self._inflow_m3h = 0.0
        self._outflow_m3h = 0.0
        self._applied_dose_mg_l = 0.0
        self._inbound_turbidity_ntu = 0.0
        self._turbidity_out_ntu = 0.0
        self._dose_transport_delta_mg_l = 0.0
        self._max_dose_step_mg_l = 0.0

    @property
    def _max_dose_step(self) -> float:
        return _nonneg(
            self._command("dose_max_step_mg_l", self._max_dose_step_mg_l),
            "dose_max_step_mg_l",
        )

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        commanded = _nonneg(self._command(self.dose_signal, 0.0), self.dose_signal)
        inbound_dose = self._inbound_payload("dose_in").get("dose_mg_l")
        if inbound_dose is not None:
            # explicit_lagged: the transported dose is one window behind the
            # current C1 command; only a delta larger than one ramp step is a fault.
            lag_delta = abs(_num(inbound_dose, "dose_mg_l") - commanded)
            self._dose_transport_delta_mg_l = round(lag_delta, 9)
            if lag_delta > self._max_dose_step + 1e-9:
                self._alarm("dose_transport_mismatch")
        self._applied_dose_mg_l = round(commanded, 6)
        self._outflow_m3h = self._inflow_m3h
        reduction = self.dose_efficiency * self._applied_dose_mg_l
        self._turbidity_out_ntu = round(max(0.0, self._inbound_turbidity_ntu * (1.0 - min(0.95, reduction))), 9)
        return (
            self._emit(
                self.next_scope_id, self.next_port, "flow_out", self.edge_id, self._outflow_m3h,
                **{
                    self.dose_signal: self._applied_dose_mg_l,
                    "turbidity_ntu": self._turbidity_out_ntu,
                },
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "flow_in":
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "inflow_m3h")
                self._inbound_turbidity_ntu = _nonneg(
                    transfer.payload.get("turbidity_ntu", self._inbound_turbidity_ntu),
                    "turbidity_ntu",
                )

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "inflow_m3h": round(self._inflow_m3h, 6),
            self.dose_signal: round(self._applied_dose_mg_l, 6),
            "turbidity_ntu": round(self._turbidity_out_ntu, 6),
            "dose_transport_delta_mg_l": round(self._dose_transport_delta_mg_l, 6),
        }


class T102Participant(DoseContactParticipant):
    dose_signal = "pac_dose"
    dose_efficiency = 0.05
    next_scope_id = "vf-shw-node-t103"
    edge_id = "vf-shw-edge-t102-t103"


class T103Participant(DoseContactParticipant):
    dose_signal = "coag_dose"
    dose_efficiency = 0.08
    family_fidelity = "synthetic_reference"
    next_scope_id = "vf-shw-node-t104"
    edge_id = "vf-shw-edge-t103-t104"


class ClarifierParticipant(ScopeParticipant):
    """settling_proxy_v1 (T105): storage with sludge withdrawal and settling."""

    family_fidelity = "synthetic_reference"
    storage = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.area_m2 = kwargs.pop("area_m2")
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3")
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._volume_m3 = self.initial_volume_m3
        self._initial_volume_m3 = self.initial_volume_m3
        self._inflow_m3h = 0.0
        self._outflow_m3h = 0.0
        self._sludge_out_m3h = 0.0
        self._turbidity_in_ntu = 0.0
        self._turbidity_out_ntu = 0.0
        self._sludge_total_m3 = 0.0
        self._outflow_held_by_downstream_inhibit = False

    def _storage_volume(self) -> float:
        return self._volume_m3

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        withdrawal = _nonneg(self._command("sludge_withdrawal_m3h", 0.0), "sludge_withdrawal_m3h")
        dt_h = dt_s / 3600.0
        available_rate = (self._volume_m3 / dt_h) if dt_h > 0 else 0.0
        self._sludge_out_m3h = round(min(withdrawal, max(0.0, available_rate)), 9)
        # C02-4: the frozen T108 high-level inhibit closes the T106 filtered-water
        # inflow PATH; the filter cannot forward what it does not receive, so the
        # upstream clarifier HOLDS its water instead of pushing it into a closed
        # path (no deletion at the receiver, no silent overflow).
        inflow_enable = bool(self._command("inflow_enable", True))
        self._outflow_held_by_downstream_inhibit = not inflow_enable
        if self._outflow_held_by_downstream_inhibit:
            self._alarm("outflow_held_by_downstream_inhibit")
            self._outflow_m3h = 0.0
        else:
            self._outflow_m3h = self._inflow_m3h
        total_out = self._outflow_m3h + self._sludge_out_m3h
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (self._inflow_m3h - total_out) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += self._inflow_m3h * dt_h
        self._volume_out_m3 += total_out * dt_h
        self._sludge_total_m3 += self._sludge_out_m3h * dt_h
        residence_bonus = min(0.05, self._sludge_total_m3 / 1000.0)
        efficiency = min(0.95, self.scenario.t105_settling_efficiency + residence_bonus)
        self._turbidity_out_ntu = round(max(0.0, self._turbidity_in_ntu * (1.0 - efficiency)), 9)
        return (
            self._emit(
                "vf-shw-node-t106", "flow_in", "flow_out", "vf-shw-edge-t105-t106", self._outflow_m3h,
                turbidity_ntu=self._turbidity_out_ntu,
            ),
            self._emit(
                "vf-shw-node-sludge-t201", "sludge_in", "sludge_out", "vf-shw-edge-t105-sludge",
                self._sludge_out_m3h,
                turbidity_ntu=self._turbidity_out_ntu,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "flow_in":
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "inflow_m3h")
                self._turbidity_in_ntu = _nonneg(
                    transfer.payload.get("turbidity_ntu", self._turbidity_in_ntu),
                    "turbidity_ntu",
                )

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "volume_m3": round(self._volume_m3, 6),
            "inflow_m3h": round(self._inflow_m3h, 6),
            "outflow_m3h": round(self._outflow_m3h, 6),
            "outflow_held_by_downstream_inhibit": self._outflow_held_by_downstream_inhibit,
            "sludge_out_m3h": round(self._sludge_out_m3h, 6),
            "turbidity_ntu": round(self._turbidity_out_ntu, 6),
        }


class FilterParticipant(ScopeParticipant):
    """filter_loading_first_order_v1 (T106): DP growth + backwash sequence effects."""

    family_fidelity = "first_order"
    storage = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3")
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._volume_m3 = self.initial_volume_m3
        self._initial_volume_m3 = self.initial_volume_m3
        self._inflow_m3h = 0.0
        self._inbound_turbidity_ntu = 0.0
        self._filtered_flow_m3h = 0.0
        self._filtered_turbidity_ntu = 0.0
        self._dp_kpa = self.scenario.t106_dp_initial_kpa
        self._valve_pos_pct = 0.0
        self._wash_out_m3h = 0.0
        self._wash_return_m3h = 0.0
        self._wash_water_limited = False
        self._inflow_inhibited = False
        self._last_step = "IDLE"
        self._backwash_count = 0

    def _storage_volume(self) -> float:
        return self._volume_m3

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        step = str(self._command("backwash_step", self._last_step))
        valve_pos = _num(self._command("inlet_valve_pos", 0.0), "inlet_valve_pos")
        self._valve_pos_pct = self._clamp(valve_pos, 0.0, 100.0, "valve_pos_out_of_range")
        dt_h = dt_s / 3600.0
        open_valve = self._valve_pos_pct >= 100.0
        # C02-4: the frozen T108 high-level permissive owns the UPSTREAM T106
        # filtered-water inflow path (``inflow_enable``). The inhibit closes that
        # path: the filter forwards nothing to T108 while it is active. The
        # permissive never deletes water at the receiving tank; the backwash
        # sequence keeps exclusive ownership of ``inlet_valve_pos``, and while a
        # backwash/settle phase runs the sequence already stops filtered
        # production, so the two agree (no double ownership of one actuator).
        inflow_enable = bool(self._command("inflow_enable", True))
        self._inflow_inhibited = not inflow_enable
        if self._inflow_inhibited:
            self._alarm("filtered_path_inhibited_by_downstream_level")
        self._filtered_flow_m3h = self._inflow_m3h if (open_valve and inflow_enable) else 0.0
        efficiency = self.scenario.t106_filter_efficiency if open_valve else 0.0
        self._filtered_turbidity_ntu = round(max(0.0, self._inbound_turbidity_ntu * (1.0 - efficiency)), 9)
        if open_valve and self._filtered_flow_m3h > 0.0:
            self._dp_kpa = round(
                min(120.0, self._dp_kpa + self.scenario.t106_dp_growth_kpa_per_s * dt_s), 9
            )
        if step == "BACKWASH" and self._last_step != "BACKWASH":
            requested_wash_out = self.scenario.t106_backwash_wash_flow_m3h
        elif step == "SETTLE" and self._last_step == "BACKWASH":
            requested_wash_out = self.scenario.t106_backwash_wash_flow_m3h * 0.5
        else:
            requested_wash_out = 0.0
        dt_h = dt_s / 3600.0
        # C02-2: the wash return is a COMMITTED process inflow delivered at the
        # end of the previous window; it is consumed here exactly once.
        wash_return = self._consume_process_flow("wash_return_flow_m3h")
        self._wash_return_m3h = wash_return
        # C03: the backwash wash-water discharge is bounded by the water the
        # filter actually holds (+ what enters this window). A discharge is never
        # allowed to invent water and be repaired by a clamp: the emitted flow is
        # limited and the limitation is alarmed.
        in_rate = self._inflow_m3h + wash_return
        available_rate = self._available_outflow_rate(dt_s, in_rate)
        self._wash_out_m3h = round(min(requested_wash_out, max(0.0, available_rate)), 9)
        self._wash_water_limited = self._wash_out_m3h < requested_wash_out - 1e-12
        if self._wash_water_limited:
            self._alarm("wash_water_limited_by_available_volume")
        if step == "IDLE" and self._last_step == "SETTLE":
            self._dp_kpa = self.scenario.t106_dp_initial_kpa
            self._backwash_count += 1
        out_rate = self._filtered_flow_m3h + self._wash_out_m3h
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (in_rate - out_rate) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += in_rate * dt_h
        self._volume_out_m3 += out_rate * dt_h
        self._last_step = step
        if self._dp_kpa > 100.0:
            self._alarm("filter_dp_high")
        return (
            self._emit(
                "vf-shw-node-t108", "filtered_in", "filtered_out", "vf-shw-edge-t106-t108",
                self._filtered_flow_m3h,
                filter_dp_kpa=self._dp_kpa,
                turbidity_ntu=self._filtered_turbidity_ntu,
            ),
            self._emit(
                "vf-shw-node-wash-t110", "wash_in", "wash_out", "vf-shw-edge-t106-wash",
                self._wash_out_m3h,
                wash_out_flow_m3h=self._wash_out_m3h,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "flow_in":
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "inflow_m3h")
                self._inbound_turbidity_ntu = _nonneg(
                    transfer.payload.get("turbidity_ntu", self._inbound_turbidity_ntu),
                    "turbidity_ntu",
                )
            elif transfer.target.port_id == "wash_in":
                # C02-2: committed process inflow (consumed once by the next step)
                self._process_input["wash_return_flow_m3h"] = _nonneg(
                    transfer.payload.get("flow_m3h", 0.0), "wash_return_flow_m3h"
                )

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "inflow_m3h": round(self._inflow_m3h, 6),
            "wash_return_m3h": round(self._wash_return_m3h, 6),
            "filtered_flow_m3h": round(self._filtered_flow_m3h, 6),
            "filter_dp_kpa": round(self._dp_kpa, 6),
            "inlet_valve_pos_pct": round(self._valve_pos_pct, 6),
            "filtered_path_inhibited": self._inflow_inhibited,
            "wash_out_m3h": round(self._wash_out_m3h, 6),
            "wash_water_limited_by_available_volume": self._wash_water_limited,
            "backwash_step": self._last_step,
            "backwash_count": self._backwash_count,
            "turbidity_ntu": round(self._filtered_turbidity_ntu, 6),
        }


class RecoveryParticipant(ScopeParticipant):
    """recovery_balance_v1 (WASH-T110): store wash water and return it to T106."""

    family_fidelity = "logical_only"
    storage = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.area_m2 = kwargs.pop("area_m2")
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._volume_m3 = 0.0
        self._initial_volume_m3 = 0.0
        self._wash_in_m3h = 0.0
        self._return_m3h = 0.0

    def _storage_volume(self) -> float:
        return self._volume_m3

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        max_return = self.scenario.wash_t110_return_flow_m3h
        dt_h = dt_s / 3600.0
        available_rate = (self._volume_m3 / dt_h) if dt_h > 0 else 0.0
        self._return_m3h = round(min(max_return, max(0.0, available_rate)), 9)
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (self._wash_in_m3h - self._return_m3h) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += self._wash_in_m3h * dt_h
        self._volume_out_m3 += self._return_m3h * dt_h
        return (
            self._emit(
                "vf-shw-node-t106", "wash_in", "return_out", "vf-shw-edge-wash-t106", self._return_m3h,
                recovery_return_flow_m3h=self._return_m3h,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "wash_in":
                self._wash_in_m3h = _nonneg(transfer.payload["flow_m3h"], "wash_in_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "volume_m3": round(self._volume_m3, 6),
            "level_m": round(self._volume_m3 / self.area_m2, 6),
            "wash_in_m3h": round(self._wash_in_m3h, 6),
            "return_m3h": round(self._return_m3h, 6),
        }


class T108Participant(StorageTankParticipant):
    upstream_scope_id = "vf-shw-node-t106"
    downstream_scope_ids = ("vf-shw-node-dist-p108",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.area_m2 = kwargs.pop("area_m2")
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3")
        self.level_band = kwargs.pop("level_band")
        super().__init__(*args, **kwargs)

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        speed = _nonneg(self._command("transfer_pump_speed_cmd", 0.0), "transfer_pump_speed_cmd")
        inflow_enabled = bool(self._command("inflow_enable", True))
        dt_h = dt_s / 3600.0
        available_rate = (self._volume_m3 / dt_h) if dt_h > 0 else 0.0
        pump_rate = self.scenario.t108_transfer_rated_flow_m3h * (speed / 100.0)
        # C03: the transfer withdrawal is bounded by the water actually held; a
        # pump can never move water that is not there.
        self._withdrawal_m3h = round(min(pump_rate, max(0.0, available_rate)), 9)
        if self._level_m <= self.level_band[0]:
            self._withdrawal_m3h = 0.0
            self._alarm("transfer_pump_lall_inhibit")
        self._inflow_permitted = inflow_enabled
        if not inflow_enabled:
            self._alarm("inhibit_upstream_intake")
        self._outflows = {"vf-shw-node-dist-p108": self._withdrawal_m3h}
        # C02-4: the received inflow is NEVER deleted at the receiving tank. The
        # high-level action inhibits the UPSTREAM T106 actuator; whatever was
        # already committed must be integrated (explicit_lagged, conservation).
        self._integrate(dt_s, self._inflow_m3h, self._withdrawal_m3h)
        self._band_alarms(self._level_m)
        return (
            self._emit(
                "vf-shw-node-dist-p108", "t108_in", "outlet_out", "vf-shw-edge-t108-dist",
                self._withdrawal_m3h,
                t108_level_m=self._level_m,
                turbidity_ntu=self._turbidity_ntu,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "filtered_in":
                self._inflow_m3h = _nonneg(transfer.payload["flow_m3h"], "filtered_flow_m3h")
                self._turbidity_ntu = _nonneg(
                    transfer.payload.get("turbidity_ntu", self._turbidity_ntu), "turbidity_ntu"
                )


class DistributionParticipant(ScopeParticipant):
    """pump_curve_algebraic_v1 (DIST-P108) with the frozen X2 fallback (80 %)."""

    family_fidelity = "synthetic_reference"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.fallback_speed_pct = kwargs.pop("fallback_speed_pct")
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._inlet_flow_m3h = 0.0
        self._l2_flow_m3h = 0.0
        self._network_flow_m3h = 0.0
        self._speed_pct = self.fallback_speed_pct
        self._pressure_bar = 0.0
        self._last_x2_producer = "x2_fallback_default"

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        commanded = self._command("hsp_speed_cmd")
        if commanded is None:
            speed = self.fallback_speed_pct
            self._last_x2_producer = "x2_fallback_default"
        else:
            speed = _num(commanded, "hsp_speed_cmd")
            self._last_x2_producer = "x2_active_controller"
        self._speed_pct = self._clamp(speed, 0.0, 100.0, "hsp_speed_out_of_range")
        self._network_flow_m3h = round(self._inlet_flow_m3h + self._l2_flow_m3h, 9)
        head = self.scenario.dist_curve_head_bar * (self._speed_pct / 100.0) ** 2
        loss = self.scenario.dist_manifold_loss_bar_per_m3h2 * (self._network_flow_m3h ** 2)
        self._pressure_bar = round(
            self._clamp(head - loss, 0.0, self.scenario.dist_pressure_ceiling_bar, "over_pressure_or_no_head"), 9
        )
        return (
            self._emit(
                "vf-shw-node-network-demand", "network_in", "network_out", "vf-shw-edge-dist-demand",
                self._network_flow_m3h,
                discharge_pressure_bar=self._pressure_bar,
                hsp_speed_pct=self._speed_pct,
                x2_speed_producer=self._last_x2_producer,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "t108_in":
                self._inlet_flow_m3h = _nonneg(transfer.payload["flow_m3h"], "outlet_flow_m3h")
            elif transfer.target.port_id == "l2_in":
                self._l2_flow_m3h = _nonneg(transfer.payload["flow_m3h"], "l2_delivery_flow_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "inlet_flow_m3h": round(self._inlet_flow_m3h, 6),
            "l2_flow_m3h": round(self._l2_flow_m3h, 6),
            "network_flow_m3h": round(self._network_flow_m3h, 6),
            "hsp_speed_pct": round(self._speed_pct, 6),
            "discharge_pressure_bar": round(self._pressure_bar, 6),
            "x2_speed_producer": self._last_x2_producer,
        }


class NetworkDemandParticipant(ScopeParticipant):
    """boundary_condition_v1: synthetic network-demand sink."""

    family_fidelity = "synthetic_reference"

    def _reset_state(self) -> None:
        self._network_flow_m3h = 0.0
        self._demand_met_fraction = 0.0
        self._excess_flow_m3h = 0.0
        self._delivered_total_m3 = 0.0

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        demand = self.scenario.network_demand_m3h
        self._demand_met_fraction = round(min(1.0, (self._network_flow_m3h / demand) if demand > 0 else 0.0), 9)
        self._excess_flow_m3h = round(max(0.0, self._network_flow_m3h - demand), 9)
        self._volume_in_m3 += self._network_flow_m3h * (dt_s / 3600.0)
        self._delivered_total_m3 = self._volume_in_m3
        return ()

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "network_in":
                self._network_flow_m3h = _nonneg(transfer.payload["flow_m3h"], "network_flow_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "network_flow_m3h": round(self._network_flow_m3h, 6),
            "demand_met_fraction": round(self._demand_met_fraction, 6),
            "excess_flow_m3h": round(self._excess_flow_m3h, 6),
            "delivered_total_m3": round(self._delivered_total_m3, 6),
        }


class ChemDosingParticipant(ScopeParticipant):
    """ratio_dosing_v1: dose follows plant flow (C1 ratio control), consumption tracked."""

    family_fidelity = "logical_only"

    def _reset_state(self) -> None:
        self._plant_flow_m3h = 0.0
        self._consumed_l = 0.0
        self._tank_level_l = self.scenario.chem_tank_capacity_l
        self._pac_dose_mg_l = 0.0
        self._coag_dose_mg_l = 0.0
        self._dosing_active = False

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        dt_h = dt_s / 3600.0
        self._plant_flow_m3h = _nonneg(self._command("plant_flow_m3h", self._plant_flow_m3h), "plant_flow_m3h")
        self._pac_dose_mg_l = _nonneg(self._command("pac_dose", 0.0), "pac_dose")
        self._coag_dose_mg_l = _nonneg(self._command("coag_dose", 0.0), "coag_dose")
        self._dosing_active = self._pac_dose_mg_l > 0.0 or self._coag_dose_mg_l > 0.0
        consumption_l = (
            (self._pac_dose_mg_l + self._coag_dose_mg_l) * self._plant_flow_m3h * dt_h * 1000.0 / 1_000_000.0
        )
        self._consumed_l += consumption_l
        self._tank_level_l = round(max(0.0, self._tank_level_l - consumption_l), 9)
        if self._tank_level_l <= 0.0:
            self._alarm("chemical_tank_low")
        return (
            self._emit(
                "vf-shw-node-t102", "dose_in", "pac_out", "vf-shw-edge-chem-t102", 0.0,
                dose_mg_l=self._pac_dose_mg_l,
            ),
            self._emit(
                "vf-shw-node-t103", "dose_in", "coag_out", "vf-shw-edge-chem-t103", 0.0,
                dose_mg_l=self._coag_dose_mg_l,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "plant_flow_in":
                self._plant_flow_m3h = _nonneg(transfer.payload.get("plant_flow_m3h", 0.0), "plant_flow_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "plant_flow_m3h": round(self._plant_flow_m3h, 6),
            "pac_dose_mg_l": round(self._pac_dose_mg_l, 6),
            "coag_dose_mg_l": round(self._coag_dose_mg_l, 6),
            "tank_level_l": round(self._tank_level_l, 6),
            "dosing_active": self._dosing_active,
        }


class SludgeSinkParticipant(ScopeParticipant):
    """duty_cycle_rule_v1: sludge receiving tank with an on/off processing pump."""

    family_fidelity = "logical_only"
    storage = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.capacity_m3 = kwargs.pop("capacity_m3")
        self.initial_volume_m3 = kwargs.pop("initial_volume_m3")
        self.area_m2 = kwargs.pop("area_m2")
        super().__init__(*args, **kwargs)

    def _reset_state(self) -> None:
        self._volume_m3 = self.initial_volume_m3
        self._initial_volume_m3 = self.initial_volume_m3
        self._sludge_in_m3h = 0.0
        self._processed_m3h = 0.0

    def _storage_volume(self) -> float:
        return self._volume_m3

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        pump_running = str(self._command("sink_pump_cmd", "STOP")) == "RUN"
        dt_h = dt_s / 3600.0
        available_rate = (self._volume_m3 / dt_h) if dt_h > 0 else 0.0
        self._processed_m3h = round(
            min(self.scenario.sludge_processed_flow_m3h, max(0.0, available_rate)) if pump_running else 0.0, 9
        )
        self._volume_m3 = self._bound_volume(
            self._volume_m3 + (self._sludge_in_m3h - self._processed_m3h) * dt_h, self.capacity_m3
        )
        self._volume_in_m3 += self._sludge_in_m3h * dt_h
        self._volume_out_m3 += self._processed_m3h * dt_h
        if self._volume_m3 >= self.scenario.sludge_t201_high_m3:
            self._alarm("sludge_level_high")
        return ()

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "sludge_in":
                self._sludge_in_m3h = _nonneg(transfer.payload["flow_m3h"], "sludge_out_flow_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "volume_m3": round(self._volume_m3, 6),
            "sludge_in_m3h": round(self._sludge_in_m3h, 6),
            "processed_m3h": round(self._processed_m3h, 6),
        }


class Line2AggregateParticipant(ScopeParticipant):
    """aggregate_split_v1: ONE shallow LINE2 aggregate (internals reference-only)."""

    family_fidelity = "logical_only"

    def _reset_state(self) -> None:
        self._feed_m3h = 0.0
        self._delivery_m3h = 0.0
        self._split_fraction = 0.0
        self._step_feed_m3h = 0.0
        self._declared_loss_m3h = 0.0
        self._capacity_spill_m3h = 0.0
        self._observed_loss_m3h = 0.0
        self._loss_audit_ok = True

    def _step(self, dt_s: float) -> tuple[BoundaryTransfer, ...]:
        fraction = _num(self._command("line2_split_fraction", self._split_fraction), "line2_split_fraction")
        if not 0.0 <= fraction <= 1.0:
            self._alarm("split_fraction_out_of_range")
            fraction = min(1.0, max(0.0, fraction))
        self._split_fraction = round(fraction, 9)
        capacity = self.scenario.line2_capacity_m3h
        # C03-4: the delivery is produced by the DECLARED loss law
        #   delivery = max(0, min(feed * (1 - loss_fraction), capacity))
        # so the loss is the declared process loss plus an explicitly modelled
        # capacity spill - never an unexplained dropped delivery.
        audit = audit_line2_process_loss(
            feed_m3h=self._feed_m3h,
            delivered_m3h=max(0.0, min(self._feed_m3h * (1.0 - self.scenario.line2_loss_fraction), capacity)),
            loss_fraction=self.scenario.line2_loss_fraction,
            capacity_m3h=capacity,
        )
        self._step_feed_m3h = round(self._feed_m3h, 12)
        self._declared_loss_m3h = round(audit["declared_loss_m3h"], 12)
        self._capacity_spill_m3h = round(audit["capacity_spill_m3h"], 12)
        self._observed_loss_m3h = round(audit["observed_loss_m3h"], 12)
        self._loss_audit_ok = bool(audit["valid"])
        if not self._loss_audit_ok:
            self._alarm("line2_process_loss_audit_failed")
        self._delivery_m3h = round(audit["expected_delivery_m3h"], 9)
        if self._feed_m3h > capacity:
            self._alarm("line2_capacity_exceeded")
        return (
            self._emit(
                "vf-shw-node-dist-p108", "l2_in", "l2_delivery_out", "vf-shw-edge-line2-dist",
                self._delivery_m3h,
                l2_quality_proxy_ntu=self.scenario.line2_quality_proxy_ntu,
            ),
            self._emit(
                "vf-shw-node-t100", "l2_split_in", "split_out", "vf-shw-info-line2-split-t100",
                self._delivery_m3h,
                split_fraction=self._split_fraction,
            ),
        )

    def _commit(self, inbound: Sequence[BoundaryTransfer]) -> None:
        for transfer in inbound:
            if transfer.target.port_id == "l2_feed_in":
                self._feed_m3h = _nonneg(transfer.payload["flow_m3h"], "l2_feed_flow_m3h")

    def monitor_values(self) -> dict:
        return {
            "time_s": round(self._time_s, 6),
            "feed_m3h": round(self._feed_m3h, 6),
            "delivery_m3h": round(self._delivery_m3h, 6),
            "split_fraction": round(self._split_fraction, 6),
            "step_feed_m3h": round(self._step_feed_m3h, 6),
            "declared_loss_m3h": round(self._declared_loss_m3h, 9),
            "capacity_spill_m3h": round(self._capacity_spill_m3h, 9),
            "observed_loss_m3h": round(self._observed_loss_m3h, 9),
            "process_loss_audit_ok": self._loss_audit_ok,
        }


# ── port/binding wiring (derived from the frozen graph edges) ─────────────

@dataclass(frozen=True, slots=True)
class BindingSpec:
    """One VF boundary binding mapped to a frozen graph edge (or declared input)."""

    binding_id: str
    source_scope_id: str
    source_port: str
    target_scope_id: str
    target_port: str
    category: PortCategory
    unit: str
    descriptor: str
    graph_edge_id: str | None
    information: bool = False


def _wiring(manifest: WholePlantContracts) -> tuple[BindingSpec, ...]:
    edges = {edge.edge_id: edge for edge in manifest.edges}
    missing = [edge_id for edge_id in X2_FLOW_EDGE_IDS if edge_id not in edges]
    if missing:
        raise WholePlantX2Error(f"frozen graph is missing X2 flow edges {sorted(missing)}")

    def flow_edge(edge_id: str, source_port: str, target_port: str) -> BindingSpec:
        edge = edges[edge_id]
        if edge.category == "reference_only" or not edge.x2_eligible:
            raise WholePlantX2Error(f"edge {edge_id!r} is not X2-eligible")
        unit = "m3/h"
        descriptor = {
            "water": "volumetric_flow",
            "wash_water": "wash_water_flow",
            "sludge": "sludge_flow",
            "chemical": "dose",
            "boundary_in": "raw_water_flow",
            "boundary_out": "network_flow",
        }.get(edge.flow, "volumetric_flow")
        if edge.flow == "chemical":
            unit = "mg/L"
        return BindingSpec(
            binding_id=edge_id,
            source_scope_id=edge.source,
            source_port=source_port,
            target_scope_id=edge.target,
            target_port=target_port,
            category=PortCategory.MATERIAL,
            unit=unit,
            descriptor=descriptor,
            graph_edge_id=edge_id,
        )

    return (
        flow_edge("vf-shw-edge-raw-source-intake", "raw_out", "raw_in"),
        flow_edge("vf-shw-edge-intake-t100", "intake_out", "intake_in"),
        flow_edge("vf-shw-edge-t100-l1", "l1_out", "feed_in"),
        flow_edge("vf-shw-edge-t100-line2", "l2_out", "l2_feed_in"),
        flow_edge("vf-shw-edge-t101-t102", "flow_out", "flow_in"),
        flow_edge("vf-shw-edge-t102-t103", "flow_out", "flow_in"),
        flow_edge("vf-shw-edge-t103-t104", "flow_out", "flow_in"),
        flow_edge("vf-shw-edge-t104-t105", "flow_out", "flow_in"),
        flow_edge("vf-shw-edge-t105-t106", "flow_out", "flow_in"),
        flow_edge("vf-shw-edge-t105-sludge", "sludge_out", "sludge_in"),
        flow_edge("vf-shw-edge-t106-t108", "filtered_out", "filtered_in"),
        flow_edge("vf-shw-edge-t106-wash", "wash_out", "wash_in"),
        flow_edge("vf-shw-edge-wash-t106", "return_out", "wash_in"),
        flow_edge("vf-shw-edge-t108-dist", "outlet_out", "t108_in"),
        flow_edge("vf-shw-edge-dist-demand", "network_out", "network_in"),
        flow_edge("vf-shw-edge-line2-dist", "l2_delivery_out", "l2_in"),
        flow_edge("vf-shw-edge-chem-t102", "pac_out", "dose_in"),
        flow_edge("vf-shw-edge-chem-t103", "coag_out", "dose_in"),
        BindingSpec(
            binding_id="vf-shw-info-t101-demand-t100",
            source_scope_id="vf-shw-node-t101", source_port="demand_out",
            target_scope_id="vf-shw-node-t100", target_port="l1_demand_in",
            category=PortCategory.INFORMATION, unit="m3/h", descriptor="flow_request",
            graph_edge_id=None, information=True,
        ),
        BindingSpec(
            binding_id="vf-shw-info-line2-split-t100",
            source_scope_id="vf-shw-node-line2-aggregate", source_port="split_out",
            target_scope_id="vf-shw-node-t100", target_port="l2_split_in",
            category=PortCategory.INFORMATION, unit="-", descriptor="split_fraction",
            graph_edge_id=None, information=True,
        ),
        BindingSpec(
            binding_id="vf-shw-info-t100-plant-flow-chem",
            source_scope_id="vf-shw-node-t100", source_port="plant_flow_out",
            target_scope_id="vf-shw-node-chem-dosing", target_port="plant_flow_in",
            category=PortCategory.INFORMATION, unit="m3/h", descriptor="flow_signal",
            graph_edge_id=None, information=True,
        ),
    )


def _build_graph(wiring: tuple[BindingSpec, ...]) -> CompositionGraph:
    ports: list[BoundaryPort] = []
    seen: set[str] = set()
    for spec in wiring:
        for scope_id, port_id, direction in (
            (spec.source_scope_id, spec.source_port, PortDirection.OUT),
            (spec.target_scope_id, spec.target_port, PortDirection.IN),
        ):
            ref = PortRef(scope_path(scope_id), port_id)
            if ref.as_string() in seen:
                continue
            seen.add(ref.as_string())
            ports.append(
                BoundaryPort(
                    ref=ref, direction=direction, category=spec.category,
                    unit=spec.unit, descriptor=spec.descriptor,
                )
            )
    bindings = [
        CompositionBinding(
            edge_id=spec.binding_id,
            source=PortRef(scope_path(spec.source_scope_id), spec.source_port),
            target=PortRef(scope_path(spec.target_scope_id), spec.target_port),
        )
        for spec in wiring
    ]
    return CompositionGraph(
        workspace_id=SHWTP_WHOLE_PLANT_WORKSPACE_ID, bindings=bindings, ports=ports
    )


def _build_overlay(manifest: WholePlantContracts) -> ScenarioTopologyOverlay:
    edges: list[AssumedTopologyEdge] = []
    for edge in manifest.edges:
        if edge.category != "vf_scenario_assumption":
            continue
        if edge.edge_id not in X2_FLOW_EDGE_IDS:
            continue
        edges.append(
            AssumedTopologyEdge(
                assumption_id=edge.assumption_id or edge.edge_id,
                version="1",
                source=scope_path(edge.source).as_string(),
                target=scope_path(edge.target).as_string(),
                relation_type="ASSUMED_FLOWS_TO",
                rationale=f"X1 frozen assumed edge {edge.edge_id} (X2 admission manifest)",
            )
        )
    return ScenarioTopologyOverlay(
        overlay_id="shwtp-x2-whole-plant-assumed-topology",
        version="1",
        domain="shwtp",
        edges=tuple(sorted(edges, key=lambda e: e.assumption_id)),
    )


# ── the whole-plant model ────────────────────────────────────────────────

@dataclass
class WholePlantX2Runtime:
    """A built, runnable X2 whole-plant model behind the canonical bridge seam."""

    workspace: Workspace
    graph: CompositionGraph
    overlay: ScenarioTopologyOverlay
    coordinator: Coordinator
    participants: dict[str, ScopeParticipant]
    scopes: tuple[ScopeRuntimeInfo, ...]
    controls: C1ControllerSet
    scenario: WholePlantScenario
    wiring: tuple[BindingSpec, ...]
    provenance_index: dict[str, dict]
    communication_step_s: float
    #: the attempt identity this model instance belongs to (from the run
    #: lifecycle context; the model never mints a run id of its own, C02-1).
    run_id: str = SHWTP_WHOLE_PLANT_DEFAULT_RUN_ID
    coupling_policy: str = SHWTP_WHOLE_PLANT_COUPLING_POLICY
    #: the bridge must use this model's own window entry (C1 evaluation first).
    model_driven_windows: bool = True
    _window_index: int = 0
    _transfers: tuple[dict, ...] = ()
    _prev_transfers: tuple[dict, ...] = ()
    _control_snapshot: dict = field(default_factory=dict)
    _feedback: dict = field(default_factory=dict)
    _plant_in_m3: float = 0.0
    _plant_out_m3: float = 0.0
    _storage_residual_bound_m3: float = 0.05
    _in_transit_m3: float = 0.0
    _information_inventory_m3: float = 0.0
    _source_availability_m3: float = 0.0
    _ledger: dict = field(default_factory=_empty_water_ledger)
    _seen_windows: set[str] = field(default_factory=set)

    # execution -----------------------------------------------------------
    def run_window(self, window_id: str) -> WindowOutcome:
        """Execute the next deterministic window of this model instance.

        The model owns its window SEQUENCE (``self._window_index + 1``): the
        caller's window id is provenance metadata (the run lifecycle supplies
        ``<run-id>-w<n>``). A repeated window id on the same instance fails
        closed; a caller-induced numbering reset (new attempt / replay) does not
        disturb the model's own deterministic sequence.
        """
        if not isinstance(window_id, str) or not window_id.strip():
            raise WholePlantX2Error("window_id must be a non-empty str")
        if window_id in self._seen_windows:
            raise WholePlantX2Error(
                f"window {window_id!r} has already been executed by this model instance"
            )
        index = self._window_index + 1
        commands = self._control_commands()
        feedback = dict(self._feedback)
        for participant in self.participants.values():
            participant.prepare_window(window_id, commands, feedback)
        outcome = self.coordinator.run_window(window_id, self.communication_step_s * index)
        if outcome.status != "completed":
            raise WholePlantX2Error(f"window {window_id!r} failed: {outcome.failure}")
        self._window_index = index
        self._seen_windows.add(window_id)
        self._record_transfers()
        self._update_water_ledger()
        self._record_committed()
        return outcome

    def _record_transfers(self) -> None:
        """Detached runtime transfer ledger of the last window (provenance source).

        Every row is classified (C02-3):

        - ``physical_water`` - water inside the plant control volume;
        - ``information`` - a signal that carries NO water (a 60 m3/h
          INFORMATION binding is 0 m3 of inventory, it is a signal value);
        - ``source_availability_outside_boundary`` - raw-source availability at
          the source, i.e. OUTSIDE the pumped-intake boundary; the water the
          intake does not pump never enters the plant and must not be counted
          (no double-counting of source availability).

        Only ``physical_water`` rows may ever enter the plant water inventory.
        """
        dt_h = self.communication_step_s / 3600.0
        records: list[dict] = []
        for participant in sorted(self.participants.values(), key=lambda p: p.scope_id):
            for transfer in participant._inbound:
                kind = self._transfer_kind(transfer.binding_id)
                flow_m3h = float(transfer.payload.get("flow_m3h", 0.0))
                records.append(
                    {
                        "transfer_id": transfer.transfer_id,
                        "run_id": transfer.run_id,
                        "binding_id": transfer.binding_id,
                        "transfer_kind": kind,
                        "boundary": BOUNDARY_ROLE.get(transfer.binding_id, "internal")
                        if kind == "physical_water"
                        else kind,
                        "water_m3": round(flow_m3h * dt_h, 12) if kind == "physical_water" else 0.0,
                        "source_scope": transfer.source.owner_scope.as_string(),
                        "target_scope": transfer.target.owner_scope.as_string(),
                        "source_port": transfer.source.port_id,
                        "target_port": transfer.target.port_id,
                        "window_id": transfer.window_id,
                        "simulation_time_s": transfer.simulation_time_s,
                        "payload": {key: value for key, value in sorted(transfer.payload.items())},
                        "provenance": self.provenance_index.get(transfer.binding_id, {}),
                    }
                )
        self._transfers = tuple(sorted(records, key=lambda row: row["transfer_id"]))
        # Water inside the plant control volume that is committed but not yet
        # consumed: every physical transfer except the boundary DISCHARGE to the
        # network (already outside the volume) - information and source
        # availability are excluded by construction (C02-3).
        self._in_transit_m3 = round(
            sum(
                row["water_m3"]
                for row in records
                if row["transfer_kind"] == "physical_water" and row["boundary"] != "exit"
            ),
            12,
        )
        self._information_inventory_m3 = round(
            sum(
                float(row["payload"].get("flow_m3h", 0.0)) * dt_h
                for row in records
                if row["transfer_kind"] == "information"
            ),
            12,
        )
        self._source_availability_m3 = round(
            sum(
                float(row["payload"].get("flow_m3h", 0.0)) * dt_h
                for row in records
                if row["transfer_kind"] == "source_availability_outside_boundary"
            ),
            12,
        )

    @staticmethod
    def _transfer_kind(binding_id: str) -> str:
        if binding_id in X2_INFORMATION_EDGE_IDS:
            return "information"
        if binding_id in OUTSIDE_BOUNDARY_BINDINGS:
            return "source_availability_outside_boundary"
        return "physical_water"

    @property
    def in_transit_m3(self) -> float:
        """Physical water inside the boundary, committed but not yet consumed."""
        return self._in_transit_m3

    @property
    def information_inventory_m3(self) -> float:
        """Information-signal inventory of the last window (NEVER water)."""
        return self._information_inventory_m3

    def _update_water_ledger(self) -> None:
        """Cumulative ledger-based plant water balance (C02-3).

        Control volume: from the pumped-INTAKE discharge to the network / sludge
        discharge. Every term is computed on ONE consistent basis (emission at
        the control-volume boundary) from the transfer ledger plus explicit
        clamp accounting:

        - IN   = the intake discharge (what the pump actually delivers);
        - OUT  = the DIST discharge to the network + the sludge tank outflow;
        - LOSS = declared LINE2 process loss (+ any L2 capacity spill) - the only
          modelled loss, and it is explicit and alarmed;
        - WATER INSIDE = storage volumes + the in-transit physical transfers of
          the current window;
        - OVERFLOW / SHORTFALL = explicitly accounted clamps (never silent).

        Source AVAILABILITY that the intake does not pump is outside the volume
        and information bindings carry no water: neither may enter the balance.
        """
        dt_h = self.communication_step_s / 3600.0
        current = self._transfers
        self._ledger["plant_in_m3"] += self._water_of(current, INTAKE_BINDING_ID)
        self._ledger["plant_out_m3"] += self._water_of(current, NETWORK_BINDING_ID)
        self._ledger["plant_out_m3"] += (
            self.participants["vf-shw-node-sludge-t201"].monitor_values()["processed_m3h"] * dt_h
        )
        # C03-4: the LINE2 loss is the DECLARED law plus the explicitly modelled
        # capacity spill (audited at step time), never an unexplained dropped
        # delivery that would be relabelled as valid process loss.
        line2 = self.participants["vf-shw-node-line2-aggregate"]
        line2_values = line2.monitor_values()
        self._ledger["process_loss_m3"] += (
            line2_values["declared_loss_m3h"] + line2_values["capacity_spill_m3h"]
        ) * dt_h
        self._ledger["process_loss_observed_m3"] += line2_values["observed_loss_m3h"] * dt_h
        if not line2_values["process_loss_audit_ok"]:
            self._ledger["process_loss_audit_failures"] += 1
        self._ledger["information_m3"] += self._information_inventory_m3
        self._ledger["source_availability_m3"] += self._source_availability_m3
        self._ledger["in_transit_m3"] = self._in_transit_m3
        self._ledger["overflow_m3"] = round(
            sum(p._overflow_m3 for p in self.participants.values()), 12
        )
        self._ledger["shortfall_m3"] = round(
            sum(p._shortfall_m3 for p in self.participants.values()), 12
        )
        self._prev_transfers = current

    @staticmethod
    def _water_of(rows: Sequence[Mapping[str, Any]], binding_id: str) -> float:
        """Physical water (m3) carried by one binding in a window ledger."""
        return round(
            sum(
                float(row["water_m3"])
                for row in rows
                if row["binding_id"] == binding_id and row["transfer_kind"] == "physical_water"
            ),
            12,
        )

    def _control_commands(self) -> dict[str, Any]:
        """Evaluate the frozen C1 set from COMMITTED state (explicit_lagged)."""
        evaluation = self.controls.evaluate(self._feedback, self._window_index + 1)
        self._control_snapshot = {
            "window_index": evaluation.window_index,
            "outputs": dict(evaluation.outputs),
            "alarms_raised": list(evaluation.alarms_raised),
            "alarms_cleared": list(evaluation.alarms_cleared),
            "detail": evaluation.detail,
        }
        commands: dict[str, Any] = dict(evaluation.outputs)
        by_controller = {
            controller_id: dict(payload.get("detail", {}))
            for controller_id, payload in evaluation.detail["controllers"].items()
        }
        # LINE2 split fraction is the C1 MV state (published through the contract detail)
        split_detail = by_controller.get("vf-shw-ctrl-line2-split", {})
        if "split_fraction" in split_detail:
            commands["line2_split_fraction"] = split_detail["split_fraction"]
        sludge_detail = by_controller.get("vf-shw-ctrl-sludge-duty", {})
        if "withdrawal_rate_m3h" in sludge_detail:
            commands["sludge_withdrawal_m3h"] = sludge_detail["withdrawal_rate_m3h"]
        dose_detail = by_controller.get("vf-shw-ctrl-dose-ratio", {})
        if "max_step_mg_l" in dose_detail:
            commands["dose_max_step_mg_l"] = dose_detail["max_step_mg_l"]
        backwash_detail = by_controller.get("vf-shw-ctrl-backwash-sequence", {})
        if "step" in backwash_detail:
            commands["backwash_step"] = backwash_detail["step"]
        commands["by_controller"] = by_controller
        return commands

    def _record_committed(self) -> None:
        dt_h = self.communication_step_s / 3600.0
        records: list[dict] = []
        for participant in sorted(self.participants.values(), key=lambda p: p.scope_id):
            values = participant.monitor_values()
            records.append({"scope_id": participant.scope_id, "values": values})
        if self._window_index > 0:
            # plant boundary IN = what the intake actually pumps into the plant
            # (the raw-source availability that is NOT pumped stays outside).
            self._plant_in_m3 += self.participants["vf-shw-node-raw-intake"].monitor_values()["intake_flow_m3h"] * dt_h
            self._plant_out_m3 += self.participants["vf-shw-node-network-demand"].monitor_values()["network_flow_m3h"] * dt_h
            self._plant_out_m3 += self.participants["vf-shw-node-sludge-t201"].monitor_values()["processed_m3h"] * dt_h
        self._feedback = {
            "screen_dp": self.participants["vf-shw-node-raw-intake"].monitor_values()["screen_dp_kpa"],
            "raw_source_available": True,
            "t100_intake_enable": bool(
                self._control_snapshot.get("outputs", {}).get("intake_enable", True)
            ),
            "t100_level": self.participants["vf-shw-node-t100"].monitor_values()["level_m"],
            "level_band": self._level_band_payload("t100"),
            "contact_time_s": self.participants["vf-shw-node-t101"].monitor_values()["contact_time_s"],
            "l1_feed_flow_m3h": self.participants["vf-shw-node-t100"].monitor_values()["outflows_m3h"]["vf-shw-node-t101"],
            "plant_flow_m3h": self.participants["vf-shw-node-t100"].monitor_values()["withdrawal_m3h"],
            "settled_volume_m3": self.participants["vf-shw-node-t105"].monitor_values()["volume_m3"],
            "settled_volume_high_m3": self.scenario.t105_settled_volume_high_m3,
            "filter_dp_kpa": self.participants["vf-shw-node-t106"].monitor_values()["filter_dp_kpa"],
            "filtered_turbidity_proxy_ntu": self.participants["vf-shw-node-t106"].monitor_values()["turbidity_ntu"],
            "filter_inlet_flow_m3h": self.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"],
            "wash_water_level_sufficient": (
                self.participants["vf-shw-node-wash-t110"].monitor_values()["volume_m3"]
                < 0.9 * self.scenario.wash_t110_capacity_m3
            ),
            "t108_level": self.participants["vf-shw-node-t108"].monitor_values()["level_m"],
            "level_band_t108": self._level_band_payload("t108"),
            "sludge_tank_volume_m3": self.participants["vf-shw-node-sludge-t201"].monitor_values()["volume_m3"],
            "sludge_tank_high_m3": self.scenario.sludge_t201_high_m3,
            "scenario_split_fraction": self.scenario.line2_split_fraction,
            "line2_capacity_available": True,
            "chemical_tank_ok": self.participants["vf-shw-node-chem-dosing"].monitor_values()["tank_level_l"] > 0.0,
            "dose_targets": {
                "pac_dose": self.scenario.chem_pac_dose_mg_l,
                "coag_dose": self.scenario.chem_coag_dose_mg_l,
            },
            "sludge_withdrawal_rate_m3h": self.scenario.t105_sludge_withdrawal_m3h,
            "suction_header_available": True,
            "mcc_reference_available": True,
            "sludge_line_available": True,
            "downstream_sink_available": True,
            "by_controller": {
                "vf-shw-ctrl-t100-permissive": {"level_band": self._level_band_payload("t100")},
                "vf-shw-ctrl-t108-permissive": {"level_band": self._level_band_payload("t108")},
            },
            "scope_records": records,
        }

    def _level_band_payload(self, which: str) -> dict:
        band = self.scenario.t100_level_band_m if which == "t100" else self.scenario.t108_level_band_m
        initial = (
            self.scenario.t100_initial_volume_m3 / self.scenario.t100_area_m2
            if which == "t100"
            else self.scenario.t108_initial_volume_m3 / self.scenario.t108_area_m2
        )
        return {
            "LALL": band[0], "LAL": band[1], "LAH": band[2], "LAHH": band[3], "initial": initial,
        }

    # projections ---------------------------------------------------------
    def assumed_topology(self) -> tuple[dict, ...]:
        """Assumed edges actually in use (read-only, labelled)."""
        return tuple(
            {
                "scope": row["source_scope_id"],
                "target_scope": row["target_scope_id"],
                "binding_id": row["binding_id"],
                "assumption_id": row["assumption_id"],
                "reversible": True,
                **AUTHORITY_LABELS,
            }
            for row in self.provenance_records()
            if row["edge_category"] == "vf_scenario_assumption"
        )

    def runtime_truth(self) -> dict:
        """The ONE authoritative X2 runtime-truth/authorization projection."""
        return {
            "model": WHOLE_PLANT_X2_SCHEMA,
            "workspace_id": SHWTP_WHOLE_PLANT_WORKSPACE_ID,
            #: the attempt identity of the ACTIVE lifecycle context (C02-1); the
            #: model never mints its own run id.
            "run_id": self.run_id,
            "run_id_source": "attempt_context",
            "coupling_policy": self.coupling_policy,
            "window_index": self._window_index,
            "communication_step_s": self.communication_step_s,
            "scope_count": len(self.participants),
            "c1_controller_count": len(self.controls.active_controller_ids),
            "whole_plant_runtime_implementation": WHOLE_PLANT_RUNTIME_IMPLEMENTATION,
            "whole_plant_runtime_authorization": WHOLE_PLANT_RUNTIME_AUTHORIZATION,
            **AUTHORITY_LABELS,
        }

    def monitor_rows(self) -> tuple[dict, ...]:
        rows: list[dict] = []
        for info in self.scopes:
            if not info.x2_admitted:
                continue
            participant = self.participants[info.scope_id]
            row = info.to_dict()
            row["time_s"] = round(participant.current_time_s, 6)
            values = dict(participant.monitor_values())
            values.update(AUTHORITY_LABELS)
            require_authority_labels(values, where=f"monitor values for {info.scope_id!r}")
            row["values"] = values
            row["open_alarms"] = list(participant.open_alarms)
            require_authority_labels(row, where=f"monitor row for {info.scope_id!r}")
            rows.append(row)
        return tuple(rows)

    def control_rows(self) -> tuple[dict, ...]:
        snapshot = self._control_snapshot.get("detail", {}).get("controllers", {})
        rows: list[dict] = []
        for controller_id in self.controls.active_controller_ids:
            payload = snapshot.get(controller_id, {})
            rows.append(
                {
                    "controller_id": controller_id,
                    "control_class": "C1",
                    "active_in_x2": True,
                    "outputs": dict(payload.get("outputs", {})),
                    "detail": dict(payload.get("detail", {})),
                    "open_alarms": list(self.controls.open_alarms().get(controller_id, ())),
                    **AUTHORITY_LABELS,
                }
            )
        return tuple(rows)

    def balance_report(self) -> dict:
        """Ledger-based plant water balance (C02-3) + physical validity (C03).

        The reconciliation is computed INDEPENDENTLY of the participants'
        ``volume_in/volume_out`` counters: it uses the transfer ledger (physical
        water only, on one consistent consumption basis at the control volume),
        the storage volumes and the explicitly accounted clamps.

        VF-SHW-X2-C03 separates two DIFFERENT claims:

        - **physical conservation** (``conserved`` / ``physical_valid``): the
          water balance closes to float rounding **without** any compensation
          term, no water was artificially CREATED (``shortfall_m3`` within a
          justified rounding tolerance) and the declared process-loss audit holds.
          An oracle must never certify invented water as conserved.
        - **reconciled accounting** (``accounting_reconciled``): the same balance
          once the diagnostic created-water amount is subtracted. This is
          reported for diagnosis only and is NOT a physical-conservation claim.
        """
        storage_rows = [p.balance() for p in self.participants.values() if p.storage]
        stored_delta_m3 = round(
            sum(
                p._storage_volume() - getattr(p, "_initial_volume_m3", 0.0)
                for p in self.participants.values()
                if p.storage
            ),
            12,
        )
        ledger = self._ledger
        # created water is read LIVE: a clamp performed outside the window loop
        # must be visible to the oracle (SA counterexample)
        created_water_m3 = round(
            sum(p._shortfall_m3 for p in self.participants.values()), 12
        )
        overflow_m3 = round(sum(p._overflow_m3 for p in self.participants.values()), 12)
        process_loss_m3 = round(ledger["process_loss_m3"], 12)
        process_loss_observed_m3 = round(ledger["process_loss_observed_m3"], 12)
        audit_failures = int(ledger["process_loss_audit_failures"])
        # NO compensation term: artificially created water must break conservation
        residual = round(
            (stored_delta_m3 + ledger["in_transit_m3"])
            - ledger["plant_in_m3"]
            + ledger["plant_out_m3"]
            + process_loss_m3
            + overflow_m3,
            12,
        )
        scale = max(
            1.0,
            abs(ledger["plant_in_m3"]) + abs(ledger["plant_out_m3"]) + abs(stored_delta_m3),
        )
        tolerance_m3 = round(
            PLANT_WATER_TOLERANCE_RELATIVE * scale + PLANT_WATER_TOLERANCE_ABSOLUTE_M3, 15
        )
        accounting_reconciled = abs(residual - created_water_m3) <= tolerance_m3
        created_within_rounding = created_water_m3 <= CREATED_WATER_TOLERANCE_M3
        loss_audit_ok = (
            audit_failures == 0
            and abs(process_loss_m3 - process_loss_observed_m3)
            <= max(PROCESS_LOSS_TOLERANCE_M3, tolerance_m3)
        )
        physically_conserved = (
            abs(residual) <= tolerance_m3 and created_within_rounding and loss_audit_ok
        )
        return {
            "window_index": self._window_index,
            "storage_balances": [
                {**row, **AUTHORITY_LABELS} for row in storage_rows
            ],
            "plant_water": {
                "basis": "control volume = pumped-intake discharge .. network/sludge discharge; IN/OUT at the boundary, water inside = storage + in-transit",
                "plant_in_m3": round(ledger["plant_in_m3"], 9),
                "plant_out_m3": round(ledger["plant_out_m3"], 9),
                "stored_delta_m3": stored_delta_m3,
                "transit_inventory_m3": round(ledger["in_transit_m3"], 9),
                "water_inside_m3": round(stored_delta_m3 + ledger["in_transit_m3"], 9),
                "process_loss_m3": round(process_loss_m3, 9),
                "process_loss_observed_m3": round(process_loss_observed_m3, 9),
                "process_loss_declared_law_plus_spill": loss_audit_ok,
                "process_loss_audit_failures": audit_failures,
                "overflow_m3": round(overflow_m3, 9),
                "shortfall_m3": created_water_m3,
                "created_water_diagnostic_m3": created_water_m3,
                "created_water_tolerance_m3": CREATED_WATER_TOLERANCE_M3,
                "created_water_within_rounding": created_within_rounding,
                "information_inventory_m3": round(ledger["information_m3"], 9),
                "source_availability_m3": round(ledger["source_availability_m3"], 9),
                "source_availability_note": (
                    "raw-source availability NOT pumped - outside the pumped-intake "
                    "control volume, never part of the water inventory"
                ),
                "residual_m3": residual,
                "closure_m3": residual,
                "tolerance_m3": tolerance_m3,
                # PHYSICAL claim: no compensation term, no created water, audit holds
                "conserved": physically_conserved,
                "physical_valid": physically_conserved,
                # ACCOUNTING claim (diagnostic only): created water subtracted
                "accounting_reconciled": accounting_reconciled,
                "accounting_note": (
                    "accounting_reconciled subtracts the created-water diagnostic and is "
                    "NOT a physical-conservation claim"
                ),
                "bounded": physically_conserved,
            },
            "max_storage_residual_m3": max((abs(row["residual_m3"]) for row in storage_rows), default=0.0),
            **AUTHORITY_LABELS,
        }

    def input_wiring(self) -> tuple[dict, ...]:
        """Runtime resolution of every X2-admitted contract input (evidence oracle 6)."""
        rows: list[dict] = []
        for info in self.scopes:
            if not info.x2_admitted:
                continue
            participant = self.participants[info.scope_id]
            for entry in participant.contract["inputs"]:
                signal = entry["signal"]
                source = entry["source"]
                producer_class = entry.get("x2_producer_class")
                if producer_class is None:
                    if isinstance(source, str) and source.startswith("vf-shw-ctrl-"):
                        producer_class = (
                            "x2_active_controller"
                            if source in self.controls.active_controller_ids
                            else "x2_fallback_default"
                        )
                    elif isinstance(source, str) and source.startswith("vf-shw-node-"):
                        producer_class = "process_node"
                    elif source in ("scenario",):
                        producer_class = "scenario"
                    else:
                        producer_class = "unresolved"
                rows.append(
                    {
                        "scope_id": info.scope_id,
                        "signal": signal,
                        "declared_source": source,
                        "x2_producer_class": producer_class,
                        "runtime_resolution": self._runtime_resolution(info.scope_id, signal, source),
                        **AUTHORITY_LABELS,
                    }
                )
        return tuple(rows)

    def _runtime_resolution(self, scope_id: str, signal: str, source: Any) -> str:
        if isinstance(source, str) and source.startswith("vf-shw-ctrl-"):
            if source in self.controls.active_controller_ids:
                return "c1_control_command"
            return "declared_x2_fallback"
        if isinstance(source, str) and source.startswith("vf-shw-node-"):
            return "coordinated_transfer"
        if source in ("scenario",):
            return "scenario_parameter"
        return "unresolved"

    def transfer_records(self) -> tuple[dict, ...]:
        return self._transfers

    def provenance_records(self) -> tuple[dict, ...]:
        return tuple(
            {
                "binding_id": spec.binding_id,
                "graph_edge_id": spec.graph_edge_id,
                "source_scope_id": spec.source_scope_id,
                "target_scope_id": spec.target_scope_id,
                "information": spec.information,
                **self.provenance_index.get(spec.binding_id, {}),
                **AUTHORITY_LABELS,
            }
            for spec in self.wiring
        )

    def reset(self) -> None:
        self.controls.reset()
        for participant in self.participants.values():
            participant.reset()
        self._window_index = 0
        self._transfers = ()
        self._prev_transfers = ()
        self._control_snapshot = {}
        self._feedback = {}
        self._plant_in_m3 = 0.0
        self._plant_out_m3 = 0.0
        self._in_transit_m3 = 0.0
        self._information_inventory_m3 = 0.0
        self._source_availability_m3 = 0.0
        self._ledger = _empty_water_ledger()
        self._seen_windows = set()
        self._record_transfers()
        self._record_committed()

    @property
    def window_index(self) -> int:
        return self._window_index

    def alarms(self) -> dict[str, tuple[str, ...]]:
        payload = {pid: p.open_alarms for pid, p in self.participants.items() if p.open_alarms}
        payload.update({f"control:{cid}": alarms for cid, alarms in self.controls.open_alarms().items()})
        return payload


def _window_index(window_id: str) -> int:
    """Window number carried by a window id (model or run-lifecycle form).

    The model does not depend on this value (its own sequence is authoritative);
    it exists for provenance/evidence and for callers that build ids themselves.
    """
    if not isinstance(window_id, str):
        raise WholePlantX2Error(f"window id must be a str, got {type(window_id).__name__}")
    match = re.fullmatch(r"(?:window-|.*-w)([1-9][0-9]*)", window_id)
    if not match:
        raise WholePlantX2Error(
            f"invalid window id {window_id!r}; expected 'window-<n>' (n >= 1) or '<run>-w<n>'"
        )
    return int(match.group(1))


def _provenance_index(manifest: WholePlantContracts) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for edge in manifest.edges:
        if edge.edge_id not in X2_FLOW_EDGE_IDS:
            continue
        index[edge.edge_id] = {
            "edge_category": edge.category,
            "pim_relation_id": edge.pim_relation_id,
            "assumption_id": edge.assumption_id,
            "evidence_status": edge.evidence_status,
            "reversible": edge.reversible if edge.assumption_id else None,
        }
    for binding_id in X2_INFORMATION_EDGE_IDS:
        index[binding_id] = {
            "edge_category": "contract_declared_input",
            "pim_relation_id": None,
            "assumption_id": None,
            "evidence_status": "VF-contract",
            "reversible": None,
        }
    return index


def build_shwtp_whole_plant_workspace() -> Workspace:
    """Build the G1 workspace containing exactly the 16 admitted X2 scopes."""
    workspace_id = SHWTP_WHOLE_PLANT_WORKSPACE_ID
    specs: list[ScopeSpec] = []
    for segments in CONTAINER_PATHS:
        specs.append(ScopeSpec(scope_id=segments[-1], mode=ScopeMode.CONTAINER_ONLY, parent_path=None))
    for scope_id in sorted(SCOPE_PATHS):
        path = scope_path(scope_id)
        parent = path.parent if len(path.scope_ids) > 1 else None
        specs.append(
            ScopeSpec(
                scope_id=path.scope_ids[-1],
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=parent,
            )
        )
    return build_workspace(workspace_id, specs)


def build_shwtp_whole_plant(
    *,
    scenario: WholePlantScenario | None = None,
    communication_step_s: float | None = None,
    run_id: str = SHWTP_WHOLE_PLANT_DEFAULT_RUN_ID,
    contracts: WholePlantContracts | None = None,
) -> WholePlantX2Runtime:
    """Build the X2 whole-plant shallow runnable model from the frozen contracts."""
    manifest = contracts or load_whole_plant_contracts()
    step = _num(
        communication_step_s if communication_step_s is not None else (scenario or WholePlantScenario()).communication_step_s,
        "communication_step_s",
    )
    if step <= 0:
        raise WholePlantX2Error("communication_step_s must be > 0")
    resolved_scenario = scenario or WholePlantScenario(communication_step_s=step)
    if resolved_scenario.communication_step_s != step:
        resolved_scenario = WholePlantScenario(
            **{
                **{field_name: getattr(resolved_scenario, field_name) for field_name in resolved_scenario.__slots__},
                "communication_step_s": step,
            }
        )

    scope_contracts = {scope.scope_id: scope.raw for scope in manifest.scopes if scope.x2_admitted}
    if len(scope_contracts) != 16:
        raise WholePlantX2Error(
            f"X2 requires exactly 16 admitted scope contracts, found {len(scope_contracts)}"
        )
    control_entries = {control.controller_id: control.raw for control in manifest.controls}
    controls = build_c1_controllers(control_entries, dt_s=step)

    workspace = build_shwtp_whole_plant_workspace()
    wiring = _wiring(manifest)
    graph = _build_graph(wiring)
    overlay = _build_overlay(manifest)

    participants: dict[str, ScopeParticipant] = {}
    common = {
        "workspace_id": SHWTP_WHOLE_PLANT_WORKSPACE_ID,
        "run_id": run_id,
        "scenario": resolved_scenario,
    }
    participants["vf-shw-node-raw-source"] = RawSourceParticipant(scope_contracts["vf-shw-node-raw-source"], **common)
    participants["vf-shw-node-raw-intake"] = RawIntakeParticipant(scope_contracts["vf-shw-node-raw-intake"], **common)
    participants["vf-shw-node-t100"] = T100Participant(
        scope_contracts["vf-shw-node-t100"], area_m2=resolved_scenario.t100_area_m2,
        capacity_m3=resolved_scenario.t100_capacity_m3,
        initial_volume_m3=resolved_scenario.t100_initial_volume_m3,
        level_band=resolved_scenario.t100_level_band_m, **common,
    )
    participants["vf-shw-node-t101"] = T101Participant(
        scope_contracts["vf-shw-node-t101"],
        capacity_m3=resolved_scenario.t101_contact_volume_m3,
        initial_volume_m3=0.0,
        **common,
    )
    participants["vf-shw-node-t102"] = T102Participant(scope_contracts["vf-shw-node-t102"], **common)
    participants["vf-shw-node-t103"] = T103Participant(scope_contracts["vf-shw-node-t103"], **common)
    participants["vf-shw-node-t104"] = T104Participant(
        scope_contracts["vf-shw-node-t104"],
        capacity_m3=resolved_scenario.t104_floc_volume_m3,
        initial_volume_m3=0.0,
        **common,
    )
    participants["vf-shw-node-t105"] = ClarifierParticipant(
        scope_contracts["vf-shw-node-t105"], area_m2=resolved_scenario.t105_area_m2,
        capacity_m3=resolved_scenario.t105_capacity_m3,
        initial_volume_m3=resolved_scenario.t105_initial_volume_m3, **common,
    )
    participants["vf-shw-node-t106"] = FilterParticipant(
        scope_contracts["vf-shw-node-t106"], capacity_m3=resolved_scenario.t106_capacity_m3,
        initial_volume_m3=resolved_scenario.t106_initial_volume_m3, **common,
    )
    participants["vf-shw-node-t108"] = T108Participant(
        scope_contracts["vf-shw-node-t108"], area_m2=resolved_scenario.t108_area_m2,
        capacity_m3=resolved_scenario.t108_capacity_m3,
        initial_volume_m3=resolved_scenario.t108_initial_volume_m3,
        level_band=resolved_scenario.t108_level_band_m, **common,
    )
    participants["vf-shw-node-wash-t110"] = RecoveryParticipant(
        scope_contracts["vf-shw-node-wash-t110"], capacity_m3=resolved_scenario.wash_t110_capacity_m3,
        area_m2=resolved_scenario.wash_t110_area_m2, **common,
    )
    participants["vf-shw-node-dist-p108"] = DistributionParticipant(
        scope_contracts["vf-shw-node-dist-p108"],
        fallback_speed_pct=_dist_fallback_speed(scope_contracts["vf-shw-node-dist-p108"]), **common,
    )
    participants["vf-shw-node-network-demand"] = NetworkDemandParticipant(
        scope_contracts["vf-shw-node-network-demand"], **common
    )
    participants["vf-shw-node-chem-dosing"] = ChemDosingParticipant(
        scope_contracts["vf-shw-node-chem-dosing"], **common
    )
    participants["vf-shw-node-sludge-t201"] = SludgeSinkParticipant(
        scope_contracts["vf-shw-node-sludge-t201"], capacity_m3=resolved_scenario.sludge_t201_capacity_m3,
        initial_volume_m3=resolved_scenario.sludge_t201_initial_volume_m3,
        area_m2=resolved_scenario.sludge_t201_area_m2, **common,
    )
    participants["vf-shw-node-line2-aggregate"] = Line2AggregateParticipant(
        scope_contracts["vf-shw-node-line2-aggregate"], **common
    )

    coordinator = Coordinator(workspace=workspace, graph=graph)
    for scope_id in sorted(participants):
        coordinator.register(participants[scope_id])

    scopes = tuple(
        ScopeRuntimeInfo(
            scope_id=scope.scope_id,
            canonical_id=scope.canonical_id,
            vf_path=scope_path(scope.scope_id).as_string(),
            process_role=scope.process_role,
            fidelity_class=scope.fidelity_class,
            update_rule_family=scope.update_rule_family,
            conservation_kind=scope.conservation_kind,
            control_ids=tuple(scope.control_ids),
            x2_admitted=True,
        )
        for scope in sorted(manifest.scopes, key=lambda s: s.scope_id)
        if scope.x2_admitted
    )

    runtime = WholePlantX2Runtime(
        workspace=workspace,
        graph=graph,
        overlay=overlay,
        coordinator=coordinator,
        participants=participants,
        scopes=scopes,
        controls=controls,
        scenario=resolved_scenario,
        wiring=wiring,
        provenance_index=_provenance_index(manifest),
        communication_step_s=step,
        run_id=run_id,
    )
    # deterministic initial feedback for window-1 explicit_lagged evaluation
    runtime._record_committed()
    return runtime


def _dist_fallback_speed(contract: Mapping[str, Any]) -> float:
    for entry in contract["inputs"]:
        if entry["signal"] == "hsp_speed_cmd":
            fallback = entry.get("x2_fallback")
            if not isinstance(fallback, Mapping):
                raise WholePlantX2Error(
                    "DIST-P108 hsp_speed_cmd must declare an explicit X2 fallback/default"
                )
            return _nonneg(fallback["value"], "dist fallback speed")
    raise WholePlantX2Error("DIST-P108 must declare an hsp_speed_cmd input")


def whole_plant_scope_metadata(contracts: WholePlantContracts | None = None) -> tuple[ScopeRuntimeInfo, ...]:
    """The 16 admitted scopes' runtime metadata (contract-derived, builds nothing)."""
    manifest = contracts or load_whole_plant_contracts()
    return tuple(
        ScopeRuntimeInfo(
            scope_id=scope.scope_id,
            canonical_id=scope.canonical_id,
            vf_path=scope_path(scope.scope_id).as_string(),
            process_role=scope.process_role,
            fidelity_class=scope.fidelity_class,
            update_rule_family=scope.update_rule_family,
            conservation_kind=scope.conservation_kind,
            control_ids=tuple(scope.control_ids),
            x2_admitted=True,
        )
        for scope in sorted(manifest.scopes, key=lambda s: s.scope_id)
        if scope.x2_admitted
    )


def whole_plant_assumed_topology(contracts: WholePlantContracts | None = None) -> tuple[dict, ...]:
    """The assumed edges in use, as a detached read-only projection."""
    manifest = contracts or load_whole_plant_contracts()
    used = set(manifest.admission.assumed_edges_used)
    rows = []
    for edge in sorted(manifest.edges, key=lambda e: e.edge_id):
        if edge.edge_id not in used or edge.category != "vf_scenario_assumption":
            continue
        rows.append(
            {
                "scope": scope_path(edge.source).as_string(),
                "target_scope": scope_path(edge.target).as_string(),
                "binding_id": edge.edge_id,
                "assumption_id": edge.assumption_id,
                "reversible": True,
                **AUTHORITY_LABELS,
            }
        )
    return tuple(rows)


def whole_plant_scope_ids() -> tuple[str, ...]:
    """The frozen 16 X2-admitted scope ids."""
    return tuple(sorted(SCOPE_PATHS))
