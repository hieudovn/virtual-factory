"""TIPA ASSY Customer Demo Scenario v1 — deterministic scenario script.

VF-DM-DEMO-ASSY-MES-01. Produces the ordered list of authoritative DemoFacts
for a single resettable run:

  WIP 1 MTR-DEMO-001 — happy path, AP04 join, AP06/AP08/AP11 PASS, LINE_OUT GOOD.
  WIP 2 MTR-DEMO-002 — AP06 FAIL attempt 1 → rework → PASS attempt 2, LINE_OUT GOOD.
  WIP 3 MTR-DEMO-003 — AP05 jam → line FAULT → STOPPED → recover → RUNNING, LINE_OUT GOOD.
  WIP 4 MTR-DEMO-004 — AP11 final-QC FAIL (terminal), LINE_OUT REJECT.

Plus line-state, exception (AP05_JAM), and downtime facts.  The OEE summary
fact is appended by the runner from reconciled counters.

Deterministic: the same call returns the same facts in the same order.
"""

from __future__ import annotations

from virtual_factory.assembly.demo_assy_mes.model import (
    FactKind,
    DemoFact,
    LineOutDisposition,
    SUB_LINE_ID,
)

# (time_s, station_id, event_type, disposition, attempt, reason)
_HAPPY = (
    (20.0, "AP01", "OPERATION_COMPLETED", "", 0, ""),
    (40.0, "AP02", "OPERATION_COMPLETED", "", 0, ""),
    (60.0, "AP03", "OPERATION_COMPLETED", "", 0, ""),
    (80.0, "AP04", "AP04_JOIN", "", 0, ""),
    (100.0, "AP05", "OPERATION_COMPLETED", "", 0, ""),
    (120.0, "AP06", "QUALITY_RESULT", "PASS", 1, ""),
    (140.0, "AP07", "OPERATION_COMPLETED", "", 0, ""),
    (160.0, "AP08", "QUALITY_RESULT", "PASS", 1, ""),
    (180.0, "AP09", "OPERATION_COMPLETED", "", 0, ""),
    (200.0, "AP10", "OPERATION_COMPLETED", "", 0, ""),
    (220.0, "AP11", "AP11_FINAL_QC_PASS", "PASS", 1, ""),
)

_RETEST = (
    (260.0, "AP01", "OPERATION_COMPLETED", "", 0, ""),
    (280.0, "AP02", "OPERATION_COMPLETED", "", 0, ""),
    (300.0, "AP03", "OPERATION_COMPLETED", "", 0, ""),
    (320.0, "AP04", "AP04_JOIN", "", 0, ""),
    (340.0, "AP05", "OPERATION_COMPLETED", "", 0, ""),
    (360.0, "AP06", "QUALITY_RESULT", "FAIL", 1, ""),
    (370.0, "AP06", "REWORK_TRIGGERED", "", 1, ""),
    (390.0, "AP06", "QUALITY_RESULT", "PASS", 2, ""),
    (410.0, "AP07", "OPERATION_COMPLETED", "", 0, ""),
    (430.0, "AP08", "QUALITY_RESULT", "PASS", 1, ""),
    (450.0, "AP09", "OPERATION_COMPLETED", "", 0, ""),
    (470.0, "AP10", "OPERATION_COMPLETED", "", 0, ""),
    (490.0, "AP11", "AP11_FINAL_QC_PASS", "PASS", 1, ""),
)

_JAM_PRE = (
    (500.0, "AP01", "OPERATION_COMPLETED", "", 0, ""),
    (520.0, "AP02", "OPERATION_COMPLETED", "", 0, ""),
    (540.0, "AP03", "OPERATION_COMPLETED", "", 0, ""),
    (560.0, "AP04", "AP04_JOIN", "", 0, ""),
)

_JAM_POST = (
    (740.0, "AP05", "OPERATION_COMPLETED", "", 0, ""),
    (760.0, "AP06", "QUALITY_RESULT", "PASS", 1, ""),
    (780.0, "AP07", "OPERATION_COMPLETED", "", 0, ""),
    (800.0, "AP08", "QUALITY_RESULT", "PASS", 1, ""),
    (820.0, "AP09", "OPERATION_COMPLETED", "", 0, ""),
    (840.0, "AP10", "OPERATION_COMPLETED", "", 0, ""),
    (860.0, "AP11", "AP11_FINAL_QC_PASS", "PASS", 1, ""),
)

