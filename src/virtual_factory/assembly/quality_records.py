"""Quality records and state model for the ASSY line.

M6-S03: Quality domain concepts — records, attempts, history.
Separate from manufacturing WIP lifecycle (WipLifecycle).

Concepts:
- QualityStatus: CLEAR, HOLD, RETEST_PENDING, REINSPECT_PENDING, FAILED_FINAL
- QualityRecord: one quality decision at a station
- QualityHistory: per-WIP store of all quality records
- MeasurementValue: a single measurement with value, unit, expected range
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════
# Quality Status
# ═══════════════════════════════════════════════════════════

class QualityStatus(str, enum.Enum):
    """Quality state — separate from manufacturing lifecycle."""
    CLEAR = "clear"                      # no quality issue
    HOLD = "hold"                        # pending quality resolution
    RETEST_PENDING = "retest_pending"    # AP06: fail, awaiting retest
    REINSPECT_PENDING = "reinspect_pending"  # AP08: NG, awaiting reinspect
    FAILED_FINAL = "failed_final"        # max attempts exhausted


# ═══════════════════════════════════════════════════════════
# Check Type
# ═══════════════════════════════════════════════════════════

class CheckType(str, enum.Enum):
    """Type of quality check."""
    CHECKLIST = "CHECKLIST"
    MEASUREMENT = "MEASUREMENT"
    TEST = "TEST"
    VISUAL_INSPECTION = "VISUAL_INSPECTION"
    FINAL_QC = "FINAL_QC"


# ═══════════════════════════════════════════════════════════
# Measurement
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class MeasurementValue:
    """A single measurement result.  DEMO_SYNTHETIC values."""
    name: str
    value: float
    unit: str = ""
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None

    @property
    def in_range(self) -> bool:
        if self.expected_min is not None and self.value < self.expected_min:
            return False
        if self.expected_max is not None and self.value > self.expected_max:
            return False
        return True

    def to_dict(self) -> dict:
        d = {"name": self.name, "value": self.value, "unit": self.unit}
        if self.expected_min is not None:
            d["expected_min"] = self.expected_min
        if self.expected_max is not None:
            d["expected_max"] = self.expected_max
        return d


# ═══════════════════════════════════════════════════════════
# Quality Record
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class QualityRecord:
    """Immutable record of one quality check/decision."""

    record_id: str
    wip_id: str
    station_id: str
    check_type: CheckType
    disposition: str  # "PASS", "FAIL", "NG", "HOLD"
    attempt_number: int = 1
    simulation_time_s: float = 0.0
    measurements: tuple[MeasurementValue, ...] = ()
    checklist_items: tuple[str, ...] = ()
    reason_code: str = ""

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "wip_id": self.wip_id,
            "station_id": self.station_id,
            "check_type": self.check_type.value,
            "disposition": self.disposition,
            "attempt_number": self.attempt_number,
            "simulation_time_s": self.simulation_time_s,
            "measurements": [m.to_dict() for m in self.measurements],
            "checklist_items": list(self.checklist_items),
            "reason_code": self.reason_code,
        }


# ═══════════════════════════════════════════════════════════
# Quality History
# ═══════════════════════════════════════════════════════════

@dataclass
class QualityHistory:
    """Per-WIP store of all quality records, indexed by station + attempt."""

    _records: list[QualityRecord] = field(default_factory=list)
    _current_status: QualityStatus = QualityStatus.CLEAR
    _attempts_by_station: dict[str, int] = field(default_factory=dict)

    @property
    def current_status(self) -> QualityStatus:
        return self._current_status

    @property
    def records(self) -> tuple[QualityRecord, ...]:
        return tuple(self._records)

    def add_record(self, record: QualityRecord) -> None:
        """Append a quality record and update status."""
        self._records.append(record)
        self._attempts_by_station[record.station_id.lower()] = record.attempt_number

    def set_status(self, status: QualityStatus) -> None:
        self._current_status = status

    def attempt_count(self, station_id: str) -> int:
        """How many attempts at this station so far."""
        return self._attempts_by_station.get(station_id.lower(), 0)

    def records_for(self, station_id: str) -> tuple[QualityRecord, ...]:
        return tuple(r for r in self._records if r.station_id == station_id.upper() or r.station_id == station_id)

    def last_disposition(self, station_id: str) -> Optional[str]:
        for r in reversed(self._records):
            if r.station_id == station_id:
                return r.disposition
        return None

    def __len__(self) -> int:
        return len(self._records)


# ═══════════════════════════════════════════════════════════
# Quality Config
# ═══════════════════════════════════════════════════════════

@dataclass
class StationQualityConfig:
    """Quality configuration for one station."""
    max_attempts: int = 1
    scenario: str = "PASS"  # "PASS", "FAIL_FIRST_THEN_PASS", "ALWAYS_FAIL"
    # Overrides: dict[wip_seq_number → list of dispositions per attempt]
    overrides: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class QualityConfig:
    """Quality configuration for the entire ASSY line."""
    ap03: StationQualityConfig = field(default_factory=lambda: StationQualityConfig(max_attempts=1, scenario="PASS"))
    ap06: StationQualityConfig = field(default_factory=lambda: StationQualityConfig(max_attempts=2, scenario="PASS"))
    ap08: StationQualityConfig = field(default_factory=lambda: StationQualityConfig(max_attempts=2, scenario="PASS"))
    ap11: StationQualityConfig = field(default_factory=lambda: StationQualityConfig(max_attempts=1, scenario="PASS"))

    def get(self, station_id: str) -> StationQualityConfig:
        key = station_id.lower().replace("-", "")
        for attr in ("ap03", "ap06", "ap08", "ap11"):
            if attr == key:
                return getattr(self, attr)
        return StationQualityConfig(max_attempts=1, scenario="PASS")


# ═══════════════════════════════════════════════════════════
# Quality Scenario Resolver
# ═══════════════════════════════════════════════════════════

def resolve_quality_disposition(
    station_id: str,
    wip_motor_seq: int,  # 1-based motor sequence number
    attempt: int,
    config: StationQualityConfig,
) -> str:
    """Determine the quality disposition for this attempt.

    Checks overrides first (by motor sequence), then falls back to scenario.
    Returns "PASS", "FAIL", or "NG".
    """
    # Check per-motor overrides
    overrides = config.overrides.get(wip_motor_seq)
    if overrides and attempt <= len(overrides):
        return overrides[attempt - 1]

    # Scenario-based
    if config.scenario == "PASS":
        return "PASS"
    elif config.scenario == "FAIL_FIRST_THEN_PASS":
        return "FAIL" if attempt == 1 else "PASS"
    elif config.scenario == "ALWAYS_FAIL":
        return "FAIL"
    return "PASS"
