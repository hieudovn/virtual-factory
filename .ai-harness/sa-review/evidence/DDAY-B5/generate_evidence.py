#!/usr/bin/env python3
"""Collect DDAY-B5 machine evidence from the live factory composition."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.workspaces.bottled_water import (
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    BottledWaterFactory,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
B5_BASE = "b6dcb08a1263e7a84792ea8697d3202fa5e79912"
CAP = "BW-FP-CAP01"
CMP = "BW-UT-CMP01"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _digest(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _walk_keys(node, acc: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            acc.add(str(key))
            _walk_keys(value, acc)
    elif isinstance(node, list):
        for item in node:
            _walk_keys(item, acc)


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")


def _signal(snapshot: dict, signal_id: str):
    return snapshot["nodes"][CAP]["signals"][signal_id]["value"]


def main() -> None:
    factory_a = _factory()
    factory_b = _factory()
    factory_a.start()
    factory_b.start()
    samples = []
    cmp_samples = []
    for step in range(340):
        factory_a.step(1.0)
        factory_b.step(1.0)
        snap = factory_a.snapshot()
        if not samples or snap["scenario"]["phase"] != samples[-1]["phase"]:
            samples.append({
                "step": step + 1,
                "phase": snap["scenario"]["phase"],
                "highlight": snap["scenario"]["highlight"],
                "total": snap["target_line"]["counts"]["total"],
                "good": snap["target_line"]["counts"]["good"],
                "fg_receipts": snap["balances"]["finished_goods"]["receipt_count"],
                "speed": _signal(snap, "speed"),
                "cycle_time": _signal(snap, "cycle_time"),
                "motor_current": _signal(snap, "motor_current"),
                "drive_load": _signal(snap, "drive_load"),
                "vibration_rms": _signal(snap, "vibration_rms"),
                "bearing_temperature": _signal(snap, "bearing_temperature"),
                "cap_torque": _signal(snap, "cap_torque"),
                "operating_state": _signal(snap, "operating_state"),
                "compressor_phase": snap["compressor_scenario"]["phase"],
                "air_pressure": snap["nodes"][CMP]["signals"]["air_pressure"]["value"],
            })
        if (
            not cmp_samples
            or snap["compressor_scenario"]["phase"] != cmp_samples[-1]["phase"]
        ):
            cmp_samples.append({
                "step": step + 1,
                "phase": snap["compressor_scenario"]["phase"],
                "highlight": snap["compressor_scenario"]["highlight"],
                "air_pressure": snap["nodes"][CMP]["signals"]["air_pressure"]["value"],
                "active_power": snap["nodes"][CMP]["signals"]["active_power"]["value"],
                "total": snap["target_line"]["counts"]["total"],
                "good": snap["target_line"]["counts"]["good"],
                "fg_receipts": snap["balances"]["finished_goods"]["receipt_count"],
                "capper_phase": snap["scenario"]["phase"],
            })
    final_a = factory_a.snapshot()
    final_b = factory_b.snapshot()
    events = [
        {
            "event_type": event["event_type"],
            "detail": event.get("detail"),
            "simulation_time_s": event.get("simulation_time_s"),
            "source_id": event.get("source_id"),
        }
        for event in final_a["recent_events"]
        if event["event_type"] in (
            "SCENARIO_PHASE_CHANGED",
            "ALARM_RAISED",
            "ALARM_CLEARED",
            "DOWNTIME_START",
            "DOWNTIME_END",
        )
    ]

    labelled = _factory()
    labelled.start()
    labelled.classify("downtime_code", "DT-BRG")
    labelled.classify("failure_code", "FAIL-BRG")
    for _ in range(220):
        labelled.step(1.0)
    labelled_snap = labelled.snapshot()

    keys: set[str] = set()
    _walk_keys(final_a, keys)
    hidden_hits = [key for key in HIDDEN_TRUTH_KEYS if key in keys]
    serialised = json.dumps(final_a).lower()
    kpi_hits = [kpi for kpi in FORBIDDEN_KPI_KEYS if kpi in serialised]

    changed = [
        line for line in _git("diff", "--name-only", B5_BASE, "HEAD").splitlines()
        if line
    ]
    payload = {
        "task": "DDAY-B5",
        "baseline": B5_BASE,
        "head": _git("rev-parse", "HEAD"),
        "replay_digest_match": _digest(final_a) == _digest(final_b),
        "digest": _digest(final_a),
        "phase_samples": samples,
        "compressor_phase_samples": cmp_samples,
        "events": events,
        "classification": labelled_snap["classification"],
        "classified_vibration": _signal(labelled_snap, "vibration_rms"),
        "plain_vibration": _signal(final_a, "vibration_rms"),
        "hidden_hits": hidden_hits,
        "kpi_hits": kpi_hits,
        "files_vs_b5_baseline": changed,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    (HERE / "01-baseline-and-scope.md").write_text(
        "# DDAY-B5 — baseline / reuse\n\n"
        f"- SA baseline: `{B5_BASE}`\n"
        f"- Head at evidence generation: `{payload['head']}`\n"
        "- Reuses B2 generic line + B4 factory composition; no second engine.\n"
        "- B1 contract `capper_degradation.contract.yaml` remains authoritative.\n"
        "- Secondary `BW-CMP-SAG-01` lives beside it; default NORMAL=240 s.\n",
        encoding="utf-8",
    )
    (HERE / "02-phase-table.md").write_text(
        "# DDAY-B5 — phase table\n\n"
        "| t (first sample) | phase | highlight | speed | vibration | temperature |\n"
        "|---|---|---|---|---|---|\n"
        + "".join(
            f"| {row['step']} | {row['phase']} | {row['highlight']} | "
            f"{row['speed']} | {row['vibration_rms']} | "
            f"{row['bearing_temperature']} |\n"
            for row in samples
        ),
        encoding="utf-8",
    )
    (HERE / "03-replay-digest.md").write_text(
        "# DDAY-B5 — deterministic replay\n\n"
        f"Two independent 340 s runs produced the same snapshot digest:\n\n"
        f"`{payload['digest']}`\n\n"
        f"Match: **{payload['replay_digest_match']}**\n",
        encoding="utf-8",
    )
    (HERE / "04-signal-trajectory.json").write_text(
        json.dumps(samples, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "05-events.md").write_text(
        "# DDAY-B5 — alarm / downtime sequence\n\n"
        + "\n".join(
            f"- t={event['simulation_time_s']}s `{event['event_type']}` "
            f"{event.get('source_id')} {event.get('detail')}"
            for event in events
        )
        + "\n",
        encoding="utf-8",
    )
    (HERE / "06-production-impact.md").write_text(
        "# DDAY-B5 — production / FG impact\n\n"
        + "\n".join(
            f"- {row['phase']}: total={row['total']} good={row['good']} "
            f"fg={row['fg_receipts']} cycle_time={row['cycle_time']}"
            for row in samples
        )
        + "\n",
        encoding="utf-8",
    )
    (HERE / "11-compressor.md").write_text(
        "# DDAY-B5 — compressor secondary scenario\n\n"
        "| t (first sample) | compressor phase | highlight | air_pressure | capper phase |\n"
        "|---|---|---|---|---|\n"
        + "".join(
            f"| {row['step']} | {row['phase']} | {row['highlight']} | "
            f"{row['air_pressure']} | {row['capper_phase']} |\n"
            for row in cmp_samples
        )
        + "\nDefault demo is non-overlapping: compressor DEGRADING begins "
        "only after Capper RECOVERY. UNDERSUPPLY inhibits production; "
        "FG receipts follow actual good output.\n",
        encoding="utf-8",
    )
    (HERE / "07-hidden-truth-scan.md").write_text(
        "# DDAY-B5 — hidden-truth / KPI scan\n\n"
        f"Hidden hits: {hidden_hits or 'none'}\n\n"
        f"KPI hits: {kpi_hits or 'none'}\n",
        encoding="utf-8",
    )
    (HERE / "08-classification.md").write_text(
        "# DDAY-B5 — classification non-causality\n\n"
        f"Codes: {labelled_snap['classification']}\n\n"
        f"Plain vibration: {payload['plain_vibration']}\n"
        f"Classified vibration: {payload['classified_vibration']}\n"
        f"Match: {payload['plain_vibration'] == payload['classified_vibration']}\n",
        encoding="utf-8",
    )
    (HERE / "09-scope-audit.md").write_text(
        "# DDAY-B5 — scope audit vs `b6dcb08`\n\n"
        + "\n".join(f"- `{path}`" for path in changed)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "digest": payload["digest"],
        "replay_match": payload["replay_digest_match"],
        "phases": [row["phase"] for row in samples],
        "compressor_phases": [row["phase"] for row in cmp_samples],
        "hidden_hits": hidden_hits,
        "kpi_hits": kpi_hits,
        "files": len(changed),
    }, indent=2))


if __name__ == "__main__":
    main()
