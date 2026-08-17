"""M6-INT-01 — ASSY reality observation bridge (P0 outbound, MES consumer).

Architecture (per M6-INT-01 contract):

    ASSY authoritative runtime facts
            ↓
    AssyObservationBridge
            ↓
    RealityInput
            ↓
    ObservationService
            ↓
    ObservationEnvelope
            ↓
    ObservationRouter
            ↓
    MESProjection
            ↓
    ProjectedMessage
            ↓
    ObservationGateway

Invariants (locked):
- Runtime truth is only READ.  The bridge never mutates simulation truth.
- ``source_event_id`` is derived from stable domain fact identity:
  execution_id (operation completion), child_wip_id (AP04 join),
  quality record_id (AP06/AP08/AP11 QC), ``release:<wip_id>`` (AP11 RELEASE).
- Idempotency: same authoritative fact → same (run_id, source_event_id)
  → delivered exactly once, even across repeated polls.
- Default-deny field projection: every ObservationPoint carries an explicit
  FieldPolicy allow-list; unknown runtime fields are invisible.
- Gateway failure is reported downstream (DeliveryResult.FAILED); it never
  reverts or mutates simulation truth.
- No timing sample is created by bridge reads (no resolver/ensure calls).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime,
    WipLifecycle,
)
from virtual_factory.assembly.operation_execution import OperationState
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
# Source / event vocabulary (P0 outbound facts)
# ═══════════════════════════════════════════════════════════

SOURCE_TYPE = "assy_runtime"
SOURCE_DOMAIN = "assy"
CATEGORY = "industrial_event"
MODEL_ID = "tipa_assy_demo"

EVENT_OPERATION_COMPLETED = "OPERATION_COMPLETED"
EVENT_AP04_JOIN = "AP04_JOIN"
EVENT_QUALITY_RESULT = "QUALITY_RESULT"
EVENT_AP11_FINAL_QC_PASS = "AP11_FINAL_QC_PASS"
EVENT_AP11_RELEASE = "AP11_RELEASE"

# Stations whose authoritative outbound fact is NOT a generic operation
# completion (they emit genealogy / quality / final-QC / release instead).
_SPECIALIZED_STATIONS = frozenset({"AP04", "AP06", "AP08", "AP11"})

# Kind ordering used to produce a deterministic ordered trace per motor.
_KIND_OPERATION = 0
_KIND_GENEALOGY = 1
_KIND_QUALITY = 2
_KIND_FINAL_QC = 2
_KIND_RELEASE = 3


# ═══════════════════════════════════════════════════════════
# ObservationPoints (default-deny FieldPolicy allow-lists)
# ═══════════════════════════════════════════════════════════

def _point(
    point_id: str,
    label: str,
    event_type: str,
    extract: tuple[str, ...],
) -> ObservationPoint:
    """One ON_EVENT point scoped to a single P0 outbound event type."""
    return ObservationPoint(
        point_id=point_id,
        observation_type=ObservationType.EVENT,
        label=label,
        source_type=SOURCE_TYPE,
        source_filter={"event_type": event_type},
        trigger=TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=(event_type,),
        ),
        fields=FieldPolicy(extract=extract),
        enabled=True,
    )


def build_assy_observation_points() -> list[ObservationPoint]:
    """Declare the P0 outbound observation points.

    Each point is scoped to exactly one authoritative event type and exposes
    only the explicitly approved fields (default-deny).
    """
    return [
        _point(
            "assy.operation_completion",
            "ASSY operation completion (pure-execution stations)",
            EVENT_OPERATION_COMPLETED,
            (
                "event_type", "execution_id", "station_id", "wip_id",
                "operation_result", "completion_mode", "attempt_number",
                "source",
            ),
        ),
        _point(
            "assy.ap04_genealogy",
            "AP04 assembly join genealogy (parent + component → child)",
            EVENT_AP04_JOIN,
            (
                "event_type", "child_wip_id", "parent_wip_ids",
                "component_ids", "join_station", "join_time_s",
                "relationship_type", "station_id", "wip_id",
            ),
        ),
        _point(
            "assy.quality_result",
            "AP06/AP08 quality result per attempt",
            EVENT_QUALITY_RESULT,
            (
                "event_type", "record_id", "wip_id", "station_id",
                "check_type", "disposition", "attempt_number",
                "simulation_time_s", "reason_code",
            ),
        ),
        _point(
            "assy.ap11_final_qc",
            "AP11 final QC PASS",
            EVENT_AP11_FINAL_QC_PASS,
            (
                "event_type", "record_id", "wip_id", "station_id",
                "check_type", "disposition", "attempt_number",
                "simulation_time_s",
            ),
        ),
        _point(
            "assy.ap11_release",
            "AP11 RELEASE (distinct final disposition)",
            EVENT_AP11_RELEASE,
            (
                "event_type", "wip_id", "station_id", "release_time_s",
            ),
        ),
    ]


# ═══════════════════════════════════════════════════════════
# AssyObservationBridge
# ═══════════════════════════════════════════════════════════

@dataclass
class AssyObservationBridge:
    """Polls ASSY runtime truth and emits P0 outbound observations.

    Polls all composition contexts, reads authoritative facts, and delivers
    them through ObservationService → ObservationRouter → gateways exactly
    once per (run_id, source_event_id, gateway_id).

    The bridge is strictly downstream: it never mutates runtime state and
    never creates timing samples.
    """

    service: ObservationService
    router: ObservationRouter
    gateways: list[ObservationGatewayProtocol]
    model_id: str = MODEL_ID

    # run tracking (sub_line_id → current generation)
    _run_generation: dict[str, int] = field(default_factory=dict)
    _last_sim_time: dict[str, float] = field(default_factory=dict)
    # per-gateway delivery checkpoint:
    #   run_id → set[(source_event_id, gateway_id)] already DELIVERED
    _delivered: dict[str, set[tuple[str, str]]] = field(default_factory=dict)
    # ordered outbound delivery trace (evidence, read-only consumers)
    _outbound: list[dict] = field(default_factory=list)

    # ── Run identity ──

    def run_id_for(self, sub_line_id: str) -> str:
        """Stable run id per sub-line; generation bumps on reset."""
        gen = self._run_generation.get(sub_line_id, 1)
        return f"{sub_line_id}:R{gen}"

    # ── Public surface ──

    def poll(self, composition: Any) -> list[DeliveryResult]:
        """Emit any not-yet-emitted authoritative facts across all contexts.

        Returns the DeliveryResults for this poll.  Idempotent: repeated polls
        do not re-emit facts already DELIVERED to a given gateway.  Delivery
        checkpoint is per (run_id, source_event_id, gateway_id): a gateway
        that already delivered a fact is never re-sent; a gateway that failed
        is retried on the next poll (at-least-once per gateway, never dup).
        """
        results: list[DeliveryResult] = []
        for sub_line_id, ctx in composition.contexts.items():
            runtime = ctx.runtime
            run_id = self._resolve_run(sub_line_id, runtime)
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
        """Detect runtime reset via simulation-time regression (monotonic).

        A reset produces exactly ONE generation transition: after detecting
        regression the stored last time is re-baselined to the current time,
        so subsequent steps within the new run stay on the new generation.
        """
        sim_time = runtime.simulation_time_s
        last = self._last_sim_time.get(sub_line_id)
        if last is not None and sim_time < last:
            # time moved backwards → runtime reset → exactly one bump
            self._run_generation[sub_line_id] = (
                self._run_generation.get(sub_line_id, 1) + 1)
            self._last_sim_time[sub_line_id] = sim_time
        else:
            self._last_sim_time[sub_line_id] = max(
                sim_time, last if last is not None else sim_time)
        return self.run_id_for(sub_line_id)

    # ── Fact collection (authoritative sources) ──

    def _collect_facts(
        self,
        runtime: AssyLineRuntime,
        ctx: Any,
        run_id: str,
    ) -> list[dict]:
        """Enumerate authoritative facts from runtime truth (read-only)."""
        facts: list[dict] = []
        station_order = {
            pos: i for i, pos in enumerate(runtime.conveyor.positions)
        }

        # 1. Operation completion (pure-execution stations only).
        for op in runtime.operation_registry.all_operations():
            if op.state != OperationState.ELIGIBLE_TO_INDEX:
                continue
            if op.station_id in _SPECIALIZED_STATIONS:
                continue
            facts.append(self._op_completion_fact(op, ctx, run_id, station_order))

        # 2. AP04 genealogy — authoritative GenealogyStore join records.
        for rec in runtime.genealogy.all_records():
            facts.append(self._genealogy_fact(rec, ctx, run_id, station_order))

        # 3. AP06/AP08 quality results + AP11 final-QC PASS per attempt.
        for wip_id in runtime.wip_ids:
            qh = runtime.get_quality_history(wip_id)
            if qh is None:
                continue
            for rec in qh.records:
                if rec.station_id == "AP11" and rec.disposition == "PASS":
                    facts.append(self._ap11_qc_fact(rec, ctx, run_id, station_order))
                elif rec.station_id in ("AP06", "AP08"):
                    facts.append(self._quality_fact(rec, ctx, run_id, station_order))

        # 4. AP11 RELEASE — authoritative WIP lifecycle fact.
        for wip_id in runtime.wip_ids:
            ws = runtime.get_wip(wip_id)
            if ws is not None and ws.lifecycle == WipLifecycle.RELEASED:
                facts.append(self._release_fact(
                    ws, ctx, run_id, station_order))
        return facts

    # ── Fact → RealityInput builders ──

    def _op_completion_fact(
        self, op: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        reality = RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=op.execution_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path=op.station_id,
            simulation_time_s=(
                op.completed_at_sim_s
                if op.completed_at_sim_s is not None
                else 0.0
            ),
            category=CATEGORY,
            source_data={
                "event_type": EVENT_OPERATION_COMPLETED,
                "target_id": op.wip_id,
                "execution_id": op.execution_id,
                "station_id": op.station_id,
                "wip_id": op.wip_id,
                "operation_result": (
                    op.operation_result.value if op.operation_result else None
                ),
                "completion_mode": op.completion_mode.value,
                "attempt_number": op.attempt_number,
                "source": op.source,
            },
            subject_type="wip",
            subject_id=op.wip_id,
            context=self._base_context(
                ctx, semantic_type="execution_event", station_id=op.station_id,
                completion_mode=op.completion_mode.value),
        )
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
        reality = RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=rec.child_wip_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path=rec.join_station,
            simulation_time_s=rec.join_time_s,
            category=CATEGORY,
            source_data={
                "event_type": EVENT_AP04_JOIN,
                "target_id": rec.child_wip_id,
                "child_wip_id": rec.child_wip_id,
                "parent_wip_ids": list(rec.parent_wip_ids),
                "component_ids": list(rec.component_ids),
                "join_station": rec.join_station,
                "join_time_s": rec.join_time_s,
                "relationship_type": rec.relationship_type,
                "station_id": rec.join_station,
                "wip_id": rec.child_wip_id,
            },
            subject_type="wip",
            subject_id=rec.child_wip_id,
            context=self._base_context(
                ctx, semantic_type="genealogy_relationship",
                station_id=rec.join_station),
        )
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
        reality = RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=rec.record_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path=rec.station_id,
            simulation_time_s=rec.simulation_time_s,
            category=CATEGORY,
            source_data={
                "event_type": EVENT_QUALITY_RESULT,
                "target_id": rec.wip_id,
                "record_id": rec.record_id,
                "wip_id": rec.wip_id,
                "station_id": rec.station_id,
                "check_type": rec.check_type.value,
                "disposition": rec.disposition,
                "attempt_number": rec.attempt_number,
                "simulation_time_s": rec.simulation_time_s,
                "reason_code": rec.reason_code,
            },
            subject_type="wip",
            subject_id=rec.wip_id,
            context=self._base_context(
                ctx, semantic_type="quality_result", station_id=rec.station_id,
                attempt=rec.attempt_number),
        )
        return {
            "reality": reality,
            "source_event_id": rec.record_id,
            "station_order": station_order.get(rec.station_id, 999),
            "kind_order": _KIND_QUALITY,
            "attempt": rec.attempt_number,
        }

    def _ap11_qc_fact(
        self, rec: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        reality = RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=rec.record_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path=rec.station_id,
            simulation_time_s=rec.simulation_time_s,
            category=CATEGORY,
            source_data={
                "event_type": EVENT_AP11_FINAL_QC_PASS,
                "target_id": rec.wip_id,
                "record_id": rec.record_id,
                "wip_id": rec.wip_id,
                "station_id": rec.station_id,
                "check_type": rec.check_type.value,
                "disposition": rec.disposition,
                "attempt_number": rec.attempt_number,
                "simulation_time_s": rec.simulation_time_s,
            },
            subject_type="wip",
            subject_id=rec.wip_id,
            context=self._base_context(
                ctx, semantic_type="quality_result", station_id=rec.station_id,
                attempt=rec.attempt_number, final_qc=True),
        )
        return {
            "reality": reality,
            "source_event_id": rec.record_id,
            "station_order": station_order.get(rec.station_id, 999),
            "kind_order": _KIND_FINAL_QC,
            "attempt": rec.attempt_number,
        }

    def _release_fact(
        self, ws: Any, ctx: Any, run_id: str, station_order: dict,
    ) -> dict:
        release_event_id = f"release:{ws.wip_id}"
        release_time_s = ws.released_at_sim_s
        reality = RealityInput(
            run_id=run_id,
            model_id=self.model_id,
            source_event_id=release_event_id,
            source_type=SOURCE_TYPE,
            source_domain=SOURCE_DOMAIN,
            source_path="AP11",
            simulation_time_s=release_time_s,
            category=CATEGORY,
            source_data={
                "event_type": EVENT_AP11_RELEASE,
                "target_id": ws.wip_id,
                "wip_id": ws.wip_id,
                "station_id": "AP11",
                "release_time_s": release_time_s,
            },
            subject_type="wip",
            subject_id=ws.wip_id,
            context=self._base_context(
                ctx, semantic_type="release", station_id="AP11",
                wip_id=ws.wip_id),
        )
        return {
            "reality": reality,
            "source_event_id": release_event_id,
            "station_order": station_order.get("AP11", 999),
            "kind_order": _KIND_RELEASE,
            "attempt": 1,
        }

    def _base_context(
        self, ctx: Any, semantic_type: str, station_id: str, **extra: Any,
    ) -> dict:
        context: dict[str, Any] = {
            "semantic_type": semantic_type,
            "station_id": station_id,
            "sub_line_id": ctx.identity.sub_line_id,
            "variant": ctx.identity.variant,
            "production_line_id": ctx.identity.production_line_id,
        }
        context.update({k: v for k, v in extra.items() if v is not None})
        return context

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
                        continue  # already delivered to this gateway
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
class AssyObservationPipeline:
    """Assembled downstream observation pipeline for the ASSY demo."""

    service: ObservationService
    router: ObservationRouter
    gateways: list[ObservationGatewayProtocol]
    bridge: AssyObservationBridge


def build_assy_observation_pipeline(
    gateways: Optional[list[ObservationGatewayProtocol]] = None,
    model_id: str = MODEL_ID,
) -> AssyObservationPipeline:
    """Build the M6-INT-01 observation pipeline.

    Default gateway: in-memory (test/demo).  Callers may supply
    InMemory / Jsonl / MQTT gateways.
    """
    service = ObservationService(
        points=build_assy_observation_points(),
        policy=ObservationPolicy.industrial(),
    )
    router = ObservationRouter()
    router.subscribe(ProjectionSubscription(
        projection=MESProjection(),
        observation_types=(ObservationType.EVENT,),
        source_domains=(SOURCE_DOMAIN,),
    ))
    gw = list(gateways) if gateways is not None else [InMemoryObsGateway()]
    bridge = AssyObservationBridge(
        service=service,
        router=router,
        gateways=gw,
        model_id=model_id,
    )
    return AssyObservationPipeline(
        service=service,
        router=router,
        gateways=gw,
        bridge=bridge,
    )
