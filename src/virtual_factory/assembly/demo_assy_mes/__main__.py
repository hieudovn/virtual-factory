"""TIPA ASSY Customer Demo Scenario v1 — end-to-end demo runner.

VF-DM-DEMO-ASSY-MES-01. One command runs the full deterministic demo and
writes JSONL + contract fixtures.

Usage:
    python -m virtual_factory.assembly.demo_assy_mes [--jsonl PATH] [--fixtures DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtual_factory.assembly.demo_assy_mes.bridge import build_demo_pipeline
from virtual_factory.assembly.demo_assy_mes.fixtures import build_fixtures
from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway
from virtual_factory.integration.gateways.memory import InMemoryObsGateway


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TIPA ASSY Customer Demo Scenario v1 (tipa-assy-demo-v1)")
    parser.add_argument("--jsonl", help="Write ProjectedMessages as JSONL")
    parser.add_argument("--fixtures", help="Write contract fixtures JSON to a dir")
    args = parser.parse_args()

    gateways = [InMemoryObsGateway()]
    jsonl_path = None
    if args.jsonl:
        jsonl_path = args.jsonl
        gateways.append(JsonlObsGateway(filepath=jsonl_path))
    pipeline = build_demo_pipeline(gateways=gateways)
    runner = DemoRunner(pipeline=pipeline)

    runner.run()
    messages = runner.delivered_messages()

    print(f"run_id: {runner.run_id}")
    print(f"line_state: {runner.line_state.value}")
    print(f"simulation_time_s: {runner.simulation_time_s}")
    print(f"total messages: {len(messages)}")
    if runner.oee:
        print("OEE summary:")
        print(json.dumps(runner.oee.to_dict(), indent=2))

    if args.fixtures:
        out_dir = Path(args.fixtures)
        out_dir.mkdir(parents=True, exist_ok=True)
        fixtures = build_fixtures(messages, runner.run_id)
        for name, value in fixtures["fixtures"].items():
            (out_dir / f"{name}.json").write_text(
                json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "fixtures-index.json").write_text(
            json.dumps({
                "contract_version": fixtures["contract_version"],
                "run_id": fixtures["run_id"],
                "subline_id": fixtures["subline_id"],
                "total_message_count": fixtures["total_message_count"],
                "fixture_names": sorted(fixtures["fixtures"].keys()),
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote fixtures to {out_dir}")

    if jsonl_path:
        print(f"wrote JSONL to {jsonl_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
