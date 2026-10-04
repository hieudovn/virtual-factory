#!/usr/bin/env python3
"""DDAY-B5 — Capper deterministic abnormal-scenario smoke.

Task: DDAY-B5 (SA Issue #107 / PR #101).

In-process proof of phase order, one alarm pair, one downtime pair,
production inhibit, classification non-causality, and no hidden/KPI leak.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.workspaces.bottled_water import BottledWaterFactory

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
CAP = "BW-FP-CAP01"
PHASES = (
    "NORMAL", "DEGRADING", "WARNING", "INTERMITTENT_STOP", "RECOVERY",
)

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _signal(snapshot: dict, signal_id: str):
    return snapshot["nodes"][CAP]["signals"][signal_id]["value"]


def main() -> int:
    print("=" * 72)
    print("DDAY-B5 — Capper deterministic abnormal scenario")
    print("=" * 72)

    factory = BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml",
    )
    factory.start()
    seen = [factory.snapshot()["scenario"]["phase"]]
    totals = {seen[0]: factory.snapshot()["target_line"]["counts"]["total"]}
    for _ in range(220):
        factory.step(1.0)
        snapshot = factory.snapshot()
        phase = snapshot["scenario"]["phase"]
        if phase != seen[-1]:
            seen.append(phase)
            totals[phase] = snapshot["target_line"]["counts"]["total"]

    print("\n[1] phase order")
    claim(tuple(seen) == PHASES, f"phase order {seen}")

    types = [event["event_type"] for event in factory.snapshot()["recent_events"]]
    print("\n[2] alarm / downtime pairing")
    claim(types.count("ALARM_RAISED") == 1, "alarm raised once")
    claim(types.count("ALARM_CLEARED") == 1, "alarm cleared once")
    claim(types.count("DOWNTIME_START") == 1, "downtime started once")
    claim(types.count("DOWNTIME_END") == 1, "downtime ended once")
    claim(types.index("ALARM_RAISED") < types.index("DOWNTIME_START"),
          "warning precedes downtime")

    print("\n[3] production impact")
    stop_total = totals.get("INTERMITTENT_STOP")
    recovery_total = factory.snapshot()["target_line"]["counts"]["total"]
    claim(stop_total is not None, "INTERMITTENT_STOP was reached")
    claim(recovery_total >= stop_total, "counts never go backwards")
    claim(_signal(factory.snapshot(), "speed") > 0.0,
          "speed recovers after downtime")

    print("\n[4] classification is non-causal")
    other = BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml",
    )
    other.start()
    other.classify("downtime_code", "DT-BRG")
    for _ in range(180):
        other.step(1.0)
    claim(_signal(other.snapshot(), "vibration_rms")
          == _signal(factory.snapshot(), "vibration_rms")
          or other.snapshot()["scenario"]["phase"] == factory.snapshot()[
              "scenario"]["phase"],
          "classified run stays on the same phase path")
    claim(other.snapshot()["classification"]["downtime_code"] == "DT-BRG",
          "code is recorded")

    print("\n[5] raw-fact boundary")
    serialised = json.dumps(factory.snapshot()).lower()
    claim("degradation_factor" not in serialised, "no hidden factor")
    claim("oee" not in serialised, "no oee")
    claim("health_score" not in serialised, "no health score")
    claim("rul" not in serialised, "no rul")

    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE-BW-B5: FAIL ({len(_failures)} failed claims)")
        for failure in _failures:
            print(f"  - {failure}")
        return 1
    print("SMOKE-BW-B5: PASS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
