"""VF-vNEXT-G23 — Multi-Workspace Runtime Selection tests.

Proves (Issue #74 required): deterministic enumeration of TIPA + shwtp;
selecting TIPA returns a TIPA RuntimeSession; selecting shwtp returns a SH-WTP
RuntimeSession; two Workspace sessions are isolated; switching selection does
not mutate the inactive session; a fresh independent session can be created for
the same Workspace; unknown Workspace fails closed; registration order does not
affect enumeration/selection; no cross-workspace runtime coupling is
introduced; G22/G21/G20/G19/G18 + TIPA ASSY + canonical baseline remain green.
"""

from __future__ import annotations

import pytest

from virtual_factory.runcontrol import (
    RuntimeSession,
    WorkspaceRegistryError,
    WorkspaceRuntimeRegistry,
    build_tipa_session,
)
from virtual_factory.shwtp import build_shwtp_plant_slice, build_shwtp_session

TIPA_CONFIG = "configs/plants/tipa_assy_demo.yaml"


def _make_registry() -> WorkspaceRuntimeRegistry:
    reg = WorkspaceRuntimeRegistry()
    # Register shwtp FIRST to exercise registration-order independence.
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


class TestEnumeration:
    def test_enumerate_tipa_and_shwtp(self):
        reg = _make_registry()
        assert reg.workspace_ids() == ("TIPA", "shwtp")
        infos = reg.enumerate()
        assert [i.workspace_id for i in infos] == ["TIPA", "shwtp"]

    def test_registration_order_does_not_affect(self):
        a = WorkspaceRuntimeRegistry()
        a.register("shwtp", lambda: build_shwtp_session())
        a.register("TIPA", lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"))
        b = WorkspaceRuntimeRegistry()
        b.register("TIPA", lambda: build_tipa_session(TIPA_CONFIG, "tipa-default"))
        b.register("shwtp", lambda: build_shwtp_session())
        assert a.workspace_ids() == b.workspace_ids() == ("TIPA", "shwtp")
        assert a.select("TIPA").workspace_id == b.select("TIPA").workspace_id == "TIPA"
        assert a.select("shwtp").workspace_id == b.select("shwtp").workspace_id == "shwtp"


class TestSelection:
    def test_select_tipa_returns_tipa_session(self):
        reg = _make_registry()
        session = reg.select("TIPA")
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "TIPA"

    def test_select_shwtp_returns_shwtp_session(self):
        reg = _make_registry()
        session = reg.select("shwtp")
        assert isinstance(session, RuntimeSession)
        assert session.workspace_id == "shwtp"

    def test_select_does_not_activate_other_workspace(self):
        reg = _make_registry()
        tipa = reg.select("TIPA")
        assert tipa.scenario_id == "tipa-default"
        shwtp = reg.select("shwtp")
        assert shwtp.scenario_id == "shwtp-g21-slice"


class TestIsolation:
    def test_two_workspace_sessions_isolated(self):
        reg = _make_registry()
        tipa = reg.select("TIPA")
        shwtp = reg.select("shwtp")
        assert tipa is not shwtp
        assert tipa.workspace_id != shwtp.workspace_id
        tipa.advance()
        shwtp.advance()
        assert tipa.record.bridge is not shwtp.record.bridge

    def test_switching_does_not_mutate_inactive_session(self):
        reg = _make_registry()
        tipa = reg.select("TIPA")
        tipa.run_all(2)
        trace_before = len(tipa.trace())
        # Switch to the other Workspace and advance it.
        shwtp = reg.select("shwtp")
        shwtp.run_all(3)
        # The inactive TIPA session is untouched.
        assert len(tipa.trace()) == trace_before
        assert tipa.state.value in ("running", "created")

    def test_fresh_independent_session_same_workspace(self):
        reg = _make_registry()
        a = reg.select("shwtp")
        b = reg.select("shwtp")
        assert a is not b
        a.run_all(2)
        assert len(a.trace()) == 2
        assert len(b.trace()) == 0  # independent instance

    def test_no_cross_workspace_coupling(self):
        reg = _make_registry()
        tipa = reg.select("TIPA")
        shwtp = reg.select("shwtp")
        tipa.advance()
        shwtp.advance()
        # No shared runtime objects, no graph/coupling in registry metadata.
        assert tipa.record.bridge is not shwtp.record.bridge
        meta = reg.metadata()
        assert "composition" not in meta
        assert "binding" not in meta


class TestFailClosed:
    def test_unknown_workspace_fails_closed(self):
        reg = _make_registry()
        with pytest.raises(WorkspaceRegistryError):
            reg.select("unknown-ws")

    def test_duplicate_registration_fails_closed(self):
        reg = _make_registry()
        with pytest.raises(WorkspaceRegistryError):
            reg.register("shwtp", lambda: build_shwtp_session())

    def test_identity_mismatch_factory_fails_closed(self):
        reg = _make_registry()
        # Register a factory under the WRONG id that returns a shwtp session.
        reg.register("wrong-id", lambda: build_shwtp_session())
        with pytest.raises(WorkspaceRegistryError):
            reg.select("wrong-id")


class TestOpenForFutureWorkspace:
    def test_register_new_workspace(self):
        reg = _make_registry()
        reg.register(
            "demo-ws",
            _demo_session_factory("demo-ws"),
            description="future workspace",
        )
        assert "demo-ws" in reg.workspace_ids()
        session = reg.select("demo-ws")
        assert session.workspace_id == "demo-ws"


def _demo_session_factory(workspace_id: str):
    from virtual_factory.runcontrol import RunLifecycleService, RuntimeSession
    from virtual_factory.workspace import ScopeMode, ScopeSpec, build_workspace

    def factory():
        class _StubBridge:
            supports_reset = False

            def natural_next_boundary(self, scope_ids):
                raise NotImplementedError("not advanced in G23 tests")

            def advance(self, *args):
                raise NotImplementedError("not advanced in G23 tests")

            def reset(self, *args):
                raise NotImplementedError("not advanced in G23 tests")

        ws = build_workspace(
            workspace_id,
            [ScopeSpec(scope_id="unit", mode=ScopeMode.EXECUTABLE_CAPABLE)],
        )
        service = RunLifecycleService(ws, lambda: _StubBridge())
        return RuntimeSession(service, workspace_id, "demo-scenario")

    return factory


class TestG22G21Unchanged:
    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import (
            SHWTP_FEDERATION_COUPLING_POLICY,
            SHWTP_PLANT_SLICE_COUPLING_POLICY,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert SHWTP_PLANT_SLICE_COUPLING_POLICY == "explicit_lagged"

    def test_g21_slice_and_g22_session_still_work(self):
        slice_ = build_shwtp_plant_slice()
        assert slice_.run_window("window-1").status == "completed"
        session = build_shwtp_session()
        assert session.workspace_id == "shwtp"
