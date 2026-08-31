"""VF-DM-DEMO-ASSY-MES-02 — six-sub-line MES contract bridge tests.

Covers the gate acceptance criteria:
- six sub-lines with distinct run identity (ASSY-SLxx:R<n>)
- operational state RUNNING → FAULT → STOPPED → RUNNING (separate from
  conveyor state)
- deterministic AP05_JAM exception (EXCEPTION_RAISED / EXCEPTION_RESOLVED)
- exactly one downtime lifecycle (DOWNTIME_START → DOWNTIME_END, 120 s)
- LINE_OUT GOOD and REJECT derived from authoritative state
- reconciled per-sub-line OEE (below 100 %, at least one reject)
- MES contract/provenance fields on every message
- duplicate poll/replay does not create new message keys
- reset creates a new run generation without reusing idempotency keys
- quality HOLD does not become a line fault/downtime
- existing quality / genealogy / release facts do not regress
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_composition import DemoScenario
from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.assy_mes_bridge import build_assy_mes_pipeline

REPO = Path(__file__).resolve().parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")

SUB_LINE_IDS = {
    "ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
    "ASSY-SL04", "ASSY-SL05", "ASSY-SL06",
}
RUN_ID_RE = re.compile(r"^ASSY-SL\d\d:R\d+$")


def _build_controller(scenario=DemoScenario.FAILED_FINAL):
    ctrl = DemoController(config_path=TIPA_YAML, scenario=scenario)
    ctrl.initialize()
    ctrl.select_sub_line("ASSY-SL03")
    pipeline = build_assy_mes_pipeline()
    ctrl.attach_mes_bridge(pipeline.bridge)
    return ctrl


@pytest.fixture(scope="module")
def demo():
    """Run the full deterministic demo once (reset → healthy → jam → downtime
    step → recover → run-to-terminal) and expose the controller + delivered
    messages.  The faulted target is frozen while AP05_JAM is active."""
    ctrl = _build_controller()
    # healthy production (target advancing)
    for _ in range(6):
        ctrl.step()
    # deterministic AP05_JAM → target frozen
    ctrl.trigger_jam()
    # one step while the fault is active → 120 s downtime (target frozen)
    ctrl.step()
    # recover (emitted after the downtime interval)
    ctrl.recover()
    # bounded run to terminal + emit OEE
    ctrl.run_to_terminal(max_steps=24)
    return {
        "ctrl": ctrl,
        "messages": ctrl.mes_messages,
        "keys": {m["message_key"] for m in ctrl.mes_messages},
    }


def _of_type(messages, message_type):
    return [m for m in messages if m["message_type"] == message_type]


class TestSixSublineIdentity:
    def test_six_sub_lines_present(self, demo):
        sublines = {m["payload"].get("subline_id") for m in demo["messages"]}
        assert SUB_LINE_IDS <= sublines

    def test_distinct_run_identity(self, demo):
        run_ids = {m["payload"].get("run_id") for m in demo["messages"]}
        for rid in run_ids:
            assert RUN_ID_RE.match(rid), f"bad run_id {rid!r}"
        # each sub-line has exactly one run_id in this run
        by_sl = {}
        for m in demo["messages"]:
            sl = m["payload"].get("subline_id")
            by_sl.setdefault(sl, set()).add(m["payload"].get("run_id"))
        assert all(len(v) == 1 for v in by_sl.values())


class TestOperationalState:
    def test_target_subline_sequence(self, demo):
        states = [
            (m["payload"].get("subline_id"), m["payload"].get("line_state"))
            for m in _of_type(demo["messages"], "mes.run_status")
            if m["payload"].get("subline_id") == "ASSY-SL03"
        ]
        assert [s for _, s in states] == ["running", "fault", "stopped", "running"]

    def test_conveyor_state_separate_field(self, demo):
        """run_status carries conveyor_state as a distinct raw field with the
        conveyor vocabulary; conveyor stopped never FORCES production
        line_state=stopped (only AP05_JAM creates production STOPPED)."""
        CONVEYOR_VOCAB = {"indexing", "stopped", "operating", "ready_to_index"}
        rs = _of_type(demo["messages"], "mes.run_status")
        assert rs, "no run_status"
        for m in rs:
            assert m["payload"]["line_state"] in ("running", "fault", "stopped")
            assert m["payload"]["conveyor_state"] in CONVEYOR_VOCAB
        # conveyor STOPPED alone never forces production STOPPED: some
        # run_status have conveyor stopped while the line is RUNNING.
        assert any(
            m["payload"]["conveyor_state"] == "stopped"
            and m["payload"]["line_state"] == "running"
            for m in rs
        )
        # the only production STOPPED is the single AP05_JAM STOPPED on target.
        stopped = [m for m in rs if m["payload"]["line_state"] == "stopped"]
        assert len(stopped) == 1
        assert stopped[0]["payload"]["subline_id"] == "ASSY-SL03"

    def test_only_operational_state_projected(self, demo):
        """mes.run_status line_state values are operational (running/fault/stopped),
        never raw conveyor indexing/operating/ready values."""
        for m in _of_type(demo["messages"], "mes.run_status"):
            assert m["payload"]["line_state"] in ("running", "fault", "stopped")

    def test_only_ap05_jam_creates_fault_or_stopped(self, demo):
        """In this demo, only the AP05_JAM lifecycle produces FAULT/STOPPED."""
        rs = _of_type(demo["messages"], "mes.run_status")
        fault_or_stopped = [
            m for m in rs if m["payload"]["line_state"] in ("fault", "stopped")
        ]
        assert fault_or_stopped, "expected fault/stopped from AP05_JAM"
        # FAULT/STOPPED appear only on the jammed target sub-line, and only
        # around the exception window.
        assert {m["payload"]["subline_id"] for m in fault_or_stopped} == {"ASSY-SL03"}
        # the single fault/stopped pair belongs to the AP05_JAM lifecycle
        starts = [m for m in demo["messages"]
                  if m["payload"].get("event_type") == "DOWNTIME_START"]
        assert len(starts) == 1


class TestExceptionLifecycle:
    def test_ap05_jam_raised_and_resolved(self, demo):
        issues = _of_type(demo["messages"], "mes.issue")
        types = sorted(m["payload"]["event_type"] for m in issues)
        assert types == ["EXCEPTION_RAISED", "EXCEPTION_RESOLVED"]
        for m in issues:
            assert m["payload"]["reason_code"] == "AP05_JAM"
            assert m["payload"]["station_id"] == "AP05"

    def test_raised_resolved_correlation(self, demo):
        issues = _of_type(demo["messages"], "mes.issue")
        raised = next(m for m in issues if m["payload"]["event_type"] == "EXCEPTION_RAISED")
        resolved = next(m for m in issues if m["payload"]["event_type"] == "EXCEPTION_RESOLVED")
        for field in ("run_id", "subline_id", "station_id", "reason_code",
                      "contract_version"):
            assert raised["payload"][field] == resolved["payload"][field], field

    def test_quality_hold_is_not_line_fault(self):
        """A quality FAIL/retest on a sub-line must NOT become run_status
        fault/stopped or downtime."""
        ctrl = _build_controller(scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
        for _ in range(60):
            ctrl.step()
        msgs = ctrl.mes_messages
        rs = _of_type(msgs, "mes.run_status")
        assert all(m["payload"]["line_state"] == "running" for m in rs)
        # no downtime for a pure quality-hold run
        downtime = [m for m in msgs
                    if m["payload"].get("event_type") in ("DOWNTIME_START", "DOWNTIME_END")]
        assert downtime == []


class TestDowntime:
    def test_one_downtime_lifecycle(self, demo):
        starts = [m for m in demo["messages"]
                  if m["payload"].get("event_type") == "DOWNTIME_START"]
        ends = [m for m in demo["messages"]
                if m["payload"].get("event_type") == "DOWNTIME_END"]
        assert len(starts) == 1
        assert len(ends) == 1
        assert ends[0]["payload"]["downtime_s"] == 120.0
        assert starts[0]["payload"]["downtime_s"] == 120.0


class TestFaultFreezeConsistency:
    """VF-DM-DEMO-ASSY-MES-02-C02: while AP05_JAM is active, the target
    sub-line is frozen — no sim-time/dwell/WIP/operation/quality/genealogy/
    release/LINE_OUT advance — while sibling sub-lines keep advancing."""

    def _target_snapshot(self, ctrl):
        from virtual_factory.assembly.demo_snapshot import build_snapshot
        target = ctrl.composition.target_sub_line_id
        ctx = ctrl.composition.get_context(target)
        return ctx.runtime, build_snapshot(ctx.runtime, ctx.effective_scenario.value)

    def _runtime_fingerprint(self, runtime):
        return {
            "sim_time": runtime.simulation_time_s,
            "dwell": runtime.conveyor.dwell_number,
            "wip_count": len(runtime.wip_ids),
            "op_count": len(runtime.operation_registry.all_operations()),
            "genealogy_count": len(runtime.genealogy.all_records()),
        }

    def test_target_frozen_during_fault_sibling_advances(self):
        ctrl = _build_controller()
        for _ in range(6):
            ctrl.step()
        target = ctrl.composition.target_sub_line_id
        target_rt, _ = self._target_snapshot(ctrl)
        before_target = self._runtime_fingerprint(target_rt)
        sibling = "ASSY-SL01"
        before_sibling = ctrl.composition.get_context(sibling).runtime.simulation_time_s

        ctrl.trigger_jam()
        ctrl.step()   # one step while the fault is active

        target_rt2, _ = self._target_snapshot(ctrl)
        after_target = self._runtime_fingerprint(target_rt2)
        after_sibling = ctrl.composition.get_context(sibling).runtime.simulation_time_s

        # target frozen: counts and sim-time unchanged while the fault is active
        assert after_target == before_target, (before_target, after_target)
        # at least one sibling advanced
        assert after_sibling > before_sibling

    def test_no_target_production_between_downtime_start_and_end(self):
        ctrl = _build_controller()
        for _ in range(6):
            ctrl.step()
        ctrl.trigger_jam()
        ctrl.step()
        ctrl.recover()
        ctrl.step()
        msgs = ctrl.mes_messages
        start = next(m for m in msgs
                     if m["payload"].get("event_type") == "DOWNTIME_START")
        end = next(m for m in msgs
                   if m["payload"].get("event_type") == "DOWNTIME_END")
        # no target production fact (operation/genealogy/quality/release/LINE_OUT)
        # from the target sub-line between DOWNTIME_START and DOWNTIME_END
        between = [
            m for m in msgs
            if start["payload"]["simulation_time_s"] < m["payload"].get("simulation_time_s", 0)
            < end["payload"]["simulation_time_s"]
        ]
        for m in between:
            if m["payload"].get("subline_id") == "ASSY-SL03":
                assert m["payload"].get("event_type") not in (
                    "OPERATION_COMPLETED", "AP04_JOIN", "QUALITY_RESULT",
                    "AP11_FINAL_QC_PASS", "AP11_FINAL_QC_FAIL", "AP11_RELEASE",
                    "LINE_OUT",
                )

    def test_recover_single_end_then_target_resumes(self):
        ctrl = _build_controller()
        for _ in range(6):
            ctrl.step()
        ctrl.trigger_jam()
        ctrl.step()
        ctrl.recover()
        ctrl.step()
        ends = [m for m in ctrl.mes_messages
                if m["payload"].get("event_type") == "DOWNTIME_END"]
        assert len(ends) == 1
        target = ctrl.composition.target_sub_line_id
        t_before = ctrl.composition.get_context(target).runtime.simulation_time_s
        ctrl.step()   # target may now advance again
        t_after = ctrl.composition.get_context(target).runtime.simulation_time_s
        assert t_after > t_before

    def test_recover_deferred_until_downtime_elapsed(self):
        ctrl = _build_controller()
        for _ in range(6):
            ctrl.step()
        ctrl.trigger_jam()
        # recover requested BEFORE any downtime step → deferred, no END yet
        ctrl.recover()
        ends = [m for m in ctrl.mes_messages
                if m["payload"].get("event_type") == "DOWNTIME_END"]
        assert ends == []
        # after one excluded step (120 s downtime), the pending recover resolves
        ctrl.step()
        ctrl.step()
        ends = [m for m in ctrl.mes_messages
                if m["payload"].get("event_type") == "DOWNTIME_END"]
        assert len(ends) == 1


class TestLineOut:
    def test_line_out_good_and_reject(self, demo):
        outs = [m for m in demo["messages"]
                if m["payload"].get("event_type") == "LINE_OUT"]
        assert outs, "no LINE_OUT facts"
        dispositions = {m["payload"]["disposition"] for m in outs}
        assert dispositions == {"good", "reject"}
        for m in outs:
            assert m["payload"]["station_id"] == "LINE_OUT"

    def test_line_out_distinct_from_release_and_qc(self, demo):
        msgs = demo["messages"]
        line_out = _of_type(msgs, "mes.execution_event")
        line_out = [m for m in line_out if m["payload"].get("event_type") == "LINE_OUT"]
        releases = _of_type(msgs, "mes.release")
        assert line_out and releases
        assert {m["message_key"] for m in line_out}.isdisjoint(
            {m["message_key"] for m in releases})


class TestOee:
    def test_oee_reconciliation(self, demo):
        oee = _of_type(demo["messages"], "mes.oee_summary")
        assert len(oee) == 6, f"expected 6 OEE summaries, got {len(oee)}"
        for m in oee:
            p = m["payload"]
            assert abs(p["planned_s"] - (p["run_s"] + p["downtime_s"])) < 1e-6
            assert p["actual_count"] == p["good_count"] + p["reject_count"]
            assert abs(p["availability"] - p["run_s"] / p["planned_s"]) < 1e-6
            assert abs(p["performance"] -
                       p["ideal_cycle_s"] * p["actual_count"] / p["run_s"]) < 1e-6
            assert abs(p["quality"] - p["good_count"] / p["actual_count"]) < 1e-6
            assert abs(p["oee"] -
                       p["availability"] * p["performance"] * p["quality"]) < 1e-6

    def test_oee_below_100_and_has_reject(self, demo):
        oee = _of_type(demo["messages"], "mes.oee_summary")
        assert all(m["payload"]["oee"] < 1.0 for m in oee)
        assert any(m["payload"]["reject_count"] >= 1 for m in oee)


class TestContractProvenance:
    def test_contract_fields_on_every_message(self, demo):
        for m in demo["messages"]:
            p = m["payload"]
            assert m["message_key"] == p.get("idempotency_key")
            assert p.get("contract_version") == "tipa-assy-demo-v1.1"
            assert RUN_ID_RE.match(p.get("run_id", ""))
            assert p.get("subline_id") in SUB_LINE_IDS
            assert p.get("occurred_at") is not None
            assert "+00:00" in p.get("occurred_at", "")
            assert isinstance(p.get("simulation_time_s"), (int, float))

    def test_all_required_message_types(self, demo):
        types = {m["message_type"] for m in demo["messages"]}
        assert {
            "mes.execution_event", "mes.quality_result",
            "mes.genealogy_relationship", "mes.release",
            "mes.run_status", "mes.issue", "mes.oee_summary",
        } <= types


class TestIdempotencyAndReset:
    def test_duplicate_poll_no_new_keys(self):
        ctrl = _build_controller()
        for _ in range(10):
            ctrl.step()
        keys1 = {m["message_key"] for m in ctrl.mes_messages}
        # poll again via an extra step (no new authoritative facts)
        ctrl.mes_bridge.poll(ctrl.composition)
        keys2 = {m["message_key"] for m in ctrl.mes_messages}
        assert keys1 == keys2

    def test_reset_new_generation_no_key_reuse(self):
        ctrl = _build_controller()
        for _ in range(10):
            ctrl.step()
        before_keys = {m["message_key"] for m in ctrl.mes_messages}
        before_run = {m["payload"]["run_id"] for m in ctrl.mes_messages}
        ctrl.reset()
        for _ in range(10):
            ctrl.step()
        after = ctrl.mes_messages
        after_run = {m["payload"]["run_id"] for m in after}
        # generation bumped: R1 → R2 (no run_id reuse across generations)
        new_runs = {r for r in after_run if r.endswith(":R2")}
        assert new_runs, "no R2 run after reset"
        assert before_run.isdisjoint(new_runs)
        # new-run idempotency keys never reuse the prior run's keys
        after_new_keys = {
            m["message_key"] for m in after
            if m["payload"]["run_id"].endswith(":R2")
        }
        assert after_new_keys
        assert after_new_keys.isdisjoint(before_keys)


class TestNoRegression:
    def test_existing_facts_still_emitted(self, demo):
        msgs = demo["messages"]
        ev_types = {m["payload"].get("event_type") for m in msgs}
        assert "OPERATION_COMPLETED" in ev_types
        assert "AP04_JOIN" in ev_types
        assert "QUALITY_RESULT" in ev_types
        assert "AP11_RELEASE" in ev_types
        # quality finality markers preserved on quality results
        qc = [m for m in msgs
              if m["message_type"] == "mes.quality_result"]
        assert qc
        assert all("is_terminal" in m["payload"] for m in qc)