_REJECT = (
    (980.0, "AP01", "OPERATION_COMPLETED", "", 0, ""),
    (1000.0, "AP02", "OPERATION_COMPLETED", "", 0, ""),
    (1020.0, "AP03", "OPERATION_COMPLETED", "", 0, ""),
    (1040.0, "AP04", "AP04_JOIN", "", 0, ""),
    (1060.0, "AP05", "OPERATION_COMPLETED", "", 0, ""),
    (1080.0, "AP06", "QUALITY_RESULT", "PASS", 1, ""),
    (1100.0, "AP07", "OPERATION_COMPLETED", "", 0, ""),
    (1120.0, "AP08", "QUALITY_RESULT", "PASS", 1, ""),
    (1140.0, "AP09", "OPERATION_COMPLETED", "", 0, ""),
    (1160.0, "AP10", "OPERATION_COMPLETED", "", 0, ""),
    (1180.0, "AP11", "AP11_FINAL_QC_FAIL", "FAIL", 1, "final_qc_failed"),
)

# component parents per WIP (AP04 genealogy join)
_COMPONENTS = {
    "MTR-DEMO-001": ("SSO2-001", "RSO2-001"),
    "MTR-DEMO-002": ("SSO2-002", "RSO2-002"),
    "MTR-DEMO-003": ("SSO2-003", "RSO2-003"),
    "MTR-DEMO-004": ("SSO2-004", "RSO2-004"),
}


def _op_fact(wip: str, t: float, station: str, event: str,
             disposition: str, attempt: int, reason: str) -> DemoFact:
    if event == "AP04_JOIN":
        p1, p2 = _COMPONENTS[wip]
        return DemoFact(
            fact_kind=FactKind.GENEALOGY,
            source_event_id=f"{wip}:AP04",
            simulation_time_s=t,
            event_type="AP04_JOIN",
            station_id="AP04",
            wip_id=wip,
            subject_id=wip,
            detail={
                "child_wip_id": wip,
                "parent_wip_ids": [p1, p2],
                "relationship_type": "assembly_join",
            },
        )
    if event == "QUALITY_RESULT":
        station_kind = {"AP06": "TEST", "AP08": "VISION"}.get(station, "TEST")
        return DemoFact(
            fact_kind=FactKind.QUALITY_RESULT,
            source_event_id=f"{wip}:{station}:{attempt}",
            simulation_time_s=t,
            event_type="QUALITY_RESULT",
            station_id=station,
            wip_id=wip,
            subject_id=wip,
            disposition=disposition,
            attempt_number=attempt,
            reason_code=reason,
            detail={"check_type": station_kind},
        )
    if event == "REWORK_TRIGGERED":
        return DemoFact(
            fact_kind=FactKind.EXECUTION_EVENT,
            source_event_id=f"{wip}:{station}:REWORK:{attempt}",
            simulation_time_s=t,
            event_type="REWORK_TRIGGERED",
            station_id=station,
            wip_id=wip,
            subject_id=wip,
            attempt_number=attempt,
        )
    if event in ("AP11_FINAL_QC_PASS", "AP11_FINAL_QC_FAIL"):
        return DemoFact(
            fact_kind=FactKind.QUALITY_RESULT,
            source_event_id=f"{wip}:AP11:{attempt}",
            simulation_time_s=t,
            event_type=event,
            station_id="AP11",
            wip_id=wip,
            subject_id=wip,
            disposition=disposition,
            attempt_number=attempt,
            reason_code=reason,
            detail={"check_type": "FINAL_QC"},
        )
    return DemoFact(
        fact_kind=FactKind.EXECUTION_EVENT,
        source_event_id=f"{wip}:{station}:{attempt or 0}",
        simulation_time_s=t,
        event_type=event,
        station_id=station,
        wip_id=wip,
        subject_id=wip,
        disposition=disposition,
        attempt_number=attempt,
    )


def _emit_enter(facts: list[DemoFact], wip: str, t: float) -> None:
    facts.append(DemoFact(
        fact_kind=FactKind.EXECUTION_EVENT,
        source_event_id=f"{wip}:ENTER",
        simulation_time_s=t,
        event_type="WIP_ENTERED",
        station_id="PRE-ASSY",
        wip_id=wip,
        subject_id=wip,
    ))


def _emit_steps(facts: list[DemoFact], wip: str, steps: tuple) -> None:
    for t, station, event, disp, attempt, reason in steps:
        facts.append(_op_fact(wip, t, station, event, disp, attempt, reason))


