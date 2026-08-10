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
class ProductionSummary:
    """Production counters."""
    motors_created: int = 0     # AP04 joins completed
    motors_released: int = 0    # AP11 RELEASED
    wips_on_line: int = 0
    active_quality_holds: int = 0
    sso2_buffer: int = 0
    rso2_buffer: int = 0


@dataclass
class AssyDemoSnapshot:
    """Complete detached snapshot of the ASSY demo state.

    Built from AssyLineRuntime public API only.
    No mutable runtime references.
    """

    simulation_time_s: float = 0.0
    line_state: str = ""          # ConveyorState value
    dwell_number: int = 0
    nominal_dwell_s: float = 120.0
    positions: list[StationPositionView] = field(default_factory=list)
    genealogy: list[GenealogySummary] = field(default_factory=list)
    recent_quality_events: list[QualityEventView] = field(default_factory=list)
    production: ProductionSummary = field(default_factory=ProductionSummary)
    scenario: str = ""

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
                "sso2_buffer": self.production.sso2_buffer,
                "rso2_buffer": self.production.rso2_buffer,
            },
            "scenario": self.scenario,
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

    # Production summary
    holds = 0
    released = 0
    for wip_id in runtime.wip_ids:
        ws = runtime.get_wip(wip_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            released += 1
        qs = runtime.get_current_quality_status(wip_id)
        if qs in (QualityStatus.RETEST_PENDING, QualityStatus.REINSPECT_PENDING,
                   QualityStatus.FAILED_FINAL):
            holds += 1

    prod = ProductionSummary(
        motors_created=runtime.motor_count,
        motors_released=released,
        wips_on_line=len(runtime.conveyor.occupied_positions()),
        active_quality_holds=holds,
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
        production=prod,
        scenario=scenario,
    )
