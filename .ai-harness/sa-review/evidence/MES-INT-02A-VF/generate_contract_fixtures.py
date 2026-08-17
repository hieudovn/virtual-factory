"""MES-INT-02A-VF — dump REAL VF P0 ProjectedMessage examples (read-only).

Runs the accepted VF bridge (M6-INT-01 + C01) against real scenarios and
serializes actual ProjectedMessage objects exactly as the JSONL gateway does
(same logical envelope as REST/MQTT). No production code is modified.

Outputs representative messages for:
  execution_event, genealogy_relationship, quality_result (AP06/AP08 PASS+FAIL/NG),
  AP11 final-QC PASS, AP11 RELEASE — plus the run/reset identity notes.
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
from virtual_factory.assembly.observation_bridge import (
    EVENT_AP11_RELEASE,
    build_assy_observation_pipeline,
)
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")


def serialized(message) -> dict:
    """Serialize a ProjectedMessage exactly like the JSONL gateway (transport)."""
    return {
        "message_key": message.key,
        "projection_id": message.projection_id,
        "message_type": message.message_type,
        "schema_name": message.schema_name,
        "schema_version": message.schema_version,
        "headers": dict(message.headers),
        "payload": dict(message.payload),
    }


def collect(comp, sl_id, motor_id, max_steps=500) -> list[dict]:
    """Drive one context to motor release and return serialized messages."""
    bridge = build_assy_observation_pipeline().bridge
    ctx = comp.get_context(sl_id)
    for _ in range(max_steps):
        ctx.step_context()
        ws = ctx.runtime.get_wip(motor_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    bridge.poll(comp)
    return [serialized(m) for m in bridge.projected_messages]


def pick(messages, message_type=None, payload_pred=None, first=True):
    out = [m for m in messages if message_type is None or m["message_type"] == message_type]
    if payload_pred:
        out = [m for m in out if payload_pred(m["payload"])]
    return (out[0] if first else out) if out else None


def main() -> None:
    result: dict = {}

    # HAPPY_PATH — ASSY-SL01 → one full motor
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    comp.initialize()
    hp = collect(comp, "ASSY-SL01", "MTR-0001")

    result["envelope_example"] = hp[0] if hp else None
    result["operation_completion"] = pick(hp, "mes.execution_event")
    result["ap04_genealogy"] = pick(hp, "mes.genealogy_relationship")
    result["ap06_pass"] = pick(hp, "mes.quality_result",
                               lambda p: p.get("station_id") == "AP06")
    result["ap08_pass"] = pick(hp, "mes.quality_result",
                               lambda p: p.get("station_id") == "AP08")
    result["ap11_final_qc_pass"] = pick(
        hp, "mes.quality_result",
        lambda p: p.get("station_id") == "AP11")
    result["ap11_release"] = pick(hp, "mes.release")

    # AP06 FAIL → PASS (ASSY-SL03 motor 2)
    comp2 = AssyDemoComposition(config_path=TIPA_YAML,
                                scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
    comp2.initialize()
    ap06 = collect(comp2, "ASSY-SL03", "MTR-0002")
    ap06_q = pick(ap06, "mes.quality_result",
                  lambda p: p.get("station_id") == "AP06", first=False)
    if ap06_q:
        result["ap06_fail_attempt1"] = next(
            (m for m in ap06_q if m["payload"].get("disposition") == "FAIL"), None)
        result["ap06_pass_attempt2"] = next(
            (m for m in ap06_q
             if m["payload"].get("disposition") == "PASS"
             and m["payload"].get("attempt_number") == 2), None)

    # AP08 NG → PASS (ASSY-SL02 motor 2)
    comp3 = AssyDemoComposition(config_path=TIPA_YAML,
                                scenario=DemoScenario.AP08_NG_REINSPECT_PASS)
    comp3.initialize()
    ap08 = collect(comp3, "ASSY-SL02", "MTR-0002")
    ap08_q = pick(ap08, "mes.quality_result",
                  lambda p: p.get("station_id") == "AP08", first=False)
    if ap08_q:
        result["ap08_ng_attempt1"] = next(
            (m for m in ap08_q if m["payload"].get("disposition") == "NG"), None)
        result["ap08_pass_attempt2"] = next(
            (m for m in ap08_q
             if m["payload"].get("disposition") == "PASS"
             and m["payload"].get("attempt_number") == 2), None)

    out = Path(__file__).resolve().parent / "vf-p0-messages.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} with {sum(1 for v in result.values() if v)} examples")
    # Print keys + run_id of each for quick verification
    for k, v in result.items():
        if v:
            print(f"  {k}: run_id={v['payload'].get('run_id')} msg_key={v['message_key'][:60]}")


if __name__ == "__main__":
    main()
