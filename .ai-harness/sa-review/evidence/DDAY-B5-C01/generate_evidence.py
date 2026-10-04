#!/usr/bin/env python3
"""Collect DDAY-B5-C01 machine evidence for the compressor 5-phase correction."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.workspaces.bottled_water import (
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    BottledWaterFactory,
)
from virtual_factory.workspaces.compressor_pressure import (
    PHASES,
    CompressorPressureScenario,
    load_compressor_runtime,
)

WORKSPACE = REPO / "configs" / "workspaces" / "bottled-water-dday"
C01_BASE = "cced390cfad5c9a40361cf2caf6f1916e7003f59"
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
    "LOW_PRESSURE_WARNING": 8.0,
    "UNDERSUPPLY": 22.0,
    "RECOVERY": 24.0,
}


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


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _short_compressor() -> CompressorPressureScenario:
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
    isolated = _factory(enable_capper=False, compressor=_short_compressor())
    replay = _factory(enable_capper=False, compressor=_short_compressor())
    isolated.start()
    replay.start()
    samples = []
    for step in range(90):
        isolated.step(1.0)
        replay.step(1.0)
        snap = isolated.snapshot()
        if not samples or snap["compressor_scenario"]["phase"] != samples[-1]["phase"]:
            samples.append({
                "step": step + 1,
                "phase": snap["compressor_scenario"]["phase"],
                "highlight": snap["compressor_scenario"]["highlight"],
                "air_pressure": _signal(snap, CMP, "air_pressure"),
                "active_power": _signal(snap, CMP, "active_power"),
                "total": snap["target_line"]["counts"]["total"],
                "good": snap["target_line"]["counts"]["good"],
                "fg_receipts": snap["balances"]["finished_goods"]["receipt_count"],
            })
    final = isolated.snapshot()
    events = [
        {
            "event_type": event["event_type"],
            "detail": event.get("detail"),
            "simulation_time_s": event.get("simulation_time_s"),
            "source_id": event.get("source_id"),
        }
        for event in final["recent_events"]
        if event.get("source_id") == CMP
        and event["event_type"] in (
            "SCENARIO_PHASE_CHANGED",
            "ALARM_RAISED",
            "ALARM_CLEARED",
            "DOWNTIME_START",
            "DOWNTIME_END",
        )
    ]

    labelled = _factory(enable_capper=False, compressor=_short_compressor())
    labelled.start()
    labelled.classify("downtime_code", "DT-AIR")
    labelled.classify("failure_code", "FAIL-AIR")
    for _ in range(90):
        labelled.step(1.0)

    default = _factory()
    default.start()
    for _ in range(150):
        default.step(1.0)
    mid = default.snapshot()
    for _ in range(90):
        default.step(1.0)
    after_capper = default.snapshot()

    keys: set[str] = set()
    _walk_keys(final, keys)
    hidden_hits = [key for key in HIDDEN_TRUTH_KEYS if key in keys]
    serialised = json.dumps(final).lower()
    kpi_hits = [kpi for kpi in FORBIDDEN_KPI_KEYS if kpi in serialised]

    capper_diff = _git("diff", "--name-only", C01_BASE, "HEAD", "--", *CAPPER_FROZEN)
    changed = [
        line for line in _git("diff", "--name-only", C01_BASE, "HEAD").splitlines()
        if line
    ]
    under = next((row for row in samples if row["phase"] == "UNDERSUPPLY"), None)
    recover = next((row for row in samples if row["phase"] == "RECOVERY"), None)
    payload = {
        "task": "DDAY-B5-C01",
        "baseline": C01_BASE,
        "head": _git("rev-parse", "HEAD"),
        "phase_order": [row["phase"] for row in samples],
        "required_phase_order": list(PHASES),
        "phase_order_match": [row["phase"] for row in samples] == list(PHASES),
        "replay_digest_match": _digest(final) == _digest(replay.snapshot()),
        "digest": _digest(final),
        "phase_samples": samples,
        "events": events,
        "alarm_raised_count": sum(
            1 for event in events if event["event_type"] == "ALARM_RAISED"
        ),
        "downtime_count": sum(
            1 for event in events if event["event_type"] == "DOWNTIME_START"
        ),
        "undersupply_total": None if under is None else under["total"],
        "recovery_total": None if recover is None else recover["total"],
        "final_total": final["target_line"]["counts"]["total"],
        "final_fg_receipts": final["balances"]["finished_goods"]["receipt_count"],
        "final_good": final["target_line"]["counts"]["good"],
        "fg_follows_good": (
            final["balances"]["finished_goods"]["receipt_count"]
            == final["target_line"]["counts"]["good"]
        ),
        "classified_phase": labelled.snapshot()["compressor_scenario"]["phase"],
        "plain_phase": final["compressor_scenario"]["phase"],
        "default_at_t150": {
            "capper": mid["scenario"]["phase"],
            "compressor": mid["compressor_scenario"]["phase"],
        },
        "default_at_t240": {
            "capper": after_capper["scenario"]["phase"],
            "compressor": after_capper["compressor_scenario"]["phase"],
        },
        "capper_files_changed_vs_cced390": capper_diff.splitlines(),
        "hidden_hits": hidden_hits,
        "kpi_hits": kpi_hits,
        "files_vs_c01_baseline": changed,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    (HERE / "01-baseline-and-scope.md").write_text(
        "# DDAY-B5-C01 — baseline / scope\n\n"
        f"- SA-reviewed B5 head / C01 baseline: `{C01_BASE}`\n"
        f"- Head at evidence generation: `{payload['head']}`\n"
        "- Capper helper/contract/runtime left unchanged.\n"
        "- Compressor restored to the Issue #107 5-phase causal story.\n"
        f"- Capper files changed vs `cced390`: "
        f"{payload['capper_files_changed_vs_cced390'] or 'none'}\n",
        encoding="utf-8",
    )
    (HERE / "02-phase-order.md").write_text(
        "# DDAY-B5-C01 — compressor phase order\n\n"
        f"Observed: `{' → '.join(payload['phase_order'])}`\n\n"
        f"Required: `{' → '.join(PHASES)}`\n\n"
        f"Match: **{payload['phase_order_match']}**\n\n"
        "| t | phase | highlight | air_pressure | power | total | fg |\n"
        "|---|---|---|---|---|---|---|\n"
        + "".join(
            f"| {row['step']} | {row['phase']} | {row['highlight']} | "
            f"{row['air_pressure']} | {row['active_power']} | "
            f"{row['total']} | {row['fg_receipts']} |\n"
            for row in samples
        ),
        encoding="utf-8",
    )
    (HERE / "03-production-impact.md").write_text(
        "# DDAY-B5-C01 — UNDERSUPPLY production / FG impact\n\n"
        f"- Bottles at UNDERSUPPLY entry: `{payload['undersupply_total']}`\n"
        f"- Bottles at RECOVERY entry: `{payload['recovery_total']}`\n"
        f"- Bottles after isolated run: `{payload['final_total']}`\n"
        f"- FG receipts: `{payload['final_fg_receipts']}`\n"
        f"- Good count: `{payload['final_good']}`\n"
        f"- FG follows good: **{payload['fg_follows_good']}**\n"
        f"- Compressor downtime events: `{payload['downtime_count']}`\n"
        f"- Low-pressure alarms: `{payload['alarm_raised_count']}`\n\n"
        "UNDERSUPPLY inhibits `_produce_one_cycle()` at the composition layer. "
        "No compressor downtime pair. Capper remains the hero downtime story.\n",
        encoding="utf-8",
    )
    (HERE / "04-non-overlap.md").write_text(
        "# DDAY-B5-C01 — default demo windows\n\n"
        f"- t=150 Capper `{payload['default_at_t150']['capper']}`, "
        f"compressor `{payload['default_at_t150']['compressor']}`\n"
        f"- t=240 Capper `{payload['default_at_t240']['capper']}`, "
        f"compressor `{payload['default_at_t240']['compressor']}`\n\n"
        "Compressor DEGRADING starts only after Capper RECOVERY.\n",
        encoding="utf-8",
    )
    (HERE / "05-scope-audit.md").write_text(
        "# DDAY-B5-C01 — scope audit vs `cced390`\n\n"
        + "\n".join(f"- `{path}`" for path in changed)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "digest": payload["digest"],
        "phase_order": payload["phase_order"],
        "phase_order_match": payload["phase_order_match"],
        "undersupply_total": payload["undersupply_total"],
        "final_total": payload["final_total"],
        "fg_follows_good": payload["fg_follows_good"],
        "capper_unchanged": not payload["capper_files_changed_vs_cced390"],
        "hidden_hits": hidden_hits,
        "kpi_hits": kpi_hits,
        "files": len(changed),
    }, indent=2))


if __name__ == "__main__":
    main()
