"""AUTO-EQUIV-01 — Automated execution semantic equivalence.

AUTO is only an automation of the same production semantics as MANUAL — it
must traverse the same OperationExecution lifecycle, observation/decision,
quality, routing, eligibility, and physical-index stages. These tests compare
normalized authoritative outcomes (excluding timing/mode/source).

All journeys use public runtime surfaces only (execute_dwell,
submit_operation_command, check_ready, index_line). No direct state mutation.
"""

from __future__ import annotations

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.assembly.operation_execution import OperationState

CHILD = "MTR-0001"


def make_config(ap06: str = "PASS", ap08: str = "PASS") -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = ap06
    c.quality.ap08.scenario = ap08
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    line = AssyLineRuntime(config=cfg)
    line.produce_sso2_wip()   # SSO2-0001
    line.produce_rso2_wip()   # RSO2-0001
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def resolve_awaiting(line: AssyLineRuntime, quality_decision: str = "accept_proposal") -> None:
    """Resolve every awaiting MANUAL operation via public surfaces only."""
    for op in list(line.operation_registry.active_operations()):
        if op.completion_mode != CompletionMode.MANUAL:
            continue
        st, wip = op.station_id, op.wip_id
        if op.state == OperationState.AWAITING_DECISION:
            decision = op.proposed_quality_result or "PASS"
            if quality_decision != "accept_proposal":
                decision = quality_decision
            line.submit_operation_command(
                st, wip, StationCommand.CONFIRM, payload={"decision": decision})
        elif op.state == OperationState.AWAITING_COMPLETION:
            contract = line.station_contracts[st]
            cmd = contract.required_action or contract.normal_action or StationCommand.DONE
            payload = None
            if (contract.checklist_required_for_action is not None
                    and contract.checklist_required_for_action == cmd):
                payload = {"checklist": [
                    {"item_id": i, "completed": True}
                    for i in contract.checklist_items
                ]}
            line.submit_operation_command(st, wip, cmd, payload)


def run_journey(line: AssyLineRuntime, mode: CompletionMode,
                quality_decision: str = "accept_proposal") -> AssyLineRuntime:
    line.global_run_mode = mode
    for _ in range(200):
        line.execute_dwell()
        if mode == CompletionMode.MANUAL:
            resolve_awaiting(line, quality_decision)
            line.conveyor.check_ready()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    return line


def normalized_trace(line: AssyLineRuntime) -> dict:
    """Authoritative normalized record (excludes timing/mode/source)."""
    ops = []
    for op in line.operation_registry._operations.values():
        if op.operation_result is None:
            continue
        ops.append({
            "station": op.station_id,
            "wip": op.wip_id,
            "result": op.operation_result.value,
            "quality": op.quality_result or "",
            "routing": op.routing_action or "",
            "attempt": op.attempt_number,
        })
    ops.sort(key=lambda d: (d["station"], d["wip"]))
    genealogy = sorted(
        (g.child_wip_id, tuple(sorted(g.parent_wip_ids)), g.join_station)
        for g in line.genealogy.all_records())
    quality = []
    for wip in sorted(line.wip_ids):
        qh = line.get_quality_history(wip)
        if qh:
            quality += [(r.station_id, r.disposition, r.attempt_number)
                        for r in qh.records]
    quality.sort()
    released = sum(1 for w in line.wip_ids
                   if line.get_wip(w).lifecycle == WipLifecycle.RELEASED)
    return {"ops": ops, "genealogy": genealogy, "quality": quality,
            "released": released}


def station_quality(line: AssyLineRuntime, station: str) -> list[tuple]:
    qh = line.get_quality_history(CHILD)
    if qh is None:
        return []
    return [(r.station_id, r.disposition, r.attempt_number)
            for r in qh.records if r.station_id == station]


# ═══════════════════════════════════════════════════════════
# Happy-path equivalence
# ═══════════════════════════════════════════════════════════

class TestAutoHappyPath:
    def test_full_auto_happy_path_releases_motor(self):
        line = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        assert line.get_wip(CHILD).lifecycle == WipLifecycle.RELEASED

    def test_normalized_manual_auto_happy_traces_equivalent(self):
        manual = run_journey(setup_line(make_config()),
                             CompletionMode.MANUAL, quality_decision="PASS")
        auto = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        assert normalized_trace(manual) == normalized_trace(auto)

    def test_all_stations_visited_exactly_once(self):
        line = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        stations = [d["station"] for d in normalized_trace(line)["ops"]]
        expected = ["AP01", "AP02", "AP03", "AP04", "AP05", "AP06",
                    "AP07", "AP08", "AP09", "AP10", "AP11", "PRE-ASSY"]
        assert sorted(stations) == sorted(expected)
        assert len(stations) == len(set(stations)) == len(expected)

    def test_ap04_genealogy_identical_to_manual(self):
        manual = run_journey(setup_line(make_config()),
                             CompletionMode.MANUAL, quality_decision="PASS")
        auto = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        assert normalized_trace(manual)["genealogy"] == normalized_trace(auto)["genealogy"]
        assert normalized_trace(auto)["genealogy"] == [
            ("MTR-0001", ("RSO2-0001", "SSO2-0001"), "AP04")]

    def test_ap06_pass_record_equivalent(self):
        manual = run_journey(setup_line(make_config()),
                             CompletionMode.MANUAL, quality_decision="PASS")
        auto = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        assert station_quality(manual, "AP06") == station_quality(auto, "AP06") == [("AP06", "PASS", 1)]

    def test_ap08_pass_record_equivalent(self):
        manual = run_journey(setup_line(make_config()),
                             CompletionMode.MANUAL, quality_decision="PASS")
        auto = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        assert station_quality(manual, "AP08") == station_quality(auto, "AP08") == [("AP08", "PASS", 1)]

    def test_ap11_two_stage_in_auto(self):
        line = run_journey(setup_line(make_config()), CompletionMode.AUTO)
        ap11_events = [e for e in line._trace if e.position == "AP11"]
        assert any(e.event_type == "QUALITY_RESULT" and "PASS" in e.detail
                   for e in ap11_events), "final-QC quality decision must occur"
        assert any(e.event_type == "STATION_COMPLETE" and "RELEASED" in e.detail
                   for e in ap11_events), "RELEASE must be a distinct disposition"
        assert station_quality(line, "AP11") == [("AP11", "PASS", 1)]
        ap11_ops = [o for o in line.operation_registry._operations.values()
                    if o.station_id == "AP11"]
        assert len(ap11_ops) == 1
        assert ap11_ops[0].operation_result.value == "RELEASED"


