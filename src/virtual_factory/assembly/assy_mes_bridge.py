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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from virtual_factory.assembly.demo_composition import AssyDemoComposition
from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime,
    WipLifecycle,
)
from virtual_factory.assembly.operation_execution import OperationState
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

CONTRACT_VERSION = "tipa-assy-demo-v1"
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
             "attempt_number", "reason_code", "check_type",
             "is_terminal", "terminal_state", "simulation_time_s"),
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

    # ── Run identity ──

    def run_id_for(self, sub_line_id: str) -> str:
        """Stable run id per sub-line; generation bumps on reset."""
        gen = self._run_generation.get(sub_line_id, 1)
        return f"{sub_line_id}:R{gen}"

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
        run_id = self.run_id_for(sub_line_id)
        oee_key = f"{run_id}"
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
        for sub_line_id, ctx in composition.contexts.items():
            runtime = ctx.runtime
            run_id = self._resolve_run(sub_line_id, runtime)
            self._emit_demo_lifecycle(
                sub_line_id, runtime, run_id, results,
                demo_step_number=composition.demo_step_number,
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
        return self.run_id_for(sub_line_id)

    # ── Operational state / exception / downtime (findings 1-3) ──

    def _emit_demo_lifecycle(
        self,
        sub_line_id: str,
        runtime: AssyLineRuntime,
        run_id: str,
        results: list[DeliveryResult],
        demo_step_number: int = 0,
    ) -> None:
        """Emit operational run_status baseline + deterministic AP05_JAM
        exception/downtime lifecycle.  Quality HOLD never becomes a line fault.

        The faulted sub-line is frozen (the controller excludes it from
        stepping) and recovery is emitted only after the deterministic 120 s
        downtime interval (>= 1 composition step since the jam).
        """
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

        # 2. Operation completion (pure-execution stations only).
        for op in runtime.operation_registry.all_operations():
            if op.state != OperationState.ELIGIBLE_TO_INDEX:
                continue
            if op.station_id in _SPECIALIZED_STATIONS:
                continue
            facts.append(self._op_completion_fact(op, ctx, run_id, station_order))

        # 3. AP04 genealogy — authoritative GenealogyStore join records.
        for rec in runtime.genealogy.all_records():
            facts.append(self._genealogy_fact(rec, ctx, run_id, station_order))

        # 4. AP06/AP08 quality results + AP11 final-QC per attempt.
        for wip_id in runtime.wip_ids:
            qh = runtime.get_quality_history(wip_id)
            if qh is None:
                continue
            for rec in qh.records:
                if rec.station_id == "AP11" and rec.disposition == "PASS":
                    facts.append(self._ap11_qc_fact(
                        rec, ctx, run_id, station_order, is_fail=False))
                elif rec.station_id == "AP11" and rec.disposition == "FAIL":
                    facts.append(self._ap11_qc_fact(
                        rec, ctx, run_id, station_order, is_fail=True))
                elif rec.station_id in ("AP06", "AP08"):
                    facts.append(self._quality_fact(rec, ctx, run_id, station_order))

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
            "production_line_id": "ASSY",
            "plant_id": "TIPA",
            "contract_version": CONTRACT_VERSION,
        }
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

    def _quality_fact(
        self, rec: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        is_terminal = bool(rec.terminal)
        terminal_state = QualityStatus.FAILED_FINAL.value if is_terminal else ""
        data = self._with_common(sub_line_id, {
            "event_type": EVENT_QUALITY_RESULT,
            "target_id": rec.wip_id,
            "station_id": rec.station_id,
            "wip_id": rec.wip_id,
            "disposition": rec.disposition,
            "attempt_number": rec.attempt_number,
            "reason_code": rec.reason_code,
            "check_type": rec.check_type.value,
            "is_terminal": is_terminal,
            "terminal_state": terminal_state,
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
        self, rec: Any, ctx: Any, run_id: str, station_order: dict,
        is_fail: bool,
    ) -> dict:
        sub_line_id = ctx.identity.sub_line_id
        event_type = EVENT_AP11_FINAL_QC_FAIL if is_fail else EVENT_AP11_FINAL_QC_PASS
        data = self._with_common(sub_line_id, {
            "event_type": event_type,
            "target_id": rec.wip_id,
            "station_id": rec.station_id,
            "wip_id": rec.wip_id,
            "disposition": rec.disposition,
            "attempt_number": rec.attempt_number,
            "reason_code": rec.reason_code,
            "check_type": rec.check_type.value,
            "is_terminal": is_fail,
            "terminal_state": QualityStatus.FAILED_FINAL.value if is_fail else "",
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
        downtime_s is 120 s only if the confirmed AP05_JAM downtime occurred
        in this run; OEE < 100 % via downtime (A<1) and/or reject (Q<1).
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
        downtime_s = DEMO_DOWNTIME_S if run_id in self._downtime_confirmed else 0.0
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
) -> AssyMesPipeline:
    """Build the VF-DM-DEMO-ASSY-MES-02 pipeline.

    Default gateway: in-memory (test/demo).  Callers may supply
    InMemory / Jsonl / MQTT gateways.
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
