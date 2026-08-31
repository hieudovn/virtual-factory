"""DEMO-CANDIDATE-01 — TIPA ASSY integrated rehearsal evidence generator.

Drives the real TIPA ASSY composition through the accepted runtime + bridge
and emits evidence markdown for:
- rehearsal matrix R1..R5
- timing/bottleneck T1..T3
- MES outbound validation
- 3x repeatability

No new architecture; uses only accepted semantics and public surfaces.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "src"))

import json

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.observation_bridge import (
    EVENT_AP11_RELEASE,
    build_assy_observation_pipeline,
)
from virtual_factory.assembly.operation_execution import OperationState
from virtual_factory.assembly.quality_records import QualityStatus
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway
from virtual_factory.integration.gateways.memory import InMemoryObsGateway

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")
OUT = Path(__file__).resolve().parent
CHILD = "MTR-0001"


def drive_until(comp, sl_id, motor_id, max_steps=500):
    ctx = comp.get_context(sl_id)
    for _ in range(max_steps):
        ctx.step_context()
        ws = ctx.runtime.get_wip(motor_id)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            return True
    return False


def drive_steps(comp, sl_id, steps):
    ctx = comp.get_context(sl_id)
    for _ in range(steps):
        ctx.step_context()


# ═══════════════════════════════════════════════════════════
# R1 — HAPPY_PATH
# ═══════════════════════════════════════════════════════════

def r1_happy_path() -> dict:
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    ok = drive_until(comp, "ASSY-SL01", CHILD)
    bridge.poll(comp)
    ctx = comp.get_context("ASSY-SL01")
    ws = ctx.runtime.get_wip(CHILD)
    gen = ctx.runtime.genealogy.get(CHILD)
    released = sum(1 for w in ctx.runtime.wip_ids
                   if ctx.runtime.get_wip(w).lifecycle == WipLifecycle.RELEASED)
    n = len(bridge.outbound_trace)
    second = bridge.poll(comp)
    return {
        "ok": ok,
        "motor": CHILD,
        "release_time_s": ws.released_at_sim_s if ws else None,
        "ap04_parents": list(gen.parent_wip_ids) if gen else [],
        "observation_count": n,
        "second_poll_new": len(second),
        "released_count": released,
    }


# ═══════════════════════════════════════════════════════════
# R2 / R3 / R4 — exception scenarios
# ═══════════════════════════════════════════════════════════

def r2_ap06_fail_retest() -> dict:
    comp = AssyDemoComposition(config_path=TIPA_YAML,
                               scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    target = comp.target_sub_line_id
    ok = drive_until(comp, target, "MTR-0002")
    bridge.poll(comp)
    ctx = comp.get_context(target)
    qh = ctx.runtime.get_quality_history("MTR-0002")
    ap06 = [(r.disposition, r.attempt_number) for r in qh.records
            if r.station_id == "AP06"] if qh else []
    obs = [t for t in bridge.outbound_trace
           if t["payload"].get("station_id") == "AP06"
           and t["payload"].get("wip_id") == "MTR-0002"]
    second = bridge.poll(comp)
    return {
        "target": target,
        "released": ok,
        "ap06_attempts": ap06,
        "mes_quality_count": len(obs),
        "mes_record_ids": [t["source_event_id"] for t in obs],
        "second_poll_new": len(second),
    }


def r3_ap08_ng_reinspect() -> dict:
    comp = AssyDemoComposition(config_path=TIPA_YAML,
                               scenario=DemoScenario.AP08_NG_REINSPECT_PASS)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    target = comp.target_sub_line_id
    ok = drive_until(comp, target, "MTR-0002")
    bridge.poll(comp)
    ctx = comp.get_context(target)
    qh = ctx.runtime.get_quality_history("MTR-0002")
    ap08 = [(r.disposition, r.attempt_number) for r in qh.records
            if r.station_id == "AP08"] if qh else []
    obs = [t for t in bridge.outbound_trace
           if t["payload"].get("station_id") == "AP08"
           and t["payload"].get("wip_id") == "MTR-0002"]
    return {
        "target": target,
        "released": ok,
        "ap08_attempts": ap08,
        "mes_quality_count": len(obs),
        "mes_record_ids": [t["source_event_id"] for t in obs],
    }


def r4_failed_final() -> dict:
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.FAILED_FINAL)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    target = comp.target_sub_line_id
    drive_steps(comp, target, 30)
    bridge.poll(comp)
    ctx = comp.get_context(target)
    ws = ctx.runtime.get_wip(CHILD)
    status = ctx.runtime.get_current_quality_status(CHILD)
    qh = ctx.runtime.get_quality_history(CHILD)
    ap06 = [(r.disposition, r.attempt_number) for r in qh.records
            if r.station_id == "AP06"] if qh else []
    releases = [t for t in bridge.outbound_trace
                if t["payload"].get("event_type") == EVENT_AP11_RELEASE
                and t["payload"].get("wip_id") == CHILD]
    return {
        "target": target,
        "wip_released": bool(ws and ws.lifecycle == WipLifecycle.RELEASED),
        "quality_status": status.value,
        "ap06_attempts": ap06,
        "release_observation_count": len(releases),
    }


# ═══════════════════════════════════════════════════════════
# R5 — MANUAL sanity
# ═══════════════════════════════════════════════════════════

def r5_manual_sanity() -> dict:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    line = AssyLineRuntime(config=c)
    line.global_run_mode = CompletionMode.MANUAL
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    bridge = build_assy_observation_pipeline().bridge
    import types
    ident = types.SimpleNamespace(sub_line_id="ASSY-SL01", variant="hydraulic",
                                  production_line_id="ASSY")
    ctx = types.SimpleNamespace(runtime=line, identity=ident)
    comp = types.SimpleNamespace(contexts={"ASSY-SL01": ctx})

    def resolve_awaiting():
        for op in list(line.operation_registry.active_operations()):
            if op.completion_mode != CompletionMode.MANUAL:
                continue
            st, wip = op.station_id, op.wip_id
            if op.state == OperationState.AWAITING_DECISION:
                decision = op.proposed_quality_result or "PASS"
                line.submit_operation_command(
                    st, wip, StationCommand.CONFIRM,
                    payload={"decision": decision})
                return (st, decision)
            elif op.state == OperationState.AWAITING_COMPLETION:
                contract = line.station_contracts[st]
                cmd = contract.required_action or contract.normal_action or StationCommand.DONE
                payload = None
                if (contract.checklist_required_for_action is not None
                        and contract.checklist_required_for_action == cmd):
                    payload = {"checklist": [
                        {"item_id": i, "completed": True}
                        for i in contract.checklist_items]}
                line.submit_operation_command(st, wip, cmd, payload)
                return (st, "completed")
        return None

    line.execute_dwell()
    awaiting_after_dwell = any(
        op.state in (OperationState.AWAITING_DECISION,
                     OperationState.AWAITING_COMPLETION)
        for op in line.operation_registry.active_operations())
    auto_completed = any(
        op.state == OperationState.ELIGIBLE_TO_INDEX
        for op in line.operation_registry.active_operations())
    # MANUAL timing stays legacy fixed (op.timing is None).
    manual_timing_none = all(
        op.timing is None
        for op in line.operation_registry.active_operations())

    # Drive MANUAL to a quality decision and resolve it (public surfaces only).
    resolved = None
    for _ in range(120):
        resolved = resolve_awaiting()
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        qh = line.get_quality_history("MTR-0001")
        if qh and any(r.station_id == "AP06" for r in qh.records):
            break
    bridge.poll(comp)
    quality_obs = [t for t in bridge.outbound_trace
                   if t["payload"].get("disposition")]
    return {
        "awaiting_after_dwell": awaiting_after_dwell,
        "auto_completed": auto_completed,
        "manual_timing_legacy": manual_timing_none,
        "resolved_decision": resolved,
        "outbound_quality_count": len(quality_obs),
    }


# ═══════════════════════════════════════════════════════════
# T1..T3 — timing / bottleneck
# ═══════════════════════════════════════════════════════════

def drive_timing(cfg_path: str, steps: int = 14) -> list[dict]:
    cfg = load_assy_config_from_yaml(cfg_path)
    line = AssyLineRuntime(config=cfg)
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    metrics = []
    for _ in range(steps):
        line.execute_dwell()
        dp = line.dwell_performance
        metrics.append({
            "actual_dwell_s": round(dp.actual_dwell_s, 1),
            "overrun_s": round(dp.dwell_overrun_s, 1),
            "bottleneck": dp.bottleneck_station_id,
        })
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
    return metrics


def timing_summary(cfg_path: str, label: str) -> dict:
    m = drive_timing(cfg_path)
    worst = max(m, key=lambda d: d["overrun_s"])
    bottlenecks = sorted({d["bottleneck"] for d in m if d["bottleneck"]})
    return {
        "label": label,
        "max_actual_dwell_s": worst["actual_dwell_s"],
        "max_overrun_s": worst["overrun_s"],
        "worst_bottleneck": worst["bottleneck"],
        "bottlenecks_seen": bottlenecks,
    }


# ═══════════════════════════════════════════════════════════
# MES outbound + repeatability
# ═══════════════════════════════════════════════════════════

def mes_outbound_evidence() -> dict:
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    drive_until(comp, "ASSY-SL01", CHILD)
    bridge.poll(comp)
    first = list(bridge.outbound_trace)
    second = bridge.poll(comp)
    ctx = comp.get_context("ASSY-SL01")
    # JSONL path
    out = OUT / "tmp_mes_outbound.jsonl"
    gw = JsonlObsGateway(str(out))
    b2 = build_assy_observation_pipeline(gateways=[gw]).bridge
    drive_until(comp, "ASSY-SL01", CHILD)  # idempotent re-read of same facts
    b2.poll(comp)
    jsonl_count = len(out.read_text(encoding="utf-8").strip().splitlines())
    out.unlink()
    return {
        "total_observations": len(first),
        "second_poll_new": len(second),
        "message_types": sorted({t["message_type"] for t in first}),
        "jsonl_lines": jsonl_count,
        "run_id": first[0]["run_id"],
    }


def repeatability() -> list[dict]:
    runs = []
    for i in range(3):
        comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        bridge = build_assy_observation_pipeline().bridge
        ok = drive_until(comp, "ASSY-SL01", CHILD)
        bridge.poll(comp)
        ctx = comp.get_context("ASSY-SL01")
        ws = ctx.runtime.get_wip(CHILD)
        runs.append({
            "run": i + 1,
            "released": ok,
            "motor": CHILD,
            "release_time_s": round(ws.released_at_sim_s, 1) if ws else None,
            "observation_count": len(bridge.outbound_trace),
            "released_count": sum(1 for w in ctx.runtime.wip_ids
                                  if ctx.runtime.get_wip(w).lifecycle == WipLifecycle.RELEASED),
        })
    return runs


# ═══════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════

def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def main() -> None:
    r1 = r1_happy_path()
    r2 = r2_ap06_fail_retest()
    r3 = r3_ap08_ng_reinspect()
    r4 = r4_failed_final()
    r5 = r5_manual_sanity()

    rehearsal = f"""# DEMO-CANDIDATE-01 — Rehearsal matrix

