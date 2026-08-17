"""M6-INT-01 — ASSY reality observation bridge & MES outbound (P0) tests.

Covers the P0 outbound observation contract:
- operation completion (pure-execution stations)
- AP04 genealogy / identity transformation
- AP06 / AP08 quality result per attempt
- AP11 final-QC PASS and AP11 RELEASE as distinct observations
- stable source_event_id + idempotency across repeated polls
- MANUAL ≡ AUTO semantic equivalence
- gateway failure isolation (never mutates simulation truth)
- reset / new-run identity separation and 6 sub-line isolation
- default-deny field projection
- no timing re-sampling by bridge reads
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

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
    EVENT_AP04_JOIN,
    EVENT_AP11_FINAL_QC_PASS,
    EVENT_AP11_RELEASE,
    EVENT_OPERATION_COMPLETED,
    EVENT_QUALITY_RESULT,
    build_assy_observation_pipeline,
)
from virtual_factory.assembly.operation_execution import OperationState
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)
from virtual_factory.integration.gateway import DeliveryStatus
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway
from virtual_factory.integration.gateways.memory import InMemoryObsGateway
from virtual_factory.observation.service import RealityInput

REPO = Path(__file__).resolve().parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")
CHILD = "MTR-0001"
SPECIALIZED = ("AP04", "AP06", "AP08", "AP11")


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def make_config(ap06: str = "PASS", ap08: str = "PASS") -> AssyLineConfig:
    """Short-dwell ASSY config for fast deterministic journeys."""
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = ap06
    c.quality.ap08.scenario = ap08
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    """Seed one SSO2 + one RSO2 and introduce the first WIP."""
    line = AssyLineRuntime(config=cfg)
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()   # SSO2-0001
    line.produce_rso2_wip()   # RSO2-0001
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def make_bridge(gateways=None):
    """Build the observation pipeline; return (bridge, pipeline)."""
    pipe = build_assy_observation_pipeline(gateways=gateways)
    return pipe.bridge, pipe


def ctx_for(line: AssyLineRuntime, sub_line_id: str = "ASSY-SL01",
            variant: str = "hydraulic"):
    """Wrap a bare runtime in the minimal context shape the bridge reads."""
    identity = types.SimpleNamespace(
        sub_line_id=sub_line_id,
        variant=variant,
        production_line_id="ASSY",
    )
    ctx = types.SimpleNamespace(runtime=line, identity=identity)
    return types.SimpleNamespace(contexts={sub_line_id: ctx})


def resolve_awaiting(line: AssyLineRuntime,
                     quality_decision: str = "accept_proposal") -> None:
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


def drive(line: AssyLineRuntime, mode: CompletionMode = CompletionMode.AUTO,
          max_steps: int = 200) -> AssyLineRuntime:
    """Drive one line until the first child motor is RELEASED."""
    line.global_run_mode = mode
    for _ in range(max_steps):
        line.execute_dwell()
        if mode == CompletionMode.MANUAL:
            resolve_awaiting(line)
            line.conveyor.check_ready()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    return line


def drive_composition(comp: AssyDemoComposition, sl_id: str,
                      max_steps: int = 300) -> None:
    """Drive one composition context until MTR-0001 is RELEASED."""
    ctx = comp.get_context(sl_id)
    for _ in range(max_steps):
        ctx.step_context()
        ws = ctx.runtime.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            return
    raise AssertionError(f"{sl_id} did not release {CHILD} in {max_steps} steps")


# ═══════════════════════════════════════════════════════════
# 1. Operation completion emits once
# ═══════════════════════════════════════════════════════════

class TestOperationCompletion:
    def test_pure_operation_completion_emits_once(self):
        line = setup_line(make_config())
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)

        completed = [
            op for op in line.operation_registry.all_operations()
            if op.state == OperationState.ELIGIBLE_TO_INDEX
            and op.station_id not in SPECIALIZED
        ]
        msgs = [t for t in bridge.outbound_trace
                if t["message_type"] == "mes.execution_event"]
        assert len(msgs) == len(completed) > 0
        keys = [t["source_event_id"] for t in msgs]
        assert len(set(keys)) == len(keys)   # exactly once


# ═══════════════════════════════════════════════════════════
# 2. Repeated poll does not duplicate
# ═══════════════════════════════════════════════════════════

class TestIdempotency:
    def test_repeated_poll_no_duplicates(self):
        line = setup_line(make_config())
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)
        first = list(bridge.outbound_trace)
        results = bridge.poll(comp)          # second poll
        assert results == []                 # nothing new delivered
        assert list(bridge.outbound_trace) == first
        assert len(bridge.projected_messages) == len(first)


# ═══════════════════════════════════════════════════════════
# 3. AP04 genealogy — authoritative parent/child relation
# ═══════════════════════════════════════════════════════════

class TestAp04Genealogy:
    def test_genealogy_emits_authoritative_parent_child(self):
        line = setup_line(make_config())
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)

        gen = [t for t in bridge.outbound_trace
               if t["message_type"] == "mes.genealogy_relationship"]
        assert len(gen) == 1
        p = gen[0]["payload"]
        assert p["event_type"] == EVENT_AP04_JOIN
        assert p["child_wip_id"] == CHILD
        assert sorted(p["parent_wip_ids"]) == sorted(["SSO2-0001", "RSO2-0001"])
        assert p["relationship_type"] == "assembly_join"
        assert p["join_station"] == "AP04"


# ═══════════════════════════════════════════════════════════
# 4/5/6. AP06 / AP08 attempt semantics
# ═══════════════════════════════════════════════════════════

class TestQualityAttempts:
    def test_ap06_pass_emits_one_attempt(self):
        line = setup_line(make_config(ap06="PASS"))
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)
        ap06 = [t for t in bridge.outbound_trace
                if t["payload"].get("station_id") == "AP06"]
        assert len(ap06) == 1
        assert ap06[0]["message_type"] == "mes.quality_result"
        assert ap06[0]["payload"]["disposition"] == "PASS"
        assert ap06[0]["payload"]["attempt_number"] == 1

    def test_ap06_fail_then_pass_emits_two_attempts(self):
        line = setup_line(make_config(ap06="FAIL_FIRST_THEN_PASS"))
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)
        ap06 = sorted(
            [t for t in bridge.outbound_trace
             if t["payload"].get("station_id") == "AP06"],
            key=lambda t: t["payload"]["attempt_number"])
        assert len(ap06) == 2
        assert [t["payload"]["disposition"] for t in ap06] == ["FAIL", "PASS"]
        assert [t["payload"]["attempt_number"] for t in ap06] == [1, 2]
        assert len({t["source_event_id"] for t in ap06}) == 2  # distinct records

    def test_ap08_ng_then_pass_emits_two_attempts(self):
        line = setup_line(make_config(ap08="FAIL_FIRST_THEN_PASS"))
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)
        ap08 = sorted(
            [t for t in bridge.outbound_trace
             if t["payload"].get("station_id") == "AP08"],
            key=lambda t: t["payload"]["attempt_number"])
        assert len(ap08) == 2
        assert [t["payload"]["disposition"] for t in ap08] == ["NG", "PASS"]
        assert [t["payload"]["attempt_number"] for t in ap08] == [1, 2]


# ═══════════════════════════════════════════════════════════
# 7. AP11 QC PASS and RELEASE are distinct
# ═══════════════════════════════════════════════════════════

class TestAp11Separation:
    def test_ap11_qc_pass_and_release_distinct(self):
        line = setup_line(make_config())
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)

        qc = [t for t in bridge.outbound_trace
              if t["payload"].get("event_type") == EVENT_AP11_FINAL_QC_PASS]
        rel = [t for t in bridge.outbound_trace
               if t["payload"].get("event_type") == EVENT_AP11_RELEASE]
        assert len(qc) == 1 and len(rel) == 1
        assert qc[0]["message_type"] == "mes.quality_result"
        assert rel[0]["message_type"] == "mes.release"
        assert qc[0]["source_event_id"] != rel[0]["source_event_id"]
        assert qc[0]["payload"]["disposition"] == "PASS"
        assert rel[0]["payload"]["wip_id"] == CHILD


# ═══════════════════════════════════════════════════════════
# 8. source_event_id stable across repeated reads
# ═══════════════════════════════════════════════════════════

class TestStableIdentity:
    def test_source_event_id_stable_across_repeated_reads(self):
        line = setup_line(make_config())
        bridge, _ = make_bridge()
        comp = ctx_for(line)
        drive(line)
        bridge.poll(comp)
        first = [(t["run_id"], t["source_event_id"])
                 for t in bridge.outbound_trace]
        bridge.poll(comp)
        second = [(t["run_id"], t["source_event_id"])
                  for t in bridge.outbound_trace]
        assert first == second


# ═══════════════════════════════════════════════════════════
# 9. MANUAL ≡ AUTO same semantic outbound fact
# ═══════════════════════════════════════════════════════════

class TestManualAutoEquivalence:
    def test_manual_auto_same_semantic_outbound_fact(self):
        auto_line = setup_line(make_config())
        man_line = setup_line(make_config())
        auto_bridge, _ = make_bridge()
        man_bridge, _ = make_bridge()

        drive(auto_line, CompletionMode.AUTO)
        drive(man_line, CompletionMode.MANUAL)

        auto_bridge.poll(ctx_for(auto_line, "ASSY-SL01"))
        man_bridge.poll(ctx_for(man_line, "ASSY-SL02"))

        def semantic(trace):
            return sorted(
                (t["message_type"], t["payload"].get("station_id"),
                 t["payload"].get("disposition"),
                 t["payload"].get("attempt_number"))
                for t in trace if t["payload"].get("disposition"))

        assert semantic(auto_bridge.outbound_trace) == \
            semantic(man_bridge.outbound_trace)

        # completion mode is allowed provenance, not different MES truth
        auto_modes = {t["payload"]["completion_mode"]
                      for t in auto_bridge.outbound_trace
                      if t["payload"].get("completion_mode")}
        man_modes = {t["payload"]["completion_mode"]
                     for t in man_bridge.outbound_trace
                     if t["payload"].get("completion_mode")}
        assert "AUTO" in auto_modes
        assert "MANUAL" in man_modes


# ═══════════════════════════════════════════════════════════
# 10. Gateway failure never mutates simulation truth
# ═══════════════════════════════════════════════════════════

class TestFailureIsolation:
    def test_gateway_failure_does_not_mutate_truth(self):
        gw = InMemoryObsGateway()
        line = setup_line(make_config())
        bridge, _ = make_bridge(gateways=[gw])
        comp = ctx_for(line)
        drive(line)

        sim_before = line.simulation_time_s
        released_before = sum(
            1 for w in line.wip_ids
            if line.get_wip(w).lifecycle == WipLifecycle.RELEASED)

        gw.set_fail_next(999)
        results = bridge.poll(comp)
        assert any(r.status == DeliveryStatus.FAILED for r in results)
        assert all(r.status != DeliveryStatus.DELIVERED for r in results)

        # simulation truth unchanged by the (failed) export
        assert line.simulation_time_s == sim_before
        released_after = sum(
            1 for w in line.wip_ids
            if line.get_wip(w).lifecycle == WipLifecycle.RELEASED)
        assert released_after == released_before

        # MES unavailability must NOT block the line: runtime still advances
        sim = line.simulation_time_s
        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        assert line.simulation_time_s > sim
        # and downstream facts are still emitted once the gateway recovers
        gw.set_fail_next(0)
        recovered = bridge.poll(comp)
        assert any(r.status == DeliveryStatus.DELIVERED for r in recovered)


# ═══════════════════════════════════════════════════════════
# 11. reset / new run does not incorrectly collide identities
# ═══════════════════════════════════════════════════════════

class TestResetRunSeparation:
    def test_reset_new_run_no_identity_collision(self):
        comp = AssyDemoComposition(
            config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        bridge, _ = make_bridge()

        drive_composition(comp, "ASSY-SL01")
        bridge.poll(comp)
        run1 = {(t["run_id"], t["source_event_id"])
                for t in bridge.outbound_trace}
        assert any(r.startswith("ASSY-SL01:R1") for r, _ in run1)
        assert any(r == "ASSY-SL01:R1" and s == "QR-0001" for r, s in run1)

        # reset rebuilds runtimes → poll immediately after reset bumps generation
        comp.initialize()
        bridge.poll(comp)                     # detects sim-time regression → R2
        drive_composition(comp, "ASSY-SL01")
        bridge.poll(comp)
        run2 = {(t["run_id"], t["source_event_id"])
                for t in bridge.outbound_trace}
        assert any(r.startswith("ASSY-SL01:R2") for r, _ in run2)
        # same record id in a NEW run is a distinct fact (no collision)
        assert ("ASSY-SL01:R2", "QR-0001") in run2
        # both runs are represented in the final trace with unique keys
        all_keys = [(t["run_id"], t["source_event_id"])
                    for t in bridge.outbound_trace]
        assert len(all_keys) == len(set(all_keys))
        assert any(r.startswith("ASSY-SL01:R1") for r, _ in all_keys)
        assert any(r.startswith("ASSY-SL01:R2") for r, _ in all_keys)


# ═══════════════════════════════════════════════════════════
# 12. Six sub-lines do not cross-contaminate identity/context
# ═══════════════════════════════════════════════════════════

class TestSubLineIsolation:
    def test_six_sub_lines_do_not_cross_contaminate(self):
        comp = AssyDemoComposition(
            config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        bridge, _ = make_bridge()

        for _ in range(120):
            comp.step_all()
            all_have = all(
                any(op.state == OperationState.ELIGIBLE_TO_INDEX
                    for op in comp.get_context(sl).runtime
                        .operation_registry.all_operations())
                for sl in comp.contexts)
            if all_have:
                break
        bridge.poll(comp)

        run_ids = {t["run_id"] for t in bridge.outbound_trace}
        assert len(run_ids) == 6                     # one run per sub-line
        keys = [(t["run_id"], t["source_event_id"]) for t in bridge.outbound_trace]
        assert len(keys) == len(set(keys))           # no identity collision
        # every sub-line's facts stay under its own run
        for t in bridge.outbound_trace:
            sl = t["run_id"].split(":")[0]
            assert sl in {f"ASSY-SL{i:02d}" for i in range(1, 7)}


# ═══════════════════════════════════════════════════════════
# 13. FieldPolicy strips unapproved fields (default-deny)
# ═══════════════════════════════════════════════════════════

class TestFieldPolicy:
    def test_field_policy_strips_unapproved_fields(self):
        pipe = build_assy_observation_pipeline()
        reality = RealityInput(
            run_id="ASSY-SL01:R1",
            model_id="tipa_assy_demo",
            source_event_id="EXEC-00001",
            source_type="assy_runtime",
            source_domain="assy",
            source_path="AP01",
            simulation_time_s=5.0,
            category="industrial_event",
            source_data={
                "event_type": EVENT_OPERATION_COMPLETED,
                "target_id": "SSO2-0001",
                "execution_id": "EXEC-00001",
                "station_id": "AP01",
                "wip_id": "SSO2-0001",
                "operation_result": "DONE",
                "completion_mode": "AUTO",
                "attempt_number": 1,
                "source": "simulated",
                "internal_secret": "SHOULD_NOT_LEAK",
                "internal_truth": {"x": 1},
            },
            subject_type="wip",
            subject_id="SSO2-0001",
            context={"semantic_type": "execution_event", "station_id": "AP01"},
        )
        envelopes = pipe.service.collect(reality)
        assert len(envelopes) == 1
        assert "internal_secret" not in envelopes[0].payload
        assert "internal_truth" not in envelopes[0].payload
        msgs = pipe.router.route(envelopes[0])
        assert len(msgs) == 1
        assert "internal_secret" not in msgs[0].payload
        assert "internal_truth" not in msgs[0].payload
        # approved fields ARE present
        assert msgs[0].payload["station_id"] == "AP01"
        assert msgs[0].payload["operation_result"] == "DONE"


# ═══════════════════════════════════════════════════════════
# 14. Bridge polling never re-samples AUTO timing
# ═══════════════════════════════════════════════════════════

class TestNoTimingResample:
    def test_bridge_poll_does_not_resample_auto_timing(self):
        cfg = load_assy_config_from_yaml(TIPA_YAML)   # has auto_timing_profiles
        line = AssyLineRuntime(config=cfg)
        line.global_run_mode = CompletionMode.AUTO
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        comp = ctx_for(line)
        bridge, _ = make_bridge()

        # read-only poll on a fresh line must not create operations
        bridge.poll(comp)
        assert len(line.operation_registry.all_operations()) == 0

        line.execute_dwell()
        ops_before = {op.execution_id: op for op in
                      line.operation_registry.all_operations()}
        samples_before = {
            eid: (op.timing.effective_duration_s if op.timing else None)
            for eid, op in ops_before.items()
        }
        assert len(samples_before) > 0

        # repeated polls must not create ops nor re-sample frozen timing
        bridge.poll(comp)
        bridge.poll(comp)
        assert len(line.operation_registry.all_operations()) == len(ops_before)
        for op in line.operation_registry.all_operations():
            if op.execution_id in samples_before:
                current = (op.timing.effective_duration_s if op.timing else None)
                assert current == samples_before[op.execution_id]


# ═══════════════════════════════════════════════════════════
# Gateway: JSONL file gateway writes deterministic trace
# ═══════════════════════════════════════════════════════════

class TestJsonlGateway:
    def test_jsonl_gateway_writes_ordered_trace(self):
        out = Path(__file__).resolve().parent / "m6_int_01_tmp_obs.jsonl"
        try:
            gw = JsonlObsGateway(str(out))
            line = setup_line(make_config())
            bridge, _ = make_bridge(gateways=[gw])
            comp = ctx_for(line)
            drive(line)
            bridge.poll(comp)

            lines = out.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) >= 13
            first = json.loads(lines[0])
            assert first["message_key"]
            assert first["message_type"] == "mes.execution_event"
            assert "payload" in first
            last = json.loads(lines[-1])
            assert last["message_type"] == "mes.release"
        finally:
            if out.exists():
                out.unlink()
