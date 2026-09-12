"""VF-DM-DEMO-ASSY-MES-02 — Six-sub-line MES contract bridge.

Uses the AUTHORITATIVE six-sub-line TIPA ASSY Docker runtime (/assy-demo) as
the VF source for the customer VF→MES demo.  This module is ADDITIVE: it
projects the runtime's authoritative facts through the EXISTING M5 pipeline
(RealityInput → ObservationService → ObservationRouter → MESProjection →
gateways).  No parallel simulation is created and the six-sub-line topology /
runtime are NOT rewritten.

Additive MES message surface (kept compatible with M6-INT-01 P0 facts):
  mes.execution_event      (OPERATION_COMPLETED, WIP_ENTERED, LINE_OUT,
                            DOWNTIME_START, DOWNTIME_END)
  mes.quality_result       (QUALITY_RESULT, AP11_FINAL_QC_PASS,
                            AP11_FINAL_QC_FAIL)
  mes.genealogy_relationship (AP04_JOIN)
  mes.release              (AP11_RELEASE)
  mes.run_status           (operational state: RUNNING → FAULT → STOPPED → RUNNING;
                            separate conveyor_state field, never the line status)
  mes.issue                (AP05_JAM EXCEPTION_RAISED / EXCEPTION_RESOLVED)
  mes.oee_summary          (per sub-line/run, reconciled)

Contract/provenance on every message: message_key, payload.idempotency_key ==
message_key, contract_version=tipa-assy-demo-v1, run_id=ASSY-SLxx:R<n>,
explicit subline_id, station_id where applicable, simulation_time_s,
deterministic non-null occurred_at, stable source event identity.

Deterministic demo fault (findings 1-3): the bridge derives an operational
state SEPARATE from conveyor state.  trigger_jam()/recover() on the control
surface drive a deterministic AP05_JAM lifecycle: RUNNING → FAULT → STOPPED →
RUNNING with exactly one DOWNTIME_START → DOWNTIME_END (120 s) derived from
the authoritative simulation clock.  Quality HOLD never becomes a line
fault/downtime.  LINE_OUT GOOD|REJECT and OEE are derived from authoritative
WIP/terminal-quality state (never hard-coded in the projection).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from virtual_factory.assembly.demo_composition import AssyDemoComposition
from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime,
    WipLifecycle,
)
from virtual_factory.assembly.operation_execution import (
    OperationResult,
    OperationState,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.integration.gateway import (
    DeliveryResult,
    DeliveryStatus,
    ObservationGatewayProtocol,
)
from virtual_factory.integration.gateways.memory import InMemoryObsGateway
from virtual_factory.observation.envelope import ObservationType
from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.policy import ObservationPolicy
from virtual_factory.observation.projection import ProjectedMessage
from virtual_factory.observation.projections.mes import MESProjection
from virtual_factory.observation.router import (
    ObservationRouter,
    ProjectionSubscription,
)
from virtual_factory.observation.service import (
    ObservationService,
    RealityInput,
)

# ═══════════════════════════════════════════════════════════
# Contract / provenance vocabulary
# ═══════════════════════════════════════════════════════════

CONTRACT_VERSION = "tipa-assy-demo-v1.1"
SOURCE_TYPE = "assy_runtime"
SOURCE_DOMAIN = "assy"
CATEGORY = "industrial_event"
MODEL_ID = "tipa_assy_demo"

# Fixed demo epoch: deterministic occurred_at = epoch + simulation_time_s.
DEMO_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def occurred_at_for(simulation_time_s: float) -> str:
    """Deterministic ISO-8601 (UTC) timestamp for a simulated time."""
    return (DEMO_EPOCH + timedelta(seconds=simulation_time_s)).isoformat()


# Common fields every MES-bound message must carry (allow-listed).
_COMMON = ("contract_version", "subline_id", "production_line_id", "plant_id")

# Events
EVENT_OPERATION_COMPLETED = "OPERATION_COMPLETED"
EVENT_AP04_JOIN = "AP04_JOIN"
EVENT_QUALITY_RESULT = "QUALITY_RESULT"
EVENT_AP11_FINAL_QC_PASS = "AP11_FINAL_QC_PASS"
EVENT_AP11_FINAL_QC_FAIL = "AP11_FINAL_QC_FAIL"
EVENT_AP11_RELEASE = "AP11_RELEASE"
EVENT_WIP_ENTERED = "WIP_ENTERED"
EVENT_LINE_OUT = "LINE_OUT"
EVENT_LINE_STATE_CHANGED = "LINE_STATE_CHANGED"
EVENT_EXCEPTION_RAISED = "EXCEPTION_RAISED"
EVENT_EXCEPTION_RESOLVED = "EXCEPTION_RESOLVED"
EVENT_DOWNTIME_START = "DOWNTIME_START"
EVENT_DOWNTIME_END = "DOWNTIME_END"
EVENT_OEE_SUMMARY = "OEE_SUMMARY"
EVENT_CHECKLIST_CONFIRMED = "CHECKLIST_CONFIRMED"
EVENT_MEASUREMENT_RESULT = "MEASUREMENT_RESULT"

# Stations whose authoritative outbound fact is NOT a generic operation
# completion (they emit genealogy / quality / final-QC / release instead).
_SPECIALIZED_STATIONS = frozenset({"AP04", "AP06", "AP08", "AP11"})

# Deterministic demo downtime (seconds) for the single confirmed AP05_JAM.
DEMO_DOWNTIME_S = 120.0
# Deterministic ideal cycle time for OEE performance (matches the accepted
# single-sub-line MES contract).
DEMO_IDEAL_CYCLE_S = 240.0

_KIND_OPERATION = 0
_KIND_GENEALOGY = 1
_KIND_QUALITY = 2
_KIND_FINAL_QC = 2
_KIND_RELEASE = 3
_KIND_WIP_ENTERED = 0
_KIND_LINE_OUT = 4


# ═══════════════════════════════════════════════════════════
# Observation points (default-deny FieldPolicy allow-lists)
# ═══════════════════════════════════════════════════════════

def _point(
    point_id: str,
    label: str,
    event_types: tuple[str, ...],
    extract: tuple[str, ...],
) -> ObservationPoint:
    """One ON_EVENT point scoped to the given authoritative event types."""
    return ObservationPoint(
        point_id=point_id,
        observation_type=ObservationType.EVENT,
        label=label,
        source_type=SOURCE_TYPE,
        source_filter={},
        trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT, event_types=event_types),
        fields=FieldPolicy(extract=_COMMON + extract),
        enabled=True,
    )


def build_assy_mes_observation_points() -> list[ObservationPoint]:
    """Declare the MES-02 outbound observation points (default-deny)."""
    return [
        _point(
            "assy2.run_status",
            "Operational line state (separate from conveyor state)",
            (EVENT_LINE_STATE_CHANGED,),
            ("event_type", "line_state", "conveyor_state", "reason_code",
             "simulation_time_s"),
        ),
        _point(
            "assy2.issue",
            "AP05_JAM exception raised/resolved",
            (EVENT_EXCEPTION_RAISED, EVENT_EXCEPTION_RESOLVED),
            ("event_type", "station_id", "wip_id", "reason_code",
             "simulation_time_s"),
        ),
        _point(
            "assy2.execution_event",
            "WIP entry / operation completion / LINE_OUT / downtime",
            (EVENT_WIP_ENTERED, EVENT_OPERATION_COMPLETED, EVENT_LINE_OUT,
             EVENT_DOWNTIME_START, EVENT_DOWNTIME_END),
            ("event_type", "station_id", "wip_id", "disposition",
             "attempt_number", "reason_code",
             "downtime_start_s", "downtime_end_s", "downtime_s",
             "simulation_time_s"),
        ),
        _point(
            "assy2.quality_result",
            "AP06/AP08/AP11 quality result per attempt",
            (EVENT_QUALITY_RESULT, EVENT_AP11_FINAL_QC_PASS,
             EVENT_AP11_FINAL_QC_FAIL),
            ("event_type", "station_id", "wip_id", "disposition",
             "attempt_number", "reason_code", "reason_source", "check_type",
             "is_terminal", "terminal_state",
             "execution_id", "record_id",
             "observations", "proposed_quality_result",
             "proposed_quality_reason", "simulation_time_s"),
        ),
        _point(
            "assy2.checklist_result",
            "AP03 checklist confirmed (checklist ≠ quality)",
            (EVENT_CHECKLIST_CONFIRMED,),
            ("event_type", "execution_id", "attempt_number", "status",
             "required_count", "completed_count", "items",
             "station_id", "wip_id", "source", "simulation_time_s"),
        ),
        _point(
            "assy2.measurement_result",
            "AP06 numerical measurement evidence per attempt",
            (EVENT_MEASUREMENT_RESULT,),
            ("event_type", "execution_id", "record_id", "attempt_number",
             "measurement_code", "value", "unit", "lower_limit",
             "upper_limit", "in_spec", "evidence_source",
             "station_id", "wip_id", "simulation_time_s"),
        ),
        _point(
            "assy2.genealogy",
            "AP04 assembly join genealogy",
            (EVENT_AP04_JOIN,),
            ("event_type", "child_wip_id", "parent_wip_ids",
             "relationship_type", "station_id", "wip_id", "simulation_time_s"),
        ),
        _point(
            "assy2.release",
            "AP11 RELEASE (distinct final disposition)",
            (EVENT_AP11_RELEASE,),
            ("event_type", "wip_id", "station_id", "release_time_s",
             "simulation_time_s"),
        ),
        _point(
            "assy2.oee_summary",
            "End-of-run OEE summary per sub-line/run",
            (EVENT_OEE_SUMMARY,),
            ("event_type", "planned_s", "run_s", "downtime_s",
             "ideal_cycle_s", "actual_count", "good_count", "reject_count",
             "availability", "performance", "quality", "oee",
             "simulation_time_s"),
        ),
    ]


# ═══════════════════════════════════════════════════════════
# AssyMesBridge
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyMesBridge:
    """Downstream MES contract bridge for the six-sub-line runtime.

    Reads authoritative runtime truth (read-only), derives operational state,
    exception lifecycle, downtime, LINE_OUT and OEE, and delivers idempotent
    MES-compatible ProjectedMessages exactly once per (run_id, source_event_id,
    gateway_id).  Never mutates simulation truth and never creates timing
    samples.
    """

    service: ObservationService
    router: ObservationRouter
    gateways: list[ObservationGatewayProtocol]
    model_id: str = MODEL_ID

    # R3 additive seam (canonical same-session output projection): when bound,
    # emitted messages carry the canonical parent-session identity and the
    # projection epoch.  Read-only metadata: it never changes runtime truth,
    # the demo lifecycle derivation or delivery idempotency.  Unbound → legacy
    # behaviour is byte-for-byte unchanged.
    canonical: Optional[Mapping[str, Any]] = None

    # run tracking (sub_line_id → generation)
    _run_generation: dict[str, int] = field(default_factory=dict)
    _last_sim_time: dict[str, float] = field(default_factory=dict)
    # per-gateway delivery checkpoint:
    #   run_id → set[(source_event_id, gateway_id)] already DELIVERED
    _delivered: dict[str, set[tuple[str, str]]] = field(default_factory=dict)
    # ordered outbound delivery trace (evidence, read-only consumers)
    _outbound: list[dict] = field(default_factory=list)

    # operational state per sub-line (separate from conveyor_state)
    _baseline_emitted: set[str] = field(default_factory=set)   # run_id
    # deterministic demo-fault lifecycle per sub-line
    _fault: dict[str, dict[str, Any]] = field(default_factory=dict)
    _jam_pending: set[str] = field(default_factory=set)
    _recover_pending: set[str] = field(default_factory=set)
    _downtime_confirmed: set[str] = field(default_factory=set)  # run_id
    _oee_emitted: set[str] = field(default_factory=set)          # run_id

    # R4 canonical fault read path: when the composition exposes the canonical
    # fault read model (``composition.faults``) this bridge only READS canonical
    # fault truth — it never owns simulation fault state. ``_canonical_faults``
    # is the last read model, ``_canonical_fault_emitted`` is emission
    # bookkeeping (idempotency), and ``_canonical_downtime`` feeds OEE.
    _canonical_faults: Optional[dict[str, dict[str, Any]]] = None
    _canonical_fault_emitted: dict[tuple[str, str], tuple] = field(
        default_factory=dict
    )
    _canonical_downtime: dict[tuple[str, str], float] = field(default_factory=dict)

    # ── Run identity ──

    def run_id_for(self, sub_line_id: str) -> str:
        """Stable run id per sub-line; generation bumps on reset."""
        gen = self._run_generation.get(sub_line_id, 1)
        return f"{sub_line_id}:R{gen}"

    def projection_epoch_for(self, sub_line_id: str) -> int:
        """Projection epoch (source generation) for a sub-line (R3).

        Subordinate projection metadata scoping message identity after a reset
        of the SAME canonical run id; never a run/lifecycle identity.
        """
        return self._run_generation.get(sub_line_id, 1)

    def reset_all(self) -> None:
        """Explicit reset: bump every sub-line generation and clear runtime
        bookkeeping so new runs never reuse idempotency keys."""
        for sl in ("ASSY-SL01", "ASSY-SL02", "ASSY-SL03", "ASSY-SL04",
                   "ASSY-SL05", "ASSY-SL06"):
            self._run_generation[sl] = self._run_generation.get(sl, 1) + 1
        self._last_sim_time.clear()
        self._fault.clear()
        self._jam_pending.clear()
        self._recover_pending.clear()
        self._baseline_emitted.clear()
        self._downtime_confirmed.clear()
        self._oee_emitted.clear()
        self._canonical_fault_emitted.clear()
        self._canonical_downtime.clear()

    # ── Control surface (deterministic demo fault) ──

    def trigger_jam(self, sub_line_id: str) -> None:
        """Request the deterministic AP05_JAM on a sub-line (control surface).

        The authoritative raise timestamps are read from the runtime's
        simulation clock on the next poll, so the sequence is deterministic.
        """
        self._jam_pending.add(sub_line_id)

    def recover(self, sub_line_id: str) -> None:
        """Resolve the AP05_JAM — deferred until the 120 s downtime interval
        has elapsed (>= 1 composition step with the faulted sub-line frozen)."""
        if sub_line_id in self._fault:
            self._recover_pending.add(sub_line_id)

    def jammed_sub_lines(self) -> set[str]:
        """Sub-lines currently in an active AP05_JAM fault (frozen)."""
        return {
            sl for sl, f in self._fault.items()
            if f is not None and f.get("resolved_at") is None
        }

    def emit_oee(self, sub_line_id: str, runtime: AssyLineRuntime) -> None:
        """Emit the end-of-run mes.oee_summary once per (sub-line, run)."""
        # R4: prefer the canonical parent-session run id when bound, so the OEE
        # fact identity and the canonical downtime lookup use the same key.
        run_id = str(
            (self.canonical or {}).get("canonical_run_id")
            or self.run_id_for(sub_line_id)
        )
        # R4: with a canonical run id shared by all six sub-lines the guard must
        # be keyed per (run, sub-line) — one OEE summary per canonical sub-line.
        oee_key = f"{run_id}|{sub_line_id}"
        if oee_key in self._oee_emitted:
            return
        reality = self._oee_fact_reality(runtime, sub_line_id, run_id)
        if reality is None:
            return
        self._deliver(run_id, f"oee:{sub_line_id}:{run_id}", reality)
        self._oee_emitted.add(oee_key)

    # ── Public surface ──

    def poll(self, composition: Any) -> list[DeliveryResult]:
        """Emit any not-yet-emitted authoritative facts across all contexts.

        Idempotent: repeated polls never re-deliver a fact already DELIVERED
        to a given gateway.  Resets (sim-time regression) or explicit
        reset_all() produce a new run generation → new keys.
        """
        results: list[DeliveryResult] = []
        canonical_faults = getattr(composition, "faults", None)
        self._canonical_faults = (
            canonical_faults if isinstance(canonical_faults, dict) else None
        )
        for sub_line_id, ctx in composition.contexts.items():
            runtime = ctx.runtime
            run_id = self._resolve_run(sub_line_id, runtime)
            if self._canonical_faults:
                fault_read = self._canonical_faults.get(sub_line_id) or {}
                downtime = float(fault_read.get("downtime_s") or 0.0)
                if fault_read.get("raised_at_s") is not None and downtime > 0:
                    key = (run_id, sub_line_id)
                    self._canonical_downtime[key] = max(
                        self._canonical_downtime.get(key, 0.0), downtime
                    )
            self._emit_demo_lifecycle(
                sub_line_id, runtime, run_id, results,
                demo_step_number=composition.demo_step_number,
                canonical_faults=self._canonical_faults,
            )
            facts = self._collect_facts(runtime, ctx, run_id)
            facts.sort(key=lambda f: (
                f["station_order"], f["kind_order"], f["attempt"]))
            for fact in facts:
                results.extend(self._deliver(
                    run_id, fact["source_event_id"], fact["reality"]))
        return results

    @property
    def outbound_trace(self) -> tuple[dict, ...]:
        """Ordered record of delivered ProjectedMessages (evidence view)."""
        return tuple(self._outbound)

    @property
    def projected_messages(self) -> tuple[ProjectedMessage, ...]:
        """All delivered ProjectedMessages across in-memory gateways."""
        messages: list[ProjectedMessage] = []
        for gw in self.gateways:
            if isinstance(gw, InMemoryObsGateway):
                messages.extend(gw.messages)
        return tuple(messages)

    # ── Reset detection ──

    def _resolve_run(self, sub_line_id: str, runtime: AssyLineRuntime) -> str:
        """Detect runtime reset via simulation-time regression (monotonic)."""
        sim_time = runtime.simulation_time_s
        last = self._last_sim_time.get(sub_line_id)
        if last is not None and sim_time < last:
            self._run_generation[sub_line_id] = (
                self._run_generation.get(sub_line_id, 1) + 1)
            self._last_sim_time[sub_line_id] = sim_time
        else:
            self._last_sim_time[sub_line_id] = max(
                sim_time, last if last is not None else sim_time)
        canonical_run_id = (self.canonical or {}).get("canonical_run_id")
        if canonical_run_id:
            # R3: the canonical parent-session run id supersedes the legacy
            # sub-line-local synthetic generation as the effective run id.
            return str(canonical_run_id)
        return self.run_id_for(sub_line_id)

    # ── Operational state / exception / downtime (findings 1-3) ──

    def _emit_demo_lifecycle(
        self,
        sub_line_id: str,
        runtime: AssyLineRuntime,
        run_id: str,
        results: list[DeliveryResult],
        demo_step_number: int = 0,
        canonical_faults: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        """Emit operational run_status baseline + AP05_JAM lifecycle.

        R4: when ``canonical_faults`` (the canonical fault read model) is given,
        the issue/downtime lifecycle is derived READ-ONLY from canonical truth
        and no projection-owned fault state is used. Without it the accepted
        legacy demo lifecycle behaviour is unchanged.
        """
        if canonical_faults is not None:
            self._emit_canonical_lifecycle(
                sub_line_id, runtime, run_id, results,
                canonical_faults.get(sub_line_id) or {},
            )
            return
        station_order = {pos: i for i, pos in enumerate(runtime.conveyor.positions)}

        # Baseline operational RUNNING once per run (all sub-lines).
        if run_id not in self._baseline_emitted:
            self._baseline_emitted.add(run_id)
            baseline = self._run_status_reality(
                runtime, sub_line_id, run_id,
                event_id=f"{sub_line_id}:operational:running:init",
                line_state="running",
                sim_time=runtime.simulation_time_s,
                reason_code="",
                conveyor_state=runtime.conveyor.state.value,
            )
            results.extend(self._deliver(
                run_id, f"{sub_line_id}:operational:running:init", baseline))

        fault = self._fault.get(sub_line_id)
        if sub_line_id in self._jam_pending and fault is None:
            fault = {
                "jam_time_s": runtime.simulation_time_s,
                "jam_step": demo_step_number,
                "raised": False,
                "resolved_at": None,
            }
            self._fault[sub_line_id] = fault
            self._jam_pending.discard(sub_line_id)

        if fault is not None and not fault["raised"]:
            jam_t = fault["jam_time_s"]
            for event_id, line_state, reason in (
                (f"{sub_line_id}:operational:fault", "fault", "AP05_JAM"),
                (f"{sub_line_id}:operational:stopped", "stopped", "AP05_JAM"),
            ):
                reality = self._run_status_reality(
                    runtime, sub_line_id, run_id, event_id=event_id,
                    line_state=line_state, sim_time=jam_t,
                    reason_code=reason,
                    conveyor_state=runtime.conveyor.state.value)
                results.extend(self._deliver(run_id, event_id, reality))
            # EXCEPTION_RAISED under mes.issue (correlated context).
            results.extend(self._deliver(
                run_id, f"exception:{sub_line_id}:AP05:raised",
                self._issue_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"exception:{sub_line_id}:AP05:raised",
                    event_type=EVENT_EXCEPTION_RAISED, station_id="AP05",
                    reason_code="AP05_JAM", sim_time=jam_t)))
            # Exactly one downtime lifecycle start.
            results.extend(self._deliver(
                run_id, f"downtime:{sub_line_id}:AP05:start",
                self._downtime_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"downtime:{sub_line_id}:AP05:start",
                    event_type=EVENT_DOWNTIME_START, sim_time=jam_t,
                    downtime_start_s=jam_t, downtime_end_s=jam_t + DEMO_DOWNTIME_S,
                    downtime_s=DEMO_DOWNTIME_S)))
            fault["raised"] = True

        if sub_line_id in self._recover_pending and fault is not None:
            # Recovery only after the 120 s downtime interval has elapsed:
            # >= 1 composition step with the faulted sub-line excluded.
            if demo_step_number >= fault["jam_step"] + 1:
                fault["resolved_at"] = fault["jam_time_s"] + DEMO_DOWNTIME_S
                self._recover_pending.discard(sub_line_id)
            # else: defer — keep recover pending until the interval elapses

        if fault is not None and fault["resolved_at"] is not None:
            resolve_t = fault["resolved_at"]
            # EXCEPTION_RESOLVED (same correlation context).
            results.extend(self._deliver(
                run_id, f"exception:{sub_line_id}:AP05:resolved",
                self._issue_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"exception:{sub_line_id}:AP05:resolved",
                    event_type=EVENT_EXCEPTION_RESOLVED, station_id="AP05",
                    reason_code="AP05_JAM", sim_time=resolve_t)))
            # Operational RUNNING (line recovered).
            results.extend(self._deliver(
                run_id, f"{sub_line_id}:operational:running",
                self._run_status_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"{sub_line_id}:operational:running",
                    line_state="running", sim_time=resolve_t,
                    reason_code="",
                    conveyor_state=runtime.conveyor.state.value)))
            # Exactly one downtime lifecycle end (120 s).
            results.extend(self._deliver(
                run_id, f"downtime:{sub_line_id}:AP05:end",
                self._downtime_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"downtime:{sub_line_id}:AP05:end",
                    event_type=EVENT_DOWNTIME_END, sim_time=resolve_t,
                    downtime_start_s=fault["jam_time_s"],
                    downtime_end_s=resolve_t,
                    downtime_s=DEMO_DOWNTIME_S)))
            self._downtime_confirmed.add(run_id)
            self._fault.pop(sub_line_id, None)

    # ── R4: canonical fault read path (projection reads, never owns) ──

    def _emit_canonical_lifecycle(
        self,
        sub_line_id: str,
        runtime: AssyLineRuntime,
        run_id: str,
        results: list[DeliveryResult],
        fault: dict[str, Any],
    ) -> None:
        """Emit run-status/issue/downtime facts from the CANONICAL fault truth.

        The canonical execution bridge owns the fault lifecycle; this bridge only
        reads it and keeps its own delivery bookkeeping (idempotency). No
        projection-owned fault state is used on this path.
        """
        if run_id not in self._baseline_emitted:
            self._baseline_emitted.add(run_id)
            results.extend(self._deliver(
                run_id, f"{sub_line_id}:operational:running:init",
                self._run_status_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"{sub_line_id}:operational:running:init",
                    line_state="running",
                    sim_time=runtime.simulation_time_s,
                    reason_code="",
                    conveyor_state=runtime.conveyor.state.value)))

        state = fault.get("state")
        raised_at = fault.get("raised_at_s")
        resolved_at = fault.get("resolved_at_s")
        signature = (state, raised_at, resolved_at)
        key = (run_id, sub_line_id)
        if self._canonical_fault_emitted.get(key) == signature:
            return  # already emitted for this canonical fault state
        reason = str(fault.get("reason_code") or "AP05_JAM")
        station = str(fault.get("station_id") or "AP05")

        if state == "FAULT" and raised_at is not None:
            jam_t = float(raised_at)
            downtime_s = float(fault.get("downtime_s") or DEMO_DOWNTIME_S)
            for event_id, line_state in (
                (f"{sub_line_id}:operational:fault", "fault"),
                (f"{sub_line_id}:operational:stopped", "stopped"),
            ):
                results.extend(self._deliver(
                    run_id, event_id,
                    self._run_status_reality(
                        runtime, sub_line_id, run_id, event_id=event_id,
                        line_state=line_state, sim_time=jam_t,
                        reason_code=reason,
                        conveyor_state=runtime.conveyor.state.value)))
            results.extend(self._deliver(
                run_id, f"exception:{sub_line_id}:{station}:raised",
                self._issue_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"exception:{sub_line_id}:{station}:raised",
                    event_type=EVENT_EXCEPTION_RAISED, station_id=station,
                    reason_code=reason, sim_time=jam_t)))
            results.extend(self._deliver(
                run_id, f"downtime:{sub_line_id}:{station}:start",
                self._downtime_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"downtime:{sub_line_id}:{station}:start",
                    event_type=EVENT_DOWNTIME_START, sim_time=jam_t,
                    downtime_start_s=jam_t, downtime_end_s=jam_t + downtime_s,
                    downtime_s=downtime_s)))
        elif state == "RUNNING" and resolved_at is not None:
            resolve_t = float(resolved_at)
            downtime_s = float(fault.get("downtime_s") or DEMO_DOWNTIME_S)
            results.extend(self._deliver(
                run_id, f"exception:{sub_line_id}:{station}:resolved",
                self._issue_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"exception:{sub_line_id}:{station}:resolved",
                    event_type=EVENT_EXCEPTION_RESOLVED, station_id=station,
                    reason_code=reason, sim_time=resolve_t)))
            results.extend(self._deliver(
                run_id, f"{sub_line_id}:operational:running",
                self._run_status_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"{sub_line_id}:operational:running",
                    line_state="running", sim_time=resolve_t,
                    reason_code="",
                    conveyor_state=runtime.conveyor.state.value)))
            results.extend(self._deliver(
                run_id, f"downtime:{sub_line_id}:{station}:end",
                self._downtime_reality(
                    runtime, sub_line_id, run_id,
                    event_id=f"downtime:{sub_line_id}:{station}:end",
                    event_type=EVENT_DOWNTIME_END, sim_time=resolve_t,
                    downtime_start_s=resolve_t - downtime_s,
                    downtime_end_s=resolve_t,
                    downtime_s=downtime_s)))
        else:
            return
        self._canonical_fault_emitted[key] = signature

    # ── Fact collection (authoritative sources) ──

    def _collect_facts(
        self,
        runtime: AssyLineRuntime,
        ctx: Any,
        run_id: str,
    ) -> list[dict]:
        """Enumerate authoritative facts from runtime truth (read-only)."""
        facts: list[dict] = []
        station_order = {pos: i for i, pos in enumerate(runtime.conveyor.positions)}

        # 1. WIP entry (authoritative LINE_ENTRY trace facts).
        for ev in runtime.trace:
            if ev.event_type == "LINE_ENTRY" and ev.wip_id:
                facts.append(self._wip_entered_fact(ev, ctx, run_id))

        # 2. Operation completion (pure-execution stations only) + AP03
        # checklist evidence.
        for op in runtime.operation_registry.all_operations():
            if op.state != OperationState.ELIGIBLE_TO_INDEX:
                continue
            if op.station_id in _SPECIALIZED_STATIONS:
                continue
            facts.append(self._op_completion_fact(op, ctx, run_id, station_order))
            # AP03 checklist: emit a confirmed checklist_result only when the
            # authoritative operation result is CONFIRMED (checklist complete),
            # never a quality PASS/FAIL.
            if (op.station_id == "AP03"
                    and op.operation_result == OperationResult.CONFIRMED):
                facts.append(self._checklist_fact(op, ctx, run_id, station_order))

        # 3. AP04 genealogy — authoritative GenealogyStore join records.
        for rec in runtime.genealogy.all_records():
            facts.append(self._genealogy_fact(rec, ctx, run_id, station_order))

        # Operation index for evidence correlation (station, wip) → operation.
        op_map = {
            (op.station_id, op.wip_id): op
            for op in runtime.operation_registry.all_operations()
        }

        # 4. AP06/AP08 quality results + AP11 final-QC per attempt, plus AP06
        # per-attempt numerical measurement evidence.
        for wip_id in runtime.wip_ids:
            qh = runtime.get_quality_history(wip_id)
            if qh is None:
                continue
            for rec in qh.records:
                op = op_map.get((rec.station_id, rec.wip_id))
                if rec.station_id == "AP11" and rec.disposition == "PASS":
                    facts.append(self._ap11_qc_fact(
                        rec, op, ctx, run_id, station_order, is_fail=False))
                elif rec.station_id == "AP11" and rec.disposition == "FAIL":
                    facts.append(self._ap11_qc_fact(
                        rec, op, ctx, run_id, station_order, is_fail=True))
                elif rec.station_id in ("AP06", "AP08"):
                    facts.append(self._quality_fact(
                        rec, op, ctx, run_id, station_order))
                    # AP06 numerical measurements (one message per point per
                    # attempt; FAIL attempt values are never rewritten).
                    if rec.station_id == "AP06":
                        for m in rec.measurements:
                            facts.append(self._measurement_fact(
                                rec, m, op, ctx, run_id, station_order))

        # 5. LINE_OUT — derived from authoritative WIP/terminal quality state.
        for wip_id in runtime.wip_ids:
            ws = runtime.get_wip(wip_id)
            if ws is not None and ws.lifecycle == WipLifecycle.RELEASED:
                facts.append(self._line_out_fact(
                    ws, ctx, run_id, station_order, disposition="good"))
        for wip_id in runtime.wip_ids:
            if runtime.get_current_quality_status(wip_id) == QualityStatus.FAILED_FINAL:
                facts.append(self._line_out_reject_fact(
                    runtime, wip_id, ctx, run_id, station_order))

        # 6. AP11 RELEASE — authoritative WIP lifecycle fact.
        for wip_id in runtime.wip_ids:
            ws = runtime.get_wip(wip_id)
            if ws is not None and ws.lifecycle == WipLifecycle.RELEASED:
                facts.append(self._release_fact(
                    ws, ctx, run_id, station_order))
        return facts

    # ── Fact → RealityInput builders ──

    def _canonical_identity(self, sub_line_id: str) -> dict[str, Any]:
        """Canonical same-session projection identity (empty when unbound).

        Carries the canonical parent-session identity (workspace / run /
        scenario / profile) plus the projection-only ``source_run_key``
        (legacy sub-line-local key, subordinate — never a second lifecycle
        authority) and the ``projection_epoch`` that scopes message identity
        after a reset of the SAME canonical run id.
        """
        if not self.canonical:
            return {}
        ident: dict[str, Any] = dict(self.canonical)
        ident.setdefault("source_run_key", self.run_id_for(sub_line_id))
        ident.setdefault(
            "projection_epoch", self._run_generation.get(sub_line_id, 1)
        )
        workspace_id = ident.get("workspace_id")
        if workspace_id:
            ident["scope_path"] = f"{workspace_id}/ASSY/{sub_line_id}"
        return ident

    def _scoped_source_event_id(
        self, source_event_id: str, reality: RealityInput,
    ) -> str:
        """Scope a fact id by source scope + projection epoch (canonical only).

        Identity shape: ``canonical_run_id`` + source scope/sub_line_id +
        projection epoch + ``source_event_id``.  The canonical run id is shared
        by all six sub-lines and is preserved across a same-run reset, so both
        the source scope and the projection epoch must participate in message
        identity (unique per line, distinct before/after reset).  Unbound →
        unchanged.
        """
        if not self.canonical:
            return source_event_id
        epoch = reality.context.get("projection_epoch", 1)
        scope = (
            reality.context.get("sub_line_id")
            or reality.context.get("subline_id")
            or ""
        )
        if scope:
            return f"E{epoch}:{scope}:{source_event_id}"
        return f"E{epoch}:{source_event_id}"

    def _base_reality(
        self,
        runtime: AssyLineRuntime,
        sub_line_id: str,
        run_id: str,
        source_event_id: str,
        source_path: str,
        sim_time_s: float,
        source_data: dict[str, Any],
        semantic_type: str,
        station_id: str,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        extra_context: Optional[dict] = None,
    ) -> RealityInput:
        context: dict[str, Any] = {
            "semantic_type": semantic_type,
            "station_id": station_id,
            "subline_id": sub_line_id,
            "sub_line_id": sub_line_id,
            "production_line_id": "ASSY",
            "plant_id": "TIPA",
            "contract_version": CONTRACT_VERSION,
        }
        context.update(self._canonical_identity(sub_line_id))
        if extra_context:
            context.update({k: v for k, v in extra_context.items() if v is not None})
        return RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=source_event_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path=source_path,
            simulation_time_s=sim_time_s,
            category=CATEGORY,
            occurred_at=occurred_at_for(sim_time_s),
            source_data=source_data,
            subject_type=subject_type,
            subject_id=subject_id,
            context=context,
        )

    def _with_common(self, sub_line_id: str, data: dict[str, Any]) -> dict[str, Any]:
        data.setdefault("contract_version", CONTRACT_VERSION)
        data.setdefault("subline_id", sub_line_id)
        data.setdefault("production_line_id", "ASSY")
        data.setdefault("plant_id", "TIPA")
        return data

    def _run_status_reality(
        self, runtime: AssyLineRuntime, sub_line_id: str, run_id: str,
        event_id: str, line_state: str, sim_time: float, reason_code: str,
        conveyor_state: str,
    ) -> RealityInput:
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_LINE_STATE_CHANGED,
            "target_id": sub_line_id,
            "line_state": line_state,
            "conveyor_state": conveyor_state,
            "reason_code": reason_code,
            "simulation_time_s": sim_time,
        })
        return self._base_reality(
            runtime, sub_line_id, run_id, event_id, sub_line_id, sim_time,
            data, "run_status", sub_line_id, extra_context={"line_state": line_state})

    def _issue_reality(
        self, runtime: AssyLineRuntime, sub_line_id: str, run_id: str,
        event_id: str, event_type: str, station_id: str, reason_code: str,
        sim_time: float,
    ) -> RealityInput:
        data = self._with_common(sub_line_id, {
            "event_type": event_type,
            "target_id": station_id,
            "station_id": station_id,
            "wip_id": "",
            "reason_code": reason_code,
            "simulation_time_s": sim_time,
        })
        return self._base_reality(
            runtime, sub_line_id, run_id, event_id, station_id, sim_time,
            data, "issue", station_id, subject_type="wip", subject_id="")

    def _downtime_reality(
        self, runtime: AssyLineRuntime, sub_line_id: str, run_id: str,
        event_id: str, event_type: str, sim_time: float,
        downtime_start_s: float, downtime_end_s: float, downtime_s: float,
    ) -> RealityInput:
        data = self._with_common(sub_line_id, {
            "event_type": event_type,
            "target_id": sub_line_id,
            "station_id": sub_line_id,
            "wip_id": "",
            "reason_code": "AP05_JAM",
            "downtime_start_s": downtime_start_s,
            "downtime_end_s": downtime_end_s,
            "downtime_s": downtime_s,
            "simulation_time_s": sim_time,
        })
        return self._base_reality(
            runtime, sub_line_id, run_id, event_id, sub_line_id, sim_time,
            data, "execution_event", sub_line_id)

    def _wip_entered_fact(
        self, ev: Any, ctx: Any, run_id: str,
    ) -> dict:
        event_id = f"enter:{ev.wip_id}"
        data = self._with_common(ctx.identity.sub_line_id, {
            "event_type": EVENT_WIP_ENTERED,
            "target_id": ev.wip_id,
            "station_id": ev.position or "PRE-ASSY",
            "wip_id": ev.wip_id,
            "simulation_time_s": ev.simulation_time_s,
        })
        reality = self._base_reality(
            ctx.runtime, ctx.identity.sub_line_id, run_id, event_id,
            ev.position or "PRE-ASSY", ev.simulation_time_s, data,
            "execution_event", ev.position or "PRE-ASSY",
            subject_type="wip", subject_id=ev.wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": 0,
            "kind_order": _KIND_WIP_ENTERED,
            "attempt": 1,
        }

    def _op_completion_fact(
        self, op: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        sim_t = op.completed_at_sim_s if op.completed_at_sim_s is not None else 0.0
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_OPERATION_COMPLETED,
            "target_id": op.wip_id,
            "station_id": op.station_id,
            "wip_id": op.wip_id,
            "disposition": "",
            "attempt_number": op.attempt_number,
            "reason_code": "",
            "simulation_time_s": sim_t,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, op.execution_id, op.station_id,
            sim_t, data, "execution_event", op.station_id,
            subject_type="wip", subject_id=op.wip_id)
        return {
            "reality": reality,
            "source_event_id": op.execution_id,
            "station_order": station_order.get(op.station_id, 999),
            "kind_order": _KIND_OPERATION,
            "attempt": op.attempt_number,
        }

    def _genealogy_fact(
        self, rec: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_AP04_JOIN,
            "target_id": rec.child_wip_id,
            "child_wip_id": rec.child_wip_id,
            "parent_wip_ids": list(rec.parent_wip_ids),
            "relationship_type": rec.relationship_type,
            "station_id": rec.join_station,
            "wip_id": rec.child_wip_id,
            "simulation_time_s": rec.join_time_s,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, rec.child_wip_id,
            rec.join_station, rec.join_time_s, data,
            "genealogy_relationship", rec.join_station,
            subject_type="wip", subject_id=rec.child_wip_id)
        return {
            "reality": reality,
            "source_event_id": rec.child_wip_id,
            "station_order": station_order.get(rec.join_station, 999),
            "kind_order": _KIND_GENEALOGY,
            "attempt": 1,
        }

    def _quality_evidence(self, op: Any, rec: Any = None) -> dict[str, Any]:
        """Authoritative per-attempt evidence fields (never fabricated):
        structured observations, machine proposal and reason code/source.

        Observations are taken from the immutable QualityRecord when present
        (`rec.observations`, frozen at decision time) so a retested attempt's
        NG observations are never overwritten by a later PASS re-observation.
        The live operation is used only as a fallback for the current attempt.
        """
        if op is None and rec is None:
            return {
                "execution_id": "",
                "observations": [],
                "proposed_quality_result": None,
                "proposed_quality_reason": None,
                "reason_source": "",
            }
        raw_observations = []
        if rec is not None:
            raw_observations = getattr(rec, "observations", ()) or ()
        if not raw_observations:
            raw_observations = getattr(op, "observations", []) or []
        observations = [
            {"observation_id": o.get("observation_id", ""), "result": o.get("result", "")}
            for o in raw_observations
        ]
        # Prefer the record's frozen per-attempt proposal/reason; fall back to
        # the live operation for the current attempt.
        proposal = getattr(op, "proposed_quality_result", None)
        reason = getattr(op, "proposed_quality_reason", None) or {}
        if rec is not None:
            rec_proposal = getattr(rec, "proposed_quality_result", "")
            rec_reason = getattr(rec, "proposed_quality_reason", None)
            if rec_proposal:
                proposal = rec_proposal
            if rec_reason:
                reason = dict(rec_reason)
        return {
            "execution_id": getattr(op, "execution_id", ""),
            "observations": observations,
            "proposed_quality_result": proposal,
            "proposed_quality_reason": dict(reason) if reason else None,
            "reason_source": reason.get("source", ""),
        }

    def _quality_fact(
        self, rec: Any, op: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        is_terminal = bool(rec.terminal)
        terminal_state = QualityStatus.FAILED_FINAL.value if is_terminal else ""
        ev = self._quality_evidence(op, rec)
        reason_code = rec.reason_code
        reason = ev["proposed_quality_reason"] or {}
        if reason.get("code"):
            reason_code = reason["code"]
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_QUALITY_RESULT,
            "target_id": rec.wip_id,
            "station_id": rec.station_id,
            "wip_id": rec.wip_id,
            "disposition": rec.disposition,
            "attempt_number": rec.attempt_number,
            "reason_code": reason_code,
            "reason_source": ev["reason_source"],
            "check_type": rec.check_type.value,
            "is_terminal": is_terminal,
            "terminal_state": terminal_state,
            "execution_id": ev["execution_id"],
            "record_id": rec.record_id,
            "observations": ev["observations"],
            "proposed_quality_result": ev["proposed_quality_result"],
            "proposed_quality_reason": ev["proposed_quality_reason"],
            "simulation_time_s": rec.simulation_time_s,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, rec.record_id, rec.station_id,
            rec.simulation_time_s, data, "quality_result", rec.station_id,
            subject_type="wip", subject_id=rec.wip_id)
        return {
            "reality": reality,
            "source_event_id": rec.record_id,
            "station_order": station_order.get(rec.station_id, 999),
            "kind_order": _KIND_QUALITY,
            "attempt": rec.attempt_number,
        }

    def _ap11_qc_fact(
        self, rec: Any, op: Any, ctx: Any, run_id: str, station_order: dict,
        is_fail: bool,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        event_type = EVENT_AP11_FINAL_QC_FAIL if is_fail else EVENT_AP11_FINAL_QC_PASS
        ev = self._quality_evidence(op, rec)
        reason_code = rec.reason_code
        reason = ev["proposed_quality_reason"] or {}
        if reason.get("code"):
            reason_code = reason["code"]
        data = self._with_common(sub_line_id, {
            "event_type": event_type,
            "target_id": rec.wip_id,
            "station_id": rec.station_id,
            "wip_id": rec.wip_id,
            "disposition": rec.disposition,
            "attempt_number": rec.attempt_number,
            "reason_code": reason_code,
            "reason_source": ev["reason_source"],
            "check_type": rec.check_type.value,
            "is_terminal": is_fail,
            "terminal_state": QualityStatus.FAILED_FINAL.value if is_fail else "",
            "execution_id": ev["execution_id"],
            "record_id": rec.record_id,
            "observations": ev["observations"],
            "proposed_quality_result": ev["proposed_quality_result"],
            "proposed_quality_reason": ev["proposed_quality_reason"],
            "simulation_time_s": rec.simulation_time_s,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, rec.record_id, rec.station_id,
            rec.simulation_time_s, data, "quality_result", rec.station_id,
            subject_type="wip", subject_id=rec.wip_id)
        return {
            "reality": reality,
            "source_event_id": rec.record_id,
            "station_order": station_order.get(rec.station_id, 999),
            "kind_order": _KIND_FINAL_QC,
            "attempt": rec.attempt_number,
        }

    def _checklist_fact(
        self, op: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        """AP03 checklist confirmed (DEMO_SYNTHETIC item ids from the station
        contract).  Checklist completion is NOT a quality PASS/FAIL."""
        sub_line_id = ctx.identity.sub_line_id
        items = [
            {
                "item_id": item.get("item_id", ""),
                "required": True,
                "completed": bool(item.get("completed", False)),
            }
            for item in (op.checklist or [])
        ]
        event_id = f"checklist:{op.execution_id}:{op.attempt_number}"
        sim_t = op.completed_at_sim_s if op.completed_at_sim_s is not None else 0.0
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_CHECKLIST_CONFIRMED,
            "target_id": op.wip_id,
            "execution_id": op.execution_id,
            "attempt_number": op.attempt_number,
            "status": "confirmed",
            "required_count": len(items),
            "completed_count": sum(1 for i in items if i["completed"]),
            "items": items,
            "station_id": op.station_id,
            "wip_id": op.wip_id,
            "source": "DEMO_SYNTHETIC",
            "simulation_time_s": sim_t,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, event_id, op.station_id, sim_t,
            data, "checklist_result", op.station_id,
            subject_type="wip", subject_id=op.wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": station_order.get(op.station_id, 999),
            "kind_order": _KIND_OPERATION,
            "attempt": op.attempt_number,
        }

    def _measurement_fact(
        self, rec: Any, m: Any, op: Any, ctx: Any, run_id: str,
        station_order: dict,
    ) -> dict:
        """One AP06 numerical measurement per point per attempt.

        Limits are the authoritative expected_min/expected_max; in_spec is
        derived (inclusive).  FAIL attempt values are never rewritten."""
        sub_line_id = ctx.identity.sub_line_id
        lo = m.expected_min
        hi = m.expected_max
        in_spec = (lo is None or lo <= m.value) and (hi is None or m.value <= hi)
        event_id = f"measurement:{rec.record_id}:{m.name}"
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_MEASUREMENT_RESULT,
            "target_id": rec.wip_id,
            "execution_id": op.execution_id if op is not None else "",
            "record_id": rec.record_id,
            "attempt_number": rec.attempt_number,
            "measurement_code": m.name,
            "value": m.value,
            "unit": m.unit,
            "lower_limit": lo,
            "upper_limit": hi,
            "in_spec": in_spec,
            "evidence_source": "DEMO_SYNTHETIC",
            "station_id": rec.station_id,
            "wip_id": rec.wip_id,
            "simulation_time_s": rec.simulation_time_s,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, event_id, rec.station_id,
            rec.simulation_time_s, data, "measurement_result", rec.station_id,
            subject_type="wip", subject_id=rec.wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": station_order.get(rec.station_id, 999),
            "kind_order": _KIND_QUALITY,
            "attempt": rec.attempt_number,
        }

    def _line_out_fact(
        self, ws: Any, ctx: Any, run_id: str, station_order: dict,
        disposition: str,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        event_id = f"line_out:{ws.wip_id}"
        sim_t = ws.released_at_sim_s
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_LINE_OUT,
            "target_id": ws.wip_id,
            "station_id": "LINE_OUT",
            "wip_id": ws.wip_id,
            "disposition": disposition,
            "simulation_time_s": sim_t,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, event_id, "LINE_OUT", sim_t,
            data, "execution_event", "LINE_OUT",
            subject_type="wip", subject_id=ws.wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": station_order.get("LINE_OUT", 999),
            "kind_order": _KIND_LINE_OUT,
            "attempt": 1,
        }

    def _line_out_reject_fact(
        self, runtime: AssyLineRuntime, wip_id: str, ctx: Any, run_id: str,
        station_order: dict,
    ) -> dict:
        """LINE_OUT REJECT derived from authoritative FAILED_FINAL quality."""
        sub_line_id = ctx.identity.sub_line_id
        event_id = f"line_out_reject:{wip_id}"
        # deterministic reject timestamp = terminal FAILED_FINAL record time.
        sim_t = runtime.simulation_time_s
        qh = runtime.get_quality_history(wip_id)
        if qh is not None:
            for rec in qh.records:
                if rec.terminal:
                    sim_t = rec.simulation_time_s
                    break
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_LINE_OUT,
            "target_id": wip_id,
            "station_id": "LINE_OUT",
            "wip_id": wip_id,
            "disposition": "reject",
            "reason_code": QualityStatus.FAILED_FINAL.value,
            "simulation_time_s": sim_t,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, event_id, "LINE_OUT", sim_t,
            data, "execution_event", "LINE_OUT",
            subject_type="wip", subject_id=wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": station_order.get("LINE_OUT", 999),
            "kind_order": _KIND_LINE_OUT,
            "attempt": 1,
        }

    def _release_fact(
        self, ws: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        event_id = f"release:{ws.wip_id}"
        sim_t = ws.released_at_sim_s
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_AP11_RELEASE,
            "target_id": ws.wip_id,
            "wip_id": ws.wip_id,
            "station_id": "AP11",
            "release_time_s": sim_t,
            "simulation_time_s": sim_t,
        })
        reality = self._base_reality(
            ctx.runtime, sub_line_id, run_id, event_id, "AP11", sim_t,
            data, "release", "AP11", subject_type="wip", subject_id=ws.wip_id)
        return {
            "reality": reality,
            "source_event_id": event_id,
            "station_order": station_order.get("AP11", 999),
            "kind_order": _KIND_RELEASE,
            "attempt": 1,
        }

    # ── OEE (finding 5) ──

    def _oee_fact_reality(
        self, runtime: AssyLineRuntime, sub_line_id: str, run_id: str,
    ) -> Optional[RealityInput]:
        """Reconciled per sub-line/run OEE from authoritative counters.

        planned_s = run_s + downtime_s; actual_count = good + reject.
        R4: downtime_s comes from the CANONICAL fault lifecycle when the
        canonical fault read model is bound (``_canonical_downtime``); otherwise
        the accepted legacy demo rule applies (120 s only if a confirmed
        AP05_JAM downtime occurred in this run). OEE < 100 % via downtime (A<1)
        and/or reject (Q<1).
        """
        good = 0
        reject = 0
        for wip_id in runtime.wip_ids:
            ws = runtime.get_wip(wip_id)
            if ws is not None and ws.lifecycle == WipLifecycle.RELEASED:
                good += 1
            elif runtime.get_current_quality_status(wip_id) == QualityStatus.FAILED_FINAL:
                reject += 1
        actual = good + reject
        canonical_downtime = self._canonical_downtime.get((run_id, sub_line_id))
        if canonical_downtime is not None:
            # R4: canonical fault lifecycle owns the downtime contribution of
            # THIS sub-line (keyed per run + sub-line).
            downtime_s = float(canonical_downtime)
        elif run_id in self._downtime_confirmed:
            downtime_s = DEMO_DOWNTIME_S
        else:
            downtime_s = 0.0
        planned_s = float(runtime.simulation_time_s)
        run_s = planned_s - downtime_s
        ideal_cycle_s = DEMO_IDEAL_CYCLE_S

        if planned_s <= 0 or actual <= 0 or run_s <= 0:
            return None
        availability = run_s / planned_s
        performance = (ideal_cycle_s * actual) / run_s
        quality = good / actual
        oee = availability * performance * quality

        data = self._with_common(sub_line_id, {
            "event_type": EVENT_OEE_SUMMARY,
            "target_id": sub_line_id,
            "planned_s": planned_s,
            "run_s": run_s,
            "downtime_s": downtime_s,
            "ideal_cycle_s": ideal_cycle_s,
            "actual_count": actual,
            "good_count": good,
            "reject_count": reject,
            "availability": round(availability, 6),
            "performance": round(performance, 6),
            "quality": round(quality, 6),
            "oee": round(oee, 6),
            "simulation_time_s": planned_s,
        })
        return self._base_reality(
            runtime, sub_line_id, run_id, f"oee:{sub_line_id}:{run_id}",
            sub_line_id, planned_s, data, "oee_summary", sub_line_id)

    # ── Delivery ──

    def _deliver(
        self,
        run_id: str,
        source_event_id: str,
        reality: RealityInput,
    ) -> list[DeliveryResult]:
        """ObservationService → ObservationRouter → gateways. Never mutates truth.

        Per-gateway idempotency: a (source_event_id, gateway_id) pair already
        DELIVERED is skipped; a FAILED gateway is retried on the next poll.
        """
        results: list[DeliveryResult] = []
        source_event_id = self._scoped_source_event_id(source_event_id, reality)
        if source_event_id != reality.source_event_id:
            reality = replace(reality, source_event_id=source_event_id)
        delivered = self._delivered.setdefault(run_id, set())
        envelopes = self.service.collect(reality)
        for envelope in envelopes:
            messages = self.router.route(envelope)
            for gateway in self.gateways:
                for msg in messages:
                    key = (source_event_id, gateway.gateway_id)
                    if key in delivered:
                        continue
                    result = gateway.send(msg)
                    results.append(result)
                    if result.status == DeliveryStatus.DELIVERED:
                        delivered.add(key)
                        self._outbound.append({
                            "gateway_id": gateway.gateway_id,
                            "message_key": msg.key,
                            "message_type": msg.message_type,
                            "schema_name": msg.schema_name,
                            "run_id": reality.run_id,
                            "source_event_id": reality.source_event_id,
                            "simulation_time_s": reality.simulation_time_s,
                            "subject_id": reality.subject_id,
                            "payload": dict(msg.payload),
                        })
        return results


# ═══════════════════════════════════════════════════════════
# Pipeline factory
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyMesPipeline:
    """Assembled MES contract pipeline for the six-sub-line demo."""

    service: ObservationService
    router: ObservationRouter
    gateways: list[ObservationGatewayProtocol]
    bridge: AssyMesBridge


def build_assy_mes_pipeline(
    gateways: Optional[list[ObservationGatewayProtocol]] = None,
    model_id: str = MODEL_ID,
    canonical: Optional[Mapping[str, Any]] = None,
) -> AssyMesPipeline:
    """Build the VF-DM-DEMO-ASSY-MES-02 pipeline.

    Default gateway: in-memory (test/demo).  Callers may supply
    InMemory / Jsonl / MQTT gateways.

    R3 additive: ``canonical`` binds the pipeline to the canonical TIPA
    parent-session identity (read-only metadata); ``None`` keeps the legacy
    sub-line-local run identity.
    """
    service = ObservationService(
        points=build_assy_mes_observation_points(),
        policy=ObservationPolicy.industrial(),
    )
    router = ObservationRouter()
    router.subscribe(ProjectionSubscription(
        projection=MESProjection(),
        observation_types=(ObservationType.EVENT,),
        source_domains=(SOURCE_DOMAIN,),
    ))
    gw = list(gateways) if gateways is not None else [InMemoryObsGateway()]
    bridge = AssyMesBridge(
        service=service,
        router=router,
        gateways=gw,
        model_id=model_id,
        canonical=canonical,
    )
    return AssyMesPipeline(
        service=service,
        router=router,
        gateways=gw,
        bridge=bridge,
    )


# ═══════════════════════════════════════════════════════════
# Deterministic demo smoke (python -m ...assy_mes_bridge)
# ═══════════════════════════════════════════════════════════

def demo_terminal(composition: Any) -> bool:
    """True when the demo has reached its bounded endpoint:
    the exception target sub-line has at least one terminal REJECT and every
    non-target sub-line has released at least one GOOD motor."""
    from virtual_factory.assembly.line_runtime import WipLifecycle
    from virtual_factory.assembly.quality_records import QualityStatus

    target = composition.target_sub_line_id
    target_ctx = composition.get_context(target)
    if target_ctx is None:
        return True
    has_reject = any(
        target_ctx.runtime.get_current_quality_status(w) == QualityStatus.FAILED_FINAL
        for w in target_ctx.runtime.wip_ids
    )
    if not has_reject:
        return False
    for sl, ctx in composition.contexts.items():
        if sl == target:
            continue
        has_good = any(
            (ctx.runtime.get_wip(w) is not None
             and ctx.runtime.get_wip(w).lifecycle == WipLifecycle.RELEASED)
            for w in ctx.runtime.wip_ids
        )
        if not has_good:
            return False
    return True


def _demo_run(config_path: str, max_steps: int = 24) -> tuple[AssyMesBridge, dict]:
    """Run the deterministic bounded demo on the six-sub-line composition and
    return (bridge, message-type counts).  Used by the smoke command and
    evidence.  The faulted target sub-line is frozen while AP05_JAM is active;
    recovery is emitted after the 120 s downtime interval."""
    from virtual_factory.assembly.demo_composition import (
        AssyDemoComposition,
        DemoScenario,
    )
    composition = AssyDemoComposition(
        config_path=config_path,
        scenario=DemoScenario.FAILED_FINAL,
        selected_sub_line_id="ASSY-SL03",
    )
    composition.initialize()
    pipeline = build_assy_mes_pipeline()
    bridge = pipeline.bridge
    target = composition.target_sub_line_id

    bridge.poll(composition)          # baseline RUNNING per sub-line
    # healthy production (target advancing)
    for _ in range(6):
        composition.step_all()
        bridge.poll(composition)
    # deterministic AP05_JAM → target frozen
    bridge.trigger_jam(target)
    bridge.poll(composition)
    # one excluded step → 120 s downtime on target, siblings advance
    composition.step_all(exclude_sub_line_ids={target})
    bridge.poll(composition)
    # recover (emitted after the downtime interval)
    bridge.recover(target)
    bridge.poll(composition)
    # bounded run to terminal (respecting any active fault freeze)
    for _ in range(max_steps):
        if demo_terminal(composition):
            break
        composition.step_all(exclude_sub_line_ids=bridge.jammed_sub_lines())
        bridge.poll(composition)

    for sl, ctx in composition.contexts.items():
        bridge.emit_oee(sl, ctx.runtime)
    bridge.poll(composition)

    counts: dict[str, int] = {}
    for msg in bridge.projected_messages:
        counts[msg.message_type] = counts.get(msg.message_type, 0) + 1
    return bridge, counts


def main(argv: Optional[list[str]] = None) -> int:
    import json
    import os
    import sys
    from pathlib import Path

    config_path = os.environ.get(
        "TIPA_ASSY_CONFIG",
        str(Path(__file__).resolve().parent.parent.parent.parent
            / "configs" / "plants" / "tipa_assy_demo.yaml"),
    )
    max_steps = int(os.environ.get("ASSY_MES_DEMO_STEPS", "24"))
    bridge, counts = _demo_run(config_path, max_steps=max_steps)
    keys = [m.key for m in bridge.projected_messages]
    print(json.dumps({
        "run_ids": sorted({m.payload.get("run_id") for m in bridge.projected_messages}),
        "message_counts": counts,
        "total": sum(counts.values()),
        "unique_message_keys": len(set(keys)),
        "duplicate_message_keys": len(keys) - len(set(keys)),
        "sub_lines": len({m.payload.get("subline_id") for m in bridge.projected_messages}),
    }, indent=2, ensure_ascii=False))
    return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
