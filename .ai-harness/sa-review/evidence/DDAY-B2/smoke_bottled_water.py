#!/usr/bin/env python3
"""DDAY-B2 — live Bottled Water hero-line runtime smoke check.

Task: DDAY-B2 (SA Issue #102 / PR #101).
Contract: .ai-harness/tasks/DDAY-B2.json

Proves, against the real reused discrete runtime (no mocks):

    START -> automatic unit progression -> Inspection result -> good/reject
          -> downstream completion
    PAUSE   -> no progression
    RESUME  -> continues from the preserved state
    RESET   -> known initial state

Exit code 0 = every claim proven. Any failed claim exits non-zero.

The smoke is fully deterministic: it is a step-driven simulation with a fixed
seed and no wall-clock dependency. The rejected-unit case is expressed as a
derived configuration file (a deterministic inspection override), not as a
private runtime mutation.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.assembly.demo_controller import DemoController  # noqa: E402
from virtual_factory.assembly.line_runtime import LineRunState  # noqa: E402

CONFIG_PATH = (
    REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
)

EXPECTED_ROUTE = [
    "BW-FP-BLW01", "BW-FP-RIN01", "BW-FP-FIL01", "BW-FP-CAP01",
    "BW-FP-INS01", "BW-FP-LAB01", "BW-FP-CPK01", "BW-FP-PAL01",
]
INSPECTION = "BW-FP-INS01"

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _write_failing_inspection_config(directory: Path) -> Path:
    """Derive a config where the Inspection checkpoint always fails.

    Deterministic by construction: the override is data, not behaviour, and the
    shipped workspace config stays PASS.
    """
    text = CONFIG_PATH.read_text(encoding="utf-8")
    derived = text.replace(
        "    check_type: VISUAL_INSPECTION\n"
        "    on_fail: reject\n"
        "    max_attempts: 1\n"
        "    scenario: PASS\n",
        "    check_type: VISUAL_INSPECTION\n"
        "    on_fail: reject\n"
        "    max_attempts: 1\n"
        "    scenario: ALWAYS_FAIL\n",
        1,
    )
    if derived == text:
        raise RuntimeError("could not derive the failing-inspection configuration")
    path = directory / "line-inspection-fail.yaml"
    path.write_text(derived, encoding="utf-8")
    return path


def main() -> int:
    print("=" * 72)
    print("DDAY-B2 — Bottled Water hero line runtime smoke")
    print(f"config: {CONFIG_PATH}")
    print("=" * 72)

    # ── 1. START ────────────────────────────────────────────────────────────
    print("\n[1] START")
    ctrl = DemoController(config_path=str(CONFIG_PATH))
    ctrl.initialize()
    claim(ctrl.is_generic_line, "configuration selects the generic line profile")
    claim(ctrl.run_state == LineRunState.STOPPED, "line starts STOPPED")

    facts = ctrl.line_facts()
    claim(facts["route"] == EXPECTED_ROUTE, "route is the frozen 8-station order")
    claim(facts["line_id"] == "BW-FP", "line identity is BW-FP")
    claim(facts["unit_type"] == "bottle", "unit_type=bottle")
    claim(facts["product_code"] == "WATER-500ML", "product_code=WATER-500ML")

    ctrl.advance()
    claim(ctrl.run_state == LineRunState.STOPPED, "no progression before START")
    claim(ctrl.line_facts()["total_count"] == 0, "no unit produced before START")

    ctrl.start()
    claim(ctrl.run_state == LineRunState.RUNNING, "START enters RUNNING")

    # ── 2. Automatic unit progression ───────────────────────────────────────
    print("\n[2] automatic unit progression")
    for _ in range(8):
        ctrl.advance()
    facts = ctrl.line_facts()
    claim(facts["total_count"] == 8, "8 units released automatically")
    claim(facts["dwell_number"] == 8, "8 dwells executed")
    claim(facts["simulation_time_s"] == 160.0, "simulation time = 8 x 20.0 s")
    claim(facts["units_on_line"] == 7, "7 units on the line after 8 cycles")

    visited = [
        e.position for e in ctrl.line.trace
        if e.wip_id == "BTL-000001" and e.event_type in ("UNIT_ENTERED", "WIP_MOVED")
    ]
    claim(visited == EXPECTED_ROUTE,
          "unit BTL-000001 traversed the full route in the frozen order")

    # ── 3. Inspection result -> good / reject -> downstream completion ──────
    print("\n[3] Inspection result and downstream completion")
    quality = [e for e in ctrl.line.trace
               if e.event_type == "QUALITY_RESULT" and e.position == INSPECTION]
    claim(bool(quality), "Inspection produced an automatic quality result")
    claim(ctrl.line.last_quality_disposition(INSPECTION) == "PASS",
          "Inspection verdict is PASS for the nominal configuration")

    completed = [e for e in ctrl.line.trace if e.event_type == "UNIT_COMPLETED"]
    claim(len(completed) == 1 and completed[0].position == EXPECTED_ROUTE[-1],
          "BTL-000001 completed downstream at the Palletizer")
    claim(facts["good_count"] == 1 and facts["reject_count"] == 0,
          "counts: good=1 reject=0")

    print("\n[3b] rejected unit is ejected and never counted good")
    with tempfile.TemporaryDirectory(prefix="dday-b2-smoke-") as tmp:
        fail_path = _write_failing_inspection_config(Path(tmp))
        reject_ctrl = DemoController(config_path=str(fail_path))
        reject_ctrl.initialize()
        reject_ctrl.start()
        for _ in range(12):
            reject_ctrl.advance()

        rf = reject_ctrl.line_facts()
        rejects = [e for e in reject_ctrl.line.trace if e.event_type == "REJECT"]
        claim(bool(rejects) and all(e.position == INSPECTION for e in rejects),
              "failed Inspection ejected the unit at the Inspection station")
        claim(rf["reject_count"] == 8, "8 units rejected")
        claim(rf["good_count"] == 0, "no rejected unit counted good")
        claim(
            [e for e in reject_ctrl.line.trace
             if e.event_type == "UNIT_COMPLETED"] == [],
            "no rejected unit reached downstream completion")
        claim(rf["good_count"] + rf["reject_count"] <= rf["total_count"],
              "count invariant good + reject <= total holds")
        claim(rf["units_on_line"] == 4 and rf["total_count"] == 12,
              "line kept running after rejects (4 in progress, 12 produced)")

    # ── 4. PAUSE -> no progression ──────────────────────────────────────────
    print("\n[4] PAUSE freezes progression")
    before = ctrl.line_facts()
    ctrl.pause()
    for _ in range(5):
        ctrl.advance()
    after = ctrl.line_facts()
    claim(ctrl.run_state == LineRunState.PAUSED, "PAUSE enters PAUSED")
    claim(after["simulation_time_s"] == before["simulation_time_s"],
          "simulation time frozen")
    claim(after["positions"] == before["positions"], "unit positions frozen")
    claim(after["total_count"] == before["total_count"], "counts frozen")

    # ── 5. RESUME -> continues ──────────────────────────────────────────────
    print("\n[5] RESUME continues from the preserved state")
    resumed_time = before["simulation_time_s"] + 20.0
    ctrl.resume()
    claim(ctrl.run_state == LineRunState.RUNNING, "RESUME enters RUNNING")
    ctrl.advance()
    resumed = ctrl.line_facts()
    claim(resumed["simulation_time_s"] == resumed_time,
          "progression continues from the preserved simulation time")
    claim(resumed["total_count"] == before["total_count"] + 1,
          "production continues from the preserved state")

    print("\n[5b] STOP is a controlled stop, never a fault")
    ctrl.stop()
    stopped_at = ctrl.line_facts()["simulation_time_s"]
    ctrl.advance()
    claim(ctrl.run_state == LineRunState.STOPPED, "STOP enters STOPPED")
    claim(ctrl.line_facts()["simulation_time_s"] == stopped_at,
          "no progression after STOP")
    surface = " ".join(
        f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in ctrl.line.trace)
    claim("FAULT" not in surface and "DOWNTIME" not in surface,
          "STOP produced no FAULT and no DOWNTIME")

    # ── 6. RESET -> known initial state ─────────────────────────────────────
    print("\n[6] RESET restores the known initial state")
    ctrl.reset()
    reset_facts = ctrl.line_facts()
    claim(ctrl.run_state == LineRunState.STOPPED, "RESET returns to STOPPED")
    claim(reset_facts["total_count"] == 0
          and reset_facts["good_count"] == 0
          and reset_facts["reject_count"] == 0, "counters reset to zero")
    claim(reset_facts["simulation_time_s"] == 0.0, "simulation time reset")
    claim(reset_facts["units_on_line"] == 0, "line is empty")
    claim(ctrl.line.trace == (), "trace is empty")

    # ── 7. deterministic replay after RESET ─────────────────────────────────
    print("\n[7] deterministic replay after RESET")
    ctrl.start()
    for _ in range(12):
        ctrl.advance()
    replay = ctrl.line_facts()

    fresh = DemoController(config_path=str(CONFIG_PATH))
    fresh.initialize()
    fresh.start()
    for _ in range(12):
        fresh.advance()
    fresh_facts = fresh.line_facts()

    claim(replay == fresh_facts,
          "same config + seed + initial state => same facts")
    claim(
        [(e.event_type, e.position, e.wip_id, e.detail) for e in ctrl.line.trace] ==
        [(e.event_type, e.position, e.wip_id, e.detail) for e in fresh.line.trace],
        "same config + seed + initial state => identical event trace")

    # ── result ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE FAILED — {len(_failures)} claim(s) failed:")
        for failure in _failures:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print("SMOKE PASSED — all Bottled Water runtime claims proven")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
