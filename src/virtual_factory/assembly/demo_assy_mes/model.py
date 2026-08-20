"""TIPA ASSY Customer Demo Scenario v1 — domain model.

VF-DM-DEMO-ASSY-MES-01. Deterministic, resettable single-sub-line demo.
Contract version: ``tipa-assy-demo-v1``.

This module only defines the scenario's domain vocabulary (enums + dataclasses).
It does NOT touch the discrete simulation engine, the observation pipeline
core, or any gateway.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

CONTRACT_VERSION = "tipa-assy-demo-v1"
SUB_LINE_ID = "ASSY-SL01"
PRODUCTION_LINE_ID = "ASSY"
PLANT_ID = "TIPA"
MODEL_ID = "tipa-assy-demo-v1"


class LineState(str, enum.Enum):
    """Customer-visible line state (demo orchestration, not engine status)."""

    RUNNING = "running"
    FAULT = "fault"
    STOPPED = "stopped"


class LineOutDisposition(str, enum.Enum):
    """Physical LINE_OUT disposition."""

    GOOD = "good"
    REJECT = "reject"


class StationKind(str, enum.Enum):
    PRE_ASSY = "pre_assy"
    PROCESS = "process"
    JOIN = "join"
    TEST = "test"
    VISION = "vision"
    FINAL_QC = "final_qc"
    LINE_OUT = "line_out"


@dataclass(frozen=True)
class Station:
    """A single station on the ASSY-SL01 line."""

    station_id: str
    label: str
    kind: StationKind


# The 12 process stations + LINE_OUT for the single sub-line ASSY-SL01.
STATIONS: tuple[Station, ...] = (
    Station("PRE-ASSY", "Stator prep", StationKind.PRE_ASSY),
    Station("AP01", "Stator assembly", StationKind.PROCESS),
    Station("AP02", "Terminal box", StationKind.PROCESS),
    Station("AP03", "Mechanical check", StationKind.PROCESS),
    Station("AP04", "Assembly join", StationKind.JOIN),
    Station("AP05", "Mechanical assembly", StationKind.PROCESS),
    Station("AP06", "Electrical test", StationKind.TEST),
    Station("AP07", "Finish", StationKind.PROCESS),
    Station("AP08", "Vision check", StationKind.VISION),
    Station("AP09", "Boxing", StationKind.PROCESS),
    Station("AP10", "Pack / label", StationKind.PROCESS),
    Station("AP11", "Final QC", StationKind.FINAL_QC),
    Station("LINE_OUT", "Line out", StationKind.LINE_OUT),
)

STATION_IDS: tuple[str, ...] = tuple(s.station_id for s in STATIONS)


class FactKind(str, enum.Enum):
    """Kind of authoritative outbound fact emitted by the demo scenario."""

    RUN_STATUS = "run_status"
    ISSUE = "issue"
    EXECUTION_EVENT = "execution_event"
    QUALITY_RESULT = "quality_result"
    GENEALOGY = "genealogy_relationship"
    LINE_OUT = "line_out"
    OEE_SUMMARY = "oee_summary"


@dataclass(frozen=True)
class DemoFact:
    """One authoritative domain fact, ready to bridge into the M5 pipeline."""

    fact_kind: FactKind
    source_event_id: str
    simulation_time_s: float
    event_type: str
    station_id: str = ""
    wip_id: str = ""
    subject_id: str = ""
    disposition: str = ""
    attempt_number: int = 0
    reason_code: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "fact_kind": self.fact_kind.value,
            "source_event_id": self.source_event_id,
            "simulation_time_s": self.simulation_time_s,
            "event_type": self.event_type,
            "station_id": self.station_id,
            "wip_id": self.wip_id,
            "subject_id": self.subject_id,
            "disposition": self.disposition,
            "attempt_number": self.attempt_number,
            "reason_code": self.reason_code,
        }
        d.update(self.detail)
        return d


@dataclass(frozen=True)
class ScenarioSpec:
    """Static, deterministic scenario specification.

    Timings are simulated seconds.  The OEE reference (planned 1200s,
    downtime 120s, run 1080s, ideal cycle 240s, actual 4, good 3, reject 1)
    is RECONCILED from the simulated data, not hard-coded into the math.
    """

    planned_s: float = 1200.0
    ideal_cycle_s: float = 240.0
    downtime_intervals: tuple[tuple[float, float], ...] = ((600.0, 720.0),)


@dataclass
class WipJourney:
    """Deterministic journey of one WIP through the line.

    Each tuple is (simulation_time_s, station_id, event_type, disposition,
    attempt_number, reason_code).  The runner expands these into DemoFacts.
    """

    wip_id: str
    component_ids: tuple[str, ...]
    line_out: LineOutDisposition
    steps: tuple[tuple[float, str, str, str, int, str], ...] = ()
