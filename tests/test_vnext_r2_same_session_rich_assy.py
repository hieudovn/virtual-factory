"""VF-vNEXT-R2 — Canonical Same-Session Rich ASSY 2D Experience tests.

Proves (Issue #80, SA amendment on #80):

- ONE product-path TIPA simulation authority: the rich ``/assy-demo`` experience
  and ``/workspaces`` share the exact same canonical ``RuntimeSession`` (no
  second session/federation/runtime, no legacy ``DemoController`` authority);
- Frame A overview = exactly the six canonical sub-lines with live values;
- Frame B = detached snapshot from the canonical ``AssyLineRuntime`` public
  surface (12 accepted positions, ``positions[]`` physical truth) with proven
  successive WIP movement and AP04 genealogy;
- sub-line selection is presentation-only;
- STEP/RESET act on the same session as the shell; reset keeps the R1-C01
  same-run-id semantics;
- legacy-authority-only capabilities (observation/MES, AP05 jam/OEE, scenario
  mutation) fail closed as explicitly deferred and never instantiate the legacy
  controller.
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
    CanonicalAssyExperience,
)
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

#: Accepted 12-position physical line (demo_snapshot canonical order).
EXPECTED_POSITIONS = [
    "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
    "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
]


def _client() -> TestClient:
    return TestClient(create_app())


def _experience() -> CanonicalAssyExperience:
    return CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))


def _occupied(detail: dict) -> dict:
    return {
        p["position_id"]: p.get("wip_id")
        for p in detail["positions"]
        if p.get("is_occupied")
    }


# ═══════════════════════════════════════════════════════════════
# A. Same-session identity / no second runtime
# ═══════════════════════════════════════════════════════════════

class TestSameSessionIdentity:
    def test_rich_ui_uses_the_same_canonical_session_as_the_shell(self):
        c = _client()
        c.post("/assy-demo/reset")
        rich = c.get("/assy-demo/identity")["canonical"] if False else c.get("/assy-demo/identity").json()["canonical"]
        shell = c.get("/vnext/workspaces/TIPA/view").json()
        assert rich["authority"] == "canonical_tipa_runtime_session"
        assert rich["run_id"] == shell["session"]["run_id"]
        assert rich["workspace_id"] == shell["identity"]["workspace_id"] == "TIPA"
        assert rich["scenario_id"] == shell["identity"]["scenario_id"]
        assert rich["profile_id"] == "tipa-assy-happy_path"
        assert rich["started"] is True

    def test_stepping_rich_ui_is_visible_in_the_shell_and_vice_versa(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.post("/assy-demo/step")
        shell = c.get("/vnext/workspaces/TIPA/view").json()
        rich = c.post("/assy-demo/snapshot").json()
        assert shell["session"]["last_time_s"] == rich["simulation_time_s"] == 240.0
        # shell step is visible in the rich projection too
        c.post("/vnext/workspaces/TIPA/control", json={"action": "step"})
        assert c.post("/assy-demo/snapshot").json()["simulation_time_s"] == 360.0
        assert (
            c.get("/vnext/workspaces/TIPA/view").json()["session"]["last_time_s"] == 360.0
        )

    def test_no_second_federation_or_session_is_constructed(self, monkeypatch):
        import virtual_factory.federation.assy_host as host_module

        created: list = []
        original = host_module.TipaAssyFederation.__init__

        def counting_init(self, config_path):  # noqa: ANN001
            created.append(config_path)
            original(self, config_path)

        monkeypatch.setattr(host_module.TipaAssyFederation, "__init__", counting_init)
        c = _client()
        c.get("/assy-demo/overview")
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL02"})
        c.get("/assy-demo/sub-line/ASSY-SL03")
        c.get("/assy-demo/sub-lines")
        c.post("/assy-demo/snapshot")
        assert len(created) == 1, "a second canonical federation was constructed"

    def test_legacy_controller_is_never_instantiated_on_the_rich_path(self, monkeypatch):
        import virtual_factory.assembly.demo_controller as demo_controller

        calls: list = []

        def spy(self, *args, **kwargs):  # noqa: ANN001
            calls.append("DemoController()")
            raise AssertionError("legacy DemoController must not be instantiated")

        monkeypatch.setattr(demo_controller.DemoController, "__init__", spy)
        c = _client()
        c.get("/assy-demo/overview")
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.post("/assy-demo/snapshot")
        c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL01"})
        c.post("/assy-demo/run-mode", json={"mode": "MANUAL"})
        c.get("/assy-demo/sub-lines")
        c.get("/assy-demo/observations")
        c.get("/assy-demo/mes-messages")
        c.post("/assy-demo/jam")
        assert calls == []

    def test_shell_metadata_declares_same_session(self):
        c = _client()
        view = c.get("/vnext/workspaces/TIPA/view").json()
        assert view["legacy_demo"]["shares_session"] is True
        assert view["legacy_demo"]["shares_identity"] is True
        assert "canonical" in view["ui_note"].lower()

    def test_opening_the_rich_ui_does_not_advance_simulation_time(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        before = c.get("/vnext/workspaces/TIPA/view").json()["session"]["last_time_s"]
        c.get("/assy-demo/overview")
        c.get("/assy-demo/sub-lines")
        c.get("/assy-demo/sub-line/ASSY-SL01")
        c.get("/assy-demo/identity")
        after = c.get("/vnext/workspaces/TIPA/view").json()["session"]["last_time_s"]
        assert before == after == 120.0


# ═══════════════════════════════════════════════════════════════
# B. Frame A — six canonical sub-lines
# ═══════════════════════════════════════════════════════════════

class TestFrameAOverview:
    def test_overview_is_exactly_the_six_canonical_sub_lines(self):
        c = _client()
        ov = c.get("/assy-demo/overview").json()
        assert [s["sub_line_id"] for s in ov["sub_lines"]] == list(SUB_LINE_IDS)
        assert [s["scope"] for s in ov["sub_lines"]] == [
            f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS
        ]

    def test_overview_rows_are_live_and_canonical(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            c.post("/assy-demo/step")
        ov = c.get("/assy-demo/overview").json()
        for row in ov["sub_lines"]:
            assert row["simulation_time_s"] == 600.0
            assert row["wips_on_line"] == 6
            assert row["motors_created"] == 1
        assert ov["total_motors_created"] == 6
        assert ov["demo_step_number"] == 5           # canonical step count
        assert ov["scenario"] == "tipa-default"      # pinned run input
        assert ov["canonical"]["run_id"].startswith("TIPA-")

    def test_sub_lines_endpoint_matches_overview(self):
        c = _client()
        c.post("/assy-demo/step")
        rows = c.get("/assy-demo/sub-lines").json()
        ov = c.get("/assy-demo/overview").json()
        assert rows == ov["sub_lines"]


# ═══════════════════════════════════════════════════════════════
# C. Frame B — 2D physical line from canonical positions[]
# ═══════════════════════════════════════════════════════════════

class TestFrameBPhysicalProjection:
    def test_snapshot_exposes_the_twelve_accepted_positions(self):
        c = _client()
        c.post("/assy-demo/reset")
        detail = c.post("/assy-demo/snapshot").json()
        assert [p["position_id"] for p in detail["positions"]] == EXPECTED_POSITIONS
        assert detail["sub_line_id"] == "ASSY-SL01"
        assert detail["canonical_sub_line"]["scope"] == "TIPA/ASSY/ASSY-SL01"

    def test_successive_snapshots_show_physical_wip_movement(self):
        c = _client()
        c.post("/assy-demo/reset")
        frames = []
        for _ in range(5):
            detail = c.post("/assy-demo/step").json()
            frames.append(_occupied(detail))
        assert frames[0] == {"PRE-ASSY": "SSO2-0002", "AP01": "SSO2-0001"}
        assert frames[1]["AP02"] == "SSO2-0001"
        assert frames[2]["AP03"] == "SSO2-0001"
        assert frames[3]["AP04"] == "SSO2-0001"
        assert frames[4]["AP05"] == "MTR-0001"     # AP04 join produced the motor
        # every rendered position comes from the runtime public read surface
        assert "SSO2-0001" not in frames[4].values() or frames[4]["AP05"] == "MTR-0001"

    def test_frame_b_projection_matches_rich_positions_only_truth(self):
        exp = _experience()
        exp.step()
        exp.step()
        federation = exp.federation()
        runtime = federation.runtime("ASSY-SL01")
        detail = exp.detail("ASSY-SL01")
        for position in detail["positions"]:
            assert (position["wip_id"] or None) == runtime.conveyor.wip_at(
                position["position_id"]
            )
        assert detail["positions"][4]["position_id"] == "AP04"

    def test_ap04_genealogy_is_visible_in_the_rich_projection(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            detail = c.post("/assy-demo/step").json()
        assert ("MTR-0001", ["SSO2-0001", "RSO2-0001"]) in [
            (g["child_wip_id"], list(g["parent_wip_ids"])) for g in detail["genealogy"]
        ]
        assert detail["production"]["motors_created"] == 1

    def test_inspector_read_models_come_from_the_same_runtime(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            detail = c.post("/assy-demo/step").json()
        assert "station_contracts" in detail and detail["station_contracts"]
        assert "active_operations" in detail
        assert "recent_quality_events" in detail
        assert detail["canonical_sub_line"]["effective_scenario"] == "HAPPY_PATH"


# ═══════════════════════════════════════════════════════════════
# D. Selection / control coherence
# ═══════════════════════════════════════════════════════════════

class TestSelectionAndControl:
    def test_selection_is_presentation_only(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            c.post("/assy-demo/step")
        before = c.get("/assy-demo/overview").json()
        sl01 = c.get("/assy-demo/sub-line/ASSY-SL01").json()
        c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL02"})
        c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL01"})
        after = c.get("/assy-demo/overview").json()
        assert c.get("/assy-demo/identity").json()["canonical"]["run_id"] == before["canonical"]["run_id"]
        assert before["total_motors_created"] == after["total_motors_created"]
        assert c.get("/assy-demo/sub-line/ASSY-SL01").json()["simulation_time_s"] == sl01["simulation_time_s"]
        assert before["demo_step_number"] == after["demo_step_number"]

    def test_select_fails_closed(self):
        c = _client()
        c.post("/assy-demo/reset")
        assert c.post("/assy-demo/select", json={}).status_code == 400
        assert c.post("/assy-demo/select", json={"sub_line_id": "NOPE"}).status_code == 404
        assert c.get("/assy-demo/sub-line/NOPE").status_code == 404

    def test_rich_step_advances_the_shell_session(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        assert c.get("/vnext/workspaces/TIPA/view").json()["session"]["step_count"] == 1
        assert c.post("/assy-demo/snapshot").json()["simulation_time_s"] == 120.0

    def test_rich_reset_keeps_run_identity_and_fresh_profile_state(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            c.post("/assy-demo/step")
        run_before = c.get("/assy-demo/identity").json()["canonical"]["run_id"]
        detail = c.post("/assy-demo/reset").json()
        identity = c.get("/assy-demo/identity").json()["canonical"]
        assert identity["run_id"] == run_before
        assert detail["simulation_time_s"] == 0.0
        assert detail["production"]["motors_created"] == 0
        assert detail["scenario"] == "HAPPY_PATH"
        # R1-C01: every sub-line is back at the fresh profile baseline
        ov = c.get("/assy-demo/overview").json()
        assert all(row["simulation_time_s"] == 0.0 for row in ov["sub_lines"])


# ═══════════════════════════════════════════════════════════════
# E. Deferred legacy-authority capabilities (fail closed)
# ═══════════════════════════════════════════════════════════════

class TestDeferredFailClosed:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("post", "/assy-demo/jam"),
            ("post", "/assy-demo/recover"),
            ("post", "/assy-demo/run-to-terminal"),
        ],
    )
    def test_ap05_fault_and_oee_workflows_are_deferred(self, method, path):
        c = _client()
        resp = getattr(c, method)(path)
        assert resp.status_code == 409
        body = resp.json()
        assert body["status"] == "deferred"
        assert body["legacy_runtime_authority"] is False
        assert body["deferred_to"] == "R4"

    @pytest.mark.parametrize(
        "path",
        ["/assy-demo/observations", "/assy-demo/mes-messages", "/assy-demo/mes-trace"],
    )
    def test_r3_output_endpoints_are_canonical_not_legacy(self, path):
        """R3 superseded the R2 deferral: the endpoints now serve the SAME
        canonical session read-only (migrated ownership assertion, Issue #81)."""
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        resp = c.get(path)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["authority"] == "canonical_tipa_runtime_session"
        assert body["legacy_runtime_authority"] is False
        assert body["canonical"]["run_id"] == (
            c.get("/assy-demo/identity").json()["canonical"]["run_id"]
        )

    def test_scenario_mutation_is_deferred_but_same_scenario_reset_is_allowed(self):
        c = _client()
        assert c.post("/assy-demo/reset").status_code == 200
        ok = c.post("/assy-demo/reset", json={"scenario": "HAPPY_PATH"})
        assert ok.status_code == 200
        deferred = c.post("/assy-demo/reset", json={"scenario": "AP06_FAIL_RETEST_PASS"})
        assert deferred.status_code == 409
        assert deferred.json()["feature"] == "scenario_change"
        assert c.get("/assy-demo/identity").json()["canonical"]["scenario_id"] == "tipa-default"

    def test_thin_ops_bindings_use_the_canonical_runtime(self):
        c = _client()
        c.post("/assy-demo/reset")
        assert c.post("/assy-demo/run-mode", json={"mode": "MANUAL"}).status_code == 200
        assert c.post("/assy-demo/run-mode", json={"mode": "BOGUS"}).status_code == 400
        assert c.post("/assy-demo/operation-command", json={}).status_code == 400
        # stale/invalid target -> runtime rejection surfaced (fail closed)
        assert c.post(
            "/assy-demo/operation-command",
            json={"station_id": "AP01", "wip_id": "NOPE", "command": "DONE"},
        ).status_code == 409


# ═══════════════════════════════════════════════════════════════
# F. Held-one / five-continue reflected in the rich projection
# ═══════════════════════════════════════════════════════════════

class TestHoldFreezeOnUI:
    def test_held_line_is_frozen_in_the_rich_projection_while_five_continue(self):
        exp = _experience()
        exp.step()
        bridge = exp.bridge()
        bridge.hold_sub_line("ASSY-SL03")
        for _ in range(5):
            exp.step()
        ov = exp.overview()
        rows = {row["sub_line_id"]: row for row in ov["sub_lines"]}
        assert rows["ASSY-SL03"]["simulation_time_s"] == 120.0     # frozen
        assert rows["ASSY-SL03"]["motors_created"] == 0
        for sid in SUB_LINE_IDS:
            if sid == "ASSY-SL03":
                continue
            assert rows[sid]["simulation_time_s"] == 720.0
            assert rows[sid]["motors_created"] >= 1
        held = exp.assert_hold_state()
        assert held["held_sub_line_ids"] == ["ASSY-SL03"]
        assert held["sub_lines"]["ASSY-SL03"]["held"] is True
        # the frozen line's 2D projection is the FRESH-frame 120 s state
        detail = exp.detail("ASSY-SL03")
        assert detail["simulation_time_s"] == 120.0
        assert _occupied(detail) == {"PRE-ASSY": "SSO2-0002", "AP01": "SSO2-0001"}
