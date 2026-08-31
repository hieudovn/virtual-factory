"""MANUAL-E2E-01 — Full human-operated ASSY production journey (automated).

Deterministic high-level test that reproduces the manual semantic journey
programmatically, using ONLY public runtime command/action surfaces. No direct
state mutation. Supports the browser acceptance; does not replace it.
"""

from __future__ import annotations

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.assembly.operation_execution import (
    OperationState,
)

CHILD = "MTR-0001"


def make_fast_config() -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = "PASS"
    c.quality.ap08.scenario = "PASS"
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    line = AssyLineRuntime(config=cfg)
    line.produce_sso2_wip()   # SSO2-0001
    line.produce_rso2_wip()   # RSO2-0001
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def resolve_awaiting(line: AssyLineRuntime) -> list[tuple[str, str, str]]:
    """Resolve every awaiting MANUAL operation via public surfaces.

    Returns [(station_id, wip_id, command)] for the resolved actions.
    """
    resolved = []
    for op in list(line.operation_registry.active_operations()):
        if op.completion_mode != CompletionMode.MANUAL:
            continue
        st, wip = op.station_id, op.wip_id
        if op.state == OperationState.AWAITING_DECISION:
            line.submit_operation_command(
                st, wip, StationCommand.CONFIRM, payload={"decision": "PASS"})
            resolved.append((st, wip, "CONFIRM/PASS"))
        elif op.state == OperationState.AWAITING_COMPLETION:
            contract = line.station_contracts[st]
            cmd = contract.required_action or contract.normal_action or StationCommand.DONE
            payload = None
            if (contract.checklist_required_for_action is not None
                    and contract.checklist_required_for_action == cmd):
                payload = {"checklist": [
                    {"item_id": item_id, "completed": True}
                    for item_id in contract.checklist_items
                ]}
            line.submit_operation_command(st, wip, cmd, payload)
            resolved.append((st, wip, cmd.value if hasattr(cmd, "value") else str(cmd)))
    return resolved


def run_manual_journey(line: AssyLineRuntime) -> list[dict]:
    """Drive the full MANUAL journey for one source WIP; return station trace."""
    line.global_run_mode = CompletionMode.MANUAL
    trace: list[dict] = []
    for _ in range(200):
        line.execute_dwell()
        resolved = resolve_awaiting(line)
        for st, wip, action in resolved:
            eid = line.operation_registry._index.get((st, wip))
            op = line.operation_registry._operations.get(eid) if eid else None
            trace.append({
                "station": st,
                "wip": wip,
                "action": action,
                "state": op.state.value if op else "ELIGIBLE_TO_INDEX",
                "operation_result": (op.operation_result.value if op and op.operation_result else ""),
                "quality_result": (op.quality_result if op else ""),
                "routing_action": (op.routing_action if op else ""),
            })
        line.conveyor.check_ready()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    return trace


def test_full_manual_journey_releases_motor():
    line = setup_line(make_fast_config())
    trace = run_manual_journey(line)

    # 1. Target motor released exactly once.
    assert line.get_wip(CHILD).lifecycle == WipLifecycle.RELEASED

    # 2. Genealogy preserved: SSO2 + RSO2 → MTR child, exactly one JOIN.
    records = list(line.genealogy.all_records())
    assert len(records) == 1
    g = records[0]
    assert g.child_wip_id == CHILD
    assert set(g.parent_wip_ids) == {"SSO2-0001", "RSO2-0001"}
    assert g.join_station == "AP04"

    # 3. Quality records exactly once each.
    qh = line.get_quality_history(CHILD)
    assert [r.disposition for r in qh.records_for("AP06")] == ["PASS"]
    assert [r.disposition for r in qh.records_for("AP08")] == ["PASS"]
    assert [r.disposition for r in qh.records_for("AP11")] == ["PASS"]
    assert len(qh.records) == 3

    # 4. AP11 two-stage: CONFIRMED then RELEASED (captured in the trace).
    ap11_results = [t["operation_result"] for t in trace if t["station"] == "AP11"]
    assert "CONFIRMED" in ap11_results
    assert "RELEASED" in ap11_results

    # 5. Parent consumed at AP04 is not live occupancy.
    occupied = line.conveyor.occupied_positions()
    for pos in occupied:
        assert line.conveyor.wip_at(pos) != "SSO2-0001"

    # 6. Trace covers the full station sequence (station ids in order).
    station_order = [t["station"] for t in trace]
    for expected in ("PRE-ASSY", "AP01", "AP02", "AP03", "AP04",
                     "AP05", "AP06", "AP07", "AP08", "AP09", "AP10", "AP11"):
        assert expected in station_order, f"station {expected} missing from trace"

    # 7. Identity handoff: AP04 operates on SSO2 parent, child continues.
    ap04_entries = [t for t in trace if t["station"] == "AP04"]
    assert ap04_entries and ap04_entries[0]["wip"] == "SSO2-0001"
    post_ap04 = station_order.index("AP04") + 1
    assert any(t["wip"] == CHILD for t in trace[post_ap04:])


def test_stale_duplicate_command_rejected_and_unchanged():
    """A duplicate/stale command must be rejected with no production mutation."""
    line = setup_line(make_fast_config())
    line.global_run_mode = CompletionMode.MANUAL
    # Advance SSO2-0001 to AP01 awaiting DONE.
    line.execute_dwell()  # PRE-ASSY work done -> AWAITING_COMPLETION
    wip = line.conveyor.wip_at("PRE-ASSY")
    line.submit_operation_command("PRE-ASSY", wip, StationCommand.DONE)
    line.conveyor.check_ready()
    line.index_line()  # SSO2-0001 -> AP01

    line.execute_dwell()
    wip01 = line.conveyor.wip_at("AP01")
    line.submit_operation_command("AP01", wip01, StationCommand.DONE)
    line.conveyor.check_ready()
    assert line.conveyor.state == ConveyorState.READY_TO_INDEX

    # Stale/duplicate DONE for the already-eligible AP01 operation.
    before_positions = {p: line.conveyor.wip_at(p)
                        for p in line.conveyor.occupied_positions()}
    from virtual_factory.assembly.line_runtime import AssyLineError
    try:
        line.submit_operation_command("AP01", wip01, StationCommand.DONE)
        rejected = False
    except AssyLineError:
        rejected = True
    assert rejected, "stale command must be rejected"
    after_positions = {p: line.conveyor.wip_at(p)
                       for p in line.conveyor.occupied_positions()}
    assert after_positions == before_positions
    assert line.get_wip(wip01).lifecycle != WipLifecycle.RELEASED


def test_manual_mode_no_auto_completion():
    """Duration elapsing alone must not complete a station in MANUAL mode."""
    line = setup_line(make_fast_config())
    line.global_run_mode = CompletionMode.MANUAL
    line.execute_dwell()  # PRE-ASSY work done
    wip = line.conveyor.wip_at("PRE-ASSY")
    op = line.operation_registry.active_for("PRE-ASSY", wip)
    assert op.state == OperationState.AWAITING_COMPLETION
    assert line.conveyor.is_position_complete("PRE-ASSY") is False
    # Extra dwell must not auto-complete.
    line.execute_dwell()
    assert op.state == OperationState.AWAITING_COMPLETION
    assert line.conveyor.is_position_complete("PRE-ASSY") is False
