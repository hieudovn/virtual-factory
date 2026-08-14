"""M6-S04 — Detached demo snapshot for TIPA ASSY visualization.

Consumes AssyLineRuntime public API only.
Produces a serializable, detached read model.
Never holds mutable runtime references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime, ConveyorState, WipLifecycle,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.operation_execution import OperationExecution, OperationState


@dataclass
class StationPositionView:
    """One ASSY line position snapshot."""
    position_id: str = ""
    station_label: str = ""
    carrier_id: str = ""
    wip_id: str = ""
    wip_type: str = ""           # "SSO2", "MTR", ""
    manufacturing_status: str = ""  # WipLifecycle value
    quality_status: str = ""        # QualityStatus value
    latest_quality_result: str = ""  # "PASS", "FAIL", "NG", ""
    attempt_number: int = 0
    is_occupied: bool = False
    is_quality_hold: bool = False
    held_reason: str = ""

    @staticmethod
    def labels() -> dict[str, str]:
        return {
            "PRE-ASSY": "PRE-ASSY — Stator prep",
            "AP01": "AP01 — Fitting / preparation",
            "AP02": "AP02 — Terminal box wiring",
            "AP03": "AP03 — Mechanical prep + QC",
            "AP04": "AP04 — Main assembly / JOIN",
            "AP05": "AP05 — Assembly + painting + measurements",
            "AP06": "AP06 — Electrical / functional test",
            "AP07": "AP07 — Finishing / nameplate",
            "AP08": "AP08 — Visual inspection",
            "AP09": "AP09 — Boxing",
            "AP10": "AP10 — Closing / labeling / palletizing",
            "AP11": "AP11 — Final QC / release",
        }


@dataclass
class GenealogySummary:
    """AP04 genealogy snapshot."""
    child_wip_id: str = ""
    parent_wip_ids: list[str] = field(default_factory=list)
    component_ids: list[str] = field(default_factory=list)
    join_time_s: float = 0.0
    join_station: str = "AP04"


@dataclass
class QualityEventView:
    """Recent quality event for activity panel."""
    event_type: str = ""
    wip_id: str = ""
    station_id: str = ""
    disposition: str = ""
    attempt: int = 0
    simulation_time_s: float = 0.0


@dataclass
class QualityRecordView:
    """M6-S04B-I06-P01 — Detached read model of one quality record.

    Built from QualityRecord only.  No mutable runtime references.
    """
    record_id: str = ""
    wip_id: str = ""
    station_id: str = ""
    check_type: str = ""
    disposition: str = ""
    attempt_number: int = 0
    simulation_time_s: float = 0.0
    measurements: list[dict] = field(default_factory=list)
    checklist_items: list[str] = field(default_factory=list)
    reason_code: str = ""

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "wip_id": self.wip_id,
            "station_id": self.station_id,
            "check_type": self.check_type,
            "disposition": self.disposition,
            "attempt_number": self.attempt_number,
            "simulation_time_s": self.simulation_time_s,
            "measurements": self.measurements,
            "checklist_items": self.checklist_items,
            "reason_code": self.reason_code,
        }


@dataclass
class ProductionSummary:
    """Production counters."""
    motors_created: int = 0     # AP04 joins completed
    motors_released: int = 0    # AP11 RELEASED
    wips_on_line: int = 0
    active_quality_holds: int = 0   # RETEST_PENDING / REINSPECT_PENDING / FAILED_FINAL
    operator_holds: int = 0         # OPS-04-C01: HELD operations (operator/exception)
    sso2_buffer: int = 0
    rso2_buffer: int = 0


@dataclass
class ActiveOperationView:
    """OPS-02 — Detached read model of one active operation execution.

    Additive projection. Built from OperationExecution only.
    `positions[]` semantics are unchanged.
    """
    execution_id: str = ""
    station_id: str = ""
    wip_id: str = ""
    state: str = ""
    completion_mode: str = ""
    command: str = ""
    operation_result: str = ""
    quality_result: str = ""
    proposed_quality_result: str = ""
    routing_action: str = ""
    attempt_number: int = 0
    terminal: bool = False
    checklist: list = field(default_factory=list)
    measurements: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "station_id": self.station_id,
            "wip_id": self.wip_id,
            "state": self.state,
            "completion_mode": self.completion_mode,
            "command": self.command,
            "operation_result": self.operation_result,
            "quality_result": self.quality_result,
            "proposed_quality_result": self.proposed_quality_result,
            "routing_action": self.routing_action,
            "attempt_number": self.attempt_number,
            "terminal": self.terminal,
            "checklist": self.checklist,
            "measurements": self.measurements,
        }


@dataclass
class StationContractView:
    """OPS-03 — Detached read model of one station capability contract.

    Provides only what the interaction renderer needs: identity, capabilities,
    allowed/required action metadata, and neutral demo checklist item templates.
    """
    station_id: str = ""
    capabilities: dict = field(default_factory=dict)
    default_mode: str = ""
    required_action: str = ""
    normal_action: str = ""
    allowed_commands: list = field(default_factory=list)
    checklist_items: list = field(default_factory=list)
    checklist_required_for_action: str = ""
    decision_actions: list = field(default_factory=list)
    exception_actions: list = field(default_factory=list)
    final_disposition_actions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "capabilities": self.capabilities,
            "default_mode": self.default_mode,
            "required_action": self.required_action,
            "normal_action": self.normal_action,
            "allowed_commands": self.allowed_commands,
            "checklist_items": self.checklist_items,
            "checklist_required_for_action": self.checklist_required_for_action,
            "decision_actions": self.decision_actions,
            "exception_actions": self.exception_actions,
            "final_disposition_actions": self.final_disposition_actions,
        }


@dataclass
class AssyDemoSnapshot:
    """Complete detached snapshot of the ASSY demo state.

    Built from AssyLineRuntime public API only.
    No mutable runtime references.

    M6-S04B-I03: Additive identity fields — plant_id, production_line_id,
    sub_line_id, variant.  Existing S04 fields preserved.
    M6-S04B-I06-P01: Additive quality_records field.
    OPS-02: Additive active_operations field.
    """

    simulation_time_s: float = 0.0
    line_state: str = ""          # ConveyorState value
    dwell_number: int = 0
    nominal_dwell_s: float = 120.0
    positions: list[StationPositionView] = field(default_factory=list)
    genealogy: list[GenealogySummary] = field(default_factory=list)
    recent_quality_events: list[QualityEventView] = field(default_factory=list)
    quality_records: list[QualityRecordView] = field(default_factory=list)
    active_operations: list[ActiveOperationView] = field(default_factory=list)
    station_contracts: list[StationContractView] = field(default_factory=list)
    production: ProductionSummary = field(default_factory=ProductionSummary)
    scenario: str = ""

    # M6-S04B-I03 — additive identity fields
    plant_id: str = ""
    production_line_id: str = ""
    sub_line_id: str = ""
    variant: str = ""

    def to_dict(self) -> dict:
        return {
            "simulation_time_s": self.simulation_time_s,
            "line_state": self.line_state,
            "dwell_number": self.dwell_number,
            "nominal_dwell_s": self.nominal_dwell_s,
            "positions": [
                {
                    "position_id": p.position_id,
                    "station_label": p.station_label,
                    "carrier_id": p.carrier_id,
                    "wip_id": p.wip_id,
                    "wip_type": p.wip_type,
                    "manufacturing_status": p.manufacturing_status,
                    "quality_status": p.quality_status,
                    "latest_quality_result": p.latest_quality_result,
                    "attempt_number": p.attempt_number,
                    "is_occupied": p.is_occupied,
                    "is_quality_hold": p.is_quality_hold,
                    "held_reason": p.held_reason,
                }
                for p in self.positions
            ],
            "genealogy": [
                {
                    "child_wip_id": g.child_wip_id,
                    "parent_wip_ids": g.parent_wip_ids,
                    "component_ids": g.component_ids,
                    "join_time_s": g.join_time_s,
                    "join_station": g.join_station,
                }
                for g in self.genealogy
            ],
            "recent_quality_events": [
                {
                    "event_type": e.event_type,
                    "wip_id": e.wip_id,
                    "station_id": e.station_id,
                    "disposition": e.disposition,
                    "attempt": e.attempt,
                    "simulation_time_s": e.simulation_time_s,
                }
                for e in self.recent_quality_events[-20:]
            ],
            "production": {
                "motors_created": self.production.motors_created,
                "motors_released": self.production.motors_released,
                "wips_on_line": self.production.wips_on_line,
                "active_quality_holds": self.production.active_quality_holds,
                "operator_holds": self.production.operator_holds,
                "sso2_buffer": self.production.sso2_buffer,
                "rso2_buffer": self.production.rso2_buffer,
            },
            "scenario": self.scenario,
            "quality_records": [qr.to_dict() for qr in self.quality_records],
            # OPS-02 — additive active operations
            "active_operations": [ao.to_dict() for ao in self.active_operations],
            # OPS-03 — additive station contracts (renderer input)
            "station_contracts": [sc.to_dict() for sc in self.station_contracts],
            # M6-S04B-I03 — additive identity
            "plant_id": self.plant_id,
            "production_line_id": self.production_line_id,
            "sub_line_id": self.sub_line_id,
            "variant": self.variant,
        }


def build_snapshot(runtime: AssyLineRuntime, scenario: str = "") -> AssyDemoSnapshot:
    """Build a detached snapshot from the runtime (public API only)."""
    labels = StationPositionView.labels()

    positions: list[StationPositionView] = []
    quality_events: list[QualityEventView] = []

    for pos_id in runtime.conveyor.positions:
        carrier = runtime.conveyor.carrier_at(pos_id)
        wip_id = runtime.conveyor.wip_at(pos_id)
        pv = StationPositionView(
            position_id=pos_id,
            station_label=labels.get(pos_id, pos_id),
        )

        if wip_id:
            pv.is_occupied = True
            pv.wip_id = wip_id
            pv.wip_type = "MTR" if wip_id.startswith("MTR") else "SSO2"

            ws = runtime.get_wip(wip_id)
            if ws:
                pv.manufacturing_status = ws.lifecycle.value
                pv.carrier_id = str(carrier.carrier_id) if carrier else ""

            qstatus = runtime.get_current_quality_status(wip_id)
            pv.quality_status = qstatus.value

            qh = runtime.get_quality_history(wip_id)
            if qh:
                for rec in qh.records:
                    if rec.station_id == pos_id:
                        pv.latest_quality_result = rec.disposition
                        pv.attempt_number = rec.attempt_number
                        pv.is_quality_hold = qstatus in (
                            QualityStatus.RETEST_PENDING,
                            QualityStatus.REINSPECT_PENDING,
                            QualityStatus.FAILED_FINAL,
                        )
                        if pv.is_quality_hold:
                            pv.held_reason = f"{rec.disposition} (attempt {rec.attempt_number})"
                    # Collect recent quality events
                    quality_events.append(QualityEventView(
                        event_type=rec.check_type.value if hasattr(rec, 'check_type') else "",
                        wip_id=rec.wip_id,
                        station_id=rec.station_id,
                        disposition=rec.disposition,
                        attempt=rec.attempt_number,
                        simulation_time_s=rec.simulation_time_s,
                    ))

        positions.append(pv)

    # Genealogy
    genealogy = []
    for rec in runtime.genealogy.all_records():
        genealogy.append(GenealogySummary(
            child_wip_id=rec.child_wip_id,
            parent_wip_ids=list(rec.parent_wip_ids),
            component_ids=list(rec.component_ids),
            join_time_s=rec.join_time_s,
            join_station=rec.join_station,
        ))

    # Quality records — additive projection (M6-S04B-I06-P01)
    quality_records: list[QualityRecordView] = []
    for wip_id in runtime.wip_ids:
        qh = runtime.get_quality_history(wip_id)
        if qh:
            for rec in qh.records:
                quality_records.append(QualityRecordView(
                    record_id=rec.record_id,
                    wip_id=rec.wip_id,
                    station_id=rec.station_id,
                    check_type=rec.check_type.value if hasattr(rec.check_type, 'value') else str(rec.check_type),
                    disposition=rec.disposition,
                    attempt_number=rec.attempt_number,
                    simulation_time_s=rec.simulation_time_s,
                    measurements=[m.to_dict() for m in rec.measurements],
                    checklist_items=list(rec.checklist_items),
                    reason_code=rec.reason_code,
                ))

    # Active operations — additive projection (OPS-02)
    active_operations: list[ActiveOperationView] = []
    for op in runtime.active_operations():
        active_operations.append(ActiveOperationView(
            execution_id=op.execution_id,
            station_id=op.station_id,
            wip_id=op.wip_id,
            state=op.state.value if hasattr(op.state, "value") else str(op.state),
            completion_mode=op.completion_mode.value if hasattr(op.completion_mode, "value") else str(op.completion_mode),
            command=op.command.value if op.command and hasattr(op.command, "value") else (str(op.command) if op.command else ""),
            operation_result=op.operation_result.value if op.operation_result and hasattr(op.operation_result, "value") else (str(op.operation_result) if op.operation_result else ""),
            quality_result=op.quality_result or "",
            proposed_quality_result=op.proposed_quality_result or "",
            routing_action=op.routing_action or "",
            attempt_number=op.attempt_number,
            terminal=op.terminal,
            checklist=list(op.checklist),
            measurements=list(op.measurements),
        ))

    # Station contracts — additive projection (OPS-03)
    station_contracts: list[StationContractView] = []
    for contract in runtime.station_contracts.values():
        # OPS-03-C01: checklist items are exposed ONLY when the checklist is a
        # completion gate for a specific action (capability alone is NOT a gate).
        checklist_items: list[dict] = []
        if contract.checklist_required_for_action is not None:
            checklist_items = [
                {"item_id": item_id, "completed": False}
                for item_id in contract.checklist_items
            ]
        station_contracts.append(StationContractView(
            station_id=contract.station_id,
            capabilities={
                "execution": contract.capabilities.execution,
                "checklist": contract.capabilities.checklist,
                "measurement": contract.capabilities.measurement,
                "quality_decision": contract.capabilities.quality_decision,
                "exception": contract.capabilities.exception,
                "identity_transformation": contract.capabilities.identity_transformation,
                "final_disposition": contract.capabilities.final_disposition,
            },
            default_mode=contract.default_mode.value,
            required_action=contract.required_action.value if contract.required_action else "",
            normal_action=contract.normal_action.value if contract.normal_action else "",
            allowed_commands=[c.value for c in contract.allowed_commands],
            checklist_items=checklist_items,
            checklist_required_for_action=(
                contract.checklist_required_for_action.value
                if contract.checklist_required_for_action else ""
            ),
            decision_actions=list(contract.decision_actions),
            exception_actions=list(contract.exception_actions),
            final_disposition_actions=list(contract.final_disposition_actions),
        ))

    # Production summary
    holds = 0
    operator_holds = 0
    released = 0
    for wip_id in runtime.wip_ids:
        ws = runtime.get_wip(wip_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            released += 1
        qs = runtime.get_current_quality_status(wip_id)
        if qs in (QualityStatus.RETEST_PENDING, QualityStatus.REINSPECT_PENDING,
                   QualityStatus.FAILED_FINAL):
            holds += 1
    # OPS-04-C01 (B): operator/exception holds derived from OperationExecution.
    operator_holds = sum(
        1 for op in runtime.active_operations()
        if op.state == OperationState.HELD
    )

    prod = ProductionSummary(
        motors_created=runtime.motor_count,
        motors_released=released,
        wips_on_line=len(runtime.conveyor.occupied_positions()),
        active_quality_holds=holds,
        operator_holds=operator_holds,
        rso2_buffer=runtime.rso2_buffer_size,
    )

    return AssyDemoSnapshot(
        simulation_time_s=runtime.simulation_time_s,
        line_state=runtime.conveyor.state.value,
        dwell_number=runtime.conveyor.dwell_number,
        nominal_dwell_s=runtime.config.conveyor.nominal_line_dwell_time_s,
        positions=positions,
        genealogy=genealogy,
        recent_quality_events=quality_events,
        quality_records=quality_records,
        active_operations=active_operations,
        station_contracts=station_contracts,
        production=prod,
        scenario=scenario,
    )


# ═══════════════════════════════════════════════════════════
# M6-S04B-I03 — Overview Projection Models
# ═══════════════════════════════════════════════════════════

# Station order for held-station selection
_CANONICAL_STATION_ORDER = (
    "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
    "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
)

_HOLD_STATUSES = frozenset({
    QualityStatus.RETEST_PENDING,
    QualityStatus.REINSPECT_PENDING,
    QualityStatus.FAILED_FINAL,
})


@dataclass(frozen=True, slots=True)
class SubLineSummaryView:
    """Lightweight detached overview of one ASSY sub-line.

    Built from public runtime state only.  No mutable references.
    """

    plant_id: str
    production_line_id: str
    sub_line_id: str
    variant: str
    label: str

    effective_scenario: str

    line_state: str             # ConveyorState value
    dwell_number: int
    simulation_time_s: float

    wips_on_line: int
    motors_created: int
    motors_released: int

    active_quality_holds: int
    operator_holds: int
    held_station: str           # first blocking station, "" if none
    held_wip_id: str            # WIP at held station, "" if none
    is_exception: bool

    def to_dict(self) -> dict:
        return {
            "plant_id": self.plant_id,
            "production_line_id": self.production_line_id,
            "sub_line_id": self.sub_line_id,
            "variant": self.variant,
            "label": self.label,
            "effective_scenario": self.effective_scenario,
            "line_state": self.line_state,
            "dwell_number": self.dwell_number,
            "simulation_time_s": self.simulation_time_s,
            "wips_on_line": self.wips_on_line,
            "motors_created": self.motors_created,
            "motors_released": self.motors_released,
            "active_quality_holds": self.active_quality_holds,
            "operator_holds": self.operator_holds,
            "held_station": self.held_station,
            "held_wip_id": self.held_wip_id,
            "is_exception": self.is_exception,
        }


@dataclass(frozen=True, slots=True)
class AssyOverviewSnapshot:
    """Complete detached ASSY six-sub-line overview.

    Built from AssyDemoComposition public state only.
    No runtime references.  No global simulation_time_s.
    """

    demo_step_number: int
    scenario: str                  # global requested demo scenario
    target_sub_line_id: str
    selected_sub_line_id: str

    total_motors_created: int
    total_motors_released: int
    total_active_holds: int

    sub_lines: tuple[SubLineSummaryView, ...]

    def to_dict(self) -> dict:
        return {
            "demo_step_number": self.demo_step_number,
            "scenario": self.scenario,
            "target_sub_line_id": self.target_sub_line_id,
            "selected_sub_line_id": self.selected_sub_line_id,
            "total_motors_created": self.total_motors_created,
            "total_motors_released": self.total_motors_released,
            "total_active_holds": self.total_active_holds,
            "sub_lines": [s.to_dict() for s in self.sub_lines],
        }


def build_summary(ctx, plant_id: str) -> SubLineSummaryView:
    """Build a SubLineSummaryView from an AssyDemoContext (public API only)."""
    runtime = ctx.runtime
    identity = ctx.identity

    # Derive held station — first occupied blocking station in canonical order
    # OPS-04-C01 (B): operator HELD operations block just like quality holds.
    held_ops = {(op.station_id, op.wip_id)
                for op in runtime.active_operations()
                if op.state == OperationState.HELD}
    held_station = ""
    held_wip_id = ""
    for pos in _CANONICAL_STATION_ORDER:
        wip_id = runtime.conveyor.wip_at(pos)
        if wip_id:
            qs = runtime.get_current_quality_status(wip_id)
            if qs in _HOLD_STATUSES or (pos, wip_id) in held_ops:
                held_station = pos
                held_wip_id = wip_id
                break

    # Count active quality holds + operator holds
    holds = 0
    operator_holds = 0
    released = 0
    for wip_id in runtime.wip_ids:
        ws = runtime.get_wip(wip_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            released += 1
        qs = runtime.get_current_quality_status(wip_id)
        if qs in _HOLD_STATUSES:
            holds += 1
    operator_holds = sum(
        1 for op in runtime.active_operations()
        if op.state == OperationState.HELD
    )

    occupied = runtime.conveyor.occupied_positions()

    return SubLineSummaryView(
        plant_id=plant_id,
        production_line_id=identity.production_line_id,
        sub_line_id=identity.sub_line_id,
        variant=identity.variant,
        label=identity.label,
        effective_scenario=ctx.effective_scenario.value,
        line_state=runtime.conveyor.state.value,
        dwell_number=runtime.conveyor.dwell_number,
        simulation_time_s=runtime.simulation_time_s,
        wips_on_line=len(occupied),
        motors_created=runtime.motor_count,
        motors_released=released,
        active_quality_holds=holds,
        operator_holds=operator_holds,
        held_station=held_station,
        held_wip_id=held_wip_id,
        is_exception=(holds > 0 or operator_holds > 0),
    )


def build_overview(composition) -> AssyOverviewSnapshot:
    """Build an AssyOverviewSnapshot from an AssyDemoComposition."""
    identity = composition.identity
    plant_id = identity.plant_id if identity else "TIPA"
    summaries: list[SubLineSummaryView] = []
    total_created = 0
    total_released = 0
    total_holds = 0
    total_operator_holds = 0

    for ctx in composition.contexts.values():
        s = build_summary(ctx, plant_id)
        summaries.append(s)
        total_created += s.motors_created
        total_released += s.motors_released
        total_holds += s.active_quality_holds
        total_operator_holds += s.operator_holds

    return AssyOverviewSnapshot(
        demo_step_number=composition.demo_step_number,
        scenario=composition.scenario.value,
        target_sub_line_id=composition.target_sub_line_id,
        selected_sub_line_id=composition.selected_sub_line_id,
        total_motors_created=total_created,
        total_motors_released=total_released,
        total_active_holds=total_holds + total_operator_holds,
        sub_lines=tuple(summaries),
    )
