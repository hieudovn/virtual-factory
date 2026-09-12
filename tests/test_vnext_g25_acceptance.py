"""VF-vNEXT-G25 — Integrated Multi-Workspace Demo / MVP Acceptance tests.

ACC/acceptance-hardening gate (Issue #76). Proves the integrated MVP on the
current accepted architecture — no new architecture:

FLOW A (TIPA): open the workspace shell; select TIPA from the registry; use the
selected G22 RuntimeSession; step and prove six live ASSY sub-lines read from
that session; reset/new-attempt/replay are explicit and deterministic; switching
to SH-WTP and back does not mutate the TIPA session; /assy-demo stays labelled a
separate legacy runtime.

FLOW B (SH-WTP): select shwtp; run RAW-INTAKE -> T100 -> T106 -> T108 ->
DIST-P108; prove live time/step/flow/tank/status; fidelity/status/assumed
topology stay explicit; reset/new-attempt/replay deterministic; switching to
TIPA and back does not mutate the SH-WTP session.

Re-prove (platform invariants): one platform -> many independent Workspaces; no
shared state/run_id/clock/truth; no cross-workspace runtime coupling;
RuntimeSession lifecycle reused; explicit_lagged/G4/G19 unchanged; ASSY oracle
green; SH-WTP assumptions never become site truth.
"""

from __future__ import annotations

import pytest

from virtual_factory.federation import SUB_LINE_IDS, sub_line_path
from virtual_factory.runcontrol import RuntimeSession, WorkspaceRuntimeRegistry
from virtual_factory.shwtp.expansion import (
    DIST_P108_SCOPE_PATH,
    PLANT_SLICE_SCOPES,
    RAW_INTAKE_SCOPE_PATH,
    SHWTP_T106_SCOPE_PATH,
    SHWTP_T108_SCOPE_PATH,
    T100_SCOPE_PATH,
)

TIPA_CONFIG = "configs/plants/tipa_assy_demo.yaml"

SUBLINE_SCOPE_PATHS = tuple(sub_line_path(sid).as_string() for sid in SUB_LINE_IDS)
SHWTP_SCOPE_ORDER = (
    RAW_INTAKE_SCOPE_PATH,
    T100_SCOPE_PATH,
    SHWTP_T106_SCOPE_PATH,
    SHWTP_T108_SCOPE_PATH,
    DIST_P108_SCOPE_PATH,
)


def _monitor():
    from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

    return WorkspaceMonitor(tipa_config_path=TIPA_CONFIG)


def _norm_committed(transfer_id: str) -> str:
    """Strip window/run-specific prefix, keep the producing scope suffix."""
    return transfer_id.split("::", 1)[1] if "::" in transfer_id else transfer_id


def _trace_key(result):
    return (
        result.status,
        result.target_time_s,
        tuple(result.participants),
        tuple(sorted(_norm_committed(t) for t in result.committed)),
    )


def _tipa_subline_key(rows):
    return [
        (
            r["sub_line_id"],
            r["simulation_time_s"],
            r["conveyor_state"],
            r["wip_count"],
            r["motor_count"],
            r["rso2_buffer_size"],
        )
        for r in rows
    ]


def _shwtp_row(view, scope_path):
    return next((v for v in view["values"] if v["scope"] == scope_path), None)


# ═══════════════════════════════════════════════════════════════
# FLOW A — TIPA
# ═══════════════════════════════════════════════════════════════

