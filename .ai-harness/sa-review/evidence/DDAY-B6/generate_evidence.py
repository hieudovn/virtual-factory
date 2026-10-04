#!/usr/bin/env python3
"""Collect DDAY-B6 machine evidence for the local PlantOS proof + overview."""

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
    ACCEPTED_AREAS,
    map_snapshot,
    overview_from_snapshot,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
B5_CLOSED = "449685a3c4c394b4e0654b720ff11f77205b4b48"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml"
    )


def main() -> None:
    factory = _factory()
    factory.start()
    for _ in range(12):
        factory.step(1.0)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    bundle = factory.plantos_export()
    overview = overview_from_snapshot(snapshot)
    changed = [line for line in _git("diff", "--name-only", B5_CLOSED, "HEAD").splitlines() if line]
    protocol_diff = _git("diff", "--name-only", B5_CLOSED, "--",
                         "src/virtual_factory/protocols",
                         "src/virtual_factory/telemetry")
    evidence = {
        "task_id": "DDAY-B6",
        "baseline_b5_closed": B5_CLOSED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "changed_files_vs_b5_closed": changed,
        "protocols_telemetry_diff": protocol_diff,
        "accepted_areas": list(ACCEPTED_AREAS),
        "sample_topics": [item.topic for item in messages[:8]],
        "id_resolution": bundle["id_resolution"],
        "current_value_count": len(bundle["current_values"]),
        "historian_count": len(bundle["historian"]),
        "event_types": sorted({item["payload"]["event_type"] for item in bundle["events"]}),
        "overview_area_ids": [area["id"] for area in overview["areas"]],
        "overview_relationships": overview["relationships"],
        "overview_drill_down": overview["drill_down"],
        "kpi_boundary": {
            "oee_absent": "oee" not in json.dumps(bundle).lower(),
            "health_score_absent": "health_score" not in json.dumps(bundle).lower(),
        },
        "second_simulator_absent": "class BottledWaterFactory" not in (
            REPO / "src/virtual_factory/workspaces/plantos_export.py"
        ).read_text(encoding="utf-8"),
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "export-sample.json").write_text(
        json.dumps({
            "topic_pattern": bundle["topic_pattern"],
            "ingestion_path": bundle["ingestion_path"],
            "id_resolution": bundle["id_resolution"],
            "current_values": bundle["current_values"][:12],
            "events": bundle["events"],
            "overview": bundle["overview"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "head": evidence["head"],
        "resolved": bundle["id_resolution"]["resolved"],
        "areas": evidence["overview_area_ids"],
        "changed": len(changed),
    }, indent=2))


if __name__ == "__main__":
    main()
