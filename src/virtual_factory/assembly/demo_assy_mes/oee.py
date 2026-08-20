"""TIPA ASSY Customer Demo Scenario v1 — OEE reconciliation.

VF-DM-DEMO-ASSY-MES-01. OEE is computed from simulated data:
  planned = run + downtime
  actual  = good + reject
  A = run / planned
  P = ideal_cycle * actual / run
  Q = good / actual
  OEE = A * P * Q

Reference for the demo timeline: planned 1200s, downtime 120s, run 1080s,
ideal cycle 240s, actual 4, good 3, reject 1 → OEE ≈ 60%.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OeeSummary:
    planned_s: float
    downtime_s: float
    run_s: float
    ideal_cycle_s: float
    actual_count: int
    good_count: int
    reject_count: int

    @property
    def availability(self) -> float:
        return self.run_s / self.planned_s if self.planned_s > 0 else 0.0

    @property
    def performance(self) -> float:
        return (self.ideal_cycle_s * self.actual_count / self.run_s) if self.run_s > 0 else 0.0

    @property
    def quality(self) -> float:
        return self.good_count / self.actual_count if self.actual_count > 0 else 0.0

    @property
    def oee(self) -> float:
        return self.availability * self.performance * self.quality

    def to_dict(self) -> dict:
        return {
            "planned_s": self.planned_s,
            "downtime_s": self.downtime_s,
            "run_s": self.run_s,
            "ideal_cycle_s": self.ideal_cycle_s,
            "actual_count": self.actual_count,
            "good_count": self.good_count,
            "reject_count": self.reject_count,
            "availability": round(self.availability, 6),
            "performance": round(self.performance, 6),
            "quality": round(self.quality, 6),
            "oee": round(self.oee, 6),
        }


def compute_oee(
    planned_s: float,
    downtime_s: float,
    ideal_cycle_s: float,
    actual_count: int,
    good_count: int,
    reject_count: int,
) -> OeeSummary:
    """Compute OEE from simulated data; run = planned - downtime."""
    run_s = max(0.0, planned_s - downtime_s)
    return OeeSummary(
        planned_s=planned_s,
        downtime_s=downtime_s,
        run_s=run_s,
        ideal_cycle_s=ideal_cycle_s,
        actual_count=actual_count,
        good_count=good_count,
        reject_count=reject_count,
    )
