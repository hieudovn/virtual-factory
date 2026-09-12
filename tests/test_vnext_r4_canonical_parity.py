"""VF-vNEXT-R4 — ASSY full parity closure on the canonical runtime (Issue #83).

Focused R4 tests:

1. same-session jam/recover;
2. one-fault/five-continue;
3. issue/downtime output from canonical fault truth (no projection-owned fault);
4. recover/resume (and fail-closed premature recovery);
5. canonical bounded run-to-terminal;
6. run-to-terminal parity with manual stepping;
7. OEE/final summary read-only/idempotent with canonical identity;
8. scenario selection creates a fresh run (never in-place mutation);
9. scenario effect on the intended line/quality behaviour;
10. shell/rich/output scenario identity consistency;
11. no second runtime/session/federation/controller;
12. strengthened same-runtime object identity assertion (no test bypass) and the
    R2V console-404 client fix;
13-14. R1/R2/R2V/R3/R3-C01 regressions + full baseline/full suite (suite-level).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from virtual_factory.federation import SUB_LINE_IDS

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.ui.assy_experience import (  # noqa: E402
    DEFERRED_FEATURES,
    CanonicalAssyExperience,
)
from virtual_factory.ui.assy_output import CanonicalAssyOutput  # noqa: E402
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")
RICH_JS = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static" / "assy_demo.js"
RUN_CONTROL_JS = (
    REPO_ROOT / "src" / "virtual_factory" / "ui" / "static" / "run_control_context.js"
)
R3_TEST = REPO_ROOT / "tests" / "test_vnext_r3_canonical_observation_mes.py"


def _client() -> TestClient:
    return TestClient(create_app())


def _experience() -> CanonicalAssyExperience:
    return CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))


def _output() -> CanonicalAssyOutput:
    return CanonicalAssyOutput(_experience())


def _frame_a(client: TestClient) -> dict[str, dict]:
    overview = client.get("/assy-demo/overview").json()
    return {row["sub_line_id"]: row for row in overview["sub_lines"]}


def _state(out: CanonicalAssyOutput, sub_line_id: str) -> dict:
    detail = out.experience.detail(sub_line_id)
    return {
        "simulation_time_s": detail["simulation_time_s"],
        "positions": detail["positions"],
        "genealogy": detail["genealogy"],
        "production": detail["production"],
        "quality_records": detail["quality_records"],
    }


# ═══════════════════════════════════════════════════════════════
# A. Same-session authority (tests 1, 11)
# ═══════════════════════════════════════════════════════════════

class TestSameSessionAuthority:
    def test_jam_recover_terminal_oee_share_one_canonical_session(
        self, monkeypatch
    ):
        import virtual_factory.assembly.demo_controller as demo_controller
        import virtual_factory.federation.assy_host as host_module
        import virtual_factory.runcontrol.session as session_module

        federations: list[str] = []
        sessions: list[str] = []
        legacy: list[str] = []
        original_fed = host_module.TipaAssyFederation.__init__
        original_sess = session_module.RuntimeSession.__init__

        def fed_init(self, config_path):  # noqa: ANN001
            federations.append(config_path)
            original_fed(self, config_path)

        def sess_init(self, *args, **kwargs):  # noqa: ANN001
            sessions.append("RuntimeSession")
            original_sess(self, *args, **kwargs)

        def legacy_init(self, *args, **kwargs):  # noqa: ANN001
            legacy.append("DemoController")
            raise AssertionError("legacy DemoController must not be instantiated")

        monkeypatch.setattr(host_module.TipaAssyFederation, "__init__", fed_init)
        monkeypatch.setattr(session_module.RuntimeSession, "__init__", sess_init)
        monkeypatch.setattr(demo_controller.DemoController, "__init__", legacy_init)

        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(3):
            c.post("/assy-demo/step")
        run_id = c.get("/assy-demo/identity").json()["canonical"]["run_id"]
        assert c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"}).status_code == 200
        for _ in range(2):
            c.post("/assy-demo/step")
        assert c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"}).status_code == 200
        terminal = c.post("/assy-demo/run-to-terminal", json={"max_windows": 40})
        assert terminal.status_code == 200
        assert terminal.json()["canonical"]["run_id"] == run_id
        oee = c.get("/assy-demo/oee")
        assert oee.status_code == 200
        assert oee.json()["canonical"]["run_id"] == run_id
        observations = c.get("/assy-demo/observations")
        assert observations.status_code == 200
        assert observations.json()["canonical"]["run_id"] == run_id
        assert len(federations) == 1, "a second canonical federation was constructed"
        assert len(sessions) == 1, "a second canonical RuntimeSession was constructed"
        assert legacy == []

    def test_six_runtime_objects_are_the_projected_ones(self):
        exp = _experience()
        exp.reset()
        exp.step()
        out = CanonicalAssyOutput(exp)
        out.poll()
        federation = out._federation
        assert set(federation.sub_lines) == set(SUB_LINE_IDS)
        for sub_line_id in SUB_LINE_IDS:
            entry = federation.get(sub_line_id)
            detail = exp.detail(sub_line_id)
            # strengthened (no `or True` bypass): the SAME runtime object is used
            # by the 2D/rich projection and by the canonical output projection.
            assert id(entry.runtime) == detail["canonical_sub_line"]["runtime_object_id"]
            assert entry.runtime is exp.federation().get(sub_line_id).runtime


# ═══════════════════════════════════════════════════════════════
# B. Canonical jam / recover (tests 1, 2, 3, 4)
# ═══════════════════════════════════════════════════════════════

class TestCanonicalJamRecover:
    def test_jam_freezes_one_line_and_five_continue(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(3):
            c.post("/assy-demo/step")
        before = _frame_a(c)
        assert c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"}).status_code == 200
        for _ in range(3):
            c.post("/assy-demo/step")
        after = _frame_a(c)
        assert after["ASSY-SL03"]["simulation_time_s"] == before["ASSY-SL03"][
            "simulation_time_s"
        ]
        assert after["ASSY-SL03"]["motors_created"] == before["ASSY-SL03"][
            "motors_created"
        ]
        for sub_line_id in SUB_LINE_IDS:
            if sub_line_id == "ASSY-SL03":
                continue
            assert after[sub_line_id]["simulation_time_s"] > before[sub_line_id][
                "simulation_time_s"
            ]
        # Frame B shows the same fault/freeze truth
        detail = c.get("/assy-demo/sub-line/ASSY-SL03").json()
        assert detail["simulation_time_s"] == after["ASSY-SL03"]["simulation_time_s"]
        assert c.get("/assy-demo/sub-line/ASSY-SL01").json()[
            "simulation_time_s"
        ] == after["ASSY-SL01"]["simulation_time_s"]

    def test_fault_state_is_owned_by_the_canonical_bridge_not_the_projection(self):
        exp = _experience()
        exp.reset()
        for _ in range(3):
            exp.step()
        out = CanonicalAssyOutput(exp)
        out.poll()
        exp.jam("ASSY-SL03")
        out.poll()
        bridge = exp.bridge()
        # canonical owner
        assert bridge.jammed_sub_line_ids == ("ASSY-SL03",)
        fault = bridge.fault_for("ASSY-SL03")
        assert fault["state"] == "FAULT"
        assert fault["reason_code"] == "AP05_JAM"
        assert fault["raised_at_s"] == 360.0
        # the projection owns NO simulation fault state (legacy internal fields
        # stay empty on the canonical path)
        assert out._mes._fault == {}
        assert out._mes._jam_pending == set()
        assert out._mes._canonical_faults is not None
        assert out._mes._canonical_faults["ASSY-SL03"]["state"] == "FAULT"

    def test_issue_and_downtime_output_comes_from_canonical_fault_truth(self):
        exp = _experience()
        exp.reset()
        for _ in range(3):
            exp.step()
        out = CanonicalAssyOutput(exp)
        out.poll()
        exp.jam("ASSY-SL03")
        out.poll()
        messages = out.mes_messages()
        issues = [
            m["payload"]
            for m in messages["mes_messages"]
            if m["message_type"] == "mes.issue"
        ]
        run_id = messages["canonical"]["run_id"]
        assert issues, "no canonical issue fact was emitted"
        raised = [i for i in issues if i.get("event_type") == "EXCEPTION_RAISED"]
        assert raised and raised[0]["run_id"] == run_id
        assert raised[0]["station_id"] == "AP05"
        assert raised[0]["simulation_time_s"] == 360.0  # canonical raised clock
        execution = [
            m["payload"]
            for m in messages["mes_messages"]
            if m["message_type"] == "mes.execution_event"
        ]
        downtime = [e for e in execution if e.get("event_type") == "DOWNTIME_START"]
        assert downtime and downtime[0]["downtime_s"] == 120.0
        assert downtime[0]["run_id"] == run_id

    def test_recover_resumes_the_same_line_and_is_fail_closed_early(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        assert c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"}).status_code == 200
        # no frozen canonical window yet → recovery fails closed
        early = c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"})
        assert early.status_code in (404, 409)
        for _ in range(2):
            c.post("/assy-demo/step")
        recover = c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"})
        assert recover.status_code == 200
        assert recover.json()["fault"]["state"] == "RUNNING"
        assert recover.json()["fault"]["resolved_at_s"] == recover.json()["fault"][
            "raised_at_s"
        ] + 120.0
        assert recover.json()["jammed_sub_line_ids"] == []
        c.post("/assy-demo/step")
        rows = _frame_a(c)
        assert rows["ASSY-SL03"]["simulation_time_s"] == rows["ASSY-SL01"][
            "simulation_time_s"
        ]

    def test_recover_without_a_fault_fails_closed(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        resp = c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL02"})
        assert resp.status_code in (404, 409)

    def test_jam_on_an_unknown_sub_line_fails_closed(self):
        c = _client()
        c.post("/assy-demo/reset")
        assert c.post("/assy-demo/jam", json={"sub_line_id": "NOPE"}).status_code == 404

    def test_reset_clears_the_canonical_fault(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"})
        assert c.post("/assy-demo/reset").status_code == 200
        rows = _frame_a(c)
        assert {row["simulation_time_s"] for row in rows.values()} == {0.0}


# ═══════════════════════════════════════════════════════════════
# C. Canonical run-to-terminal (tests 5, 6)
# ═══════════════════════════════════════════════════════════════

class TestRunToTerminal:
    def test_bounded_canonical_run_to_terminal(self):
        c = _client()
        c.post("/assy-demo/reset")
        resp = c.post("/assy-demo/run-to-terminal", json={"max_windows": 40})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("terminal", "bounded")
        assert 0 < body["windows"] <= 40
        assert body["terminal_reached"] is True
        assert body["max_windows"] == 40
        rows = _frame_a(c)
        for row in rows.values():
            assert row["simulation_time_s"] > 0

    def test_run_to_terminal_is_bounded_and_fails_closed(self):
        c = _client()
        c.post("/assy-demo/reset")
        assert (
            c.post("/assy-demo/run-to-terminal", json={"max_windows": 0}).status_code
            in (404, 409)
        )
        assert (
            c.post("/assy-demo/run-to-terminal", json={"max_windows": 500}).status_code
            in (404, 409)
        )

    def test_run_to_terminal_parity_with_manual_stepping(self):
        automated = _output()
        automated.experience.reset()
        result = automated.experience.run_to_terminal(40)
        windows = int(result["windows"])
        assert windows > 0

        manual = _output()
        manual.experience.reset()
        for _ in range(windows):
            manual.experience.step()

        for sub_line_id in SUB_LINE_IDS:
            assert _state(automated, sub_line_id) == _state(manual, sub_line_id), (
                f"{sub_line_id} state differs between terminal run and manual stepping"
            )
        assert automated.experience.terminal_reached() is True
        assert manual.experience.terminal_reached() is True
        assert automated.experience.detail()["simulation_time_s"] == manual.experience.detail(
        )["simulation_time_s"]

    def test_run_to_terminal_never_advances_inside_the_output_projection(self):
        out = _output()
        out.experience.reset()
        out.experience.run_to_terminal(40)
        before = _state(out, "ASSY-SL01")
        generation = out.experience.session.reset_generation
        for _ in range(2):
            out.oee_summary()
            out.mes_messages()
        assert _state(out, "ASSY-SL01") == before
        assert out.experience.session.reset_generation == generation


# ═══════════════════════════════════════════════════════════════
# D. OEE / final summary (test 7)
# ═══════════════════════════════════════════════════════════════

class TestOeeSummary:
    def test_oee_is_read_only_idempotent_and_canonical(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/run-to-terminal", json={"max_windows": 40})
        identity = c.get("/assy-demo/identity").json()["canonical"]
        before = c.post("/assy-demo/snapshot").json()
        first = c.get("/assy-demo/oee")
        assert first.status_code == 200
        body = first.json()
        assert body["legacy_runtime_authority"] is False
        assert body["authority"] == "canonical_tipa_runtime_session"
        assert body["canonical"]["run_id"] == identity["run_id"]
        assert body["count"] == 6, "expected one OEE summary per canonical sub-line"
        for summary in body["oee_summaries"]:
            assert summary["payload"]["run_id"] == identity["run_id"]
            assert summary["payload"]["event_type"] == "OEE_SUMMARY"
            assert 0.0 <= summary["payload"]["oee"] <= 1.0
            assert summary["message_key"].startswith(identity["run_id"])
        keys_first = [s["message_key"] for s in body["oee_summaries"]]
        second = c.get("/assy-demo/oee").json()
        assert [s["message_key"] for s in second["oee_summaries"]] == keys_first
        assert second["count"] == 6
        after = c.post("/assy-demo/snapshot").json()
        assert after["simulation_time_s"] == before["simulation_time_s"]
        assert after["production"] == before["production"]

    def test_oee_downtime_comes_from_the_canonical_fault_lifecycle(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(3):
            c.post("/assy-demo/step")
        c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"})
        for _ in range(2):
            c.post("/assy-demo/step")
        c.post("/assy-demo/recover", json={"sub_line_id": "ASSY-SL03"})
        c.post("/assy-demo/run-to-terminal", json={"max_windows": 40})
        body = c.get("/assy-demo/oee").json()
        summaries = {
            s["payload"]["subline_id"]: s["payload"] for s in body["oee_summaries"]
        }
        assert summaries["ASSY-SL03"]["downtime_s"] == 120.0
        assert summaries["ASSY-SL03"]["availability"] < 1.0
        for sub_line_id, payload in summaries.items():
            if sub_line_id == "ASSY-SL03":
                continue
            assert payload["downtime_s"] == 0.0
        sub_lines = {row["sub_line_id"]: row for row in body["sub_lines"]}
        assert sub_lines["ASSY-SL03"]["downtime_s"] == 120.0


# ═══════════════════════════════════════════════════════════════
# E. Scenario = fresh canonical run (tests 8, 9, 10)
# ═══════════════════════════════════════════════════════════════

class TestScenarioFreshRun:
    def test_scenario_selection_creates_a_fresh_canonical_run(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(2):
            c.post("/assy-demo/step")
        previous = c.get("/assy-demo/identity").json()["canonical"]
        resp = c.post("/assy-demo/scenario", json={"scenario_id": "FAILED_FINAL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "fresh_run"
        assert body["legacy_runtime_authority"] is False
        assert body["previous"]["run_id"] == previous["run_id"]
        assert body["previous"]["scenario_id"] == previous["scenario_id"]
        fresh = body["canonical"]
        assert fresh["run_id"] != previous["run_id"]
        assert fresh["scenario_id"] == "FAILED_FINAL"
        assert fresh["profile_id"] == "tipa-assy-failed_final"
        # the previous run is historical/unchanged and visible as history
        view = c.get("/vnext/workspaces/TIPA/view").json()
        assert view["identity"]["run_id"] == fresh["run_id"]
        assert view["session"]["step_count"] == 0
        history = view["run_history"]
        assert history and history[-1]["run_id"] == previous["run_id"]
        assert history[-1]["scenario_id"] == previous["scenario_id"]

    def test_scenario_identity_is_consistent_across_shell_rich_and_output(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/scenario", json={"scenario_id": "AP08_NG_REINSPECT_PASS"})
        rich = c.get("/assy-demo/identity").json()["canonical"]
        shell = c.get("/vnext/workspaces/TIPA/view").json()
        output = c.get("/assy-demo/observations").json()["canonical"]
        assert rich["run_id"] == shell["identity"]["run_id"] == output["run_id"]
        assert rich["scenario_id"] == shell["identity"]["scenario_id"] == output[
            "scenario_id"
        ]
        assert rich["profile_id"] == output["profile_id"]
        assert shell["identity"]["scenario_id"] == "AP08_NG_REINSPECT_PASS"

    def test_scenario_affects_domain_behaviour(self):
        out = _output()
        out.experience.reset()
        out.experience.select_scenario("FAILED_FINAL")
        out.experience.run_to_terminal(60)
        assert out.experience.session_identity()["scenario_id"] == "FAILED_FINAL"
        # The FAILED_FINAL scenario makes its target line emit a terminal reject
        # (LINE_OUT reject derived from authoritative FAILED_FINAL) ...
        rejects = [
            m["payload"]
            for m in out.mes_messages()["mes_messages"]
            if m["payload"].get("disposition") == "reject"
        ]
        assert rejects, "FAILED_FINAL scenario produced no reject output"
        assert {r["reason_code"] for r in rejects} == {"failed_final"}
        # ... and that line holds/no longer releases while the other five do.
        target = out.experience.detail("ASSY-SL03")["production"]
        assert target["motors_released"] == 0
        assert target["active_quality_holds"] >= 1
        assert out.experience.detail("ASSY-SL01")["production"][
            "motors_released"
        ] >= 1
        # the pinned default scenario produces no rejects at all
        happy = _output()
        happy.experience.reset()
        happy.experience.run_to_terminal(40)
        assert [
            m
            for m in happy.mes_messages()["mes_messages"]
            if m["payload"].get("disposition") == "reject"
        ] == []

    def test_unknown_scenario_fails_closed(self):
        c = _client()
        c.post("/assy-demo/reset")
        resp = c.post("/assy-demo/scenario", json={"scenario_id": "NOT_A_SCENARIO"})
        assert resp.status_code in (400, 404, 409)
        assert c.get("/assy-demo/identity").json()["canonical"]["scenario_id"] == (
            "tipa-default"
        )

    def test_reset_with_a_different_scenario_starts_a_fresh_run(self):
        c = _client()
        c.post("/assy-demo/reset")
        run_id = c.get("/assy-demo/identity").json()["canonical"]["run_id"]
        resp = c.post("/assy-demo/reset", json={"scenario": "AP06_FAIL_RETEST_PASS"})
        assert resp.status_code == 200
        assert resp.json()["canonical"]["run_id"] != run_id
        assert resp.json()["canonical"]["scenario_id"] == "AP06_FAIL_RETEST_PASS"
        # the same-scenario reset keeps the run id (in-context reset semantics)
        kept = c.post("/assy-demo/reset", json={"scenario": "AP06_FAIL_RETEST_PASS"})
        assert kept.status_code == 200
        assert kept.json()["canonical"]["run_id"] == resp.json()["canonical"]["run_id"]


# ═══════════════════════════════════════════════════════════════
# F. Product-path cleanup + hygiene (tests 7, 12)
# ═══════════════════════════════════════════════════════════════

class TestProductPathCleanup:
    @pytest.mark.parametrize(
        "path,body",
        [
            ("/assy-demo/jam", {"sub_line_id": "ASSY-SL03"}),
            ("/assy-demo/recover", {"sub_line_id": "ASSY-SL03"}),
            ("/assy-demo/run-to-terminal", {"max_windows": 8}),
        ],
    )
    def test_canonicalized_endpoints_are_no_longer_deferred(self, path, body):
        c = _client()
        c.post("/assy-demo/reset")
        if path.endswith("recover"):
            c.post("/assy-demo/step")
            c.post("/assy-demo/jam", json={"sub_line_id": "ASSY-SL03"})
            c.post("/assy-demo/step")
        resp = c.post(path, json=body)
        assert resp.status_code == 200
        assert resp.json().get("legacy_runtime_authority") is False
        assert resp.json().get("status") != "deferred"

    def test_no_capability_is_declared_deferred_any_more(self):
        assert DEFERRED_FEATURES == {}

    def test_r3_same_runtime_assertion_has_no_bypass(self):
        text = R3_TEST.read_text(encoding="utf-8")
        assert "or True" not in text, "the R3 same-runtime assertion still has a bypass"
        assert "runtime_object_id" in text

    def test_r2v_console_404_is_fixed_locally_in_the_client(self):
        js = RUN_CONTROL_JS.read_text(encoding="utf-8")
        assert "vf-canonical-identity" in js, "canonical pages still probe the legacy context"
        c = _client()
        # the legacy contract itself is unchanged (still 404 for TIPA)
        assert c.get("/vnext/runs/current", params={"workspace": "TIPA"}).status_code == 404

    def test_rich_ui_has_canonical_capability_bindings(self):
        js = RICH_JS.read_text(encoding="utf-8")
        for probe in ("uiJam", "uiRecover", "uiRunToTerminal", "uiOee", "/scenario"):
            assert probe in js, f"missing rich UI binding: {probe}"
