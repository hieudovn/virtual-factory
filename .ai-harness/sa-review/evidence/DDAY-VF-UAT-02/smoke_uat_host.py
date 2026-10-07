#!/usr/bin/env python3
"""DDAY-VF-UAT-02 — UAT host evidence smoke (no live SSH, no secrets)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVIDENCE = HERE / "machine-evidence.json"
REPORTS = [
    REPO / ".ai-harness/sa-review/reports/DDAY-VF-UAT-02.md",
    REPO / "reports/dday-vf-uat-01/09-uat-host.md",
]
FORBIDDEN = ("#2026", "BiPsiKKz", "password:", "PASSWORD=")
SHA = "d7db6d0909da968c2b4a4ea2cdb712e5d7601282"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def main() -> int:
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    claim(data["accepted_vf_sha"] == SHA, "accepted VF SHA is frozen d7db6d0")
    claim(data["deployed_vf_source_sha"] == SHA, "deployed VF_SOURCE_SHA matches")
    claim(data["sha_match"] is True, "SHA match is true")
    claim(data["password_stored_in_repo"] is False, "password not stored in evidence")
    claim(data["container"]["name"] == "virtual-factory-dday", "container name recorded")
    claim(data["container"]["public_ports"] == {}, "no public ports recorded")
    claim("plantos-net" in data["container"]["networks"], "attached to plantos-net")
    claim(data["mqtt_sample_12s"]["distinct_signals"] == 22, "22 live signals sampled")
    claim(data["mqtt_sample_12s"]["operating_state_signal_publishes"] == 0, "no operating_state signal")
    claim(data["mqtt_sample_12s"]["fast_motor_current"] > data["mqtt_sample_12s"]["slow_water_flow"], "FAST > SLOW")
    claim(data.get("evidence_role") == "historical_run_a", "UAT-02 is a historical Run A snapshot")
    claim(data.get("canonical_current") is False, "UAT-02 is not the current canonical state")
    claim(data["run_a_started"] is True, "historical snapshot recorded Run A")
    claim(data["run_b_started"] is False, "historical snapshot recorded Run B not yet started at inspect time")
    claim(data["vf_product_changed"] is False, "no VF product change")
    blob = EVIDENCE.read_text(encoding="utf-8")
    for path in REPORTS:
        claim(path.is_file(), f"{path.name} exists")
        blob += path.read_text(encoding="utf-8")
    claim(all(token not in blob for token in FORBIDDEN), "reports/evidence contain no SSH password")
    print("SMOKE-DDAY-VF-UAT-02", "PASS" if not _failures else "FAIL")
    for item in _failures:
        print("  -", item)
    return 0 if not _failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
