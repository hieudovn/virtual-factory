"""SH-WTP X3 execution profile: physical bounds + the two admitted PI loops.

Implements the SA design freeze (Issue #97 D1-D9) as a NEW execution profile that
reuses the accepted X2 process laws and the frozen X1 contract layer:

- **D1** exactly the 16 admitted participants; exactly two C2 PI loops (T106 inlet
  flow, T108 level); DIST keeps its declared fixed 80 % command with head/flow/
  power feasibility; pressure/RAW/T100/chlorine loops stay deferred;
- **D2** global deterministic 1-second coordinator windows; one attempt-bound
  identity; a transfer emitted this tick is consumed at the NEXT tick;
- **D3** the X3 profile is validated before execution and invalid states are
  rejected before stepping;
- **D4** a model-level conservative allocation stage supplies immutable per-edge
  budgets (source availability, reserved receiver headroom, edge/trunk ratings,
  bounded queue); withheld water stays in the source storage;
- **D5** the PI drives the ACTUAL T105->T106 inlet flow through the valve budget
  and the T108 pump request is feasibility-limited; abstractions stay synthetic;
- **D6** pump head/power feasibility, OFF-is-zero-flow, hydraulic/electrical power
  and energy integration with explicit units; unmodelled drives are unavailable;
- **D8** hard numeric checks, a closed water ledger with no created water, and
  independent projections for the evidence.

No new process graph edge, scope authority, second simulation engine or
lifecycle/run-identity authority is introduced here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.composition import Coordinator, WindowOutcome
from virtual_factory.shwtp.contracts import WholePlantContracts, load_whole_plant_contracts
from virtual_factory.shwtp.physical_budget import (
    PumpModel,
    PumpOperatingPoint,
    TickAllocation,
    allocate_tick,
)
from virtual_factory.shwtp.whole_plant import (
    AUTHORITY_LABELS,
    CREATED_WATER_TOLERANCE_M3,
    INTAKE_BINDING_ID,
    NETWORK_BINDING_ID,
    PLANT_WATER_TOLERANCE_ABSOLUTE_M3,
    PLANT_WATER_TOLERANCE_RELATIVE,
    SCOPE_PATHS,
    SHWTP_WHOLE_PLANT_WORKSPACE_ID,
    WHOLE_PLANT_RUNTIME_AUTHORIZATION,
    WHOLE_PLANT_RUNTIME_IMPLEMENTATION,
    ChemDosingParticipant,
    ClarifierParticipant,
    DistributionParticipant,
    FilterParticipant,
    Line2AggregateParticipant,
    NetworkDemandParticipant,
    RawIntakeParticipant,
    RawSourceParticipant,
    RecoveryParticipant,
    ScopeParticipant,
    SludgeSinkParticipant,
    T100Participant,
    T101Participant,
    T102Participant,
    T103Participant,
    T104Participant,
    T108Participant,
    WholePlantScenario,
    WholePlantX2Runtime,
    _build_graph,
    _build_overlay,
    _dist_fallback_speed,
    _provenance_index,
    _wiring,
    build_shwtp_whole_plant_workspace,
    require_authority_labels,
    whole_plant_scope_metadata,
)
from virtual_factory.shwtp.x3_controls import X3ControlEvaluation, X3ControlLayer
from virtual_factory.shwtp.x3_profile import X3Profile, load_x3_profile

X3_MODEL_SCHEMA = "vf.shwtp.x3.whole_plant_runtime.v1"
X3_OUT_BUDGET_KEY = "x3_out_budget_m3h_by_scope"
X3_TICK_KEY = "x3_tick_s"
X3_PROFILE_KEY = "x3_profile_id"
X3_EXPECTED_SCOPE_COUNT = 16

#: Pass-through water scopes that hold exactly one tick of COMMITTED water before
#: they forward it (mixing contact basins, the LINE2 manifold and the distribution
#: header). Their holding is explicit physical inventory in the balance. The
#: intake boundary and the demand sink are excluded: the intake discharge is the
#: IN term and the network discharge is the OUT term.
PIPELINE_SCOPES = frozenset(
    {
        "vf-shw-node-t102",
        "vf-shw-node-t103",
        "vf-shw-node-dist-p108",
        "vf-shw-node-line2-aggregate",
    }
)


class WholePlantX3Error(ValueError):
    """Raised when an X3 invariant is violated (fail closed)."""


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WholePlantX3Error(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise WholePlantX3Error(f"{name} must be a finite number, got {value!r}")
    return out


#: Per-tick allowance for the deterministic 1e-12 rounding of the ledger terms.
#: One X3 tick rounds ~25 accumulated terms, so <=2.5e-11 m3 of pure float
#: rounding enters the closure per tick; 5e-11 is a conservative bound. This is a
#: rounding allowance, never a licence for a physical imbalance (any created water
#: or unbounded discharge still fails the gate at 1e-9).
X3_LEDGER_ROUNDING_PER_TICK_M3 = 5e-11

#: The physical transfer that carries each powered pump's DISCHARGE: the committed
#: water (m3) on this binding in a tick is exactly the pumped throughput of the tick,
#: which is the basis of the realized operating point / energy integration (C01-2).
PUMP_DISCHARGE_BINDINGS: dict[str, str] = {
    "raw-intake-pump": "vf-shw-edge-intake-t100",
    "t108-transfer-pump": "vf-shw-edge-t108-dist",
    "dist-hsp": "vf-shw-edge-dist-demand",
}


def _nonneg_float(value: Any, name: str = "value") -> float:
    out = _num(value, name)
    if out < 0.0:
        raise WholePlantX3Error(f"{name} must be >= 0, got {out!r}")
    return out


def _fraction(value: Any) -> float:
    out = _num(value, "split_fraction")
    if not 0.0 <= out <= 1.0:
        raise WholePlantX3Error(f"split_fraction must be within [0, 1], got {out!r}")
    return out


def build_x3_scenario(
    profile: X3Profile, *, base: WholePlantScenario | None = None
) -> WholePlantScenario:
    """Derive the X3 scenario: accepted X2 process laws + X3 tank geometry (D8)."""
    base = base or WholePlantScenario()
    overrides: dict[str, Any] = {"communication_step_s": profile.tick_s}
    mapping = {
        "vf-shw-node-t100": ("t100_area_m2", "t100_capacity_m3", "t100_initial_volume_m3", "t100_level_band_m"),
        "vf-shw-node-t101": (None, "t101_contact_volume_m3", None, None),
        "vf-shw-node-t104": (None, "t104_floc_volume_m3", None, None),
        "vf-shw-node-t105": ("t105_area_m2", "t105_capacity_m3", "t105_initial_volume_m3", None),
        "vf-shw-node-t106": (None, "t106_capacity_m3", "t106_initial_volume_m3", None),
        "vf-shw-node-t108": ("t108_area_m2", "t108_capacity_m3", "t108_initial_volume_m3", "t108_level_band_m"),
        "vf-shw-node-wash-t110": ("wash_t110_area_m2", "wash_t110_capacity_m3", None, None),
        "vf-shw-node-sludge-t201": (
            "sludge_t201_area_m2",
            "sludge_t201_capacity_m3",
            "sludge_t201_initial_volume_m3",
            None,
        ),
    }
    for scope_id, fields in mapping.items():
        tank = profile.tank(scope_id)
        area_field, capacity_field, initial_field, band_field = fields
        if area_field is not None:
            overrides[area_field] = tank.area_m2
        if capacity_field is not None:
            overrides[capacity_field] = tank.capacity_m3
        if initial_field is not None:
            overrides[initial_field] = tank.initial_volume_m3
        if band_field is not None:
            overrides[band_field] = tuple(tank.level_band_m)
    return WholePlantScenario(
        **{**{name: getattr(base, name) for name in base.__slots__}, **overrides}
    )


def build_x3_participants(
    *,
    profile: X3Profile,
    contracts: WholePlantContracts,
    scenario: WholePlantScenario,
    run_id: str,
) -> dict[str, ScopeParticipant]:
    """Build the 16 admitted participants with the X3 geometry and 1-second ticks."""
    scope_contracts = {scope.scope_id: scope.raw for scope in contracts.scopes if scope.x2_admitted}
    if len(scope_contracts) != X3_EXPECTED_SCOPE_COUNT:
        raise WholePlantX3Error(
            f"X3 requires exactly {X3_EXPECTED_SCOPE_COUNT} admitted scope contracts, "
            f"found {len(scope_contracts)}"
        )
    common = {
        "workspace_id": SHWTP_WHOLE_PLANT_WORKSPACE_ID,
        "run_id": run_id,
        "scenario": scenario,
    }
    participants: dict[str, ScopeParticipant] = {
        "vf-shw-node-raw-source": RawSourceParticipant(scope_contracts["vf-shw-node-raw-source"], **common),
        "vf-shw-node-raw-intake": RawIntakeParticipant(scope_contracts["vf-shw-node-raw-intake"], **common),
        "vf-shw-node-t100": T100Participant(
            scope_contracts["vf-shw-node-t100"],
            area_m2=scenario.t100_area_m2,
            capacity_m3=scenario.t100_capacity_m3,
            initial_volume_m3=scenario.t100_initial_volume_m3,
            level_band=scenario.t100_level_band_m,
            **common,
        ),
        "vf-shw-node-t101": T101Participant(
            scope_contracts["vf-shw-node-t101"],
            capacity_m3=scenario.t101_contact_volume_m3,
            initial_volume_m3=profile.tank("vf-shw-node-t101").initial_volume_m3,
            **common,
        ),
        "vf-shw-node-t102": T102Participant(scope_contracts["vf-shw-node-t102"], **common),
        "vf-shw-node-t103": T103Participant(scope_contracts["vf-shw-node-t103"], **common),
        "vf-shw-node-t104": T104Participant(
            scope_contracts["vf-shw-node-t104"],
            capacity_m3=scenario.t104_floc_volume_m3,
            initial_volume_m3=profile.tank("vf-shw-node-t104").initial_volume_m3,
            **common,
        ),
        "vf-shw-node-t105": ClarifierParticipant(
            scope_contracts["vf-shw-node-t105"],
            area_m2=scenario.t105_area_m2,
            capacity_m3=scenario.t105_capacity_m3,
            initial_volume_m3=scenario.t105_initial_volume_m3,
            **common,
        ),
        "vf-shw-node-t106": FilterParticipant(
            scope_contracts["vf-shw-node-t106"],
            capacity_m3=scenario.t106_capacity_m3,
            initial_volume_m3=scenario.t106_initial_volume_m3,
            **common,
        ),
        "vf-shw-node-t108": T108Participant(
            scope_contracts["vf-shw-node-t108"],
            area_m2=scenario.t108_area_m2,
            capacity_m3=scenario.t108_capacity_m3,
            initial_volume_m3=scenario.t108_initial_volume_m3,
            level_band=scenario.t108_level_band_m,
            **common,
        ),
        "vf-shw-node-wash-t110": RecoveryParticipant(
            scope_contracts["vf-shw-node-wash-t110"],
            capacity_m3=scenario.wash_t110_capacity_m3,
            area_m2=scenario.wash_t110_area_m2,
            **common,
        ),
        "vf-shw-node-dist-p108": DistributionParticipant(
            scope_contracts["vf-shw-node-dist-p108"],
            fallback_speed_pct=_dist_fallback_speed(scope_contracts["vf-shw-node-dist-p108"]),
            **common,
        ),
        "vf-shw-node-network-demand": NetworkDemandParticipant(
            scope_contracts["vf-shw-node-network-demand"], **common
        ),
        "vf-shw-node-chem-dosing": ChemDosingParticipant(
            scope_contracts["vf-shw-node-chem-dosing"], **common
        ),
        "vf-shw-node-sludge-t201": SludgeSinkParticipant(
            scope_contracts["vf-shw-node-sludge-t201"],
            capacity_m3=scenario.sludge_t201_capacity_m3,
            initial_volume_m3=scenario.sludge_t201_initial_volume_m3,
            area_m2=scenario.sludge_t201_area_m2,
            **common,
        ),
        "vf-shw-node-line2-aggregate": Line2AggregateParticipant(
            scope_contracts["vf-shw-node-line2-aggregate"], **common
        ),
    }
    if set(participants) != set(SCOPE_PATHS):
        raise WholePlantX3Error("the X3 participant set must be exactly the 16 admitted scopes")
    return participants


@dataclass(slots=True)
class X3WaterLedger:
    """Cumulative X3 water ledger (physical conservation vs reconciled accounting)."""

    plant_in_m3: float = 0.0
    plant_out_m3: float = 0.0
    process_loss_m3: float = 0.0
    process_loss_observed_m3: float = 0.0
    process_loss_audit_failures: int = 0
    overflow_m3: float = 0.0
    created_water_m3: float = 0.0
    in_transit_m3: float = 0.0
    pipeline_inventory_m3: float = 0.0
    information_m3: float = 0.0
    source_availability_m3: float = 0.0


@dataclass(slots=True)
class X3EnergyLedger:
    """Energy integration (J) of the declared powered pumps only (D6)."""

    total_j: float = 0.0
    per_pump_j: dict[str, float] = field(default_factory=dict)
    per_pump_hydraulic_j: dict[str, float] = field(default_factory=dict)
    per_pump_seconds: dict[str, float] = field(default_factory=dict)
    unavailable: tuple[str, ...] = ()

    def integrate(self, point: PumpOperatingPoint, dt_s: float) -> float:
        """E = P_elec * dt; an OFF pump integrates exactly zero energy."""
        if point.off:
            return 0.0
        electric = point.electric_w * dt_s
        self.total_j += electric
        self.per_pump_j[point.pump_id] = self.per_pump_j.get(point.pump_id, 0.0) + electric
        self.per_pump_hydraulic_j[point.pump_id] = (
            self.per_pump_hydraulic_j.get(point.pump_id, 0.0) + point.hydraulic_w * dt_s
        )
        self.per_pump_seconds[point.pump_id] = self.per_pump_seconds.get(point.pump_id, 0.0) + dt_s
        return electric

    def to_dict(self, units_note: str) -> dict[str, Any]:
        return {
            "total_energy_j": round(self.total_j, 6),
            "total_energy_kwh": round(self.total_j / 3_600_000.0, 9),
            "per_pump_electric_j": {
                key: round(value, 6) for key, value in sorted(self.per_pump_j.items())
            },
            "per_pump_hydraulic_j": {
                key: round(value, 6) for key, value in sorted(self.per_pump_hydraulic_j.items())
            },
            "per_pump_running_s": {
                key: round(value, 6) for key, value in sorted(self.per_pump_seconds.items())
            },
            "unavailable_energy": list(self.unavailable),
            "units_note": units_note,
        }


class WholePlantX3Runtime:
    """The X3 whole-plant runtime: 1-second physical ticks + two PI loops."""

    def __init__(
        self,
        *,
        profile: X3Profile,
        contracts: WholePlantContracts,
        run_id: str,
        scenario: WholePlantScenario | None = None,
    ) -> None:
        self.profile = profile
        self.contracts = contracts
        self.run_id = run_id
        self.scenario = scenario or build_x3_scenario(profile)
        control_entries = {control.controller_id: control.raw for control in contracts.controls}
        self.control_layer = X3ControlLayer(profile=profile, control_entries=control_entries)
        self.participants = build_x3_participants(
            profile=profile, contracts=contracts, scenario=self.scenario, run_id=run_id
        )
        self.wiring = _wiring(contracts)
        self.workspace = build_shwtp_whole_plant_workspace()
        self.graph = _build_graph(self.wiring)
        self.overlay = _build_overlay(contracts)
        self.provenance_index = _provenance_index(contracts)
        self.coordinator = Coordinator(workspace=self.workspace, graph=self.graph)
        for scope_id in sorted(self.participants):
            self.coordinator.register(self.participants[scope_id])
        self._scope_infos = whole_plant_scope_metadata(contracts)
        self.bindings = tuple(
            {
                "binding_id": spec.binding_id,
                "source_scope": spec.source_scope_id,
                "target_scope": spec.target_scope_id,
                "source_port": spec.source_port,
                "target_port": spec.target_port,
                "information": bool(spec.information),
            }
            for spec in self.wiring
        )
        self.source_ports = {spec.binding_id: spec.source_port for spec in self.wiring}
        #: D4 budget allocation applies to WATER edges only: information bindings
        #: carry no water and are never allocated (they stay uncapped signals).
        self.water_bindings = tuple(
            binding for binding in self.bindings if not binding["information"]
        )
        self.pump_models = {
            pump.pump_id: PumpModel(pump, profile.units) for pump in profile.pumps.values()
        }
        self.water = X3WaterLedger()
        self.energy = X3EnergyLedger(unavailable=profile.energy_unavailable)
        self._tick_index = 0
        self._network_delivered_m3 = 0.0
        self._transfers: tuple[dict, ...] = ()
        self._seen_windows: set[str] = set()
        self._control: X3ControlEvaluation | None = None
        self._allocation: TickAllocation | None = None
        self._balance_baseline: dict[str, Any] | None = None
        #: CAPACITY points of the current tick: allocation/envelope statement ONLY
        #: (never an energy measurement, SA C01-2)
        self._pump_capacity_points: dict[str, PumpOperatingPoint] = {}
        #: REALIZED points of the current tick, from the committed achieved throughput
        self._pump_points: dict[str, PumpOperatingPoint] = {}
        #: actual commanded speed of the tick whose realized points were evaluated
        self._tick_speeds: dict[str, float] = {}
        #: per-tick realized operating data (actual Q, speed, H/Hreq, power, energy)
        self._energy_trace: list[dict[str, Any]] = []
        self._energy_realized_trace: dict[str, Any] = {}
        self._feedback: dict[str, Any] = {}
        self._alarms: set[str] = set()
        self._record_transfers()
        self._feedback = self._committed_feedback()

    # ── identity / projections ─────────────────────────────────────────────
    @property
    def scopes(self) -> tuple:
        return self._scope_infos

    @property
    def tick_index(self) -> int:
        return self._tick_index

    @property
    def communication_step_s(self) -> float:
        return self.profile.tick_s

    @property
    def coupling_policy(self) -> str:
        return self.profile.coupling_policy

    @property
    def model_driven_windows(self) -> bool:
        return True

    @property
    def model_label(self) -> str:
        """Human-readable identity of the canonical X3 execution profile."""
        return "SH-WTP X3 whole plant (1 s windows, two PI loops)"

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    def runtime_truth(self) -> dict:
        return {
            "model": X3_MODEL_SCHEMA,
            "profile_id": self.profile.profile_id,
            "profile_version": self.profile.version,
            "workspace_id": SHWTP_WHOLE_PLANT_WORKSPACE_ID,
            "run_id": self.run_id,
            "run_id_source": "attempt_context",
            "coupling_policy": self.coupling_policy,
            "tick_index": self._tick_index,
            "tick_s": self.profile.tick_s,
            "scope_count": len(self.participants),
            "active_c2_loop_ids": list(self.control_layer.active_c2_loop_ids),
            "deferred_loops": dict(sorted(self.profile.deferred_loops.items())),
            "whole_plant_runtime_implementation": WHOLE_PLANT_RUNTIME_IMPLEMENTATION,
            "whole_plant_runtime_authorization": WHOLE_PLANT_RUNTIME_AUTHORIZATION,
            **AUTHORITY_LABELS,
        }

    def monitor_rows(self) -> tuple[dict, ...]:
        rows: list[dict] = []
        for info in self._scope_infos:
            participant = self.participants[info.scope_id]
            row = info.to_dict()
            row["time_s"] = round(participant.current_time_s, 6)
            values = dict(participant.monitor_values())
            values.update(AUTHORITY_LABELS)
            require_authority_labels(values, where=f"X3 monitor values for {info.scope_id!r}")
            row["values"] = values
            row["open_alarms"] = list(participant.open_alarms)
            require_authority_labels(row, where=f"X3 monitor row for {info.scope_id!r}")
            rows.append(row)
        return tuple(rows)

    def _c1_snapshot(self) -> dict[str, dict]:
        if self._control is None:
            return {}
        return {
            controller_id: dict(payload)
            for controller_id, payload in self._control.c1.detail.get("controllers", {}).items()
        }

    def control_rows(self) -> tuple[dict, ...]:
        snapshot = self._c1_snapshot()
        c1_alarms = self.control_layer.c1.open_alarms()
        rows: list[dict] = []
        for controller_id in self.control_layer.c1.active_controller_ids:
            payload = snapshot.get(controller_id, {})
            rows.append(
                {
                    "controller_id": controller_id,
                    "control_class": "C1",
                    "active_in_x3": True,
                    "outputs": dict(payload.get("outputs", {})),
                    "detail": dict(payload.get("detail", {})),
                    "open_alarms": list(c1_alarms.get(controller_id, ())),
                    **AUTHORITY_LABELS,
                }
            )
        statuses = self._control.pi_statuses if self._control is not None else {}
        for loop_id in self.control_layer.active_c2_loop_ids:
            status = statuses.get(loop_id)
            config = self.profile.controllers[loop_id]
            rows.append(
                {
                    "controller_id": loop_id,
                    "control_class": "C2",
                    "active_in_x3": True,
                    "mv_signal": config.mv_signal,
                    "pv_signal": config.pv_signal,
                    "sp": status.sp if status else config.sp,
                    "sp_admissible": list(config.sp_admissible),
                    "mode": status.mode if status else "AUTO",
                    "pv": status.pv if status else None,
                    "error": status.error if status else None,
                    "requested_mv": status.requested_mv if status else None,
                    "applied_mv": status.applied_mv if status else None,
                    "pi_output_mv": status.pi_output_mv if status else None,
                    "applied_by": status.applied_by if status else "pi",
                    "arbitration": (
                        self._control.arbitration.get(config.mv_signal, "")
                        if self._control is not None
                        else ""
                    ),
                    "integral": status.integral if status else 0.0,
                    "saturated": status.saturated if status else False,
                    "limitation_reason": status.limitation_reason if status else "not_evaluated",
                    "alarm": status.alarm if status else None,
                    **AUTHORITY_LABELS,
                }
            )
        return tuple(rows)

    def transfer_records(self) -> tuple[dict, ...]:
        return self._transfers

    def provenance_records(self) -> tuple[dict, ...]:
        return tuple(
            {
                "binding_id": spec.binding_id,
                "graph_edge_id": spec.graph_edge_id,
                "source_scope_id": spec.source_scope_id,
                "target_scope_id": spec.target_scope_id,
                "information": bool(spec.information),
                "information_kind": "contract_declared_input" if spec.information else None,
                **self.provenance_index.get(spec.binding_id, {}),
                **AUTHORITY_LABELS,
            }
            for spec in self.wiring
        )

    def assumed_topology(self) -> tuple[dict, ...]:
        return tuple(
            {
                "scope": row["source_scope_id"],
                "target_scope": row["target_scope_id"],
                "binding_id": row["binding_id"],
                "assumption_id": row.get("assumption_id"),
                "reversible": True,
                **AUTHORITY_LABELS,
            }
            for row in self.provenance_records()
            if row.get("edge_category") == "vf_scenario_assumption"
        )

    # ── execution ──────────────────────────────────────────────────────────
    def _reject_invalid_state(self) -> None:
        for scope_id, participant in self.participants.items():
            volume = float(getattr(participant, "_volume_m3", 0.0))
            if not math.isfinite(volume) or volume < -CREATED_WATER_TOLERANCE_M3:
                raise WholePlantX3Error(
                    f"invalid state before stepping: {scope_id} volume={volume!r}"
                )

    def _scope_snapshot(self) -> dict[str, dict[str, Any]]:
        snapshot: dict[str, dict[str, Any]] = {}
        dt_h = self.profile.tick_s / 3600.0
        for scope_id, participant in self.participants.items():
            storage = bool(getattr(participant, "storage", False))
            queued = sum(
                float(transfer.payload.get("flow_m3h", 0.0))
                for transfer in getattr(participant, "_inbound", ())
            ) * dt_h
            state: dict[str, Any] = {
                "volume_m3": float(getattr(participant, "_volume_m3", 0.0)),
                "queued_inbound_m3": queued,
                "storage": storage,
            }
            if storage:
                state["capacity_m3"] = float(getattr(participant, "capacity_m3", 0.0))
            if scope_id == "vf-shw-node-raw-source":
                state["source_availability_m3_s"] = self.scenario.raw_flow_sp_m3h / 3600.0
            snapshot[scope_id] = state
        return snapshot

    def _committed_feedback(self) -> dict[str, Any]:
        """The committed-state feedback the C1/PI layers read (X2-compatible)."""
        participants = self.participants

        def values(scope_id: str) -> Mapping[str, Any]:
            return participants[scope_id].monitor_values()

        return {
            "screen_dp": values("vf-shw-node-raw-intake")["screen_dp_kpa"],
            "raw_source_available": True,
            "t100_intake_enable": bool(
                self._control.commands.get("intake_enable", True) if self._control else True
            ),
            "t100_level": values("vf-shw-node-t100")["level_m"],
            "level_band": self._level_band_payload("t100"),
            "contact_time_s": values("vf-shw-node-t101")["contact_time_s"],
            "l1_feed_flow_m3h": values("vf-shw-node-t100")["outflows_m3h"]["vf-shw-node-t101"],
            "plant_flow_m3h": values("vf-shw-node-t100")["withdrawal_m3h"],
            "settled_volume_m3": values("vf-shw-node-t105")["volume_m3"],
            "settled_volume_high_m3": self.scenario.t105_settled_volume_high_m3,
            "filter_dp_kpa": values("vf-shw-node-t106")["filter_dp_kpa"],
            "filtered_turbidity_proxy_ntu": values("vf-shw-node-t106")["turbidity_ntu"],
            # D5: the flow PI PV is the DELAYED DELIVERED inlet flow on T105->T106
            "f106_inlet_flow_m3h": values("vf-shw-node-t106")["inflow_m3h"],
            "filter_inlet_flow_m3h": values("vf-shw-node-t106")["inflow_m3h"],
            "wash_water_level_sufficient": (
                values("vf-shw-node-wash-t110")["volume_m3"]
                < 0.9 * self.scenario.wash_t110_capacity_m3
            ),
            "t108_level": values("vf-shw-node-t108")["level_m"],
            "level_band_t108": self._level_band_payload("t108"),
            "sludge_tank_volume_m3": values("vf-shw-node-sludge-t201")["volume_m3"],
            "sludge_tank_high_m3": self.scenario.sludge_t201_high_m3,
            "scenario_split_fraction": self.scenario.line2_split_fraction,
            "line2_capacity_available": True,
            "chemical_tank_ok": values("vf-shw-node-chem-dosing")["tank_level_l"] > 0.0,
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
            "scope_records": [
                {"scope_id": scope_id, "values": participants[scope_id].monitor_values()}
                for scope_id in sorted(participants)
            ],
        }

    def _level_band_payload(self, which: str) -> dict:
        band = self.scenario.t100_level_band_m if which == "t100" else self.scenario.t108_level_band_m
        initial = (
            self.scenario.t100_initial_volume_m3 / self.scenario.t100_area_m2
            if which == "t100"
            else self.scenario.t108_initial_volume_m3 / self.scenario.t108_area_m2
        )
        return {"LALL": band[0], "LAL": band[1], "LAH": band[2], "LAHH": band[3], "initial": initial}

    def _pump_speeds(self) -> dict[str, float]:
        """The ACTUAL commanded speed of each declared powered pump (D6).

        DIST keeps its accepted declared fixed 80 % command (its pressure PI is
        explicitly deferred): when no C1/PI signal is published the participant's
        own declared fallback speed applies, exactly as in the accepted X2 model.
        """
        commands = self._control.commands if self._control is not None else {}
        dist_scope = self.participants["vf-shw-node-dist-p108"]
        dist_signal = commands.get("hsp_speed_cmd")
        dist_speed = (
            float(dist_signal)
            if dist_signal is not None
            else float(getattr(dist_scope, "fallback_speed_pct", 0.0))
        )
        return {
            "raw-intake-pump": float(commands.get("pump_speed_cmd", 0.0)),
            "t108-transfer-pump": float(commands.get(self.control_layer.pump_signal, 0.0)),
            "dist-hsp": dist_speed,
        }

    def _requested_edge_flows(self, speeds: Mapping[str, float]) -> dict[str, float]:
        """D5/D6: declared process requests + valve/pump feasibility (D4 inputs).

        Passive edges request their declared capacity. The two edges whose process
        law is fully determined by COMMITTED state (the accepted T100 LINE1/LINE2
        split and the resulting LINE2 delivery) request the flow that law will
        actually produce, so a branch never reserves shared downstream capacity
        far above what it can carry (an inflated reservation would starve the
        parallel branches of the same header). The declared controlled elements
        (the T106 inlet valve and the three powered pumps) request their
        physically achievable throughput.
        """
        commands = self._control.commands if self._control is not None else {}
        valve_pct = float(commands.get(self.control_layer.valve_signal, 0.0))
        valve = self.profile.valves["vf-shw-node-t106"]
        requested: dict[str, float] = {
            binding["binding_id"]: self.profile.edge(binding["binding_id"]).max_flow_m3_s
            for binding in self.water_bindings
        }
        # accepted T100 law (volume_balance_first_order_v1), evaluated on committed state
        t100 = self.participants["vf-shw-node-t100"].monitor_values()
        dt_h = self.profile.tick_s / 3600.0
        available_rate = (float(t100["volume_m3"]) / dt_h) if dt_h > 0 else 0.0
        intake_rate = float(t100["inflow_m3h"])
        demand = _nonneg_float(commands.get("line1_demand_m3h", self.scenario.line1_demand_m3h))
        split = _fraction(commands.get("line2_split_fraction", self.scenario.line2_split_fraction))
        l1_feed = min(demand, available_rate + intake_rate)
        l2_feed = min(split * l1_feed, max(0.0, available_rate + intake_rate - l1_feed))
        requested["vf-shw-edge-t100-l1"] = min(
            requested["vf-shw-edge-t100-l1"], l1_feed / 3600.0
        )
        requested["vf-shw-edge-t100-line2"] = min(
            requested["vf-shw-edge-t100-line2"], l2_feed / 3600.0
        )
        requested["vf-shw-edge-line2-dist"] = min(
            requested["vf-shw-edge-line2-dist"],
            l2_feed * (1.0 - self.scenario.line2_loss_fraction) / 3600.0,
        )
        requested["vf-shw-edge-t105-t106"] = (valve_pct / 100.0) * valve.q_valve_max_m3_s
        points: dict[str, PumpOperatingPoint] = {}
        for pump_id, speed_pct in speeds.items():
            model = self.pump_models[pump_id]
            points[pump_id] = model.operating_point(speed_pct, model.pump.q_rated_m3_s)
        # CAPACITY statement only: the energy ledger uses the realized points below
        self._pump_capacity_points = points
        requested["vf-shw-edge-intake-t100"] = points["raw-intake-pump"].flow_m3_s
        requested["vf-shw-edge-t108-dist"] = points["t108-transfer-pump"].flow_m3_s
        requested["vf-shw-edge-dist-demand"] = points["dist-hsp"].flow_m3_s
        return requested

    def run_window(self, window_id: str) -> WindowOutcome:
        """Execute one deterministic 1-second X3 tick: allocate -> step -> commit."""
        if not isinstance(window_id, str) or not window_id.strip():
            raise WholePlantX3Error("window_id must be a non-empty str")
        if window_id in self._seen_windows:
            raise WholePlantX3Error(
                f"window {window_id!r} has already been executed by this X3 instance"
            )
        self._reject_invalid_state()
        tick = self._tick_index + 1
        snapshot = self._scope_snapshot()
        feedback = self._feedback
        inlet_flow_m3_s = (
            float(self.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"]) / 3600.0
        )
        t108_level_m = float(self.participants["vf-shw-node-t108"].monitor_values()["level_m"])
        self._control = self.control_layer.evaluate(
            feedback,
            inlet_flow_m3_s=inlet_flow_m3_s,
            t108_level_m=t108_level_m,
            trips={"f106_inlet_path_interlock": False, "t108_pump_interlock": False},
        )
        speeds = self._pump_speeds()
        self._tick_speeds = dict(speeds)
        requests = self._requested_edge_flows(speeds)
        allocation = allocate_tick(
            profile=self.profile,
            tick_index=tick,
            scope_state=snapshot,
            requested_m3_s=requests,
            bindings=self.water_bindings,
            source_ports=self.source_ports,
        )
        self._allocation = allocation
        commands: dict[str, Any] = dict(self._control.commands)
        commands[X3_OUT_BUDGET_KEY] = allocation.budget_m3h_by_scope_port()
        commands[X3_TICK_KEY] = self.profile.tick_s
        commands[X3_PROFILE_KEY] = self.profile.profile_id
        for participant in self.participants.values():
            participant.prepare_window(window_id, commands, feedback)
        outcome = self.coordinator.run_window(window_id, tick * self.profile.tick_s)
        if outcome.status != "completed":
            raise WholePlantX3Error(f"X3 tick {window_id!r} failed: {outcome.failure}")
        self._tick_index = tick
        self._seen_windows.add(window_id)
        self.control_layer.commit_tick(self._control)
        for alarm in self._control.alarms:
            self._alarms.add(alarm)
        self._record_transfers()
        self._update_water_ledger()
        self._update_energy()
        self._feedback = self._committed_feedback()
        return outcome

    def reset(self) -> None:
        self.control_layer.reset()
        for participant in self.participants.values():
            participant.reset()
        self.water = X3WaterLedger()
        self.energy = X3EnergyLedger(unavailable=self.profile.energy_unavailable)
        self._tick_index = 0
        self._transfers = ()
        self._seen_windows = set()
        self._control = None
        self._allocation = None
        self._pump_capacity_points = {}
        self._pump_points = {}
        self._tick_speeds = {}
        self._energy_trace = []
        self._energy_realized_trace = {}
        self._alarms = set()
        # a reset starts a NEW deterministic state: the pipeline bookkeeping and the
        # marked evaluation window must not carry anything over from the old run
        self._network_delivered_m3 = 0.0
        self._balance_baseline = None
        self._record_transfers()
        self._feedback = self._committed_feedback()

    # ── ledger / transfer bookkeeping ──────────────────────────────────────
    def _record_transfers(self) -> None:
        dt_h = self.profile.tick_s / 3600.0
        records: list[dict] = []
        for participant in sorted(self.participants.values(), key=lambda item: item.scope_id):
            for transfer in getattr(participant, "_inbound", ()):
                kind = WholePlantX2Runtime._transfer_kind(transfer.binding_id)
                flow_m3h = float(transfer.payload.get("flow_m3h", 0.0))
                records.append(
                    {
                        "transfer_id": transfer.transfer_id,
                        "run_id": transfer.run_id,
                        "binding_id": transfer.binding_id,
                        "transfer_kind": kind,
                        "water_m3": round(flow_m3h * dt_h, 12)
                        if kind == "physical_water"
                        else 0.0,
                        "source_scope": transfer.source.owner_scope.as_string(),
                        "target_scope": transfer.target.owner_scope.as_string(),
                        "source_port": transfer.source.port_id,
                        "target_port": transfer.target.port_id,
                        "window_id": transfer.window_id,
                        "simulation_time_s": transfer.simulation_time_s,
                        "payload": {
                            key: value for key, value in sorted(transfer.payload.items())
                        },
                        "provenance": self.provenance_index.get(transfer.binding_id, {}),
                    }
                )
        self._transfers = tuple(sorted(records, key=lambda row: row["transfer_id"]))

    @property
    def in_transit_m3(self) -> float:
        """Pending physical in-transit inventory of the current window.

        Every transfer emitted this window is consumed by its target at the NEXT
        tick, so it is still physically in transit at the end of this window --
        including the DIST discharge that has not yet reached the demand sink.
        The value is deliberately NOT re-rounded here: the participants integrate
        the same float flow, and re-rounding the inventory would inject a
        per-tick mismatch into the conservation identity.
        """
        return sum(
            row["water_m3"]
            for row in self._transfers
            if row["transfer_kind"] == "physical_water"
        )

    @property
    def information_inventory_m3(self) -> float:
        dt_h = self.profile.tick_s / 3600.0
        return round(
            sum(
                float(row["payload"].get("flow_m3h", 0.0)) * dt_h
                for row in self._transfers
                if row["transfer_kind"] == "information"
            ),
            12,
        )

    @property
    def source_availability_m3(self) -> float:
        dt_h = self.profile.tick_s / 3600.0
        return round(
            sum(
                float(row["payload"].get("flow_m3h", 0.0)) * dt_h
                for row in self._transfers
                if row["transfer_kind"] == "source_availability_outside_boundary"
            ),
            12,
        )

    def _water_of(self, rows: Sequence[Mapping[str, Any]], binding_id: str) -> float:
        return sum(
            float(row["water_m3"])
            for row in rows
            if row["binding_id"] == binding_id and row["transfer_kind"] == "physical_water"
        )

    @property
    def pending_by_scope(self) -> dict[str, float]:
        """Per-scope change of the pipeline (conduit) holding in this window."""
        pending: dict[str, float] = {}
        for binding in self.bindings:
            for row in self._transfers:
                if row["transfer_kind"] != "physical_water":
                    continue
                if row["binding_id"] != binding["binding_id"]:
                    continue
                water = float(row["water_m3"])
                if binding["source_scope"] in PIPELINE_SCOPES:
                    pending[binding["source_scope"]] = (
                        pending.get(binding["source_scope"], 0.0) - water
                    )
                if binding["target_scope"] in PIPELINE_SCOPES:
                    pending[binding["target_scope"]] = (
                        pending.get(binding["target_scope"], 0.0) + water
                    )
        return {scope_id: value for scope_id, value in pending.items() if value != 0.0}

    def mark_balance_baseline(self) -> dict:
        """Mark the start of the conservation evaluation window (D8)."""
        report = self.balance_report()["plant_water"]
        self._balance_baseline = {
            "tick_index": self._tick_index,
            "residual_m3": float(report["residual_m3"]),
        }
        return dict(self._balance_baseline)

    def _update_water_ledger(self) -> None:
        dt_h = self.profile.tick_s / 3600.0
        current = self._transfers
        self.water.plant_in_m3 += self._water_of(current, INTAKE_BINDING_ID)
        # D8 pipeline accounting: the DIST discharge leaves the plant when the
        # demand sink CONSUMES it (one tick after the transfer was emitted), so
        # the emitted transfer is in-transit inventory rather than an early OUT.
        # The identity reads the RAW integrated quantity, never the display-rounded
        # monitor projection (which would inject a rounding drift every tick).
        delivered = float(self.participants["vf-shw-node-network-demand"]._volume_in_m3)
        self.water.plant_out_m3 += delivered - self._network_delivered_m3
        self._network_delivered_m3 = delivered
        self.water.plant_out_m3 += (
            float(self.participants["vf-shw-node-sludge-t201"]._processed_m3h) * dt_h
        )
        # a pass-through conduit holds exactly one window of committed water before
        # forwarding it: that physical holding is explicit inventory, never a leak
        for scope_id, value in self.pending_by_scope.items():
            self.water.pipeline_inventory_m3 += value
        line2 = self.participants["vf-shw-node-line2-aggregate"].monitor_values()
        self.water.process_loss_m3 += (
            line2["declared_loss_m3h"] + line2["capacity_spill_m3h"]
        ) * dt_h
        self.water.process_loss_observed_m3 += line2["observed_loss_m3h"] * dt_h
        if not line2["process_loss_audit_ok"]:
            self.water.process_loss_audit_failures += 1
        self.water.information_m3 += self.information_inventory_m3
        self.water.source_availability_m3 += self.source_availability_m3
        self.water.in_transit_m3 = self.in_transit_m3
        self.water.overflow_m3 = sum(
            participant._overflow_m3 for participant in self.participants.values()
        )
        self.water.created_water_m3 = sum(
            participant._shortfall_m3 for participant in self.participants.values()
        )

    def _realized_pump_points(self) -> dict[str, PumpOperatingPoint]:
        """SA C01-2: the operating point of the ACHIEVED pumped throughput.

        The capacity point of :meth:`_requested_edge_flows` is an allocation/envelope
        statement; the energy ledger must integrate what the pumps really moved. The
        actual throughput is read from the committed physical transfer records of THIS
        tick (``_water_of``), so a startup inventory limit, an empty source, a full
        receiver or a narrowed downstream capacity all show up as a smaller realized
        flow instead of a capacity-rated power.
        """
        dt_s = self.profile.tick_s
        points: dict[str, PumpOperatingPoint] = {}
        for pump_id, binding_id in sorted(PUMP_DISCHARGE_BINDINGS.items()):
            achieved_m3 = self._water_of(self._transfers, binding_id)
            achieved_m3_s = achieved_m3 / dt_s if dt_s > 0.0 else 0.0
            points[pump_id] = self.pump_models[pump_id].realized_point(
                self._tick_speeds.get(pump_id, 0.0), achieved_m3_s
            )
        return points

    def _update_energy(self) -> None:
        """Integrate energy from the REALIZED operating points (SA C01-2)."""
        points = self._realized_pump_points()
        self._pump_points = points
        rows: dict[str, Any] = {}
        total_delta_j = 0.0
        for pump_id, point in sorted(points.items()):
            delta = self.energy.integrate(point, self.profile.tick_s)
            total_delta_j += delta
            if not point.feasible:
                self._alarms.add(f"{pump_id}:motor_or_head_infeasible")
            capacity = self._pump_capacity_points.get(pump_id)
            rows[pump_id] = {
                "commanded_speed_pct": self._tick_speeds.get(pump_id, 0.0),
                "achieved_flow_m3_s": point.flow_m3_s,
                "achieved_flow_m3h": point.flow_m3h,
                "capacity_flow_m3h": capacity.flow_m3h if capacity else 0.0,
                "head_m": point.head_m,
                "required_head_m": point.required_head_m,
                "throttle_head_m": point.throttle_head_m,
                "hydraulic_w": point.hydraulic_w,
                "electric_w": point.electric_w,
                "motor_rating_w": point.motor_rating_w,
                "feasible": point.feasible,
                "energized": point.energized,
                "idle": point.idle,
                "off": point.off,
                "reason": point.reason,
                "energy_delta_j": delta,
            }
        self._energy_trace.append(
            {
                "tick_index": self._tick_index,
                "dt_s": self.profile.tick_s,
                "pumps": rows,
                "total_electric_w": round(
                    sum(row["electric_w"] for row in rows.values()), 9
                ),
                "total_hydraulic_w": round(
                    sum(row["hydraulic_w"] for row in rows.values()), 9
                ),
                "total_energy_delta_j": round(total_delta_j, 9),
            }
        )

    def energy_trace(self) -> tuple[dict[str, Any], ...]:
        """Per-tick realized operating data (actual Q, speed, H/Hreq, P, energy)."""
        return tuple(self._energy_trace)

    # ── reports ────────────────────────────────────────────────────────────
    def balance_report(self) -> dict:
        """Plant + per-scope water balance (SA Issue #98 section 2 identity).

        The plant identity is evaluated on ONE consistent basis, from tick zero:

        ``R(t) = [storage_flow_delta(t) + pipeline_inventory(t) + transit(t)]
                 - cumulative_in + cumulative_out - declared_losses``

        where ``storage_flow_delta`` is the storage change DERIVED FROM THE FLOWS
        each participant actually integrated (explicit overflow/shortfall included)
        rather than from the float state variable, and ``pipeline_inventory`` is the
        explicitly initialised holding of the pass-through conduits (zero at tick
        zero, because their committed state starts empty). ``residual_m3`` is this
        full-run residual and is authoritative; the state-based storage delta is
        reported next to it as an integration diagnostic.
        """
        storage_rows = [
            {**participant.balance(), **AUTHORITY_LABELS}
            for participant in self.participants.values()
            if getattr(participant, "storage", False)
        ]
        storage_state_delta = sum(
            participant._storage_volume() - getattr(participant, "_initial_volume_m3", 0.0)
            for participant in self.participants.values()
            if getattr(participant, "storage", False)
        )
        storage_flow_delta = sum(
            participant._volume_in_m3 - participant._volume_out_m3
            for participant in self.participants.values()
            if getattr(participant, "storage", False)
        )
        created = sum(
            participant._shortfall_m3 for participant in self.participants.values()
        )
        overflow = sum(
            participant._overflow_m3 for participant in self.participants.values()
        )
        stored_delta = storage_flow_delta + created
        integration_gap = storage_state_delta - storage_flow_delta - created + overflow
        inside = stored_delta + self.in_transit_m3
        residual = round(
            inside
            - self.water.plant_in_m3
            + self.water.plant_out_m3
            + self.water.process_loss_m3,
            12,
        )
        baseline = self._balance_baseline
        window_residual = round(
            residual - float(baseline["residual_m3"]) if baseline else residual, 12
        )
        scale = max(
            1.0,
            abs(self.water.plant_in_m3)
            + abs(self.water.plant_out_m3)
            + abs(stored_delta),
        )
        tolerance = round(
            PLANT_WATER_TOLERANCE_RELATIVE * scale
            + PLANT_WATER_TOLERANCE_ABSOLUTE_M3
            + X3_LEDGER_ROUNDING_PER_TICK_M3 * self._tick_index,
            15,
        )
        created_ok = created <= CREATED_WATER_TOLERANCE_M3
        audit_ok = (
            self.water.process_loss_audit_failures == 0
            and abs(self.water.process_loss_m3 - self.water.process_loss_observed_m3) <= tolerance
        )
        # physical validity is asserted on the FULL RUN from tick zero: a
        # differenced window after warm-up can supplement the diagnosis but can
        # never certify a run whose full-run conservation failed. The storage
        # INTEGRATION gap is a separate physical claim: a state stock that the
        # integrated flows do not explain (a duplicated or missing initialisation,
        # a hidden clamp) must fail even when the flow-based residual still closes.
        integration_ok = abs(integration_gap) <= tolerance
        physical_valid = (
            abs(residual) <= tolerance and integration_ok and created_ok and audit_ok
        )
        window_valid = (
            abs(window_residual) <= tolerance and integration_ok and created_ok and audit_ok
        )
        return {
            "tick_index": self._tick_index,
            "storage_balances": storage_rows,
            "plant_water": {
                "basis": (
                    "control volume = pumped-intake discharge .. network/sludge discharge; "
                    "1-second ticks; water inside = storage + physical in-transit"
                ),
                "plant_in_m3": round(self.water.plant_in_m3, 9),
                "plant_out_m3": round(self.water.plant_out_m3, 9),
                "stored_delta_m3": round(stored_delta, 12),
                "storage_flow_delta_m3": round(storage_flow_delta, 12),
                "storage_state_delta_m3": round(storage_state_delta, 12),
                "storage_integration_gap_m3": round(integration_gap, 12),
                "storage_integration_gap_within_rounding": integration_ok,
                "transit_inventory_m3": round(self.in_transit_m3, 9),
                "pipeline_inventory_m3": round(self.water.pipeline_inventory_m3, 9),
                "pipeline_inventory_note": (
                    "the explicitly declared holding of the pass-through conduits at the "
                    "current tick (empty at tick zero); it is REPORTED inventory, never an "
                    "identity term: the pending-slug transit inventory already carries the "
                    "water the conduits hold"
                ),
                "water_inside_m3": round(stored_delta + self.in_transit_m3, 9),
                "process_loss_m3": round(self.water.process_loss_m3, 9),
                "process_loss_observed_m3": round(self.water.process_loss_observed_m3, 9),
                "process_loss_declared_law_plus_spill": audit_ok,
                "process_loss_audit_failures": self.water.process_loss_audit_failures,
                "overflow_m3": overflow,
                "shortfall_m3": created,
                "created_water_diagnostic_m3": created,
                "created_water_tolerance_m3": CREATED_WATER_TOLERANCE_M3,
                "created_water_within_rounding": created_ok,
                "information_inventory_m3": round(self.water.information_m3, 9),
                "source_availability_m3": round(self.water.source_availability_m3, 9),
                "residual_m3": residual,
                "closure_m3": residual,
                "window_residual_m3": window_residual,
                "residual_basis": (
                    "R(t) = [storage_flow_delta + created_water + in_transit] - cumulative_in "
                    "+ cumulative_out - declared_losses, evaluated from tick zero; "
                    "storage_flow_delta is derived from the flows the participants "
                    "integrated, in_transit is the pending-slug inventory of the current "
                    "tick (empty at tick zero)"
                ),
                "window_basis": (
                    "supplementary diagnostic: window residual = the same identity "
                    "differenced over the marked evaluation window; it can never clear a "
                    "failed full-run residual"
                ),
                "evaluation_window_start_tick": int(baseline["tick_index"]) if baseline else 0,
                "window_physical_valid": window_valid,
                "full_run_authoritative": True,
                "tolerance_m3": tolerance,
                "tolerance_basis": (
                    "relative + absolute + per-tick deterministic rounding allowance "
                    f"({X3_LEDGER_ROUNDING_PER_TICK_M3!r} m3/tick)"
                ),
                "conserved": physical_valid,
                "physical_valid": physical_valid,
                "accounting_reconciled": abs(residual - created) <= tolerance,
                "accounting_note": (
                    "accounting_reconciled subtracts the created-water diagnostic and is "
                    "NOT a physical-conservation claim; physical_valid carries the "
                    "full-run identity with no compensation term"
                ),
                "bounded": physical_valid,
            },
            "max_storage_residual_m3": max(
                (abs(row["residual_m3"]) for row in storage_rows), default=0.0
            ),
            **AUTHORITY_LABELS,
        }

    def energy_report(self) -> dict:
        report = self.energy.to_dict(
            "P_elec = P_hyd(Hreq)/eta_total + no_load (declared synthetic, realized on the "
            "achieved pumped throughput); P_hyd uses the head actually delivered to the "
            "water; J -> kWh at the named boundary"
        )
        report["operating_point_basis"] = "realized_actual_pumped_throughput"
        report["idle_loss_rule"] = (
            "an OFF pump integrates exactly zero flow and zero energy; an energized pump "
            "that moves no water integrates only the declared no_load_w idle loss with no "
            "useful hydraulic power; the excess available head stays a recorded "
            "throttle_head_m dissipation instead of invented useful power"
        )
        report["pump_operating_points"] = {
            pump_id: {
                "speed_pct": point.speed_fraction * 100.0,
                "flow_m3_s": point.flow_m3_s,
                "flow_m3h": point.flow_m3h,
                "head_m": point.head_m,
                "required_head_m": point.required_head_m,
                "throttle_head_m": point.throttle_head_m,
                "hydraulic_w": point.hydraulic_w,
                "electric_w": point.electric_w,
                "motor_rating_w": point.motor_rating_w,
                "feasible": point.feasible,
                "reason": point.reason,
                "energized": point.energized,
                "idle": point.idle,
                "off": point.off,
            }
            for pump_id, point in sorted(self._pump_points.items())
        }
        report["allocation_capacity_points"] = {
            pump_id: {
                "speed_pct": point.speed_fraction * 100.0,
                "flow_m3_s": point.flow_m3_s,
                "flow_m3h": point.flow_m3h,
                "feasible": point.feasible,
                "reason": point.reason,
                "energized": point.energized,
                "off": point.off,
            }
            for pump_id, point in sorted(self._pump_capacity_points.items())
        }
        realized = [row for row in self._energy_trace]
        infeasible = [
            {"tick_index": row["tick_index"], "pumps": sorted(
                pump_id for pump_id, data in row["pumps"].items() if not data["feasible"]
            )}
            for row in realized
            if any(not data["feasible"] for data in row["pumps"].values())
        ]
        report["realized_feasibility"] = {
            "ticks_observed": len(realized),
            "infeasible_ticks": len(infeasible),
            "first_infeasible": infeasible[:5],
            "all_realized_points_feasible": not infeasible,
        }
        report["idle_energy_j"] = round(
            sum(
                data["electric_w"] * row["dt_s"]
                for row in realized
                for data in row["pumps"].values()
                if data["idle"]
            ),
            6,
        )
        report["actual_pumped_energy_j"] = round(
            sum(
                data["energy_delta_j"]
                for row in realized
                for data in row["pumps"].values()
                if not data["idle"]
            ),
            6,
        )
        report.update(AUTHORITY_LABELS)
        return report

    def control_report(self) -> dict:
        if self._control is None:
            return {
                "tick_index": self._tick_index,
                "pi": {},
                "arbitration": {},
                "active_c2_loop_ids": list(self.control_layer.active_c2_loop_ids),
                **AUTHORITY_LABELS,
            }
        payload = self._control.to_dict()
        payload["active_c2_loop_ids"] = list(self.control_layer.active_c2_loop_ids)
        payload["c1_active_controller_ids"] = list(self.control_layer.c1.active_controller_ids)
        payload.update(AUTHORITY_LABELS)
        return payload

    def budget_report(self) -> dict:
        if self._allocation is None:
            return {"tick_index": self._tick_index, "budgets": {}, **AUTHORITY_LABELS}
        allocation = self._allocation
        return {
            "tick_index": allocation.tick_index,
            "dt_s": allocation.dt_s,
            "budgets": {
                binding_id: {
                    "source_scope": budget.source_scope,
                    "target_scope": budget.target_scope,
                    "requested_m3_s": budget.requested_m3_s,
                    "budget_m3_s": budget.budget_m3_s,
                    "limiting_factor": budget.limiting_factor,
                }
                for binding_id, budget in sorted(allocation.budgets.items())
            },
            "source_available_m3_s": {
                key: (None if value == math.inf else value)
                for key, value in sorted(allocation.source_available_m3_s.items())
            },
            "receiver_headroom_m3_s": {
                key: (None if value == math.inf else value)
                for key, value in sorted(allocation.receiver_headroom_m3_s.items())
            },
            "trunk_remaining_m3_s": dict(sorted(allocation.trunk_used_m3_s.items())),
            "queued_volume_m3": allocation.queued_volume_m3,
            "diagnostics": list(allocation.diagnostics),
            **AUTHORITY_LABELS,
        }

    def alarms(self) -> dict[str, tuple[str, ...]]:
        payload = {
            scope_id: participant.open_alarms
            for scope_id, participant in self.participants.items()
            if participant.open_alarms
        }
        for controller_id, alarms in self.control_layer.c1.open_alarms().items():
            if alarms:
                payload[f"control:{controller_id}"] = alarms
        if self._alarms:
            payload["x3_model"] = tuple(sorted(self._alarms))
        return payload


def build_shwtp_whole_plant_x3(
    *,
    run_id: str,
    profile: X3Profile | None = None,
    contracts: WholePlantContracts | None = None,
    scenario: WholePlantScenario | None = None,
) -> WholePlantX3Runtime:
    """Build the X3 whole-plant runtime (1-second ticks, two PI loops)."""
    resolved_profile = profile or load_x3_profile()
    resolved_contracts = contracts or load_whole_plant_contracts()
    return WholePlantX3Runtime(
        profile=resolved_profile,
        contracts=resolved_contracts,
        run_id=run_id,
        scenario=scenario,
    )