## R1 — HAPPY_PATH (ASSY-SL01)

- motor: {r1['motor']}
- release time: {r1['release_time_s']} s
- AP04 parent IDs: {r1['ap04_parents']}
- MES observation count: {r1['observation_count']}
- second poll new deliveries: {r1['second_poll_new']}
- final released count: {r1['released_count']}

## R2 — AP06 FAIL → RETEST → PASS

- target sub-line: {r2['target']}
- released: {r2['released']}
- AP06 authoritative quality history (MTR-0002): {r2['ap06_attempts']}
- MES quality observations: {r2['mes_quality_count']} (record ids {r2['mes_record_ids']})
- second poll new deliveries: {r2['second_poll_new']}

## R3 — AP08 NG → REINSPECT → PASS

- target sub-line: {r3['target']}
- released: {r3['released']}
- AP08 authoritative quality history (MTR-0002): {r3['ap08_attempts']}
- MES quality observations: {r3['mes_quality_count']} (record ids {r3['mes_record_ids']})

## R4 — FAILED_FINAL

- target sub-line: {r4['target']}
- WIP released: {r4['wip_released']}
- quality status: {r4['quality_status']}
- AP06 attempts: {r4['ap06_attempts']}
- AP11 RELEASE observations for failed WIP: {r4['release_observation_count']}

