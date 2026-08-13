"""SIM-VAL-01 — Minimal ASSY continuous-flow validation runner.

Runs one ASSY sub-line continuously using the existing authoritative
AssyDemoComposition → AssyLineRuntime chain. No second simulation engine.

Feed policy: bounded upstream replenishment (SSO2 low-watermark top-up).
RSO2 is produced on-demand by the existing step_context orchestration.

Usage:
    python tools/run_assy_continuous_validation.py \
        --sub-line ASSY-SL01 --scenario HAPPY_PATH --steps 50 \
        --continuous-feed \
        --output docs/ui/evidence/sim-val-01/assy_sl01_trace.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)


def run(
    config_path: str,
    sub_line_id: str,
    scenario: str,
    steps: int,
    continuous_feed: bool,
    output_path: str,
) -> dict:
    composition = AssyDemoComposition(
        config_path=config_path,
        scenario=DemoScenario(scenario),
        selected_sub_line_id=sub_line_id,
        continuous_feed_enabled=continuous_feed,
    )
    composition.initialize()
    composition.select_sub_line(sub_line_id)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prev_genealogy_len = 0
    prev_quality_len = 0
    starvation_step = None
    total_released_before_starvation = 0

    with out_path.open("w", encoding="utf-8") as fh:
        for step in range(steps):
            ctx = composition.selected_context
            assert ctx is not None

            # Continuous feed is applied inside composition.step_all()
            # via the shared ContinuousFeedPolicy. No duplicate logic here.

            composition.step_all()

            snap = composition.snapshot()
            d = snap.to_dict()

            # Detect starvation: line not indexing and no pending SSO2 feed
            if (snap.line_state == "stopped"
                    and ctx.sso2_idx >= len(ctx.sso2_ids)
                    and snap.production.wips_on_line == 0
                    and starvation_step is None):
                starvation_step = step
                total_released_before_starvation = snap.production.motors_released

            # New genealogy/quality events since last step
            new_genealogy = d.get("genealogy", [])[prev_genealogy_len:]
            new_quality = d.get("recent_quality_events", [])[prev_quality_len:]
            prev_genealogy_len = len(d.get("genealogy", []))
            prev_quality_len = len(d.get("recent_quality_events", []))

            record = {
                "demo_step_number": composition.demo_step_number,
                "simulation_time_s": snap.simulation_time_s,
                "dwell_number": snap.dwell_number,
                "line_state": snap.line_state,
                "sub_line_id": snap.sub_line_id,
                "production": d.get("production"),
                "positions": [
                    p for p in d.get("positions", []) if p.get("is_occupied")
                ],
                "new_genealogy": new_genealogy,
                "new_quality_events": new_quality,
            }
            fh.write(json.dumps(record) + "\n")

    final = composition.snapshot()
    return {
        "steps": steps,
        "simulation_time_s": final.simulation_time_s,
        "motors_created": final.production.motors_created,
        "motors_released": final.production.motors_released,
        "wips_on_line": final.production.wips_on_line,
        "active_quality_holds": final.production.active_quality_holds,
        "sso2_buffer": final.production.sso2_buffer,
        "rso2_buffer": final.production.rso2_buffer,
        "genealogy_count": len(final.genealogy),
        "starvation_step": starvation_step,
        "released_before_starvation": total_released_before_starvation,
        "trace_path": str(out_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ASSY continuous validation runner")
    ap.add_argument("--config", default="configs/plants/tipa_assy_demo.yaml")
    ap.add_argument("--sub-line", default="ASSY-SL01")
    ap.add_argument("--scenario", default="HAPPY_PATH")
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--continuous-feed", action="store_true")
    ap.add_argument("--output", default="docs/ui/evidence/sim-val-01/assy_sl01_trace.jsonl")
    args = ap.parse_args()

    result = run(
        config_path=args.config,
        sub_line_id=args.sub_line,
        scenario=args.scenario,
        steps=args.steps,
        continuous_feed=args.continuous_feed,
        output_path=args.output,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
