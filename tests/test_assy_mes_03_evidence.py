"""VF-DM-DEMO-ASSY-MES-03 — Detailed Operation Evidence Contract tests.

Covers: AP03 checklist evidence (mes.checklist_result), AP06 numerical
measurement evidence (mes.measurement_result), AP08/AP11 structured
observations on mes.quality_result, contract v1.1 provenance, idempotency,
reset generation, and no regression of the MES-02 scenario.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_composition import DemoScenario
from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.assy_mes_bridge import (
    CONTRACT_VERSION,
    build_assy_mes_pipeline,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.station_contracts import CompletionMode

REPO = Path(__file__).resolve().parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")
CHILD = "MTR-0001"
SUB_LINE_IDS = {"ASSY-SL01", "ASSY-SL02", "ASSY-SL03", "ASSY-SL04", "ASSY-SL05", "ASSY-SL06"}


def make_config(ap06="PASS", ap08="PASS"):
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
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def ctx_for(line: AssyLineRuntime, sub_line_id="ASSY-SL01", variant="hydraulic"):
    identity = types.SimpleNamespace(
        sub_line_id=sub_line_id, variant=variant, production_line_id="ASSY")
    ctx = types.SimpleNamespace(runtime=line, identity=identity)
    return types.SimpleNamespace(contexts={sub_line_id: ctx}, demo_step_number=0)


def make_mes_bridge():
    return build_assy_mes_pipeline().bridge


def drive(line: AssyLineRuntime, max_steps: int = 300) -> AssyLineRuntime:
    for _ in range(max_steps):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    return line


def _payloads(bridge):
    return [dict(m.payload) for m in bridge.projected_messages]


# ═══════════════════════════════════════════════════════════
# AP03 checklist contract
# ═══════════════════════════════════════════════════════════

class TestAp03Checklist:
    def test_confirmed_emits_exactly_one(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        cl = [p for p in _payloads(bridge)
              if p.get("event_type") == "CHECKLIST_CONFIRMED"]
        assert len(cl) == 1
        p = cl[0]
        assert p["station_id"] == "AP03"
        assert p["status"] == "confirmed"

    def test_incomplete_not_emitted(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        # one dwell: AP03 not yet confirmed
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        bridge.poll(ctx_for(line))
        cl = [p for p in _payloads(bridge)
              if p.get("event_type") == "CHECKLIST_CONFIRMED"]
        assert cl == []
        # complete and poll: exactly one confirmed appears
        drive(line)
        bridge.poll(ctx_for(line))
        cl = [p for p in _payloads(bridge)
              if p.get("event_type") == "CHECKLIST_CONFIRMED"]
        assert len(cl) == 1

    def test_no_fabricated_quality_disposition(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        cl = [p for p in _payloads(bridge)
              if p.get("event_type") == "CHECKLIST_CONFIRMED"]
        for p in cl:
            assert "disposition" not in p
            assert p.get("status") == "confirmed"

    def test_item_ids_and_counts_match_contract(self):
        from virtual_factory.assembly.station_contracts import DEMO_CHECKLIST_ITEM_IDS
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        cl = [p for p in _payloads(bridge)
              if p.get("event_type") == "CHECKLIST_CONFIRMED"][0]
        assert cl["required_count"] == len(DEMO_CHECKLIST_ITEM_IDS) == 3
        assert cl["completed_count"] == 3
        item_ids = [i["item_id"] for i in cl["items"]]
        assert item_ids == list(DEMO_CHECKLIST_ITEM_IDS)
        assert all(i["required"] and i["completed"] for i in cl["items"])
        assert cl.get("source") == "DEMO_SYNTHETIC"


# ═══════════════════════════════════════════════════════════
# AP06 measurement contract
# ═══════════════════════════════════════════════════════════

class TestAp06Measurement:
    def test_three_measurements_per_attempt(self):
        line = setup_line(make_config(ap06="PASS"))
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        qr = [p for p in _payloads(bridge)
              if p.get("station_id") == "AP06" and p.get("event_type") == "QUALITY_RESULT"]
        assert qr, "no AP06 quality result"
        for rec in qr:
            rid = rec["record_id"]
            ms = [p for p in _payloads(bridge)
                  if p.get("event_type") == "MEASUREMENT_RESULT"
                  and p.get("record_id") == rid]
            codes = sorted(m["measurement_code"] for m in ms)
            assert codes == ["R_U-V", "R_V-W", "R_W-U"]

    def test_limits_unit_in_spec(self):
        line = setup_line(make_config(ap06="PASS"))
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        ms = [p for p in _payloads(bridge)
              if p.get("event_type") == "MEASUREMENT_RESULT"]
        assert ms
        for m in ms:
            assert m["unit"] == "\u03a9"
            assert m["lower_limit"] == 0.3
            assert m["upper_limit"] == 0.6
            assert m["in_spec"] == (0.3 <= m["value"] <= 0.6)
            assert m["evidence_source"] == "DEMO_SYNTHETIC"

    def test_fail_measurement_preserved_after_retest(self):
        line = setup_line(make_config(ap06="FAIL_FIRST_THEN_PASS"))
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        ru = [p for p in _payloads(bridge)
              if p.get("event_type") == "MEASUREMENT_RESULT"
              and p.get("measurement_code") == "R_U-V"]
        by_attempt = {m["attempt_number"]: m for m in ru}
        assert 1 in by_attempt and 2 in by_attempt
        assert by_attempt[1]["value"] == 0.29
        assert by_attempt[1]["in_spec"] is False
        assert by_attempt[2]["value"] > 0.3
        assert by_attempt[2]["in_spec"] is True
        # distinct record ids / keys — FAIL attempt never rewritten
        assert by_attempt[1]["record_id"] != by_attempt[2]["record_id"]

    def test_measurement_linked_to_quality_attempt(self):
        line = setup_line(make_config(ap06="FAIL_FIRST_THEN_PASS"))
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        payloads = _payloads(bridge)
        ms = [p for p in payloads if p.get("event_type") == "MEASUREMENT_RESULT"]
        qr = [p for p in payloads
              if p.get("station_id") == "AP06"
              and p.get("event_type") == "QUALITY_RESULT"]
        qr_by_id = {r["record_id"]: r for r in qr}
        for m in ms:
            rec = qr_by_id[m["record_id"]]
            assert rec["attempt_number"] == m["attempt_number"]
            assert rec["wip_id"] == m["wip_id"]
            assert rec["station_id"] == m["station_id"]


# ═══════════════════════════════════════════════════════════
# AP08 / AP11 observations
# ═══════════════════════════════════════════════════════════

class TestObservations:
    def test_ap08_observations_and_proposal_separate(self):
        line = setup_line(make_config(ap06="PASS", ap08="FAIL_FIRST_THEN_PASS"))
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        qr = [p for p in _payloads(bridge)
              if p.get("station_id") == "AP08"
              and p.get("event_type") == "QUALITY_RESULT"]
        assert qr
        ng = [r for r in qr if r["disposition"] == "NG"]
        assert ng, "expected an AP08 NG attempt"
        r = ng[0]
        assert r["check_type"] == "VISUAL_INSPECTION"
        assert r["observations"], "AP08 observations missing"
        assert any(o["result"] == "anomaly" for o in r["observations"])
        # proposal and final decision are two separate fields
        assert "proposed_quality_result" in r
        assert "disposition" in r
        assert r["proposed_quality_result"] == "NG"
        assert r["disposition"] == "NG"

    def test_ap11_observations_not_release_or_line_out(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        payloads = _payloads(bridge)
        ap11_qc = [p for p in payloads
                   if p.get("station_id") == "AP11"
                   and p.get("event_type") in ("AP11_FINAL_QC_PASS", "AP11_FINAL_QC_FAIL")]
        assert ap11_qc
        r = ap11_qc[0]
        assert r["check_type"] == "FINAL_QC"
        assert "observations" in r
        # Final QC is a distinct message from RELEASE and LINE_OUT
        assert r["event_type"].startswith("AP11_FINAL_QC")
        release_keys = {p["idempotency_key"] for p in payloads
                        if p.get("event_type") == "AP11_RELEASE"}
        line_out_keys = {p["idempotency_key"] for p in payloads
                         if p.get("event_type") == "LINE_OUT"}
        assert r["idempotency_key"] not in release_keys
        assert r["idempotency_key"] not in line_out_keys


# ═══════════════════════════════════════════════════════════
# Contract provenance, idempotency, reset, version
# ═══════════════════════════════════════════════════════════

class TestContractAndIdempotency:
    def test_contract_version_v1_1_on_messages(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        for m in bridge.projected_messages:
            p = dict(m.payload)
            assert p["contract_version"] == CONTRACT_VERSION == "tipa-assy-demo-v1.1"
            assert m.key == p.get("idempotency_key")

    def test_repeated_poll_no_duplicate_keys(self):
        line = setup_line(make_config())
        bridge = make_mes_bridge()
        drive(line)
        bridge.poll(ctx_for(line))
        keys = {m.key for m in bridge.projected_messages}
        bridge.poll(ctx_for(line))
        keys2 = {m.key for m in bridge.projected_messages}
        assert keys == keys2

    def test_version_endpoint_v1_1(self):
        from fastapi.testclient import TestClient
        from virtual_factory.ui.api import create_app
        import os
        os.environ.setdefault("VF_ENABLE_S04B_OVERVIEW", "1")
        client = TestClient(create_app(
            config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0))
        resp = client.get("/assy-demo/version").json()
        assert resp["contract_version"] == "tipa-assy-demo-v1.1"


# ═══════════════════════════════════════════════════════════
# No regression of the MES-02 scenario (bounded demo)
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def demo():
    ctrl = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.FAILED_FINAL)
    ctrl.initialize()
    ctrl.select_sub_line("ASSY-SL03")
    ctrl.attach_mes_bridge(build_assy_mes_pipeline().bridge)
    for _ in range(6):
        ctrl.step()
    ctrl.trigger_jam()
    ctrl.step()
    ctrl.recover()
    ctrl.run_to_terminal(max_steps=24)
    return {
        "ctrl": ctrl,
        "payloads": [dict(m.payload) for m in ctrl.mes_bridge.projected_messages],
        "keys": {m.key for m in ctrl.mes_bridge.projected_messages},
    }


class TestScenarioNoRegression:
    def test_sl03_sequence_and_downtime(self, demo):
        rs = [p["line_state"] for p in demo["payloads"]
              if p.get("subline_id") == "ASSY-SL03"
              and p.get("event_type") == "LINE_STATE_CHANGED"]
        assert rs == ["running", "fault", "stopped", "running"]
        ends = [p for p in demo["payloads"]
                if p.get("event_type") == "DOWNTIME_END"]
        assert len(ends) == 1 and ends[0]["downtime_s"] == 120.0

    def test_oee_and_line_out(self, demo):
        oee = [p for p in demo["payloads"]
               if p.get("event_type") == "OEE_SUMMARY"]
        assert len(oee) == 6
        assert all(p["oee"] < 1.0 for p in oee)
        outs = [p for p in demo["payloads"] if p.get("event_type") == "LINE_OUT"]
        dispositions = {p["disposition"] for p in outs}
        assert {"good", "reject"} <= dispositions

    def test_duplicate_keys_zero_and_new_evidence(self, demo):
        assert len(demo["keys"]) == len(demo["payloads"])
        types = {p.get("idempotency_key"): p for p in demo["payloads"]}
        assert len(types) == len(demo["payloads"])
        # new evidence present
        assert any(p.get("event_type") == "CHECKLIST_CONFIRMED" for p in demo["payloads"])
        assert any(p.get("event_type") == "MEASUREMENT_RESULT" for p in demo["payloads"])