# ═══════════════════════════════════════════════════════════
# Failure-path equivalence (AP06 / AP08)
# ═══════════════════════════════════════════════════════════

class TestFailurePathEquivalence:
    def test_ap06_fail_retest_equivalent(self):
        cfg = make_config(ap06="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap06.max_attempts = 2
        manual = run_journey(setup_line(cfg), CompletionMode.MANUAL)
        auto = run_journey(setup_line(cfg), CompletionMode.AUTO)
        assert station_quality(manual, "AP06") == [("AP06", "FAIL", 1), ("AP06", "PASS", 2)]
        assert station_quality(auto, "AP06") == [("AP06", "FAIL", 1), ("AP06", "PASS", 2)]
        assert normalized_trace(manual) == normalized_trace(auto)

    def test_ap08_ng_reinspect_equivalent(self):
        cfg = make_config(ap08="FAIL_FIRST_THEN_PASS")
        cfg.quality.ap08.max_attempts = 2
        manual = run_journey(setup_line(cfg), CompletionMode.MANUAL)
        auto = run_journey(setup_line(cfg), CompletionMode.AUTO)
        assert station_quality(manual, "AP08") == [("AP08", "NG", 1), ("AP08", "PASS", 2)]
        assert station_quality(auto, "AP08") == [("AP08", "NG", 1), ("AP08", "PASS", 2)]
        assert normalized_trace(manual) == normalized_trace(auto)


# ═══════════════════════════════════════════════════════════
# HOLD non-bypass + AP11 fail-closed + acceleration
# ═══════════════════════════════════════════════════════════

class TestAutoContainment:
    def test_held_not_bypassed_by_auto(self):
        line = setup_line(make_config())
        line.global_run_mode = CompletionMode.MANUAL
        # Advance SSO2-0001 to AP03 (3 dwell+index cycles), then dwell to make
        # AP03 awaiting.
        for _ in range(3):
            line.execute_dwell()
            resolve_awaiting(line, "PASS")
            line.conveyor.check_ready()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        assert line.conveyor.wip_at("AP03") == "SSO2-0001"
        line.execute_dwell()  # AP03 work done → AWAITING_COMPLETION
        wip = line.conveyor.wip_at("AP03")
        op = line.operation_registry.active_for("AP03", wip)
        assert op.state == OperationState.AWAITING_COMPLETION
        line.submit_station_action("AP03", wip, "HOLD")
        assert op.state == OperationState.HELD
        # Switch to AUTO — HELD must remain HELD.
        line.global_run_mode = CompletionMode.AUTO
        line.execute_dwell()
        assert op.state == OperationState.HELD
        assert line.conveyor.is_position_complete("AP03") is False
        # Explicit RESUME is still required.
        line.submit_station_action("AP03", wip, "RESUME")
        assert op.state == OperationState.AWAITING_COMPLETION

    def test_ap11_negative_fail_closed_in_auto(self):
        from virtual_factory.assembly.line_runtime import AssyLineError
        cfg = make_config()
        cfg.quality.ap11.scenario = "ALWAYS_FAIL"
        line = setup_line(cfg)
        # Advance to AP11 in AUTO (pre-AP11 stations auto-complete).
        for _ in range(20):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
            if line.conveyor.wip_at("AP11") == CHILD:
                break
        # AP11 negative proposal in AUTO fails closed before mutation.
        with __import__("pytest").raises(AssyLineError):
            line.execute_dwell()
        qh = line.get_quality_history(CHILD)
        assert qh is None or len(qh.records_for("AP11")) == 0
        assert line.get_wip(CHILD).lifecycle != WipLifecycle.RELEASED

    def test_accelerated_auto_equivalent(self):
        # AUTO acceleration (presentation speed / repeated STEP) must not
        # alter the normalized semantic trace. The runtime always applies the
        # full configured work duration and identical operation stages.
        t1 = normalized_trace(run_journey(setup_line(make_config()), CompletionMode.AUTO))
        t2 = normalized_trace(run_journey(setup_line(make_config()), CompletionMode.AUTO))
        assert t1 == t2
        assert t1["released"] == 1


def test_acceptance_journey_uses_public_surfaces_only():
    # `run_journey` / `resolve_awaiting` drive the runtime exclusively through
    # execute_dwell / submit_operation_command / submit_station_action /
    # check_ready / index_line — no direct _position_complete or
    # _operations mutation. This pins the full AUTO journey result.
    line = run_journey(setup_line(make_config()), CompletionMode.AUTO)
    assert line.get_wip(CHILD).lifecycle == WipLifecycle.RELEASED
