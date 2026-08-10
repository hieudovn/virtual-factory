"""M6-S02-C02 — TIPA ASSY Demo Fixture (YAML-driven, public API only).

Loads authoritative config from configs/plants/tipa_assy_demo.yaml.
Demonstrates: simulated time progression, multi-WIP concurrent dwell,
AP04 join with genealogy, overrun behavior, happy path to RELEASED.
Uses only public API.
"""

from __future__ import annotations

import os
from pathlib import Path

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig, AssyLineRuntime, ConveyorState, WipLifecycle,
    load_assy_config_from_yaml,
)

# Path to authoritative TIPA ASSY demo config
_TIPA_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "configs", "plants", "tipa_assy_demo.yaml"
)


def run_tipa_demo(
    num_motors: int = 2,
    verbose: bool = True,
    config_path: str | None = None,
) -> AssyLineRuntime:
    """Run TIPA ASSY demo.

    Loads config from configs/plants/tipa_assy_demo.yaml by default.
    All runtime behavior is driven by the YAML — no manual overrides.
    """
    path = config_path or _TIPA_CONFIG_PATH
    config = load_assy_config_from_yaml(path)
    line = AssyLineRuntime(config=config)

    if verbose:
        print("=" * 60)
        print("TIPA ASSY Demo — M6-S02-C02 (YAML-driven)")
        print(f"Config: {path}")
        print(f"Target: {num_motors} motor(s)")
        print(f"Nominal dwell: {config.conveyor.nominal_line_dwell_time_s:.0f}s")
        print("=" * 60)
        print()

    # Produce upstream WIPs
    total_sso2 = num_motors + 4
    total_rso2 = num_motors + 4  # one RSO2 per SSO2 that reaches AP04
    sso2_ids = [line.produce_sso2_wip() for _ in range(total_sso2)]
    rso2_ids = [line.produce_rso2_wip() for _ in range(total_rso2)]
    if verbose:
        for wid in sso2_ids:
            print(f"  [UPSTREAM] SSO2: {wid}")
        for rid in rso2_ids:
            print(f"  [UPSTREAM] RSO2: {rid}")
        print()

    carrier_seq = 1
    sso2_idx = 0
    completed = 0
    max_cycles = 200
    cycle = 0

    # Introduce first WIP
    first = sso2_ids[sso2_idx]; sso2_idx += 1
    line.introduce_to_assy(first, f"PAL-{carrier_seq:03d}")
    carrier_seq += 1
    if verbose:
        print(f"[LINE] Introduced {first} at PRE-ASSY")

    while completed < num_motors and cycle < max_cycles:
        cycle += 1

        # Show current state
        if verbose:
            parts = []
            for pos in line.conveyor.positions:
                w = line.conveyor.wip_at(pos)
                if w:
                    parts.append(f"{pos}:{w}")
            print(f"CYCLE {cycle:03d} | {' | '.join(parts) if parts else '(empty)'}")
            print(f"  state={line.conveyor.state.value} t={line.simulation_time_s:.0f}s")

        # Ensure RSO2 buffer sufficient (public API)
        ap04_wip = line.conveyor.wip_at("AP04")
        if ap04_wip and line.rso2_buffer_size == 0:
            line.produce_rso2_wip()
            if verbose:
                print(f"  [UPSTREAM] RSO2 (on-demand)")

        dwell_events = line.execute_dwell()

        if verbose:
            for e in dwell_events:
                if e.event_type in ("AP04_JOIN", "STATION_COMPLETE", "STATION_PROGRESS"):
                    print(f"  [{e.position}] {e.event_type} {e.wip_id} ({e.detail})")
                elif e.event_type == "DWELL_META":
                    print(f"  → {e.detail}")

        # Check for released WIPs at AP11
        for pos in line.conveyor.occupied_positions():
            wip = line.conveyor.wip_at(pos)
            if wip and pos == "AP11":
                ws = line.get_wip(wip)
                if ws and ws.lifecycle == WipLifecycle.RELEASED and ws.is_child_of_join:
                    completed += 1
                    if verbose:
                        print(f"  *** RELEASED {wip} (motor #{completed}) ***")

        # Index if ready
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()

            # Introduce next SSO2 if available and PRE-ASSY empty
            if sso2_idx < len(sso2_ids) and line.conveyor.wip_at("PRE-ASSY") is None:
                next_wip = sso2_ids[sso2_idx]; sso2_idx += 1
                line.introduce_to_assy(next_wip, f"PAL-{carrier_seq:03d}")
                carrier_seq += 1
                if verbose:
                    print(f"  [LINE] Introduced {next_wip}")

        if verbose:
            print()

    # Summary
    if verbose:
        print("=" * 60)
        print("DEMO COMPLETE")
        print(f"Completed motors: {completed}")
        print(f"Total cycles: {cycle}")
        print(f"Simulation time: {line.simulation_time_s:.0f}s")
        print(f"Trace events: {len(line.trace)}")
        print(f"Genealogy records: {len(line.genealogy)}")
        print()

        for rec in line.genealogy.all_records():
            child_ws = line.get_wip(rec.child_wip_id)
            lc = child_ws.lifecycle.value if child_ws else "?"
            print(f"  {rec.child_wip_id} [{lc}]")
            print(f"    parents={list(rec.parent_wip_ids)}")
            print(f"    join_time={rec.join_time_s:.0f}s")

    return line


if __name__ == "__main__":
    run_tipa_demo(num_motors=2, verbose=True)
