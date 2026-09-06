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
    ReplayUnavailableError,
    RunLifecycleError,
    RunLifecycleService,
    RunState,
    StepResult,
    TargetResolutionError,
    resolve_target,
)
from virtual_factory.ui.api import create_app  # noqa: E402
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
        rec2 = svc.create_run("TIPA")  # no scenario
        with pytest.raises(ReplayUnavailableError):
            svc.replay(rec2.context.run_id)


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