## R5 — MANUAL sanity

- operations awaiting action after dwell: {r5['awaiting_after_dwell']}
- auto-completed without command: {r5['auto_completed']}
- MANUAL timing stays legacy fixed (op.timing is None): {r5['manual_timing_legacy']}
- resolved decision: {r5['resolved_decision']}
- outbound quality observations after completion: {r5['outbound_quality_count']}
"""
    (OUT / "rehearsal-matrix.md").write_text(rehearsal, encoding="utf-8")

    t1 = timing_summary(TIPA_YAML, "T1 baseline (nominal 120, AP05 90)")
    t2 = timing_summary(
        str(REPO / ".ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/config_ap05_135.yaml"),
        "T2 forced AP05 bottleneck (~135)")
    t3 = timing_summary(
        str(REPO / ".ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/config_ap05_065.yaml"),
        "T3 improvement (~65)")
    timing = f"""# DEMO-CANDIDATE-01 — Timing / bottleneck rehearsal

{md_table(["label", "max_actual_dwell_s", "max_overrun_s", "worst_bottleneck", "bottlenecks_seen"],
          [t1, t2, t3])}
"""
    (OUT / "timing.md").write_text(timing, encoding="utf-8")

    mes = mes_outbound_evidence()
    rep = repeatability()
    outbound = f"""# DEMO-CANDIDATE-01 — MES outbound validation

- total observations (HAPPY_PATH one motor): {mes['total_observations']}
- second poll new deliveries: {mes['second_poll_new']}
- message types: {mes['message_types']}
- JSONL lines written (InMemory-free gateway path): {mes['jsonl_lines']}
- run_id: {mes['run_id']}
"""
    (OUT / "mes-outbound.md").write_text(outbound, encoding="utf-8")

    rep_md = f"""# DEMO-CANDIDATE-01 — Repeatability (3x HAPPY_PATH)

{md_table(["run", "released", "motor", "release_time_s", "observation_count", "released_count"], rep)}
"""
    (OUT / "repeatability.md").write_text(rep_md, encoding="utf-8")

    print("R1:", r1)
    print("R2:", r2)
    print("R3:", r3)
    print("R4:", r4)
    print("R5:", r5)
    print("T1:", t1)
    print("T2:", t2)
    print("T3:", t3)
    print("MES:", mes)
    print("REPEAT:", rep)


if __name__ == "__main__":
    main()
