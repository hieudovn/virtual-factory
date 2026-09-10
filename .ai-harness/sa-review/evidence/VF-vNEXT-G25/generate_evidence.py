#!/usr/bin/env python3
"""G25 integrated acceptance evidence generator (deterministic).

Runs the two integrated MVP flows through the Workspace Shell backend
(``WorkspaceMonitor`` over the G23 registry + G22 RuntimeSession) and writes
deterministic JSON traces into this evidence directory:

- flow-a-tipa.json  : select TIPA, step xN, six live sub-lines, reset/replay
- flow-b-shwtp.json : select shwtp, step xN, 5-scope slice live values,
                      reset/replay, fidelity/status/assumed-topology
- invariants.json   : platform invariants re-proven (independence, no coupling)

No randomness, no wall-clock: identical output on every run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent.parent

sys.path.insert(0, str(REPO / "src"))

from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

TIPA_CONFIG = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")


def _monitor() -> WorkspaceMonitor:
    return WorkspaceMonitor(tipa_config_path=TIPA_CONFIG)


def _norm(transfer_id: str) -> str:
    return transfer_id.split("::", 1)[1] if "::" in transfer_id else transfer_id


def _trace(view):
    return [
        {
            "status": s["status"],
            "target_time_s": s["target_time_s"],
            "participants": s["participants"],
            "committed": sorted(_norm(t) for t in s["committed"]),
        }
        for s in view["trace"]
    ]


def flow_a() -> dict:
    mon = _monitor()
    mon.select("TIPA")
    mon.control("TIPA", "step")
    mon.control("TIPA", "step")
    view = mon.view("TIPA")
    sub_lines = [
        {
            "sub_line_id": r["sub_line_id"],
            "scope": r["scope"],
            "variant": r["variant"],
            "simulation_time_s": r["simulation_time_s"],
            "conveyor_state": r["conveyor_state"],
            "wip_count": r["wip_count"],
            "motor_count": r["motor_count"],
            "rso2_buffer_size": r["rso2_buffer_size"],
        }
        for r in view["sub_lines"]
    ]
    trace = _trace(view)
    # deterministic replay equivalence
    mon.control("TIPA", "replay")
    mon.control("TIPA", "step")
    mon.control("TIPA", "step")
    replay_trace = _trace(mon.view("TIPA"))
    return {
        "flow": "A-TIPA",
        "workspace_id": view["workspace_id"],
        "runtime_kind": view["runtime_kind"],
        "session": view["session"],
        "sub_line_count": len(sub_lines),
        "sub_lines": sub_lines,
        "trace": trace,
        "replay_equivalent": trace == replay_trace,
        "legacy_demo": view["legacy_demo"],
        "site_truth": view["site_truth"],
    }


def flow_b() -> dict:
    mon = _monitor()
    mon.select("shwtp")
    for _ in range(4):
        mon.control("shwtp", "step")
    view = mon.view("shwtp")
    scopes = [
        {
            "scope": v["scope"],
            "canonical_id": v["canonical_id"],
            "role": v["role"],
            "fidelity": v["fidelity"],
            "status": v["status"],
            "inbound_link_assumed": v["inbound_link_assumed"],
            "current_values": v.get("current_values", {}),
        }
        for v in view["values"]
    ]
    trace = _trace(view)
    mon.control("shwtp", "replay")
    for _ in range(4):
        mon.control("shwtp", "step")
    replay_trace = _trace(mon.view("shwtp"))
    return {
        "flow": "B-SH-WTP",
        "workspace_id": view["workspace_id"],
        "runtime": view["runtime"],
        "session": view["session"],
        "scopes": scopes,
        "scope_count": len(scopes),
        "assumed_topology": view["assumed_topology"],
        "trace": trace,
        "replay_equivalent": trace == replay_trace,
        "site_truth": view["site_truth"],
        "ui_note": view["ui_note"],
    }


def invariants() -> dict:
    mon = _monitor()
    tipa = mon.select("TIPA")
    shwtp = mon.select("shwtp")
    tipa_run, shwtp_run = tipa["session"]["run_id"], shwtp["session"]["run_id"]
    mon.control("TIPA", "step")
    tipa_steps = mon.view("TIPA")["session"]["step_count"]
    mon.select("shwtp")
    mon.control("shwtp", "step")
    mon.control("shwtp", "step")
    tipa_after = mon.view("TIPA")["session"]["step_count"]
    return {
        "workspace_ids": list(mon.workspace_ids()),
        "independent_run_ids": tipa_run != shwtp_run,
        "no_cross_workspace_mutation": tipa_steps == tipa_after,
        "registry_metadata_keys": sorted(mon.workspace_list().keys()),
        "shwtp_bridge_slice_coupling_policy": _shwtp_coupling(mon),
        "shwtp_assumed_not_site_truth": mon.view("shwtp")["site_truth"] is False,
    }


def _shwtp_coupling(mon) -> str:
    session = mon._sessions["shwtp"]  # white-box read-only inspection
    bridge = session.record.bridge
    if bridge is None or getattr(bridge, "slice", None) is None:
        return "not_built"
    return bridge.slice.coupling_policy


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "flow-a-tipa.json").write_text(
        json.dumps(flow_a(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (HERE / "flow-b-shwtp.json").write_text(
        json.dumps(flow_b(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (HERE / "invariants.json").write_text(
        json.dumps(invariants(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("evidence written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
