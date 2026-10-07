#!/usr/bin/env python3
"""DDAY-VF-UAT-03 — cross-track closeout smoke."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVIDENCE = HERE / "machine-evidence.json"
CURRENT = REPO / ".ai-harness/sa-review/CURRENT.md"
UAT02 = REPO / ".ai-harness/sa-review/evidence/DDAY-VF-UAT-02/machine-evidence.json"
OLD_HOLD_TEST = REPO / "tests/test_dday_vf_uat_02_host_hold.py"
VF_SHA = "d7db6d0909da968c2b4a4ea2cdb712e5d7601282"
PLANTOS_SHA = "a1695c5457515e2b565a5f9fe107c1e18b3e0879"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def main() -> int:
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    hist = json.loads(UAT02.read_text(encoding="utf-8"))
    current = CURRENT.read_text(encoding="utf-8")
    claim(data["canonical_current"] is True, "UAT-03 is the current canonical evidence")
    claim(data["deployed_vf_runtime_sha"] == VF_SHA, "deployed VF runtime SHA is d7db6d0")
    claim(data["plantos_accepted_uat_merge_sha"] == PLANTOS_SHA, "PlantOS accepted merge is a1695c5")
    claim(data["run_b_completed"] is True, "Run B is completed")
    claim(data["run_b_hold_current"] is False, "Run B HOLD is not current")
    claim(data["run_b"]["reused_vf_source_timestamps"] is True, "Run B reused VF source timestamps")
    claim(data["reset_dday_receive_epoch"]["succeeded"] is True, "reset_dday_receive_epoch succeeded")
    claim(hist.get("evidence_role") == "historical_run_a", "UAT-02 remains historical Run A")
    claim(hist.get("canonical_current") is False, "UAT-02 is not canonical current")
    claim(not OLD_HOLD_TEST.is_file(), "test_dday_vf_uat_02_host_hold.py is gone")
    claim("Run B HOLD" not in current, "CURRENT.md does not claim Run B HOLD")
    claim("Run B completed" in current, "CURRENT.md records Run B completed")
    claim(data["vf_product_changed"] is False, "no VF product change")
    print("SMOKE-DDAY-VF-UAT-03", "PASS" if not _failures else "FAIL")
    for item in _failures:
        print("  -", item)
    return 0 if not _failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
