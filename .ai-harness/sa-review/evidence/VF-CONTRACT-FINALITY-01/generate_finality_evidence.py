"""VF-CONTRACT-FINALITY-01 — generate real finality evidence (read-only bridge).

Drives the accepted composition + observation bridge for each scenario and
serializes the actual ProjectedMessage payloads, focusing on the terminal
quality semantics and release absence/presence.

Outputs (machine-readable):
  - failed-final-journey.json       (FAILED_FINAL scenario evidence)
  - non-terminal-journeys.json      (AP06 FAIL1->PASS2, AP08 NG1->PASS2, HAPPY)
  - failed-final-projected-message.json  (sanitized real fixture for MES B3-C01)

No production code is modified.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "src"))

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.line_runtime import WipLifecycle
from virtual_factory.assembly.observation_bridge import build_assy_observation_pipeline

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")


def serialized(message) -> dict:
    return {
        "message_key": message.key,
        "projection_id": message.projection_id,
        "message_type": message.message_type,
        "schema_name": message.schema_name,
        "schema_version": message.schema_version,
        "headers": dict(message.headers),
        "payload": dict(message.payload),
    }


def drive(scenario: str, sub_line: str, max_steps: int = 400) -> list[dict]:
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=scenario)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    ctx = comp.get_context(sub_line)
    target_motor = None
    for _ in range(max_steps):
        ctx.step_context()
        for wip_id in ctx.runtime.wip_ids:
            ws = ctx.runtime.get_wip(wip_id)
            if ws is not None and ws.lifecycle == WipLifecycle.RELEASED:
                target_motor = wip_id
                break
        if target_motor:
            break
    bridge.poll(comp)
    return [serialized(m) for m in bridge.projected_messages]


def quality_of(msgs, station: str):
    return [m for m in msgs
            if m["message_type"] == "mes.quality_result"
            and m["payload"].get("station_id") == station]


def releases(msgs):
    return [m for m in msgs if m["message_type"] == "mes.release"]


def compact(m: dict) -> dict:
    p = m["payload"]
    return {
        "message_key": m["message_key"],
        "message_type": m["message_type"],
        "schema_name": m["schema_name"],
        "run_id": p.get("run_id"),
        "station_id": p.get("station_id"),
        "event_type": p.get("event_type"),
        "record_id": p.get("record_id"),
        "wip_id": p.get("wip_id"),
        "disposition": p.get("disposition"),
        "attempt_number": p.get("attempt_number"),
        "is_terminal": p.get("is_terminal"),
        "terminal_state": p.get("terminal_state"),
        "simulation_time_s": p.get("simulation_time_s"),
        "release_time_s": p.get("release_time_s"),
        "subject_id": p.get("subject_id"),
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parent

    # ── 1. FAILED_FINAL journey ──
    ff = drive("FAILED_FINAL", "ASSY-SL03")
    ap06_ff = quality_of(ff, "AP06")
    rel_ff = releases(ff)
    failed_final_journey = {
        "scenario": "FAILED_FINAL",
        "target_sub_line": "ASSY-SL03",
        "quality_records_ap06": [compact(m) for m in ap06_ff],
        "releases": [compact(m) for m in rel_ff],
        "terminal_facts": [compact(m) for m in ap06_ff
                           if m["payload"].get("is_terminal") is True],
    }
    (out_dir / "failed-final-journey.json").write_text(
        json.dumps(failed_final_journey, indent=2), encoding="utf-8")

    # Sanitized real fixture for MES B3-C01 (one full terminal record).
    terminal_msgs = [m for m in ap06_ff if m["payload"].get("is_terminal") is True]
    non_term = [m for m in ap06_ff if m["payload"].get("is_terminal") is False]
    fixture = {
        "source_system": "virtual_factory",
        "description": "REAL FAILED_FINAL scenario terminal quality fact (generated from accepted runtime)",
        "semantic_fields_mes_should_use": [
            "message_key", "message_type", "schema_name",
            "payload.is_terminal", "payload.terminal_state",
            "payload.station_id", "payload.wip_id", "payload.record_id",
            "payload.disposition", "payload.attempt_number",
            "payload.simulation_time_s", "payload.run_id",
        ],
        "fields_mes_must_not_infer": [
            "finality (do NOT infer from attempt_number or silence)",
            "retry limit (do NOT guess max_attempts)",
            "scrap / rework routing",
        ],
        "terminal_message": compact(terminal_msgs[0]) if terminal_msgs else None,
        "prior_non_terminal_message": compact(non_term[0]) if non_term else None,
        "release_absent": len(rel_ff) == 0,
    }
    (out_dir / "failed-final-projected-message.json").write_text(
        json.dumps(fixture, indent=2), encoding="utf-8")

    # ── 2. Non-terminal journeys ──
    non_term_journeys = {}

    # AP06 FAIL1 -> PASS2
    ap06fp = drive("AP06_FAIL_RETEST_PASS", "ASSY-SL03")
    ap06_q = quality_of(ap06fp, "AP06")
    non_term_journeys["AP06_FAIL_RETEST_PASS"] = {
        "records": [compact(m) for m in ap06_q],
        "any_terminal": any(m["payload"].get("is_terminal") is True for m in ap06_q),
        "releases": len(releases(ap06fp)),
    }

    # AP08 NG1 -> PASS2
    ap08ng = drive("AP08_NG_REINSPECT_PASS", "ASSY-SL02")
    ap08_q = quality_of(ap08ng, "AP08")
    non_term_journeys["AP08_NG_REINSPECT_PASS"] = {
        "records": [compact(m) for m in ap08_q],
        "any_terminal": any(m["payload"].get("is_terminal") is True for m in ap08_q),
        "releases": len(releases(ap08ng)),
    }

    # HAPPY_PATH (all 6 sub-lines; ensure no terminal marker anywhere)
    hp = drive("HAPPY_PATH", "ASSY-SL01")
    all_q = [m for m in hp if m["message_type"] == "mes.quality_result"]
    non_term_journeys["HAPPY_PATH"] = {
        "quality_count": len(all_q),
        "any_terminal": any(m["payload"].get("is_terminal") is True for m in all_q),
        "releases": len(releases(hp)),
    }

    (out_dir / "non-terminal-journeys.json").write_text(
        json.dumps(non_term_journeys, indent=2), encoding="utf-8")

    print("wrote failed-final-journey.json, failed-final-projected-message.json, non-terminal-journeys.json")
    print("FAILED_FINAL ap06 records:", len(ap06_ff), "terminal:", sum(
        1 for m in ap06_ff if m["payload"].get("is_terminal") is True))
    print("FAILED_FINAL releases:", len(rel_ff))


if __name__ == "__main__":
    main()
