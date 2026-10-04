#!/usr/bin/env python3
"""DDAY-B4-C01 — unmet-water conservation smoke.

Task: DDAY-B4-C01 (SA Issue #106 / PR #101).

Proves the empty-tank Filler draw does not silently discard pending demand,
and that later tank inventory satisfies the preserved request.

Exit code 0 = every claim proven. Any failed claim exits non-zero.
"""

from __future__ import annotations

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

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _approx(left: float, right: float, tol: float = 1e-12) -> bool:
    return abs(left - right) <= tol


def main() -> int:
    print("=" * 72)
    print("DDAY-B4-C01 — unmet water demand conservation")
    print("=" * 72)

    factory = BottledWaterFactory(
        line_config_path=WORKSPACE / "line.yaml",
        factory_config_path=WORKSPACE / "factory.yaml",
    )
    request = 0.01
    factory._tank_volume_m3 = 0.0
    factory._pending_draw_m3 = request
    factory._apply_draw()
    water = factory.snapshot()["balances"]["water"]

    print("\n[1] empty tank must preserve unmet demand")
    claim(_approx(water["unmet_water_demand_m3"], request),
          "unmet demand equals the requested draw")
    claim(_approx(water["water_draw_total_m3"], 0.0),
          "no water was taken from an empty tank")
    claim(_approx(water["water_request_total_m3"], request),
          "request ledger still holds the original demand")

    print("\n[2] partial inventory pays part of the ledger")
    factory._tank_volume_m3 = 0.004
    factory._apply_draw()
    water = factory.snapshot()["balances"]["water"]
    claim(_approx(water["unmet_water_demand_m3"], 0.006),
          "unmet remainder is 0.006 m3")
    claim(_approx(water["water_draw_total_m3"], 0.004),
          "0.004 m3 was drawn")
    claim(_approx(water["water_request_total_m3"],
                  water["water_draw_total_m3"] + water["unmet_water_demand_m3"]),
          "request = draw + unmet")

    print("\n[3] later inventory clears the remainder")
    factory._tank_volume_m3 = 0.02
    factory._apply_draw()
    water = factory.snapshot()["balances"]["water"]
    claim(_approx(water["unmet_water_demand_m3"], 0.0),
          "no unmet demand remains")
    claim(_approx(water["water_draw_total_m3"], request),
          "the original request was fully drawn")
    claim(_approx(water["tank_volume_m3"], 0.014),
          "tank retains the unused remainder")

    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE FAILED — {len(_failures)} claim(s) failed:")
        for failure in _failures:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print("SMOKE PASSED — unmet water demand is preserved and later satisfied")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
