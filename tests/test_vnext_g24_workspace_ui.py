"""VF-vNEXT-G24 — Multi-Workspace UI Switching + Monitoring Shell tests.

Proves (Issue #75 required): workspace selector sourced from the backend G23
registry (deterministic, registration-order independent); selecting TIPA reuses
the existing six-sub-line ASSY UI/runtime; selecting shwtp displays the accepted
G21 5-scope slice (RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108) with key
flow/tank values; switching never mutates the inactive workspace session; every
workspace view exposes the minimum monitor fields (identity, run/session state,
simulation time/step, scope/unit structure, key current values/status, live
trace); run control acts only on the selected workspace/session; unknown
workspace/session/action fails closed; SH-WTP assumed topology/fidelity is never
presented as site truth; the static workspace shell page + FastAPI endpoints
are served; G23 registry + G22 session semantics are unchanged; TIPA ASSY +
canonical baseline + full suite remain green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from virtual_factory.runcontrol import (
    RuntimeSession,
    WorkspaceRegistryError,
    WorkspaceRuntimeRegistry,
    build_tipa_session,
)
from virtual_factory.shwtp import build_shwtp_plant_slice, build_shwtp_session
from virtual_factory.shwtp.expansion import (
    DIST_P108_SCOPE_PATH,
    PLANT_SLICE_SCOPES,
    RAW_INTAKE_SCOPE_PATH,
    SHWTP_T106_SCOPE_PATH,
    SHWTP_T108_SCOPE_PATH,
    T100_SCOPE_PATH,
)
from virtual_factory.federation import SUB_LINE_IDS

TIPA_CONFIG = "configs/plants/tipa_assy_demo.yaml"

UI_STATIC = (
    Path(__file__).resolve().parent.parent
    / "src" / "virtual_factory" / "ui" / "static"
)


def _make_registry() -> WorkspaceRuntimeRegistry:
    reg = WorkspaceRuntimeRegistry()
    reg.register(
        "shwtp",
        lambda: build_shwtp_session(),
        description="SH-WTP G21/G22 plant slice",
    )
    reg.register(
        "TIPA",
        lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"),
        description="TIPA ASSY 6 sub-lines",
    )
    return reg


def _monitor():
    from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

    return WorkspaceMonitor(_make_registry())


class TestSelectorSource:
    def test_registry_lists_tipa_and_shwtp(self):
        reg = _make_registry()
        assert reg.workspace_ids() == ("TIPA", "shwtp")
        assert reg.metadata()["workspace_ids"] == ["TIPA", "shwtp"]
        infos = {i.workspace_id: i.description for i in reg.enumerate()}
        assert "TIPA" in infos and "shwtp" in infos

    def test_registration_order_independent(self):
        a = WorkspaceRuntimeRegistry()
        a.register("shwtp", lambda: build_shwtp_session())
        a.register("TIPA", lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"))
        b = WorkspaceRuntimeRegistry()
        b.register("TIPA", lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"))
        b.register("shwtp", lambda: build_shwtp_session())
        assert a.workspace_ids() == b.workspace_ids() == ("TIPA", "shwtp")

    def test_monitor_selector_source(self):
        mon = _monitor()
        assert mon.workspace_ids() == ("TIPA", "shwtp")
        assert mon.workspace_list()["workspace_ids"] == ["TIPA", "shwtp"]


class TestSelectTipa:
    def test_select_tipa_returns_tipa_view(self):
        mon = _monitor()
        view = mon.select("TIPA")
        assert view["workspace_id"] == "TIPA"
        assert view["identity"]["workspace_id"] == "TIPA"
        assert view["runtime"] == "TIPA ASSY (six sub-lines)"

    def test_tipa_reuses_six_subline_assy_ui(self):
        mon = _monitor()
        view = mon.select("TIPA")
        assert view["ui_page"] == "/assy-demo"
        # six sub-line structure
        paths = [row["scope"] for row in view["structure"]]
        assert len(paths) == 6
        assert all(p.startswith("TIPA/ASSY/ASSY-SL") for p in paths)
        assert "TIPA/ASSY/ASSY-SL01" in paths

    def test_tipa_view_has_minimum_fields(self):
        mon = _monitor()
        view = mon.select("TIPA")
        assert "session" in view
        assert view["session"]["state"] in ("created", "running", "stopped")
        assert "simulation" in view
        assert isinstance(view["values"], list)
        assert isinstance(view["trace"], list)


class TestSelectShwtp:
    def test_select_shwtp_returns_shwtp_view(self):
        mon = _monitor()
        view = mon.select("shwtp")
        assert view["workspace_id"] == "shwtp"
        assert view["runtime"] == "SH-WTP G21 plant slice"

    def test_shwtp_shows_accepted_five_scope_slice(self):
        mon = _monitor()
        view = mon.select("shwtp")
        scopes = [row["vf_path"] for row in view["structure"]]
        expected = [
            RAW_INTAKE_SCOPE_PATH.as_string(),
            T100_SCOPE_PATH.as_string(),
            SHWTP_T106_SCOPE_PATH.as_string(),
            SHWTP_T108_SCOPE_PATH.as_string(),
            DIST_P108_SCOPE_PATH.as_string(),
        ]
        assert scopes == expected
        assert len(PLANT_SLICE_SCOPES) == 5

    def test_shwtp_view_has_minimum_fields(self):
        mon = _monitor()
        view = mon.select("shwtp")
        assert "identity" in view
        assert "session" in view
        assert "simulation" in view
        assert len(view["structure"]) == 5
        assert isinstance(view["values"], list)
        assert isinstance(view["trace"], list)

    def test_shwtp_live_tank_values_after_steps(self):
        mon = _monitor()
        mon.select("shwtp")
        for _ in range(3):
            mon.control("shwtp", "step")
        view = mon.view("shwtp")
        t108 = next(
            (r for r in view["values"] if r["scope"] == SHWTP_T108_SCOPE_PATH.as_string()),
            None,
        )
        assert t108 is not None
        vals = t108.get("current_values", {})
        assert "volume_m3" in vals
        assert "level_m" in vals
        assert isinstance(vals["volume_m3"], (int, float))


class TestIsolation:
    def test_two_workspace_sessions_isolated(self):
        mon = _monitor()
        tipa_view = mon.select("TIPA")
        shwtp_view = mon.select("shwtp")
        assert tipa_view["workspace_id"] != shwtp_view["workspace_id"]

    def test_switching_does_not_mutate_inactive_session(self):
        mon = _monitor()
        mon.select("shwtp")
        mon.control("shwtp", "step")
        mon.control("shwtp", "step")
        shwtp_steps_before = mon.view("shwtp")["session"]["step_count"]
        # Switch to TIPA and back
        mon.select("TIPA")
        mon.select("shwtp")
        shwtp_after = mon.view("shwtp")["session"]
        assert shwtp_after["step_count"] == shwtp_steps_before

    def test_control_only_affects_selected(self):
        mon = _monitor()
        mon.select("shwtp")
        mon.control("shwtp", "step")
        tipa_before = mon.select("TIPA")["session"]["step_count"]
        # advance shwtp again: TIPA must not move
        mon.select("shwtp")
        mon.control("shwtp", "step")
        tipa_after = mon.select("TIPA")["session"]["step_count"]
        assert tipa_after == tipa_before

    def test_registry_select_isolation(self):
        reg = _make_registry()
        tipa = reg.select("TIPA")
        shwtp = reg.select("shwtp")
        assert isinstance(tipa, RuntimeSession)
        assert isinstance(shwtp, RuntimeSession)
        tipa.advance()
        shwtp.advance()
        assert tipa.record.bridge is not shwtp.record.bridge


class TestFailClosed:
    def test_unknown_workspace_fails_closed(self):
        mon = _monitor()
        with pytest.raises(Exception):
            mon.select("unknown-ws")
        with pytest.raises(Exception):
            mon.view("unknown-ws")

    def test_unknown_control_action_fails_closed(self):
        mon = _monitor()
        mon.select("shwtp")
        with pytest.raises(Exception):
            mon.control("shwtp", "bogus")

    def test_registry_unknown_fails_closed(self):
        reg = _make_registry()
        with pytest.raises(WorkspaceRegistryError):
            reg.select("nope")


class TestShwtpTruth:
    def test_shwtp_not_presented_as_site_truth(self):
        mon = _monitor()
        view = mon.select("shwtp")
        assert view["site_truth"] is False
        assert isinstance(view.get("assumed_topology"), list)
        assert view.get("ui_page") is None
        # scenario-assumed scopes carry status/fidelity markers
        raw = next(
            r for r in view["structure"]
            if r["vf_path"] == RAW_INTAKE_SCOPE_PATH.as_string()
        )
        assert raw["status"] == "scenario_assumed"
        assert raw["fidelity"] == "logical_only"
        t108 = next(
            r for r in view["structure"]
            if r["vf_path"] == SHWTP_T108_SCOPE_PATH.as_string()
        )
        assert t108["status"] == "accepted"
        assert t108["fidelity"] == "first_order"

    def test_observer_only_monitor_rows_do_not_mutate(self):
        slice_ = build_shwtp_plant_slice()
        before = slice_.coordinator
        rows = slice_.monitor_rows()
        assert len(rows) == 5
        # No mutation: coordinator and participants unchanged.
        assert slice_.coordinator is before
        assert all(r["status"] in ("accepted", "scenario_assumed") for r in rows)


class TestApiAndStatic:
    fastapi = pytest.importorskip("fastapi")

    def _client(self):
        from fastapi.testclient import TestClient
        from virtual_factory.ui.api import create_app

        return TestClient(
            create_app(
                config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0
            )
        )

    def test_workspaces_endpoint(self):
        client = self._client()
        res = client.get("/vnext/workspaces")
        assert res.status_code == 200
        assert res.json()["workspace_ids"] == ["TIPA", "shwtp"]

    def test_workspace_view_endpoint(self):
        client = self._client()
        res = client.get("/vnext/workspaces/shwtp/view")
        assert res.status_code == 200
        assert res.json()["workspace_id"] == "shwtp"

    def test_select_endpoint(self):
        client = self._client()
        res = client.post("/vnext/workspaces/select", json={"workspace_id": "TIPA"})
        assert res.status_code == 200
        assert res.json()["workspace_id"] == "TIPA"

    def test_control_endpoint(self):
        client = self._client()
        res = client.post(
            "/vnext/workspaces/shwtp/control", json={"action": "step"}
        )
        assert res.status_code == 200
        assert res.json()["session"]["step_count"] == 1

    def test_unknown_workspace_404(self):
        client = self._client()
        assert client.get("/vnext/workspaces/nope/view").status_code == 404
        assert (
            client.post("/vnext/workspaces/select", json={"workspace_id": "nope"}).status_code
            == 404
        )

    def test_static_shell_page_served(self):
        client = self._client()
        res = client.get("/workspaces")
        assert res.status_code == 200
        assert "Workspace Shell" in res.text or "workspace" in res.text.lower()

    def test_static_shell_files_exist(self):
        for name in ("workspace_shell.html", "workspace_shell.js", "workspace_shell.css"):
            assert (UI_STATIC / name).is_file()
        html = (UI_STATIC / "workspace_shell.html").read_text(encoding="utf-8")
        js = (UI_STATIC / "workspace_shell.js").read_text(encoding="utf-8")
        # selector is driven by the backend registry and control is workspace-scoped
        assert "/vnext/workspaces" in js
        assert "workspace_id" in js


class TestG24C01TipaLiveProjection:
    """G24-C01: the shell's TIPA view reflects the selected G22 RuntimeSession.

    Live per-sub-line state/status/key values are read from the SELECTED
    session's own execution bridge (no second runtime), and /assy-demo is
    explicitly labelled a SEPARATE legacy demo runtime (not the same session).
    """

    def test_step_changes_per_sub_line_values(self):
        mon = _monitor()
        mon.select("TIPA")
        before = mon.view("TIPA")
        # No bridge yet -> no live sub-line rows; session state is created.
        assert before["sub_lines"] == []
        mon.control("TIPA", "step")
        after = mon.view("TIPA")
        rows = after["sub_lines"]
        assert len(rows) == 6
        assert all(r["simulation_time_s"] > 0 for r in rows)
        # the step actually moved per-sub-line state
        assert any(r["simulation_time_s"] != 0 for r in rows)

    def test_six_sub_lines_present(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        view = mon.view("TIPA")
        ids = [r["sub_line_id"] for r in view["sub_lines"]]
        assert ids == list(SUB_LINE_IDS)
        # structure carries six sub-lines too
        assert len(view["structure"]) == 6

    def test_runtime_identity_is_selected_g22_session(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        view = mon.view("TIPA")
        assert view["runtime_kind"] == "selected_g22_session"
        assert view["identity"]["run_id"] == view["session"]["run_id"]
        assert view["session"]["scenario_id"] == "tipa-default"

    def test_no_second_runtime_in_shell(self):
        mon = _monitor()
        mon.select("TIPA")
        # The shell only reads the session's own bridge; it must not have
        # built any separate federation/runtime for TIPA.
        assert mon.selected() == "TIPA"
        view = mon.view("TIPA")
        # before step the session has no bridge yet (lazily built on step)
        assert view["sub_lines"] == []

    def test_assy_demo_not_presented_as_same_session(self):
        mon = _monitor()
        view = mon.select("TIPA")
        assert view["ui_page"] == "/assy-demo"
        legacy = view.get("legacy_demo", {})
        assert legacy.get("shares_session") is False
        assert legacy.get("shares_identity") is False
        note = (legacy.get("note") or "") + (view.get("ui_note") or "")
        assert "SEPARATE" in note or "separate" in note.lower()
        assert "not" in note.lower()

    def test_step_increments_session_step_count(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        view = mon.view("TIPA")
        assert view["session"]["step_count"] == 1
        assert view["session"]["last_time_s"] is not None

    def test_shwtp_unaffected(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        shwtp = mon.select("shwtp")
        # TIPA session stepping must not have touched shwtp monitor
        assert shwtp["workspace_id"] == "shwtp"
        assert shwtp["session"]["step_count"] == 0


class TestG23G22Unchanged:
    def test_registry_select_still_fresh_independent(self):
        reg = _make_registry()
        a = reg.select("shwtp")
        b = reg.select("shwtp")
        assert a is not b
        a.advance()
        assert len(a.trace()) == 1
        assert len(b.trace()) == 0

    def test_shwtp_slice_and_session_still_work(self):
        slice_ = build_shwtp_plant_slice()
        assert slice_.run_window("window-1").status == "completed"
        session = build_shwtp_session()
        assert session.workspace_id == "shwtp"
        session.advance()
        assert len(session.trace()) == 1

    def test_tipa_session_still_works(self):
        s = build_tipa_session(TIPA_CONFIG, "tipa-default")
        assert s.workspace_id == "TIPA"
        s.advance()
        assert len(s.trace()) == 1

    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import (
            SHWTP_FEDERATION_COUPLING_POLICY,
            SHWTP_PLANT_SLICE_COUPLING_POLICY,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert SHWTP_PLANT_SLICE_COUPLING_POLICY == "explicit_lagged"
        assert len(PLANT_SLICE_SCOPES) == 5
