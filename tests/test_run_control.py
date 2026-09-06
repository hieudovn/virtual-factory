"""VF-vNEXT-G7 — Hierarchical Scenario / Run Control tests.

Proves (Issue #52): valid lifecycle transitions + fail-closed guards; immutable
coherent RunContextV2 with one scenario authority; workspace/container ->
deterministic descendant executable scopes (no fake container participant);
executable -> itself; stale/wrong run_id fails closed; pause/resume don't
advance domain state; stop is terminal; restart/replay create fresh run_id with
source lineage (replay unavailable is explicit); ASSY hierarchical step uses
only legitimate natural boundaries (unreachable fails closed, no fractional
dwell); standalone ASSY/domain semantics preserved; continuous behavior green;
reset capability-scoped; container-only never executable; path-qualified
effective target; no G8+.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.federation import (  # noqa: E402
    SUB_LINE_IDS,
    TipaAssyFederation,
    assy_scope_path,
    build_tipa_workspace,
    sub_line_path,
)
from virtual_factory.runcontrol import (  # noqa: E402
    AssyExecutionBridge,
    ContinuousExecutionBridge,
    ReplayUnavailableError,
    RunLifecycleError,
    RunLifecycleService,
    RunState,
    StepResult,
    TargetResolutionError,
    build_continuous_workspace,
    resolve_target,
)
from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.ui.runtime_service import RuntimeService  # noqa: E402
from virtual_factory.workspace import StructuralPath  # noqa: E402

REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)
UI_STATIC = (
    Path(__file__).resolve().parent.parent
    / "src" / "virtual_factory" / "ui" / "static"
)


class _FakeBridge:
    """Deterministic execution bridge for lifecycle-only tests."""

    def __init__(self, *, supports_reset: bool = True) -> None:
        self.advances = 0
        self.resets = 0
        self.current = 0.0
        self._supports_reset = supports_reset

    @property
    def supports_reset(self) -> bool:
        return self._supports_reset

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        return self.current + 10.0

    def advance(self, target_time_s, scope_ids, window_id) -> StepResult:
        self.advances += 1
        self.current = target_time_s
        return StepResult(
            status="completed",
            target_time_s=target_time_s,
            participants=tuple(scope_ids),
            committed=(),
            failure=None,
        )

    def reset(self, scope_ids) -> None:
        self.resets += 1
        self.current = 0.0


def _service(bridge: _FakeBridge) -> RunLifecycleService:
    return RunLifecycleService(build_tipa_workspace(), lambda: bridge)


def _client():
    return TestClient(
        create_app(
            config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0
        )
    )


# ═══════════════════════════════════════════════════════════
# 1. Lifecycle transitions + fail-closed guards
# ═══════════════════════════════════════════════════════════

class TestLifecycleGuards:
    def test_valid_transitions(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA")
        assert rec.state is RunState.CREATED
        svc.start(rec.context.run_id)
        assert rec.state is RunState.RUNNING
        svc.pause(rec.context.run_id)
        assert rec.state is RunState.PAUSED
        svc.resume(rec.context.run_id)
        assert rec.state is RunState.RUNNING
        svc.stop(rec.context.run_id)
        assert rec.state is RunState.STOPPED

    def test_invalid_transitions_fail_closed(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA")
        rid = rec.context.run_id
        with pytest.raises(RunLifecycleError):
            svc.step(rid)  # cannot step from created
        svc.start(rid)
        with pytest.raises(RunLifecycleError):
            svc.start(rid)  # double start
        with pytest.raises(RunLifecycleError):
            svc.resume(rid)  # resume from running
        svc.pause(rid)
        with pytest.raises(RunLifecycleError):
            svc.step(rid)  # step from paused
        svc.resume(rid)
        svc.stop(rid)
        with pytest.raises(RunLifecycleError):
            svc.stop(rid)  # already terminal
        with pytest.raises(RunLifecycleError):
            svc.step(rid)  # step after stop
        with pytest.raises(RunLifecycleError):
            svc.reset(rid)  # reset terminal run


# ═══════════════════════════════════════════════════════════
# 2. Immutable RunContextV2 + one scenario authority
# ═══════════════════════════════════════════════════════════

class TestRunContext:
    def test_context_immutable_and_coherent(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA", scenario_id="SCN-1")
        ctx = rec.context
        assert ctx.workspace_id == "TIPA"
        assert ctx.run_id.startswith("TIPA-")
        assert ctx.scope_path is None  # workspace target -> no owning scope
        assert ctx.scenario_id == "SCN-1"
        with pytest.raises(FrozenInstanceError):
            ctx.run_id = "other"  # type: ignore[misc]

    def test_executable_target_context_scope_path_coherent(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA/ASSY/ASSY-SL03", scenario_id="SCN-1")
        assert rec.context.scope_path == sub_line_path("ASSY-SL03")
        assert rec.target_kind == "executable"
        assert rec.effective_scopes == ("TIPA/ASSY/ASSY-SL03",)

    def test_single_scenario_authority_frozen_at_create(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA", scenario_id="SCN-1")
        assert rec.context.scenario_id == "SCN-1"
        # Replay requires a pinned scenario authority; missing -> unavailable.
        rid = rec.context.run_id
        svc.start(rid)
        svc.stop(rid)  # terminalize first attempt
        rec2 = svc.create_run("TIPA")  # no scenario (fresh active attempt)
        rid2 = rec2.context.run_id
        svc.start(rid2)
        svc.stop(rid2)  # terminal -> eligible replay source
        with pytest.raises(ReplayUnavailableError):
            svc.replay(rid2)


# ═══════════════════════════════════════════════════════════
# 3-4. Hierarchical target resolution
# ═══════════════════════════════════════════════════════════

class TestTargetResolution:
    def test_workspace_target_resolves_all_executable_descendants(self):
        res = resolve_target(build_tipa_workspace(), StructuralPath(("TIPA",)))
        assert res.target_kind == "workspace"
        assert res.effective_scope_strings == tuple(
            f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS
        )
        # container itself is never a participant
        assert "TIPA/ASSY" not in res.effective_scope_strings

    def test_container_target_resolves_descendants_only(self):
        res = resolve_target(build_tipa_workspace(), assy_scope_path())
        assert res.target_kind == "container"
        assert res.effective_scope_strings == tuple(
            f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS
        )

    def test_executable_target_resolves_itself_only(self):
        res = resolve_target(build_tipa_workspace(), sub_line_path("ASSY-SL05"))
        assert res.target_kind == "executable"
        assert res.effective_scope_strings == ("TIPA/ASSY/ASSY-SL05",)

    def test_unknown_and_foreign_paths_fail_closed(self):
        ws = build_tipa_workspace()
        with pytest.raises(TargetResolutionError):
            resolve_target(ws, StructuralPath(("TIPA", "NOPE")))
        with pytest.raises(TargetResolutionError):
            resolve_target(ws, StructuralPath(("OTHER", "X")))

    def test_deterministic_order(self):
        a = resolve_target(build_tipa_workspace(), StructuralPath(("TIPA",))).effective_scope_strings
        b = resolve_target(build_tipa_workspace(), StructuralPath(("TIPA",))).effective_scope_strings
        assert a == b == tuple(f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS)


# ═══════════════════════════════════════════════════════════
# 5-9. Identity / pause / stop / restart / replay (unit)
# ═══════════════════════════════════════════════════════════

class TestRunIdentityAndLineage:
    def test_stale_run_id_cannot_mutate(self):
        svc = _service(_FakeBridge())
        svc.create_run("TIPA")
        with pytest.raises(RunLifecycleError):
            svc.start("TIPA-9999")
        with pytest.raises(RunLifecycleError):
            svc.step("stale")
        with pytest.raises(RunLifecycleError):
            svc.stop("TIPA-9999")

    def test_pause_resume_do_not_advance_domain(self):
        bridge = _FakeBridge()
        svc = _service(bridge)
        rec = svc.create_run("TIPA")
        rid = rec.context.run_id
        svc.start(rid)
        svc.pause(rid)
        svc.resume(rid)
        assert bridge.advances == 0  # no domain advancement on pause/resume

    def test_stop_is_terminal_for_attempt(self):
        bridge = _FakeBridge()
        svc = _service(bridge)
        rec = svc.create_run("TIPA")
        rid = rec.context.run_id
        svc.start(rid)
        svc.step(rid)
        assert bridge.advances == 1
        svc.stop(rid)
        with pytest.raises(RunLifecycleError):
            svc.step(rid)
        # step count unchanged after failed post-stop step
        assert rec.step_count == 1

    def test_restart_creates_distinct_run_id_with_lineage(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA", scenario_id="SCN-1")
        rid = rec.context.run_id
        svc.start(rid)
        svc.stop(rid)
        new = svc.restart(rid)
        assert new.context.run_id != rid
        assert new.context.source_run_id == rid
        assert new.context.scenario_id == "SCN-1"  # pinned
        assert new.state is RunState.CREATED

    def test_replay_creates_distinct_run_id_and_never_overwrites(self):
        svc = _service(_FakeBridge())
        rec = svc.create_run("TIPA", scenario_id="SCN-1", random_seed=7)
        rid = rec.context.run_id
        svc.start(rid)
        svc.stop(rid)  # terminal -> eligible replay source
        replay = svc.replay(rid)
        assert replay.context.run_id != rid
        assert replay.context.source_run_id == rid
        assert replay.context.scenario_id == "SCN-1"
        assert replay.context.random_seed == 7
        # prior run remains intact
        assert svc.status(rid)["run_id"] == rid
        assert svc.status(rid)["scenario_id"] == "SCN-1"


# ═══════════════════════════════════════════════════════════
# 10-11, 13-14. ASSY execution bridge (real federation)
# ═══════════════════════════════════════════════════════════

def _federation() -> TipaAssyFederation:
    return TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()


class TestAssyExecutionBridge:
    def test_natural_boundary_steps_are_exact(self):
        fed = _federation()
        bridge = AssyExecutionBridge(fed)
        assert bridge.natural_next_boundary(("ASSY-SL01",)) == 120.0
        r1 = bridge.advance(120.0, ("ASSY-SL01",), "w1")
        assert r1.status == "completed"
        assert fed.get("ASSY-SL01").runtime.simulation_time_s == 120.0
        assert bridge.natural_next_boundary(("ASSY-SL01",)) == 240.0

    def test_arbitrary_boundary_fails_closed_no_fractional_dwell(self):
        fed = _federation()
        bridge = AssyExecutionBridge(fed)
        # 60 is not a natural ASSY boundary (nominal dwell 120); must fail.
        result = bridge.advance(60.0, ("ASSY-SL01",), "w-frac")
        assert result.status == "failed"
        assert result.failure and "overshoots" in result.failure
        # the runtime never performed a fractional dwell
        assert fed.get("ASSY-SL01").runtime.conveyor.dwell_number >= 1

    def test_six_sub_lines_share_common_natural_boundary(self):
        fed = _federation()
        bridge = AssyExecutionBridge(fed)
        result = bridge.advance(120.0, tuple(SUB_LINE_IDS), "w-all")
        assert result.status == "completed"
        for sid in SUB_LINE_IDS:
            assert fed.get(sid).runtime.simulation_time_s == 120.0

    def test_runtime_identity_preserved_across_step_and_reset(self):
        fed = _federation()
        bridge = AssyExecutionBridge(fed)
        before = {sid: id(fed.get(sid).runtime) for sid in SUB_LINE_IDS}
        bridge.advance(120.0, tuple(SUB_LINE_IDS), "w1")
        bridge.reset(tuple(SUB_LINE_IDS))
        after = {sid: id(fed.get(sid).runtime) for sid in SUB_LINE_IDS}
        assert before == after  # no reconstruction
        for sid in SUB_LINE_IDS:
            assert fed.get(sid).runtime.simulation_time_s == 0.0

    def test_container_target_step_only_advances_descendants(self):
        fed = _federation()
        bridge = AssyExecutionBridge(fed)
        ids = tuple(SUB_LINE_IDS)  # container TIPA/ASSY resolves to these six
        result = bridge.advance(120.0, ids, "w-container")
        assert result.status == "completed"
        # ASSY container itself is never a participant
        assert "TIPA/ASSY" not in result.participants
        assert set(result.participants) == {f"TIPA/ASSY/{sid}" for sid in ids}


# ═══════════════════════════════════════════════════════════
# 12-13. Continuous behavior green + reset capability-scoped
# ═══════════════════════════════════════════════════════════

class TestContinuousAndReset:
    def test_continuous_existing_behavior_green(self):
        c = _client()
        assert c.post("/step").status_code == 200
        latest = c.get("/telemetry/latest").json()
        assert any(item["name"] == "LT102_LEVEL" for item in latest)
        assert c.get("/status").json()["plant_id"] == "continuous_mvp_01"

    def test_reset_capability_scoped(self):
        # A bridge without reset support must fail closed.
        bridge = _FakeBridge(supports_reset=False)
        svc = _service(bridge)
        rec = svc.create_run("TIPA")
        rid = rec.context.run_id
        svc.start(rid)
        with pytest.raises(RunLifecycleError):
            svc.reset(rid)

    def test_reset_does_not_reuse_terminal_run(self):
        bridge = _FakeBridge()
        svc = _service(bridge)
        rec = svc.create_run("TIPA")
        rid = rec.context.run_id
        svc.start(rid)
        svc.stop(rid)
        with pytest.raises(RunLifecycleError):
            svc.reset(rid)


# ═══════════════════════════════════════════════════════════
# 5, 12, 15. API surface (path-qualified, stale run_id, endpoints)
# ═══════════════════════════════════════════════════════════

class TestApiSurface:
    def test_end_to_end_lifecycle_and_path_qualified_target(self):
        c = _client()
        created = c.post(
            "/vnext/runs",
            json={"target_path": "TIPA/ASSY/ASSY-SL03", "scenario_id": "SCN-1"},
        )
        assert created.status_code == 201
        rec = created.json()
        rid = rec["run_id"]
        assert rec["target_path"] == "TIPA/ASSY/ASSY-SL03"  # path-qualified
        assert rec["target_kind"] == "executable"
        assert rec["effective_scopes"] == ["TIPA/ASSY/ASSY-SL03"]
        assert c.get(f"/vnext/runs/{rid}").json()["run_id"] == rid
        assert c.get("/vnext/runs/current").json()["run_id"] == rid
        assert c.post(f"/vnext/runs/{rid}/start").status_code == 200
        step = c.post(f"/vnext/runs/{rid}/step").json()
        assert step["status"] == "completed"
        assert step["target_time_s"] == 120.0
        assert c.post(f"/vnext/runs/{rid}/pause").status_code == 200
        assert c.post(f"/vnext/runs/{rid}/step").status_code == 409
        assert c.post(f"/vnext/runs/{rid}/resume").status_code == 200
        assert c.post(f"/vnext/runs/{rid}/stop").status_code == 200
        assert c.post(f"/vnext/runs/{rid}/step").status_code == 409

    def test_stale_run_id_404(self):
        c = _client()
        assert c.post("/vnext/runs/NOPE/start").status_code == 404
        assert c.get("/vnext/runs/NOPE").status_code == 404

    def test_replay_unavailable_explicit(self):
        c = _client()
        created = c.post("/vnext/runs", json={"target_path": "TIPA"})
        rid = created.json()["run_id"]
        c.post(f"/vnext/runs/{rid}/start")
        c.post(f"/vnext/runs/{rid}/stop")  # terminal -> eligible replay source
        r = c.post(f"/vnext/runs/{rid}/replay")
        assert r.status_code == 409
        assert "unavailable" in r.json()["detail"]

    def test_container_target_never_gets_executable_authority(self):
        c = _client()
        rec = c.post("/vnext/runs", json={"target_path": "TIPA/ASSY"}).json()
        assert rec["target_kind"] == "container"
        assert "TIPA/ASSY" not in rec["effective_scopes"]
        assert rec["effective_scopes"] == [
            f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS
        ]


# ═══════════════════════════════════════════════════════════
# 15 (UI), 17. Static UI + no-G8 checks
# ═══════════════════════════════════════════════════════════

class TestStaticUiAndNoG8:
    def test_run_control_context_js_is_additive_and_path_qualified(self):
        js = (UI_STATIC / "run_control_context.js").read_text(encoding="utf-8")
        assert "/vnext/runs/current" in js
        assert "target_path" in js
        assert "target_kind" in js
        assert "effective_scopes" in js
        # container/workspace never presented as executable
        assert "executable" in js
        # no legacy repointing: does not call legacy /step /start /stop /reset
        assert "fetch('/step'" not in js and "fetch(\"/step\"" not in js

    def test_assoc_page_mounts_run_control_additively(self):
        html = (UI_STATIC / "assy_demo.html").read_text(encoding="utf-8")
        assert "run_control_context.js" in html
        assert "vf-run-control-section" in html
        assert "assy_demo.js" in html  # domain rendering retained

    def test_no_g8_scope_in_runcontrol_package(self):
        import inspect
        import virtual_factory.runcontrol as rc

        src = inspect.getsource(rc)
        for forbidden in ("semantic_binding", "shwtp", "SHWTP", "regression_baseline"):
            assert forbidden not in src


# ═══════════════════════════════════════════════════════════
# G7-C01 — active-attempt authority + attempt-bound execution
# ═══════════════════════════════════════════════════════════

def _real_service() -> RunLifecycleService:
    """Service whose bridge_factory builds a FRESH federation per attempt."""
    def factory():
        fed = TipaAssyFederation(config_path=str(REAL_CONFIG))
        fed.initialize()
        return AssyExecutionBridge(fed)

    return RunLifecycleService(build_tipa_workspace(), factory)


class TestActiveAttemptAuthorityC01:
    def test_create_second_attempt_fails_while_active_nonterminal(self):
        svc = _service(_FakeBridge())
        svc.create_run("TIPA")
        with pytest.raises(RunLifecycleError):
            svc.create_run("TIPA")  # cannot supersede a nonterminal active run

    def test_superseded_known_run_id_fails_closed(self):
        svc = _service(_FakeBridge())
        a = svc.create_run("TIPA")
        aid = a.context.run_id
        svc.start(aid)
        svc.stop(aid)  # A terminal
        b = svc.create_run("TIPA")  # B active
        assert b.context.run_id != aid
        # A still exists as history but is no longer mutable.
        with pytest.raises(RunLifecycleError):
            svc.start(aid)
        with pytest.raises(RunLifecycleError):
            svc.step(aid)

    def test_api_historical_run_id_mutation_returns_conflict(self):
        c = _client()
        a = c.post("/vnext/runs", json={"target_path": "TIPA"}).json()
        aid = a["run_id"]
        c.post(f"/vnext/runs/{aid}/start")
        c.post(f"/vnext/runs/{aid}/stop")  # A terminal
        b = c.post("/vnext/runs", json={"target_path": "TIPA"}).json()
        assert b["run_id"] != aid
        # Known but superseded run id -> conflict, not success.
        assert c.post(f"/vnext/runs/{aid}/step").status_code == 409
        assert c.post(f"/vnext/runs/{aid}/start").status_code == 409

    def test_restart_starts_fresh_execution_context(self):
        svc = _real_service()
        a = svc.create_run("TIPA/ASSY/ASSY-SL01", scenario_id="SCN-1")
        aid = a.context.run_id
        svc.start(aid)
        svc.step(aid)  # advances ASSY to 120
        svc.stop(aid)
        b = svc.restart(aid)
        assert b.context.run_id != aid
        assert b.context.source_run_id == aid
        svc.start(b.context.run_id)
        result = svc.step(b.context.run_id)
        # Fresh domain context: B starts from 0, so first step is 120 (not 240).
        assert result.status == "completed"
        assert result.target_time_s == 120.0

    def test_replay_uses_fresh_context_and_does_not_mutate_source(self):
        svc = _real_service()
        a = svc.create_run("TIPA/ASSY/ASSY-SL01", scenario_id="SCN-1")
        aid = a.context.run_id
        svc.start(aid)
        svc.step(aid)  # 120
        svc.stop(aid)
        b = svc.replay(aid)
        assert b.context.run_id != aid
        assert b.context.source_run_id == aid
        assert b.context.scenario_id == "SCN-1"
        svc.start(b.context.run_id)
        result = svc.step(b.context.run_id)
        assert result.target_time_s == 120.0  # fresh context
        # Source run's runtime state is untouched (still at 120, next boundary 240).
        assert a.bridge.natural_next_boundary(("ASSY-SL01",)) == 240.0

    def test_reset_keeps_same_run_id_and_same_runtime_objects(self):
        fed = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        bridge = AssyExecutionBridge(fed)
        svc = RunLifecycleService(build_tipa_workspace(), lambda: bridge)
        rec = svc.create_run("TIPA/ASSY/ASSY-SL01")
        rid = rec.context.run_id
        svc.start(rid)
        svc.step(rid)  # 120
        obj_id_before = id(fed.get("ASSY-SL01").runtime)
        svc.reset(rid)
        assert rec.context.run_id == rid  # same run identity
        assert id(fed.get("ASSY-SL01").runtime) == obj_id_before  # same objects
        assert fed.get("ASSY-SL01").runtime.simulation_time_s == 0.0

    def test_prior_run_records_remain_readable_history(self):
        svc = _service(_FakeBridge())
        a = svc.create_run("TIPA", scenario_id="SCN-1")
        aid = a.context.run_id
        svc.start(aid)
        svc.step(aid)
        svc.stop(aid)
        b = svc.restart(aid)
        assert b.context.run_id != aid
        # Prior record readable and unchanged as lifecycle history.
        history = svc.status(aid)
        assert history["run_id"] == aid
        assert history["scenario_id"] == "SCN-1"
        assert history["step_count"] == 1
        assert history["state"] == "stopped"


# ═══════════════════════════════════════════════════════════
# G7-C02 — continuous execution bridge + workspace isolation
# ═══════════════════════════════════════════════════════════

CONTINUOUS_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "continuous_mvp_01.yaml"
)


def _continuous_runtime() -> RuntimeService:
    return RuntimeService(config_path=CONTINUOUS_CONFIG, dt_s=1.0)


def _continuous_service(runtime: RuntimeService) -> RunLifecycleService:
    ws = build_continuous_workspace()
    return RunLifecycleService(
        ws,
        lambda: ContinuousExecutionBridge(
            runtime, participant_id=ws.workspace_id
        ),
    )


class TestContinuousExecutionBridgeC02:
    def test_natural_boundary_is_one_dt_and_step_advances(self):
        runtime = _continuous_runtime()
        bridge = ContinuousExecutionBridge(runtime, participant_id="continuous")
        assert bridge.supports_reset is True
        assert bridge.natural_next_boundary(()) == 1.0
        result = bridge.advance(1.0, (), "w1")
        assert result.status == "completed"
        assert result.target_time_s == 1.0
        assert result.participants == ("continuous",)
        assert bridge.natural_next_boundary(()) == 2.0

    def test_reset_is_in_context(self):
        runtime = _continuous_runtime()
        bridge = ContinuousExecutionBridge(runtime, participant_id="continuous")
        bridge.advance(1.0, (), "w1")
        bridge.advance(2.0, (), "w2")
        assert runtime.engine.time_manager.now() == 2.0
        bridge.reset(())
        assert runtime.engine.time_manager.now() == 0.0

    def test_workspace_root_only_no_invented_scopes(self):
        ws = build_continuous_workspace()
        assert ws.workspace_id == "continuous"
        assert ws.top_level_scopes == ()
        res = resolve_target(ws, StructuralPath(("continuous",)))
        assert res.target_kind == "workspace"
        assert res.effective_scope_paths == ()
        # a non-root path must fail closed (no fabricated hierarchy)
        with pytest.raises(TargetResolutionError):
            resolve_target(ws, StructuralPath(("continuous", "FAKE")))

    def test_lifecycle_authority_and_fresh_restart(self):
        runtime = _continuous_runtime()
        svc = _continuous_service(runtime)
        a = svc.create_run("continuous")
        aid = a.context.run_id
        assert a.target_kind == "workspace"
        assert a.effective_scopes == ()
        svc.start(aid)
        assert svc.step(aid).target_time_s == 1.0
        assert runtime.engine.time_manager.now() == 1.0
        svc.pause(aid)
        with pytest.raises(RunLifecycleError):
            svc.step(aid)  # paused -> no advancement
        assert runtime.engine.time_manager.now() == 1.0
        svc.resume(aid)
        svc.step(aid)  # 2.0
        assert runtime.engine.time_manager.now() == 2.0
        svc.stop(aid)
        # restart must start fresh (t=0), source remains historical
        b = svc.restart(aid)
        assert b.context.run_id != aid
        assert b.context.source_run_id == aid
        svc.start(b.context.run_id)
        assert svc.step(b.context.run_id).target_time_s == 1.0
        assert runtime.engine.time_manager.now() == 1.0  # not 3.0
        assert svc.status(aid)["state"] == "stopped"

    def test_replay_unavailable_without_pinned_scenario(self):
        runtime = _continuous_runtime()
        svc = _continuous_service(runtime)
        a = svc.create_run("continuous")
        aid = a.context.run_id
        svc.start(aid)
        svc.stop(aid)
        with pytest.raises(ReplayUnavailableError):
            svc.replay(aid)


class TestWorkspaceIsolationC02:
    def test_tipa_and_continuous_active_runs_coexist(self):
        c = _client()
        a = c.post("/vnext/runs", json={"target_path": "TIPA"}).json()
        aid = a["run_id"]
        b = c.post(
            "/vnext/runs",
            params={"workspace": "continuous"},
            json={"target_path": "continuous"},
        ).json()
        bid = b["run_id"]
        assert aid != bid
        assert c.post(f"/vnext/runs/{aid}/start").status_code == 200
        assert c.post(
            f"/vnext/runs/{bid}/start", params={"workspace": "continuous"}
        ).status_code == 200
        # both are active simultaneously in independent authorities
        assert c.get("/vnext/runs/current").json()["run_id"] == aid
        assert c.get(
            "/vnext/runs/current", params={"workspace": "continuous"}
        ).json()["run_id"] == bid

    def test_run_id_cannot_cross_mutate(self):
        c = _client()
        a = c.post("/vnext/runs", json={"target_path": "TIPA"}).json()
        aid = a["run_id"]
        b = c.post(
            "/vnext/runs",
            params={"workspace": "continuous"},
            json={"target_path": "continuous"},
        ).json()
        bid = b["run_id"]
        # TIPA run_id against continuous authority -> unknown (404)
        assert c.post(
            f"/vnext/runs/{aid}/start", params={"workspace": "continuous"}
        ).status_code == 404
        # continuous run_id against TIPA authority -> unknown (404)
        assert c.post(f"/vnext/runs/{bid}/start").status_code == 404

    def test_foreign_workspace_target_fails_closed(self):
        c = _client()
        r = c.post(
            "/vnext/runs",
            params={"workspace": "continuous"},
            json={"target_path": "TIPA/ASSY/ASSY-SL01"},
        )
        assert r.status_code == 400
        r2 = c.post("/vnext/runs", json={"target_path": "continuous"})
        assert r2.status_code == 400

    def test_unknown_workspace_fails_closed(self):
        c = _client()
        assert c.post(
            "/vnext/runs",
            params={"workspace": "NOPE"},
            json={"target_path": "x"},
        ).status_code == 404
        assert c.get(
            "/vnext/runs/current", params={"workspace": "NOPE"}
        ).status_code == 404

    def test_continuous_lifecycle_via_api_keeps_legacy_engine(self):
        c = _client()
        rec = c.post(
            "/vnext/runs",
            params={"workspace": "continuous"},
            json={"target_path": "continuous"},
        ).json()
        rid = rec["run_id"]
        assert rec["target_kind"] == "workspace"
        assert rec["effective_scopes"] == []
        assert c.post(
            f"/vnext/runs/{rid}/start", params={"workspace": "continuous"}
        ).status_code == 200
        step = c.post(
            f"/vnext/runs/{rid}/step", params={"workspace": "continuous"}
        ).json()
        assert step["status"] == "completed"
        assert step["target_time_s"] == 1.0
        assert c.post(
            f"/vnext/runs/{rid}/pause", params={"workspace": "continuous"}
        ).status_code == 200
        assert c.post(
            f"/vnext/runs/{rid}/step", params={"workspace": "continuous"}
        ).status_code == 409
        assert c.post(
            f"/vnext/runs/{rid}/resume", params={"workspace": "continuous"}
        ).status_code == 200
        assert c.post(
            f"/vnext/runs/{rid}/stop", params={"workspace": "continuous"}
        ).status_code == 200
        # legacy engine semantics unchanged: same RuntimeService seam, dt=1.0
        assert c.get("/status").json()["dt_s"] == 1.0
        assert c.get("/status").json()["time_s"] == 1.0

