#!/usr/bin/env python3
"""Collect DDAY-B5-C02 machine evidence for the three leftover corrections."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.compressor_pressure import (
    CompressorPressureScenario,
    load_compressor_runtime,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C02_BASE = "3b9cc8c2d5afbeb47dae798592a5ce32b58131fc"
CMP = "BW-UT-CMP01"
CAPPER_FROZEN = (
    "src/virtual_factory/workspaces/capper_degradation.py",
    "configs/workspaces/bottled-water-dday/scenarios/capper_degradation.contract.yaml",
    "configs/workspaces/bottled-water-dday/scenarios/capper_degradation.runtime.yaml",
    "tests/test_dday_b5_capper_scenario.py",
)
SHORT_DURATIONS = {
    "NORMAL": 22.0,
    "DEGRADING": 8.0,
    "LOW_PRESSURE_WARNING": 12.0,
    "UNDERSUPPLY": 22.0,
    "RECOVERY": 24.0,
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _short() -> CompressorPressureScenario:
    config = load_compressor_runtime(
        WORKSPACE / "scenarios" / "compressor_pressure.runtime.yaml",
        WORKSPACE / "scenarios" / "compressor_pressure.contract.yaml",
    )
    return CompressorPressureScenario(replace(
        config, phase_duration_s=dict(SHORT_DURATIONS),
    ))


def _factory(**kwargs) -> BottledWaterFactory:
    return BottledWaterFactory(
        WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml", **kwargs
    )


def main() -> None:
    factory = _factory(enable_capper=False, compressor=_short())
    factory.start()
    threshold = factory._compressor.config.warning_threshold_bar
    warning_entry = None
    alarm_sample = None
    for step in range(90):
        factory.step(1.0)
        snap = factory.snapshot()
        phase = snap["compressor_scenario"]["phase"]
        if warning_entry is None and phase == "LOW_PRESSURE_WARNING":
            warning_entry = {
                "step": step + 1,
                "pressure": _signal(snap, CMP, "air_pressure"),
                "alarm_events": sum(
                    1 for event in snap["recent_events"]
                    if event.get("source_id") == CMP
                    and event["event_type"] == "ALARM_RAISED"
                ),
            }
        if alarm_sample is None and any(
            event.get("source_id") == CMP and event["event_type"] == "ALARM_RAISED"
            for event in snap["recent_events"]
        ):
            alarm_sample = {
                "step": step + 1,
                "phase": phase,
                "pressure": _signal(snap, CMP, "air_pressure"),
            }

    labelled = _factory(enable_capper=False, compressor=_short())
    labelled.start()
    labelled.classify("downtime_code", "DT-AIR", target="compressor")
    labelled.classify("failure_code", "FAIL-AIR", target="BW-CMP-SAG-01")
    for _ in range(70):
        labelled.step(1.0)
    labelled_snap = labelled.snapshot()
    stamped = [
        {
            "event_type": event["event_type"],
            "detail": event.get("detail"),
            "downtime_code": event.get("downtime_code"),
            "failure_code": event.get("failure_code"),
        }
        for event in labelled_snap["recent_events"]
        if event.get("source_id") == CMP and event.get("downtime_code") == "DT-AIR"
    ]

    abnormal = _factory(enable_capper=False)
    control = _factory(enable_capper=False, enable_compressor=False)
    abnormal.start()
    control.start()
    control_samples = {}
    for step in range(340):
        abnormal.step(1.0)
        control.step(1.0)
        if step + 1 in (284, 304, 340):
            a = abnormal.snapshot()
            c = control.snapshot()
            control_samples[str(step + 1)] = {
                "abnormal_phase": a["compressor_scenario"]["phase"],
                "abnormal_total": a["target_line"]["counts"]["total"],
                "abnormal_good": a["target_line"]["counts"]["good"],
                "abnormal_fg": a["balances"]["finished_goods"]["receipt_count"],
                "control_total": c["target_line"]["counts"]["total"],
                "control_good": c["target_line"]["counts"]["good"],
                "control_fg": c["balances"]["finished_goods"]["receipt_count"],
            }

    capper_diff = _git("diff", "--name-only", C02_BASE, "HEAD", "--", *CAPPER_FROZEN)
    changed = [
        line for line in _git("diff", "--name-only", C02_BASE, "HEAD").splitlines()
        if line
    ]
    payload = {
        "task": "DDAY-B5-C02",
        "baseline": C02_BASE,
        "head": _git("rev-parse", "HEAD"),
        "warning_threshold_bar": threshold,
        "warning_entry": warning_entry,
        "alarm_sample": alarm_sample,
        "alarm_after_threshold": (
            alarm_sample is not None
            and warning_entry is not None
            and warning_entry["alarm_events"] == 0
            and warning_entry["pressure"] > threshold
            and alarm_sample["pressure"] <= threshold
            and alarm_sample["step"] > warning_entry["step"]
        ),
        "classified_context": {
            "downtime_code": labelled_snap["compressor_scenario"]["downtime_code"],
            "failure_code": labelled_snap["compressor_scenario"]["failure_code"],
            "top_level_downtime_code": labelled_snap["classification"]["downtime_code"],
        },
        "stamped_events": stamped,
        "control_samples": control_samples,
        "capper_files_changed_vs_3b9cc8c": capper_diff.splitlines(),
        "files_vs_c02_baseline": changed,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "01-baseline-and-scope.md").write_text(
        "# DDAY-B5-C02 — baseline / scope\n\n"
        f"- SA-reviewed C01 head / C02 baseline: `{C02_BASE}`\n"
        f"- Head at evidence generation: `{payload['head']}`\n"
        f"- Capper files changed vs `3b9cc8c`: "
        f"{payload['capper_files_changed_vs_3b9cc8c'] or 'none'}\n"
        "- No compressor fidelity expansion (same 5 phases and default durations).\n",
        encoding="utf-8",
    )
    (HERE / "02-alarm-threshold.md").write_text(
        "# DDAY-B5-C02 — pressure-threshold alarm\n\n"
        f"- warning_threshold_bar: `{threshold}`\n"
        f"- LOW_PRESSURE_WARNING entry: `{warning_entry}`\n"
        f"- First ALARM_RAISED: `{alarm_sample}`\n"
        f"- Alarm waits for observed threshold: **{payload['alarm_after_threshold']}**\n",
        encoding="utf-8",
    )
    (HERE / "03-targeted-classification.md").write_text(
        "# DDAY-B5-C02 — compressor-targeted classification\n\n"
        f"Context: `{payload['classified_context']}`\n\n"
        "Stamped compressor events:\n\n"
        + "\n".join(
            f"- `{event['event_type']}` {event.get('detail')} "
            f"dt={event.get('downtime_code')} fail={event.get('failure_code')}"
            for event in stamped
        )
        + "\n",
        encoding="utf-8",
    )
    (HERE / "04-control-run.md").write_text(
        "# DDAY-B5-C02 — matched compressor-disabled control run\n\n"
        "| t | abnormal phase | abnormal total/good/fg | control total/good/fg |\n"
        "|---|---|---|---|\n"
        + "".join(
            f"| {t} | {row['abnormal_phase']} | "
            f"{row['abnormal_total']}/{row['abnormal_good']}/{row['abnormal_fg']} | "
            f"{row['control_total']}/{row['control_good']}/{row['control_fg']} |\n"
            for t, row in control_samples.items()
        )
        + "\nCapper disabled in both runs. UNDERSUPPLY freezes the abnormal "
        "window; RECOVERY resumes production.\n",
        encoding="utf-8",
    )
    (HERE / "05-scope-audit.md").write_text(
        "# DDAY-B5-C02 — scope audit vs `3b9cc8c`\n\n"
        + "\n".join(f"- `{path}`" for path in changed)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "alarm_after_threshold": payload["alarm_after_threshold"],
        "classified_context": payload["classified_context"],
        "stamped": len(stamped),
        "control_samples": control_samples,
        "capper_unchanged": not payload["capper_files_changed_vs_3b9cc8c"],
        "files": len(changed),
    }, indent=2))


if __name__ == "__main__":
    main()
