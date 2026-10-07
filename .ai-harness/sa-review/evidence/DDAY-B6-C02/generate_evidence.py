#!/usr/bin/env python3
"""Collect DDAY-B6-C02 machine evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    TIMESTAMP_SEMANTICS,
    dictionary_summary,
    selected_signal_keys,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C01_REVIEWED = "e0763b9dfb3b42d57e95f6c4bb234f59f8f63ab5"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def main() -> None:
    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    for _ in range(8):
        factory.step(1.0)
    bundle = factory.plantos_export()
    current = {
        f"{item['asset_id']}.{item['signal_or_event']}": item["payload"]["value"]
        for item in bundle["current_values"]
    }
    evidence = {
        "task_id": "DDAY-B6-C02",
        "baseline_c01_reviewed": C01_REVIEWED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "timestamp_semantics": TIMESTAMP_SEMANTICS,
        "export_dictionary": dictionary_summary(),
        "selected_keys": [f"{a}.{s}" for a, s in selected_signal_keys()],
        "sample_new_values": {
            key: current.get(key)
            for key in (
                "BW-FP-CAP01.speed",
                "BW-FP-CAP01.cycle_time",
                "BW-FP-CAP01.cap_torque",
                "BW-UT-CMP01.active_power",
                "BW-UT-CMP01.energy_total",
                "BW-WH-FG01.dispatch_count",
                "BW-FP-FIL01.fill_rate",
            )
        },
        "sample_envelope": bundle["current_values"][0]["payload"] if bundle["current_values"] else {},
        "plantos_ingest_proof_in_c02": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