def _emit_line_out(facts: list[DemoFact], wip: str, t: float,
                   disp: LineOutDisposition) -> None:
    facts.append(DemoFact(
        fact_kind=FactKind.LINE_OUT,
        source_event_id=f"{wip}:LINE_OUT",
        simulation_time_s=t,
        event_type="LINE_OUT",
        station_id="LINE_OUT",
        wip_id=wip,
        subject_id=wip,
        disposition=disp.value,
    ))


def build_scenario_facts() -> list[DemoFact]:
    """Return the ordered, deterministic DemoFacts for one full run."""
    facts: list[DemoFact] = []

    facts.append(DemoFact(
        fact_kind=FactKind.RUN_STATUS, source_event_id="LINE:RUNNING:0",
        simulation_time_s=0.0, event_type="LINE_STATE_CHANGED",
        station_id=SUB_LINE_ID, detail={"line_state": "running"},
    ))

    # WIP 1 — happy path
    _emit_enter(facts, "MTR-DEMO-001", 0.0)
    _emit_steps(facts, "MTR-DEMO-001", _HAPPY)
    _emit_line_out(facts, "MTR-DEMO-001", 240.0, LineOutDisposition.GOOD)

    # WIP 2 — AP06 fail/retest/pass
    _emit_enter(facts, "MTR-DEMO-002", 240.0)
    _emit_steps(facts, "MTR-DEMO-002", _RETEST)
    _emit_line_out(facts, "MTR-DEMO-002", 480.0, LineOutDisposition.GOOD)

    # WIP 3 — AP05 jam: pre steps, fault, downtime, recovery, post steps
    _emit_enter(facts, "MTR-DEMO-003", 480.0)
    _emit_steps(facts, "MTR-DEMO-003", _JAM_PRE)
    facts.append(DemoFact(
        fact_kind=FactKind.ISSUE, source_event_id="MTR-DEMO-003:AP05:JAM:RAISED",
        simulation_time_s=580.0, event_type="EXCEPTION_RAISED",
        station_id="AP05", wip_id="MTR-DEMO-003", subject_id="MTR-DEMO-003",
        reason_code="AP05_JAM",
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.RUN_STATUS, source_event_id="LINE:FAULT",
        simulation_time_s=600.0, event_type="LINE_STATE_CHANGED",
        station_id=SUB_LINE_ID, detail={"line_state": "fault"},
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.RUN_STATUS, source_event_id="LINE:STOPPED",
        simulation_time_s=600.0, event_type="LINE_STATE_CHANGED",
        station_id=SUB_LINE_ID, detail={"line_state": "stopped"},
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.EXECUTION_EVENT, source_event_id="DOWNTIME:AP05_JAM:START",
        simulation_time_s=600.0, event_type="DOWNTIME_START",
        station_id=SUB_LINE_ID, reason_code="AP05_JAM",
        detail={"downtime_start_s": 600.0},
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.ISSUE, source_event_id="MTR-DEMO-003:AP05:JAM:RESOLVED",
        simulation_time_s=720.0, event_type="EXCEPTION_RESOLVED",
        station_id="AP05", wip_id="MTR-DEMO-003", subject_id="MTR-DEMO-003",
        reason_code="AP05_JAM",
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.RUN_STATUS, source_event_id="LINE:RUNNING:1",
        simulation_time_s=720.0, event_type="LINE_STATE_CHANGED",
        station_id=SUB_LINE_ID, detail={"line_state": "running"},
    ))
    facts.append(DemoFact(
        fact_kind=FactKind.EXECUTION_EVENT, source_event_id="DOWNTIME:AP05_JAM:END",
        simulation_time_s=720.0, event_type="DOWNTIME_END",
        station_id=SUB_LINE_ID, reason_code="AP05_JAM",
        detail={"downtime_end_s": 720.0, "downtime_s": 120.0},
    ))
    _emit_steps(facts, "MTR-DEMO-003", _JAM_POST)
    _emit_line_out(facts, "MTR-DEMO-003", 880.0, LineOutDisposition.GOOD)

    # WIP 4 — terminal final-quality failure → reject
    _emit_enter(facts, "MTR-DEMO-004", 960.0)
    _emit_steps(facts, "MTR-DEMO-004", _REJECT)
    _emit_line_out(facts, "MTR-DEMO-004", 1200.0, LineOutDisposition.REJECT)

    return facts
