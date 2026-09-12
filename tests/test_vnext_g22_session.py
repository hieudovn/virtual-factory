"""VF-vNEXT-G22 â€” Scenario / Run / Replay Integration tests.

Proves (Issue #73 required): explicit session/run identity per Workspace;
fresh new attempt has fresh runtime state and distinct attempt/run identity;
deterministic replay from identical scenario/config reproduces equivalent
outcome/trace; reset/new-attempt/replay semantics are unambiguous; TIPA and
SH-WTP sessions are isolated; mismatched workspace/run/scenario identity fails
closed; SH-WTP assumed topology/fidelity metadata survives replay unchanged;
existing behavior remains green.
"""

from __future__ import annotations

import pytest

from virtual_factory.runcontrol import (
    RunLifecycleError,
    RuntimeSession,
    SessionError,
    build_tipa_session,
)
from virtual_factory.shwtp import build_shwtp_session, build_shwtp_g21_slice_session
from virtual_factory.runcontrol.lifecycle import RunLifecycleService
from virtual_factory.shwtp.expansion import PLANT_SLICE_SCOPES

TIPA_CONFIG = "configs/plants/tipa_assy_demo.yaml"


def _norm_transfer(tid: str) -> str:
    # Transfer ids embed the run identity ("<run_id>-w<n>::<scope>"). For
    # semantic replay equivalence, strip the run-specific prefix and keep the
    # window number + producing scope.
    return "w" + tid.split("-w", 1)[1] if "-w" in tid else tid


def _trace_key(result):
    return (result.status, result.target_time_s, tuple(result.participants),
            tuple(sorted(_norm_transfer(t) for t in result.committed)))


def _t108_volume(session):
    bridge = session.record.bridge
    assert bridge is not None
    t108 = bridge.slice.participants["shwtp/line1/l1_t108"]
    return t108._runtime.state.volume_m3


class TestTipaSession:
    def test_tipa_deterministic_replay(self):
        s = build_tipa_session(TIPA_CONFIG, "tipa-default")
        t1 = s.run_all(3)
        s.replay()
        t2 = s.run_all(3)
        assert [_trace_key(r) for r in t1] == [_trace_key(r) for r in t2]

    def test_tipa_session_identity(self):
        s = build_tipa_session(TIPA_CONFIG, "tipa-default")
        assert s.workspace_id == "TIPA"
        assert s.run_id
        assert s.scenario_id == "tipa-default"


class TestShwtpSession:
    def test_shwtp_deterministic_replay(self):
        s = build_shwtp_g21_slice_session()
        t1 = s.run_all(4)
        s.replay()
        t2 = s.run_all(4)
        assert [_trace_key(r) for r in t1] == [_trace_key(r) for r in t2]

    def test_shwtp_session_identity(self):
        s = build_shwtp_g21_slice_session()
        assert s.workspace_id == "shwtp"
        assert s.run_id
        assert s.scenario_id == "shwtp-g21-slice"

    def test_shwtp_overlay_and_fidelity_survive_replay(self):
        s = build_shwtp_g21_slice_session()
        s.advance()
        before_overlay = s.record.bridge.slice.overlay.serialize()
        s.replay()
        s.advance()
        after_overlay = s.record.bridge.slice.overlay.serialize()
        assert after_overlay == before_overlay
        assert s.record.bridge.slice.scopes == PLANT_SLICE_SCOPES


class TestFreshAttempt:
    def test_new_attempt_fresh_identity_and_state(self):
        s = build_shwtp_g21_slice_session()
        s.advance()
        s.advance()
        old_run = s.run_id
        old_bridge = s.record.bridge
        old_volume = _t108_volume(s)
        new_run = s.new_attempt()
        assert new_run != old_run
        # Fresh attempt: bridge not yet rebuilt (lazy), no state carry-over.
        assert s.record.bridge is None
        s.advance()
        assert s.record.bridge is not old_bridge
        assert _t108_volume(s) != old_volume

    def test_reset_same_identity_fresh_state(self):
        s = build_shwtp_g21_slice_session()
        s.advance()
        s.advance()
        run_before = s.run_id
        s.reset()
        assert s.run_id == run_before          # same run identity
        assert len(s.trace()) == 0             # trace cleared
        s.advance()
        assert len(s.trace()) == 1


class TestIsolation:
    def test_tipa_and_shwtp_isolated(self):
        tipa = build_tipa_session(TIPA_CONFIG, "tipa-default")
        shwtp = build_shwtp_g21_slice_session()
        assert tipa.workspace_id == "TIPA"
        assert shwtp.workspace_id == "shwtp"
        assert tipa.run_id != shwtp.run_id
        tipa.advance()
        shwtp.advance()
        # No shared truth: independent services, independent bridges.
        assert tipa.record.bridge is not shwtp.record.bridge


class TestFailClosed:
    def test_invalid_workspace_fails_closed(self):
        with pytest.raises(SessionError):
            build_tipa_session(TIPA_CONFIG, "tipa-default", workspace_id="WRONG")

    def test_invalid_run_id_fails_closed(self):
        s = build_shwtp_g21_slice_session()
        with pytest.raises(RunLifecycleError):
            s._service.step("bogus-run-id")

    def test_empty_scenario_fails_closed(self):
        # RuntimeSession requires a non-empty scenario_id.
        from virtual_factory.shwtp.expansion import build_shwtp_plant_slice_workspace
        from virtual_factory.runcontrol import RunLifecycleService
        from virtual_factory.shwtp.bridge import ShwtpExecutionBridge
        from virtual_factory.shwtp.expansion import build_shwtp_plant_slice
        ws = build_shwtp_plant_slice_workspace()
        service = RunLifecycleService(
            ws, lambda: ShwtpExecutionBridge(lambda: build_shwtp_plant_slice())
        )
        with pytest.raises(SessionError):
            RuntimeSession(service, "shwtp", "")


class TestG21G20G19G18G14G15Unchanged:
    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import (
            SHWTP_FEDERATION_COUPLING_POLICY,
            SHWTP_PLANT_SLICE_COUPLING_POLICY,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert SHWTP_PLANT_SLICE_COUPLING_POLICY == "explicit_lagged"

    def test_g21_slice_still_builds(self):
        from virtual_factory.shwtp import build_shwtp_plant_slice
        slice_ = build_shwtp_plant_slice()
        outcome = slice_.run_window("window-1")
        assert outcome.status == "completed"

    def test_g18_overlay_unchanged(self):
        from virtual_factory.shwtp.overlay import build_shwtp_t108_dist_p108_overlay
        overlay = build_shwtp_t108_dist_p108_overlay()
        assert overlay.edge_count == 1

    def test_g14a_projection_unchanged(self):
        from virtual_factory.shwtp import build_shwtp_f01_projection
        proj = build_shwtp_f01_projection()
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

