#!/usr/bin/env python3
"""Collect DDAY-B6-C01 machine evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from test_dday_b6_c01_contract_fidelity import collect_durable_examples
from virtual_factory.workspaces.plantos_compat import write_compatibility_evidence
from virtual_factory.workspaces.plantos_export import (
    ACCEPTED_AREAS,
    CONTRACT_VERSION,
    dictionary_summary,
    map_snapshot,
)
from virtual_factory.workspaces.bottled_water import BottledWaterFactory

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
B6_REVIEWED = "9e76f406246ecd989eda1f23def283fa93408e1b"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _sample_payloads(examples: dict) -> dict:
    def _pick(bundle: dict | None, kind: str) -> list[dict]:
        if not bundle:
            return []
        items = [item for item in bundle.get("events", ()) if item["kind"] == "event"]
        return [item["payload"] for item in items[-3:]]

    return {
        "capper_warning": _pick(examples.get("capper_warning"), "event"),
        "capper_downtime": _pick(examples.get("capper_downtime"), "event"),
        "capper_recovery": _pick(examples.get("capper_recovery"), "event"),
        "compressor_warning": _pick(examples.get("compressor_warning"), "event"),
        "compressor_undersupply": _pick(examples.get("compressor_undersupply"), "event"),
        "process_history": [
            item["payload"] for item in examples["process_history"][:: max(1, len(examples["process_history"]) // 4)][:4]
        ],
        "condition_history": [
            item["payload"] for item in examples["condition_history"][:: max(1, len(examples["condition_history"]) // 4)][:4]
        ],
    }


def main() -> None:
    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    for _ in range(8):
        factory.step(1.0)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    short = factory.plantos_export()
    examples = collect_durable_examples()
    compat = write_compatibility_evidence(HERE / "plantos-compatibility.json", live_probe=True)
    changed = [
        line for line in _git("diff", "--name-only", B6_REVIEWED, "HEAD").splitlines() if line
    ]
    evidence = {
        "task_id": "DDAY-B6-C01",
        "baseline_b6_reviewed": B6_REVIEWED,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "changed_files_vs_b6_reviewed": changed,
        "contract_version": CONTRACT_VERSION,
        "accepted_areas": list(ACCEPTED_AREAS),
        "export_dictionary": dictionary_summary(),
        "sample_envelope": messages[0].payload if messages else {},
        "adapter_role": short["adapter_role"],
        "plantos_ingestion_proven": short["plantos_ingestion_proven"],
        "plantos_historian_proven": short["plantos_historian_proven"],
        "plantos_compatibility": compat,
        "overview_area_ids": [area["id"] for area in short["overview"]["areas"]],
        "durable": {
            "capper_warning_phase": (examples["capper_warning"] or {}).get("capper_phase"),
            "capper_downtime_phase": (examples["capper_downtime"] or {}).get("capper_phase"),
            "capper_recovery_phase": (examples["capper_recovery"] or {}).get("capper_phase"),
            "compressor_warning_phase": (examples["compressor_warning"] or {}).get("compressor_phase"),
            "compressor_undersupply_phase": (examples["compressor_undersupply"] or {}).get("compressor_phase"),
            "classified": examples["classified"],
            "process_history_count": len(examples["process_history"]),
            "condition_history_count": len(examples["condition_history"]),
            "final_event_types": sorted({
                item["payload"]["event_type"] for item in examples["final"]["events"]
            }),
        },
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "export-sample.json").write_text(
        json.dumps({
            "contract_version": short["contract_version"],
            "topic_pattern": short["topic_pattern"],
            "adapter_role": short["adapter_role"],
            "plantos_ingestion_proven": False,
            "plantos_historian_proven": False,
            "id_resolution": short["id_resolution"],
            "current_values": short["current_values"][:8],
            "events": short["events"][:8],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    (HERE / "durable-examples.json").write_text(
        json.dumps(_sample_payloads(examples), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