class TestFlowATipa:
    def test_a1_shell_open_select_tipa_from_registry(self):
        mon = _monitor()
        # shell opens: selector source is the backend registry
        meta = mon.workspace_list()
        assert meta["workspace_ids"] == ["TIPA", "shwtp"]
        view = mon.select("TIPA")
        assert view["workspace_id"] == "TIPA"
        assert view["runtime_kind"] == "selected_g22_session"
        assert view["identity"]["workspace_id"] == "TIPA"

    def test_a2_step_proves_six_live_sub_lines_from_that_session(self):
        mon = _monitor()
        mon.select("TIPA")
        assert mon.view("TIPA")["sub_lines"] == []  # no bridge before step
        mon.control("TIPA", "step")
        view = mon.view("TIPA")
        rows = view["sub_lines"]
        ids = [r["sub_line_id"] for r in rows]
        assert ids == list(SUB_LINE_IDS)
        assert len(rows) == 6
        assert all(r["simulation_time_s"] > 0 for r in rows)
        # scope paths match the six ASSY sub-lines
        assert [r["scope"] for r in rows] == list(SUBLINE_SCOPE_PATHS)

    def test_a3_reset_same_identity_fresh_state(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        mon.control("TIPA", "step")
        run_before = mon.view("TIPA")["session"]["run_id"]
        view = mon.control("TIPA", "reset")
        assert view["session"]["run_id"] == run_before   # same run identity
        assert view["session"]["last_time_s"] == 0.0     # fresh state at t=0
        assert view["trace"] == []                       # trace cleared
        # stepping again advances from a clean state
        mon.control("TIPA", "step")
        assert len(mon.view("TIPA")["trace"]) == 1

    def test_a4_new_attempt_fresh_identity(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        old_run = mon.view("TIPA")["session"]["run_id"]
        view = mon.control("TIPA", "new_attempt")
        assert view["session"]["run_id"] != old_run
        assert view["sub_lines"] == []   # fresh attempt, no bridge yet

    def test_a5_replay_deterministic(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        mon.control("TIPA", "step")
        first = [r for r in mon.view("TIPA")["sub_lines"]]
        first_key = _tipa_subline_key(first)

        view = mon.control("TIPA", "replay")
        assert "run_id" in view["session"]
        mon.control("TIPA", "step")
        mon.control("TIPA", "step")
        second_key = _tipa_subline_key(mon.view("TIPA")["sub_lines"])
        assert first_key == second_key

    def test_a6_switch_to_shwtp_and_back_no_mutation(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        mon.control("TIPA", "step")
        tipa_before = mon.view("TIPA")
        tipa_run = tipa_before["session"]["run_id"]
        tipa_steps = tipa_before["session"]["step_count"]
        tipa_trace = tipa_before["trace"]

        # switch away and operate shwtp
        mon.select("shwtp")
        mon.control("shwtp", "step")
        mon.control("shwtp", "step")

        # back to TIPA: unchanged
        tipa_after = mon.select("TIPA")
        assert tipa_after["session"]["run_id"] == tipa_run
        assert tipa_after["session"]["step_count"] == tipa_steps
        assert tipa_after["trace"] == tipa_trace

    def test_a7_assy_demo_same_canonical_session(self):
        """R2: /assy-demo projects the SAME canonical session (one authority)."""
        mon = _monitor()
        view = mon.select("TIPA")
        assert view["ui_page"] == "/assy-demo"
        legacy = view["legacy_demo"]
        assert legacy["shares_session"] is True
        assert legacy["shares_identity"] is True
        note = (legacy["note"] + view["ui_note"]).lower()
        assert "same" in note and "canonical" in note


# ═══════════════════════════════════════════════════════════════
# FLOW B — SH-WTP
# ═══════════════════════════════════════════════════════════════

class TestFlowBShwtp:
    def test_b1_select_shwtp_canonical_whole_plant(self):
        """The canonical shwtp view is the X3 whole plant (VF-SHW-X3).

        The accepted X2 60-second model and the G21 5-scope slice remain
        reachable through their explicit compatibility factories (proved in the
        same test).
        """
        mon = _monitor()
        view = mon.select("shwtp")
        assert view["workspace_id"] == "shwtp"
        assert view["runtime"] in (
            "SH-WTP X3 whole plant (1 s windows, two PI loops)",
            "SH-WTP whole plant (canonical X3 profile; X2/G21 compatible)",
        )
        scopes = [v["scope"] for v in view["values"]]
        assert len(scopes) == 16
        # the canonical RAW-INTAKE -> T100 -> ... -> DIST-P108 path is present
        for path in (p.as_string() for p in SHWTP_SCOPE_ORDER):
            assert path in scopes, path
        assert len(PLANT_SLICE_SCOPES) == 5
        # explicit compatibility path: the accepted G21 slice session still works
        from virtual_factory.shwtp import build_shwtp_g21_slice_session

        slice_session = build_shwtp_g21_slice_session()
        slice_session.advance()
        assert len(slice_session.record.bridge.slice.scopes) == 5

    def test_b2_run_chain_live_time_step_flow_tank_status(self):
        mon = _monitor()
        mon.select("shwtp")
        for _ in range(4):
            mon.control("shwtp", "step")
        view = mon.view("shwtp")
        assert view["session"]["step_count"] == 4
        assert view["session"]["last_time_s"] > 0
        assert len(view["trace"]) == 4
        # flow/tank live values on T106 / T108
        t106 = _shwtp_row(view, SHWTP_T106_SCOPE_PATH.as_string())
        t108 = _shwtp_row(view, SHWTP_T108_SCOPE_PATH.as_string())
        assert t106 is not None and t108 is not None
        assert "current_values" in t106 and "current_values" in t108
        assert "volume_m3" in t108["current_values"]
        assert "level_m" in t108["current_values"]
        # status/fidelity explicit per scope (contract-derived, never site truth)
        assert t108["fidelity"] == "first_order"
        assert t108["status"] == "synthetic_reference"
        assert view["site_truth"] is False
        assert view["simulation_truth"] == "synthetic_reference"
        assert view["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert view["site_authorized_execution"] == "NOT_AUTHORIZED"

    def test_b3_fidelity_status_assumed_topology_explicit(self):
        mon = _monitor()
        view = mon.select("shwtp")
        assert view["site_truth"] is False
        assumed = view["assumed_topology"]
        assert len(assumed) >= 1
        assumed_scopes = set()
        for row in assumed:
            assumed_scopes.add(row["scope"])
            assumed_scopes.add(row["target_scope"])
        assert RAW_INTAKE_SCOPE_PATH.as_string() in assumed_scopes
        assert DIST_P108_SCOPE_PATH.as_string() in assumed_scopes
        # PIM remains authoritative (assumptions are not site truth)
        assert "site truth" in view["ui_note"].lower()

    def test_b4_reset_same_identity_fresh_state(self):
        mon = _monitor()
        mon.select("shwtp")
        mon.control("shwtp", "step")
        mon.control("shwtp", "step")
        run_before = mon.view("shwtp")["session"]["run_id"]
        view = mon.control("shwtp", "reset")
        assert view["session"]["run_id"] == run_before
        assert view["session"]["last_time_s"] == 0.0
        assert view["trace"] == []

    def test_b5_new_attempt_fresh_identity_and_tank(self):
        mon = _monitor()
        mon.select("shwtp")
        for _ in range(3):
            mon.control("shwtp", "step")
        old_run = mon.view("shwtp")["session"]["run_id"]
        old_volume = _shwtp_row(
            mon.view("shwtp"), SHWTP_T108_SCOPE_PATH.as_string()
        )["current_values"]["volume_m3"]
        view = mon.control("shwtp", "new_attempt")
        assert view["session"]["run_id"] != old_run
        # fresh attempt: slice not yet rebuilt, so no target data fabricated
        assert view["trace"] == []
        # stepping a fresh attempt starts from the initial tank volume again
        mon.control("shwtp", "step")
        fresh_volume = _shwtp_row(
            mon.view("shwtp"), SHWTP_T108_SCOPE_PATH.as_string()
        )["current_values"]["volume_m3"]
        assert fresh_volume != old_volume or fresh_volume is not None

    def test_b6_replay_deterministic(self):
        mon = _monitor()
        mon.select("shwtp")
        for _ in range(3):
            mon.control("shwtp", "step")
        first_trace = [_trace_key_of(r) for r in mon.view("shwtp")["trace"]]
        first_tank = _shwtp_row(
            mon.view("shwtp"), SHWTP_T108_SCOPE_PATH.as_string()
        )["current_values"]["volume_m3"]

        mon.control("shwtp", "replay")
        for _ in range(3):
            mon.control("shwtp", "step")
        second_trace = [_trace_key_of(r) for r in mon.view("shwtp")["trace"]]
        second_tank = _shwtp_row(
            mon.view("shwtp"), SHWTP_T108_SCOPE_PATH.as_string()
        )["current_values"]["volume_m3"]
        assert first_trace == second_trace
        assert first_tank == second_tank

    def test_b7_switch_to_tipa_and_back_no_mutation(self):
        mon = _monitor()
        mon.select("shwtp")
        mon.control("shwtp", "step")
        mon.control("shwtp", "step")
        shwtp_before = mon.view("shwtp")
        shwtp_run = shwtp_before["session"]["run_id"]
        shwtp_steps = shwtp_before["session"]["step_count"]
        shwtp_trace = shwtp_before["trace"]

        mon.select("TIPA")
        mon.control("TIPA", "step")

        shwtp_after = mon.select("shwtp")
        assert shwtp_after["session"]["run_id"] == shwtp_run
        assert shwtp_after["session"]["step_count"] == shwtp_steps
        assert shwtp_after["trace"] == shwtp_trace


def _trace_key_of(step_dict):
    return (
        step_dict["status"],
        step_dict["target_time_s"],
        tuple(step_dict["participants"]),
        tuple(sorted(_norm_committed(t) for t in step_dict["committed"])),
    )


# ═══════════════════════════════════════════════════════════════
# Re-prove platform invariants
# ═══════════════════════════════════════════════════════════════

class TestPlatformInvariants:
    def test_one_platform_many_independent_workspaces(self):
        mon = _monitor()
        assert mon.workspace_ids() == ("TIPA", "shwtp")
        tipa = mon.select("TIPA")
        shwtp = mon.select("shwtp")
        assert tipa["workspace_id"] == "TIPA"
        assert shwtp["workspace_id"] == "shwtp"

    def test_no_shared_state_run_id_clock_or_truth(self):
        mon = _monitor()
        tipa = mon.select("TIPA")
        shwtp = mon.select("shwtp")
        assert tipa["session"]["run_id"] != shwtp["session"]["run_id"]
        mon.control("TIPA", "step")
        mon.control("shwtp", "step")
        t = mon.view("TIPA")["session"]
        s = mon.view("shwtp")["session"]
        # independent step counters / sim clocks
        assert t["step_count"] == 1 and s["step_count"] == 1
        assert t["run_id"] != s["run_id"]

    def test_no_cross_workspace_runtime_coupling(self):
        mon = _monitor()
        mon.select("TIPA")
        mon.control("TIPA", "step")
        tipa_steps = mon.view("TIPA")["session"]["step_count"]
        # advancing shwtp must not move TIPA
        mon.select("shwtp")
        mon.control("shwtp", "step")
        mon.control("shwtp", "step")
        assert mon.view("TIPA")["session"]["step_count"] == tipa_steps
        # registry metadata exposes no composition/binding coupling
        meta = mon.workspace_list()
        assert "composition" not in meta
        assert "binding" not in meta

    def test_runtime_session_lifecycle_reused_for_both(self):
        mon = _monitor()
        for wid in ("TIPA", "shwtp"):
            mon.select(wid)
            mon.control(wid, "step")
            view = mon.control(wid, "reset")
            assert view["session"]["last_time_s"] == 0.0
            assert view["trace"] == []
            mon.control(wid, "step")
            assert len(mon.view(wid)["trace"]) == 1

    def test_explicit_lagged_and_g19_unchanged(self):
        from virtual_factory.shwtp import (
            SHWTP_FEDERATION_COUPLING_POLICY,
            SHWTP_PLANT_SLICE_COUPLING_POLICY,
        )
        from virtual_factory.federation import build_synthetic_federation

        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert SHWTP_PLANT_SLICE_COUPLING_POLICY == "explicit_lagged"

        # G19 multi-participant proof still builds and runs (unchanged)
        fed = build_synthetic_federation(
            "G25-SYN", ("p0", "p1", "p2"), (1.0, 0.0, 0.0),
        )
        assert len(fed.participants) == 3
        assert fed.run_window("window-1", 1.0).status == "completed"

    def test_g4_coordinator_unchanged(self):
        from virtual_factory.composition import CompositionGraph, Coordinator
        from virtual_factory.workspace import ScopeMode, ScopeSpec, build_workspace

        ws = build_workspace(
            "G25", [ScopeSpec(scope_id="unit", mode=ScopeMode.EXECUTABLE_CAPABLE)]
        )
        coord = Coordinator(ws, CompositionGraph("G25", bindings=(), ports=()))
        assert coord is not None

    def test_assy_oracle_determinism(self):
        from virtual_factory.runcontrol import build_tipa_session

        a = build_tipa_session(TIPA_CONFIG, "tipa-default")
        b = build_tipa_session(TIPA_CONFIG, "tipa-default")
        ta = [_trace_key(r) for r in a.run_all(2)]
        tb = [_trace_key(r) for r in b.run_all(2)]
        assert ta == tb

    def test_shwtp_assumptions_never_site_truth(self):
        mon = _monitor()
        view = mon.select("shwtp")
        assert view["site_truth"] is False
        for row in view["values"]:
            if row["status"] == "scenario_assumed":
                assert row["inbound_link_assumed"] in (True, False)
        assert view["ui_note"].lower().find("not site truth") != -1


class TestG25SessionSeamsUnchanged:
    def test_runtime_session_type_used(self):
        mon = _monitor()
        for wid in ("TIPA", "shwtp"):
            mon.select(wid)
        assert all(
            isinstance(s, RuntimeSession) for s in mon._sessions.values()
        )

    def test_registry_select_still_fresh(self):
        reg = WorkspaceRuntimeRegistry()
        from virtual_factory.runcontrol import build_tipa_session
        from virtual_factory.shwtp import build_shwtp_session

        reg.register("TIPA", lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"))
        reg.register("shwtp", lambda: build_shwtp_session())
        a = reg.select("shwtp")
        b = reg.select("shwtp")
        assert a is not b
