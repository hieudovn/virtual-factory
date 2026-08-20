"""TIPA ASSY Customer Demo Scenario v1 — M5 pipeline bridge.

VF-DM-DEMO-ASSY-MES-01. Bridges authoritative DemoFacts through the EXISTING
M5 pipeline (RealityInput → ObservationService → ObservationRouter →
MESProjection → gateways). No pipeline core is redesigned.

Every message carries: idempotency key (stable), run_id, subline_id,
contract_version, station identity, WIP identity, simulated timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from virtual_factory.assembly.demo_assy_mes.model import (
    CONTRACT_VERSION,
    MODEL_ID,
    PLANT_ID,
    PRODUCTION_LINE_ID,
    SUB_LINE_ID,
    FactKind,
    DemoFact,
    occurred_at_for,
)
from virtual_factory.integration.gateway import DeliveryResult
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

SOURCE_TYPE = "assy_demo"
SOURCE_DOMAIN = "assy"

# FactKind → MES semantic_type (context.semantic_type)
_KIND_TO_SEMANTIC: dict[FactKind, str] = {
    FactKind.RUN_STATUS: "run_status",
    FactKind.ISSUE: "issue",
    FactKind.EXECUTION_EVENT: "execution_event",
    FactKind.QUALITY_RESULT: "quality_result",
    FactKind.GENEALOGY: "genealogy_relationship",
    FactKind.LINE_OUT: "execution_event",
    FactKind.OEE_SUMMARY: "oee_summary",
}

# Common fields every message must carry.
_COMMON = ("contract_version", "subline_id", "production_line_id", "plant_id")


def _point(point_id: str, label: str, event_types: tuple[str, ...],
           extract: tuple[str, ...]) -> ObservationPoint:
    """One ON_EVENT point with a default-deny FieldPolicy allow-list."""
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


def build_observation_points() -> list[ObservationPoint]:
    """Declare the demo P0 observation points (default-deny allow-lists)."""
    return [
        _point("assy.run_status", "ASSY line state change",
               ("LINE_STATE_CHANGED",),
               ("event_type", "line_state", "reason_code")),
        _point("assy.issue", "ASSY exception raised/resolved",
               ("EXCEPTION_RAISED", "EXCEPTION_RESOLVED"),
               ("event_type", "station_id", "wip_id", "reason_code")),
        _point("assy.execution_event", "ASSY operation / WIP / LINE_OUT",
               ("WIP_ENTERED", "OPERATION_COMPLETED", "REWORK_TRIGGERED",
                "LINE_OUT", "DOWNTIME_START", "DOWNTIME_END"),
               ("event_type", "station_id", "wip_id", "disposition",
                "attempt_number", "reason_code",
                "downtime_start_s", "downtime_end_s", "downtime_s")),
        _point("assy.quality_result", "ASSY quality result",
               ("QUALITY_RESULT", "AP11_FINAL_QC_PASS", "AP11_FINAL_QC_FAIL"),
               ("event_type", "station_id", "wip_id", "disposition",
                "attempt_number", "reason_code", "check_type",
                "is_terminal", "terminal_state")),
        _point("assy.genealogy", "AP04 assembly join genealogy",
               ("AP04_JOIN",),
               ("event_type", "child_wip_id", "parent_wip_ids",
                "relationship_type", "station_id", "wip_id")),
        _point("assy.oee_summary", "End-of-run OEE summary",
               ("OEE_SUMMARY",),
               ("event_type", "planned_s", "downtime_s", "run_s",
                "ideal_cycle_s", "actual_count", "good_count", "reject_count",
                "availability", "performance", "quality", "oee")),
    ]


@dataclass
class DemoPipeline:
    """Composes the existing M5 pipeline for the demo scenario."""

    service: ObservationService
    router: ObservationRouter
    gateways: list[Any] = field(default_factory=list)

    def emit(self, reality: RealityInput) -> list[DeliveryResult]:
        """ObservationService → ObservationRouter → gateways."""
        results: list[DeliveryResult] = []
        envelopes = self.service.collect(reality)
        for envelope in envelopes:
            for message in self.router.route(envelope):
                for gateway in self.gateways:
                    results.append(gateway.send(message))
        return results


def build_demo_pipeline(gateways: Optional[list] = None) -> DemoPipeline:
    """Build the demo pipeline (MESProjection + optional gateways)."""
    service = ObservationService(
        points=build_observation_points(),
        policy=ObservationPolicy.industrial(),
    )
    router = ObservationRouter()
    router.subscribe(ProjectionSubscription(
        projection=MESProjection(),
        observation_types=(ObservationType.EVENT,),
        source_domains=(SOURCE_DOMAIN,),
    ))
    gw = list(gateways) if gateways is not None else [InMemoryObsGateway()]
    return DemoPipeline(service=service, router=router, gateways=gw)


def fact_to_reality(fact: DemoFact, run_id: str) -> RealityInput:
    """Convert one authoritative DemoFact into a neutral RealityInput."""
    semantic_type = _KIND_TO_SEMANTIC[fact.fact_kind]
    source_data: dict[str, Any] = {
        "event_type": fact.event_type,
        "target_id": fact.wip_id or fact.station_id,
        "station_id": fact.station_id,
        "wip_id": fact.wip_id,
        "disposition": fact.disposition,
        "attempt_number": fact.attempt_number,
        "reason_code": fact.reason_code,
        "is_terminal": fact.is_terminal,
        "terminal_state": fact.terminal_state,
        "contract_version": CONTRACT_VERSION,
        "subline_id": SUB_LINE_ID,
        "production_line_id": PRODUCTION_LINE_ID,
        "plant_id": PLANT_ID,
    }
    source_data.update(fact.detail)

    context: dict[str, Any] = {
        "semantic_type": semantic_type,
        "station_id": fact.station_id,
        "subline_id": SUB_LINE_ID,
        "production_line_id": PRODUCTION_LINE_ID,
        "plant_id": PLANT_ID,
        "contract_version": CONTRACT_VERSION,
    }

    subject_id = fact.wip_id or None
    subject_type = "wip" if fact.wip_id else None

    return RealityInput(
        run_id=run_id,
        model_id=MODEL_ID,
        source_event_id=fact.source_event_id,
        source_type=SOURCE_TYPE,
        source_domain=SOURCE_DOMAIN,
        source_path=fact.station_id or SUB_LINE_ID,
        simulation_time_s=fact.simulation_time_s,
        category="industrial_event",
        occurred_at=occurred_at_for(fact.simulation_time_s),
        source_data=source_data,
        subject_type=subject_type,
        subject_id=subject_id,
        context=context,
    )
