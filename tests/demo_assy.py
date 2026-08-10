"""M6-S02 — TIPA ASSY Demo Fixture.

Demonstrates the synchronized indexed ASSY line with:
- SSO2/RSO2 upstream production
- Multi-WIP concurrent dwell processing
- AP04 join with genealogy
- Deterministic happy path to RELEASED_FINISHED_GOOD

No UI, no MES wiring, no conveyor physics. Runtime verification only.
"""

from __future__ import annotations

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
)


def run_tipa_demo(
    num_motors: int = 2,
    dwell_time_s: float = 120.0,
    verbose: bool = True,
) -> AssyLineRuntime:
    """Run the TIPA ASSY demo.

    Args:
        num_motors: Number of complete motors to produce.
        dwell_time_s: Nominal line dwell time (120s confirmed).
        verbose: Print trace to stdout.

    Returns:
        The runtime after completion, with trace and genealogy populated.
    """
    # Configure with demo-appropriate timings
    config = AssyLineConfig()
    config.conveyor.nominal_line_dwell_time_s = dwell_time_s
    config.conveyor.index_movement_duration_s = 0.0  # instantaneous

    # Create runtime
    line = AssyLineRuntime(config=config)

    if verbose:
        print("=" * 60)
        print("TIPA ASSY Demo — M6-S02 Runtime Verification")
        print(f"Target: {num_motors} motor(s)")
        print(f"Nominal dwell: {dwell_time_s}s")
        print("=" * 60)
        print()

    # Produce initial upstream WIPs
    sso2_ids: list[str] = []
    rso2_ids: list[str] = []

    # We need SSO2 WIPs and RSO2 WIPs
    # For each motor: 1 SSO2 + 1 RSO2
    # Plus initial line fill

    total_sso2_needed = num_motors + 3  # line fill + motors
    total_rso2_needed = num_motors + 1  # buffer + motors

    for i in range(total_sso2_needed):
        wid = line.produce_sso2_wip()
        sso2_ids.append(wid)
        if verbose:
            print(f"  [UPSTREAM] SSO2: {wid}")

    for i in range(total_rso2_needed):
        rid = line.produce_rso2_wip()
        rso2_ids.append(rid)
        if verbose:
            print(f"  [UPSTREAM] RSO2: {rid}")

    if verbose:
        print()

    # Introduce first WIP to ASSY
    carrier_seq = 1
    sso2_idx = 0

    def next_carrier() -> str:
        nonlocal carrier_seq
        cid = f"PAL-{carrier_seq:03d}"
        carrier_seq += 1
        return cid

    # Introduce first SSO2 WIP
    first_wip = sso2_ids[sso2_idx]
    sso2_idx += 1
    line.introduce_to_assy(first_wip, next_carrier())
    if verbose:
        print(f"[LINE] Introduced {first_wip} at PRE-ASSY")

    completed_motors = 0
    dwell = 0
    max_dwells = 100  # safety limit

    while completed_motors < num_motors and dwell < max_dwells:
        dwell += 1

        # --- DWELL BEGIN ---
        line.conveyor.begin_dwell(dwell_time_s)
        line.conveyor.begin_operating()

        if verbose:
            occupied = line.conveyor.occupied_positions()
            status_line = f"DWELL {dwell:02d} | "
            parts = []
            for pos in line.conveyor.positions:
                wip = line.conveyor.wip_at(pos)
                if wip:
                    parts.append(f"{pos}:{wip}")
            status_line += " | ".join(parts) if parts else "(empty)"
            print(status_line)

        # --- PROCESS EACH OCCUPIED POSITION ---
        for pos in line.conveyor.occupied_positions():
            wip = line.conveyor.wip_at(pos)
            if wip is None:
                continue

            if pos == "PRE-ASSY":
                if verbose:
                    print(f"  [{pos}] processing {wip}")

            elif pos == "AP04":
                # JOIN: require RSO2
                if not line._rso2_wips:
                    rid = line.produce_rso2_wip()
                    rso2_ids.append(rid)
                    if verbose:
                        print(f"  [UPSTREAM] RSO2 (on-demand): {rid}")

                join_events = line._execute_ap04_join(wip)
                for evt in join_events:
                    if verbose and evt.event_type == "AP04_JOIN":
                        print(f"  [{pos}] JOIN → {evt.wip_id} | parents={evt.detail}")

            elif pos == "AP11":
                # Final QC
                child_id = wip
                ws = line.get_wip(child_id)
                if ws:
                    from virtual_factory.assembly.line_runtime import WipLifecycle
                    ws.lifecycle = WipLifecycle.RELEASED
                completed_motors += 1
                if verbose:
                    print(f"  [{pos}] RELEASED {wip} ✓ (motor #{completed_motors})")

            else:
                if verbose:
                    duration = line.config.station_durations.get(pos, 60)
                    print(f"  [{pos}] processing {wip} (duration={duration}s)")

            line.conveyor.mark_position_complete(pos)

        # --- CHECK READY ---
        ready = line.conveyor.check_ready()

        if ready:
            if verbose:
                print(f"  → READY TO INDEX")
            # Introduce next SSO2 WIP before indexing (if available)
            if sso2_idx < len(sso2_ids) and line.conveyor.wip_at("PRE-ASSY") is None:
                next_wip = sso2_ids[sso2_idx]
                sso2_idx += 1
                line.introduce_to_assy(next_wip, next_carrier())
                if verbose:
                    print(f"  [LINE] Introduced {next_wip} at PRE-ASSY")

            if verbose:
                print(f"  INDEX {dwell:02d}")
            line.conveyor.index()
        else:
            if verbose:
                print(f"  → DWELL EXTENDED (overrun — PROVISIONAL)")

        if verbose:
            print()

    # --- SUMMARY ---
    if verbose:
        print("=" * 60)
        print("DEMO COMPLETE")
        print(f"Completed motors: {completed_motors}")
        print(f"Total dwells: {dwell}")
        print(f"Total trace events: {len(line.trace)}")
        print(f"Genealogy records: {len(line.genealogy)}")
        print()

        for rec in line.genealogy.all_records():
            print(f"  Genealogy: {rec.child_wip_id}")
            print(f"    Parents: {list(rec.parent_wip_ids)}")
            print(f"    Components: {list(rec.component_ids)}")
            print(f"    Station: {rec.join_station} @ t={rec.join_time_s:.0f}s")

    return line


# ═══════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_tipa_demo(num_motors=2, dwell_time_s=120.0, verbose=True)
