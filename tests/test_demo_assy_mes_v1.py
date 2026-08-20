"""VF-DM-DEMO-ASSY-MES-01 — TIPA ASSY Customer Demo Scenario v1 tests.

Covers the task acceptance criteria:
- single-sub-line topology (PRE-ASSY + AP01..AP11 + LINE_OUT)
- four deterministic WIPs (happy / retest / jam / reject)
- AP05 jam fault → STOPPED → RUNNING recovery
- LINE_OUT GOOD vs REJECT
- OEE reconciliation (A/P/Q from simulated data)
- reset determinism + no runtime-state carryover
- idempotent message keys (no duplicates)
- MESProjection emits mes.oee_summary + LINE_OUT execution_event
- JSONL serialization compatibility
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_assy_mes import (
    STATIONS,
    STATION_IDS,
    LineState,
    build_demo_pipeline,
    build_scenario_facts,
)
from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway
from virtual_factory.integration.gateways.memory import InMemoryObsGateway


def make_runner():
    gw = InMemoryObsGateway()
    return DemoRunner(pipeline=build_demo_pipeline(gateways=[gw]))


def serialized(messages):
    return [
        {
            "message_key": m.key,
            "message_type": m.message_type,
            "schema_name": m.schema_name,
            "schema_version": m.schema_version,
            "headers": dict(m.headers),
            "payload": dict(m.payload),
        }
        for m in messages
    ]


class TestTopology:
    def test_single_sub_line_stations(self):
        """ASSY-SL01 has PRE-ASSY + AP01..AP11 + LINE_OUT."""
        assert STATION_IDS == (
            "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05", "AP06",
            "AP07", "AP08", "AP09", "AP10", "AP11", "LINE_OUT",
        )
        assert len(STATIONS) == 13

    def test_station_kinds(self):
        """AP04=join, AP06=test, AP08=vision, AP11=final_qc, LINE_OUT=line_out."""
        kinds = {s.station_id: s.kind.value for s in STATIONS}
        assert kinds["AP04"] == "join"
        assert kinds["AP06"] == "test"
        assert kinds["AP08"] == "vision"
        assert kinds["AP11"] == "final_qc"
        assert kinds["LINE_OUT"] == "line_out"


class TestFourWips:
    def test_four_line_out_facts(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        line_outs = [m for m in msgs if m["payload"].get("event_type") == "LINE_OUT"]
        assert len(line_outs) == 4
        wips = sorted(m["payload"]["wip_id"] for m in line_outs)
        assert wips == ["MTR-DEMO-001", "MTR-DEMO-002", "MTR-DEMO-003", "MTR-DEMO-004"]

    def test_good_and_reject_line_out(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        good = [m for m in msgs if m["payload"].get("event_type") == "LINE_OUT"
                and m["payload"]["disposition"] == "good"]
        reject = [m for m in msgs if m["payload"].get("event_type") == "LINE_OUT"
                   and m["payload"]["disposition"] == "reject"]
        assert len(good) == 3
        assert len(reject) == 1
        assert reject[0]["payload"]["wip_id"] == "MTR-DEMO-004"

    def test_ap04_genealogy_parents(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        joins = [m for m in msgs if m["payload"].get("event_type") == "AP04_JOIN"]
        assert len(joins) == 4
        by_child = {m["payload"]["child_wip_id"]: m["payload"]["parent_wip_ids"] for m in joins}
        assert by_child["MTR-DEMO-001"] == ["SSO2-001", "RSO2-001"]
        assert by_child["MTR-DEMO-004"] == ["SSO2-004", "RSO2-004"]

    def test_ap06_fail_retest_pass(self):
        """MTR-DEMO-002: AP06 FAIL attempt 1 → PASS attempt 2 (distinct keys)."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        ap06 = [m for m in msgs if m["payload"].get("station_id") == "AP06"
                and m["payload"].get("wip_id") == "MTR-DEMO-002"]
        fail = [m for m in ap06 if m["payload"].get("disposition") == "FAIL"]
        pass2 = [m for m in ap06 if m["payload"].get("disposition") == "PASS"
                 and m["payload"].get("attempt_number") == 2]
        assert len(fail) == 1
        assert len(pass2) == 1
        assert fail[0]["payload"]["attempt_number"] == 1
        assert fail[0]["message_key"] != pass2[0]["message_key"]

    def test_ap11_reject_terminal(self):
        """MTR-DEMO-004: AP11 final QC FAIL → reject LINE_OUT."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        ap11_fail = [m for m in msgs
                     if m["payload"].get("event_type") == "AP11_FINAL_QC_FAIL"
                     and m["payload"].get("wip_id") == "MTR-DEMO-004"]
        assert len(ap11_fail) == 1
        assert ap11_fail[0]["payload"]["disposition"] == "FAIL"


class TestFaultRecovery:
    def test_jam_fault_stopped_running(self):
        """AP05 jam → line FAULT → STOPPED → recover → RUNNING."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        states = [m["payload"].get("line_state")
                  for m in msgs if m["payload"].get("event_type") == "LINE_STATE_CHANGED"]
        assert states == ["running", "fault", "stopped", "running"]
        # exception raised/resolved with AP05_JAM
        issues = [m for m in msgs if m["message_type"] == "mes.issue"]
        assert [m["payload"]["reason_code"] for m in issues] == ["AP05_JAM", "AP05_JAM"]
        assert [m["payload"]["event_type"] for m in issues] == ["EXCEPTION_RAISED", "EXCEPTION_RESOLVED"]

    def test_downtime_interval_120s(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        dt = [m for m in msgs if m["payload"].get("event_type") in ("DOWNTIME_START", "DOWNTIME_END")]
        assert len(dt) == 2
        end = [m for m in dt if m["payload"].get("event_type") == "DOWNTIME_END"][0]
        assert end["payload"]["downtime_s"] == 120.0


class TestOee:
    def test_oee_reconciliation(self):
        """planned 1200, downtime 120, run 1080, ideal 240, actual 4, good 3, reject 1 → 60%."""
        runner = make_runner()
        runner.run_to_completion()
        oee = runner.oee
        assert oee is not None
        assert oee.planned_s == 1200.0
        assert oee.downtime_s == 120.0
        assert oee.run_s == 1080.0
        assert oee.ideal_cycle_s == 240.0
        assert oee.actual_count == 4
        assert oee.good_count == 3
        assert oee.reject_count == 1
        assert oee.run_s + oee.downtime_s == oee.planned_s
        assert oee.good_count + oee.reject_count == oee.actual_count
        assert round(oee.availability, 6) == 0.9
        assert round(oee.performance, 6) == round(240 * 4 / 1080, 6)
        assert round(oee.quality, 6) == 0.75
        assert round(oee.oee, 6) == 0.6

    def test_oee_summary_message_emitted(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        oee_msgs = [m for m in msgs if m["message_type"] == "mes.oee_summary"]
        assert len(oee_msgs) == 1
        p = oee_msgs[0]["payload"]
        assert p["actual_count"] == 4 and p["good_count"] == 3 and p["reject_count"] == 1
        assert round(p["oee"], 6) == 0.6


class TestDeterminism:
    def test_repeated_runs_identical_order_and_content(self):
        """Same scenario → identical message order and payload (modulo run_id)."""
        r1 = make_runner()
        msgs1 = serialized(r1.run_to_completion())
        r1.reset()
        msgs2 = serialized(r1.run_to_completion())
        assert len(msgs1) == len(msgs2)
        for a, b in zip(msgs1, msgs2):
            assert a["message_type"] == b["message_type"]
            assert a["payload"]["event_type"] == b["payload"]["event_type"]
            assert a["payload"]["simulation_time_s"] == b["payload"]["simulation_time_s"]
            # run_id differs (generation bump), key differs only by run_id
            assert a["payload"]["run_id"] == "ASSY-SL01:R1"
            assert b["payload"]["run_id"] == "ASSY-SL01:R2"
            assert a["message_key"].replace("R1", "R2") == b["message_key"]

    def test_reset_leaves_no_runtime_state(self):
        """Reset clears messages and line state (only generation increments)."""
        runner = make_runner()
        runner.run_to_completion()
        assert runner.delivered_messages()
        runner.reset()
        assert runner.delivered_messages() == []
        assert runner.line_state == LineState.STOPPED
        assert runner.simulation_time_s == 0.0
        assert runner.oee is None


class TestIdempotency:
    def test_message_keys_distinct_and_stable(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        keys = [m["message_key"] for m in msgs]
        assert len(keys) == len(set(keys))  # no duplicates within one run
        # all keys carry run_id | source_event_id | point_id | schema_version
        for k in keys:
            assert k.startswith("ASSY-SL01:R1|")
            assert k.endswith("|1.0")


class TestProjection:
    def test_required_message_types(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        types = {m["message_type"] for m in msgs}
        assert {
            "mes.run_status", "mes.issue", "mes.execution_event",
            "mes.quality_result", "mes.genealogy_relationship", "mes.oee_summary",
        } <= types

    def test_required_payload_fields_present(self):
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        for m in msgs:
            p = m["payload"]
            for f in ("idempotency_key", "run_id", "simulation_time_s",
                      "contract_version", "subline_id"):
                assert f in p, f"missing {f}"
            assert p["contract_version"] == "tipa-assy-demo-v1"
            assert p["subline_id"] == "ASSY-SL01"


class TestJsonlSerialization:
    def test_jsonl_envelope_keys(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "demo.jsonl")
            gw = JsonlObsGateway(filepath=path)
            runner = DemoRunner(pipeline=build_demo_pipeline(gateways=[gw]))
            runner.run_to_completion()
            lines = [json.loads(l) for l in open(path, encoding="utf-8")]
            assert len(lines) == 63
            first = lines[0]
            assert set(first.keys()) == {
                "message_key", "projection_id", "message_type", "schema_name",
                "schema_version", "headers", "payload",
            }


class TestControlSurface:
    def test_snapshot_wip_tokens_and_line_state(self):
        runner = make_runner()
        runner.run_to_completion()
        snap = runner.snapshot()
        assert snap["line_state"] == "running"
        assert snap["contract_version"] == "tipa-assy-demo-v1"
        assert snap["subline_id"] == "ASSY-SL01"
        assert "MTR-DEMO-001" in snap["wip_tokens"]

    def test_step_advances_cursor(self):
        runner = make_runner()
        runner.reset()
        runner.start()
        before = runner.snapshot()["cursor"]
        runner.step()
        after = runner.snapshot()["cursor"]
        assert after == before + 1


class TestControlSemanticsC02:
    def test_start_does_not_process_timeline(self):
        """Start must NOT run the whole timeline synchronously."""
        runner = make_runner()
        runner.reset()
        runner.start()
        snap = runner.snapshot()
        assert snap["cursor"] == 0
        assert snap["simulation_time_s"] == 0.0

    def test_pause_prevents_next_step(self):
        """Pause prevents the next step."""
        runner = make_runner()
        runner.reset()
        runner.start()
        runner.step()          # emits fact 1
        runner.pause()
        before = runner.snapshot()["cursor"]
        runner.step()          # should be a no-op
        assert runner.snapshot()["cursor"] == before

    def test_step_emits_exactly_one_fact(self):
        """Step emits exactly one fact."""
        runner = make_runner()
        runner.reset()
        runner.start()
        runner.step()
        assert runner.snapshot()["cursor"] == 1
        runner.step()
        assert runner.snapshot()["cursor"] == 2

    def test_trigger_jam_brings_to_fault(self):
        """Trigger Jam deterministically brings the line to FAULT (then STOPPED)."""
        runner = make_runner()
        runner.reset()
        runner.start()
        runner.trigger_jam()
        assert runner.line_state == LineState.STOPPED  # advanced through FAULT → STOPPED
        # the recent event log contains the exception + fault
        events = [e["event_type"] for e in runner.snapshot()["recent_events"]]
        assert "EXCEPTION_RAISED" in events
        assert "LINE_STATE_CHANGED" in events

    def test_recover_only_after_fault_and_continues(self):
        """Recover only works after fault/stop and resumes to RUNNING."""
        runner = make_runner()
        runner.reset()
        runner.start()
        # recover before any fault is a no-op
        runner.recover()
        assert runner.line_state == LineState.STOPPED
        # trigger jam → STOPPED, then recover → RUNNING
        runner.trigger_jam()
        assert runner.line_state == LineState.STOPPED
        runner.recover()
        assert runner.line_state == LineState.RUNNING

    def test_reset_clears_state_and_bumps_generation(self):
        runner = make_runner()
        runner.run_to_completion()
        g1 = runner.generation
        runner.reset()
        assert runner.generation == g1 + 1
        assert runner.delivered_messages() == []
        assert runner.line_state == LineState.STOPPED
        assert runner.simulation_time_s == 0.0
        assert runner.oee is None


class TestQualityFinalityC02:
    def test_ap11_reject_has_terminal_markers(self):
        """MTR-DEMO-004 AP11 final failure: is_terminal=true, terminal_state=failed_final."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        ap11_fail = [m for m in msgs
                     if m["payload"].get("event_type") == "AP11_FINAL_QC_FAIL"]
        assert len(ap11_fail) == 1
        p = ap11_fail[0]["payload"]
        assert p["is_terminal"] is True
        assert p["terminal_state"] == "failed_final"

    def test_non_terminal_ap06_fail_not_terminal(self):
        """MTR-DEMO-002 AP06 FAIL attempt 1: is_terminal=false, terminal_state=''."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        ap06_fail = [m for m in msgs
                     if m["payload"].get("station_id") == "AP06"
                     and m["payload"].get("disposition") == "FAIL"]
        assert ap06_fail, "no AP06 FAIL"
        for m in ap06_fail:
            assert m["payload"]["is_terminal"] is False
            assert m["payload"]["terminal_state"] == ""

    def test_line_out_reject_independent_of_final_qc(self):
        """LINE_OUT reject is a distinct fact from the terminal final-QC."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        line_out_reject = [m for m in msgs
                           if m["payload"].get("event_type") == "LINE_OUT"
                           and m["payload"].get("disposition") == "reject"]
        ap11_fail = [m for m in msgs
                     if m["payload"].get("event_type") == "AP11_FINAL_QC_FAIL"]
        assert len(line_out_reject) == 1 and len(ap11_fail) == 1
        assert line_out_reject[0]["message_key"] != ap11_fail[0]["message_key"]


class TestStateOrderingC02:
    def test_fault_and_stopped_distinct_timestamps(self):
        """FAULT and STOPPED must have different simulated timestamps."""
        runner = make_runner()
        msgs = serialized(runner.run_to_completion())
        states = [(m["payload"].get("line_state"), m["payload"]["simulation_time_s"])
                  for m in msgs if m["payload"].get("event_type") == "LINE_STATE_CHANGED"]
        assert [s for s, _ in states] == ["running", "fault", "stopped", "running"]
        fault_t = dict([(s, t) for s, t in states])["fault"]
        stopped_t = dict([(s, t) for s, t in states])["stopped"]
        assert fault_t != stopped_t
        assert fault_t < stopped_t

    def test_downtime_still_120s(self):
        runner = make_runner()
        runner.run_to_completion()
        assert runner.oee.downtime_s == 120.0

    def test_occurred_at_deterministic_iso8601(self):
        """occurred_at is deterministic ISO-8601 (fixed epoch + simulation_time_s)."""
        from virtual_factory.assembly.demo_assy_mes.model import occurred_at_for
        assert occurred_at_for(0.0) == "2026-01-01T00:00:00+00:00"
        assert occurred_at_for(120.0) == "2026-01-01T00:02:00+00:00"
        r1 = make_runner()
        r1.run_to_completion()
        msgs1 = serialized(r1.delivered_messages())
        r1.reset()
        msgs2 = serialized(r1.run_to_completion())
        for a, b in zip(msgs1, msgs2):
            # occurred_at deterministic regardless of wall-clock ingest time
            assert a["payload"]["occurred_at"] == b["payload"]["occurred_at"]
            assert a["payload"]["occurred_at"] is not None


class TestCustomerPage:
    def test_customer_page_route_renders(self):
        """GET /demo-assy-mes returns the customer-facing HTML page."""
        from fastapi.testclient import TestClient
        from virtual_factory.ui.api import create_app
        client = TestClient(create_app(config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0))
        resp = client.get("/demo-assy-mes")
        assert resp.status_code == 200
        assert "TIPA ASSY" in resp.text
        assert "PRE-ASSY" in resp.text
