"""M6-INT-01 evidence generator — ordered P0 outbound traces.

Reproducible: runs the real TIPA ASSY composition through the observation
bridge and writes the ordered P0 outbound trace for:

1. HAPPY_PATH (ASSY-SL01, one motor) — full journey including AP11 QC + RELEASE.
2. AP06_FAIL_RETEST_PASS (ASSY-SL03, motor 2) — exception trace FAIL → PASS.

Also demonstrates idempotency: a second poll emits nothing new.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "src"))

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.line_runtime import WipLifecycle
from virtual_factory.assembly.observation_bridge import (
    build_assy_observation_pipeline,
)

TIPA_YAML = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)
OUT = Path(__file__).resolve().parent


def drive_until(comp: AssyDemoComposition, sl_id: str, motor_id: str,
                max_steps: int = 400) -> None:
    ctx = comp.get_context(sl_id)
    for _ in range(max_steps):
        ctx.step_context()
        ws = ctx.runtime.get_wip(motor_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            return
    raise RuntimeError(f"{sl_id} did not release {motor_id}")


def format_trace(bridge) -> str:
    lines = []
    for t in bridge.outbound_trace:
        p = t["payload"]
        kind = p.get("event_type", "")
        detail = ""
        if p.get("disposition"):
            detail = f"attempt={p.get('attempt_number')} disposition={p['disposition']}"
        elif p.get("operation_result"):
            detail = f"result={p['operation_result']}"
        elif p.get("child_wip_id"):
            detail = f"child={p['child_wip_id']} parents={sorted(p['parent_wip_ids'])}"
        lines.append(
            f"{t['message_type']:<28} {t['source_event_id']:<22} "
            f"{kind:<22} {p.get('station_id', ''):<8} {detail}"
        )
    return "\n".join(lines)


def happy_path_trace() -> str:
    comp = AssyDemoComposition(config_path=TIPA_YAML,
                               scenario=DemoScenario.HAPPY_PATH)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    drive_until(comp, "ASSY-SL01", "MTR-0001")
    bridge.poll(comp)
    first = format_trace(bridge)
    results = bridge.poll(comp)   # idempotency: second poll
    assert results == [], "second poll must emit nothing"
    assert bridge.outbound_trace, "expected a non-empty trace"
    return first + "\n\n[second poll: 0 new deliveries — idempotent]\n"


def exception_trace() -> str:
    comp = AssyDemoComposition(config_path=TIPA_YAML,
                               scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    drive_until(comp, "ASSY-SL03", "MTR-0002")   # motor 2 carries FAIL→PASS
    bridge.poll(comp)
    ap06 = sorted(
        [t for t in bridge.outbound_trace
         if t["payload"].get("station_id") == "AP06"
         and t["payload"].get("wip_id") == "MTR-0002"],
        key=lambda t: t["payload"]["attempt_number"])
    lines = []
    for t in ap06:
        p = t["payload"]
        lines.append(
            f"{t['message_type']:<28} {t['source_event_id']:<22} "
            f"QUALITY_RESULT {'AP06':<8} "
            f"attempt={p['attempt_number']} disposition={p['disposition']}"
        )
    assert [p["payload"]["disposition"] for p in ap06] == ["FAIL", "PASS"], ap06
    return "\n".join(lines)


def main() -> None:
    hp = happy_path_trace()
    (OUT / "trace-happy-path.txt").write_text(hp + "\n", encoding="utf-8")
    exc = exception_trace()
    (OUT / "trace-ap06-fail-retest.txt").write_text(exc + "\n", encoding="utf-8")
    print("HAPPY_PATH trace:")
    print(hp)
    print("\nAP06 FAIL→PASS exception trace:")
    print(exc)


if __name__ == "__main__":
    main()
