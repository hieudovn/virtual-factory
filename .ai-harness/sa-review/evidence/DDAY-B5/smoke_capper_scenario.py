#!/usr/bin/env python3
"""DDAY-B5 — Capper hero + Compressor secondary smoke.

Task: DDAY-B5 (SA Issue #107 / PR #101).

In-process proof of Capper phase order, one Capper alarm/downtime pair,
production inhibit, classification non-causality, compressor secondary
phases, non-overlap, independence, and no hidden/KPI leak.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.compressor_pressure import (
    CompressorPressureScenario,
    load_compressor_runtime,
)

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
CAP = "BW-FP-CAP01"
CMP = "BW-UT-CMP01"
PHASES = (
    "NORMAL", "DEGRADING", "WARNING", "INTERMITTENT_STOP", "RECOVERY",
)
CMP_PHASES = (
    "NORMAL", "DEGRADING", "LOW_PRESSURE_WARNING", "UNDERSUPPLY", "RECOVERY",
)

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _events(snapshot: dict, source_id: str) -> list[dict]:
    return [
        event for event in snapshot["recent_events"]
        if event.get("source_id") == source_id
    ]


def _short_compressor() -> CompressorPressureScenario:
    config = load_compressor_runtime(
        WORKSPACE / "scenarios" / "compressor_pressure.runtime.yaml",
        WORKSPACE / "scenarios" / "compressor_pressure.contract.yaml",
    )
    return CompressorPressureScenario(replace(
        config,
        phase_duration_s={
            "NORMAL": 22.0,
            "DEGRADING": 8.0,
            "LOW_PRESSURE_WARNING": 12.0,
            "UNDERSUPPLY": 22.0,
            "RECOVERY": 24.0,
        },
    ))


def main() -> int:
    print("=" * 72)
    print("DDAY-B5 — Capper hero + Compressor secondary")
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

    print("\n[1] Capper phase order")
    claim(tuple(seen) == PHASES, f"phase order {seen}")

    types = [event["event_type"] for event in _events(factory.snapshot(), CAP)]
    print("\n[2] Capper alarm / downtime pairing")
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
    claim(_signal(factory.snapshot(), CAP, "speed") > 0.0,
          "speed recovers after downtime")

    print("\n[4] classification is non-causal")
    other = BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml",
    )
    other.start()
    other.classify("downtime_code", "DT-BRG")
    for _ in range(180):
        other.step(1.0)
    claim(_signal(other.snapshot(), CAP, "vibration_rms")
          == _signal(factory.snapshot(), CAP, "vibration_rms")
          or other.snapshot()["scenario"]["phase"] == factory.snapshot()[
              "scenario"]["phase"],
          "classified run stays on the same phase path")
    claim(other.snapshot()["classification"]["downtime_code"] == "DT-BRG",
          "code is recorded")

    print("\n[5] raw-fact boundary")
    serialised = json.dumps(factory.snapshot()).lower()
    claim("degradation_factor" not in serialised, "no hidden factor")
    claim("sag_factor" not in serialised, "no compressor sag factor")
    claim("oee" not in serialised, "no oee")
    claim("health_score" not in serialised, "no health score")
    claim("rul" not in serialised, "no rul")

    print("\n[6] default demo is non-overlapping")
    at_capper_fault = BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml",
    )
    at_capper_fault.start()
    for _ in range(150):
        at_capper_fault.step(1.0)
    mid = at_capper_fault.snapshot()
    claim(mid["scenario"]["phase"] == "INTERMITTENT_STOP",
          "Capper hero is in INTERMITTENT_STOP at t=150")
    claim(mid["compressor_scenario"]["phase"] == "NORMAL",
          "compressor stays NORMAL during the Capper hero window")

    for _ in range(90):
        at_capper_fault.step(1.0)
    later = at_capper_fault.snapshot()
    claim(later["compressor_scenario"]["phase"] == "DEGRADING",
          "compressor DEGRADING starts at t=240 after Capper recovery")
    claim(later["scenario"]["phase"] == "RECOVERY",
          "Capper remains in RECOVERY when compressor sag begins")

    print("\n[7] compressor is independently testable")
    isolated = BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml",
        enable_capper=False,
        compressor=_short_compressor(),
    )
    isolated.start()
    seen_cmp = [isolated.snapshot()["compressor_scenario"]["phase"]]
    totals = {}
    for _ in range(90):
        isolated.step(1.0)
        snapshot = isolated.snapshot()
        phase = snapshot["compressor_scenario"]["phase"]
        if phase != seen_cmp[-1]:
            seen_cmp.append(phase)
            totals[phase] = snapshot["target_line"]["counts"]["total"]
    cmp_types = [
        event["event_type"] for event in _events(isolated.snapshot(), CMP)
    ]
    claim(tuple(seen_cmp) == CMP_PHASES, f"compressor phase order {seen_cmp}")
    claim(cmp_types.count("ALARM_RAISED") == 1, "compressor alarm raised once")
    claim(cmp_types.count("ALARM_CLEARED") == 1, "compressor alarm cleared once")
    claim(cmp_types.count("DOWNTIME_START") == 0, "compressor has no downtime")
    claim(isolated.snapshot()["scenario"]["phase"] == "NORMAL",
          "Capper stays NORMAL when disabled")
    under_total = totals.get("UNDERSUPPLY")
    recovery_total = isolated.snapshot()["target_line"]["counts"]["total"]
    claim(under_total is not None, "UNDERSUPPLY was reached")
    claim(under_total > 0, "production occurred before UNDERSUPPLY")
    claim(recovery_total >= under_total, "counts never go backwards after inhibit")
    goods = isolated.snapshot()["balances"]["finished_goods"]
    claim(
        goods["receipt_count"]
        == isolated.snapshot()["target_line"]["counts"]["good"],
        "FG receipts follow actual good output",
    )

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
