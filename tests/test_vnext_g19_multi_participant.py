"""VF-vNEXT-G19 — Generic Multi-Participant Federation Proof (>2) tests.

Proves (Issue #70 required): 3+ synthetic participants coordinate over 2+
bindings in one window; at least 2 transfers commit deterministically; no
same-window feed-through under explicit_lagged; participant/transfer ordering is
independent of declaration/registration order; identity/workspace mismatch
fails closed; a failed window is never reported completed; detached immutable
transfers only; identical inputs produce identical results; coupling policy
remains orchestration policy; G14/G15/G18 behavior unchanged.
"""

from __future__ import annotations

import pytest

from virtual_factory.composition import (
    BoundaryPort,
    BoundaryTransfer,
    CompositionBinding,
    CompositionError,
    CompositionGraph,
    Coordinator,
    CoordinationError,
    ParticipantError,
    PortCategory,
    PortDirection,
    PortRef,
    TransferError,
)
from virtual_factory.federation.generic import (
    GENERIC_FEDERATION_COUPLING_POLICY,
    GenericFederationError,
    SyntheticParticipant,
    build_synthetic_federation,
)
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    build_workspace,
)


def _run_three_windows(fed):
    return [
        fed.run_window("window-1", 1.0),
        fed.run_window("window-2", 2.0),
        fed.run_window("window-3", 3.0),
    ]


class TestCoordination:
    def test_three_participants_coordinate(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        outcome = fed.run_window("window-1", 1.0)
        assert outcome.status == "completed"
        assert outcome.participants == ("ws-g19/p0", "ws-g19/p1", "ws-g19/p2")
        assert len(outcome.committed) == 2  # p0->p1, p1->p2

    def test_four_participants_coordinate(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2", "p3"), (1.0, 2.0, 3.0, 4.0),
        )
        outcome = fed.run_window("window-1", 1.0)
        assert outcome.status == "completed"
        assert len(outcome.participants) == 4
        assert len(outcome.committed) == 3  # three bindings

    def test_at_least_two_transfers_commit_in_one_window(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        outcome = fed.run_window("window-1", 1.0)
        assert len(outcome.committed) >= 2


class TestExplicitLaggedNoFeedThrough:
    def test_no_same_window_feed_through(self):
        # Source emits a per-window sequence: window1=1, window2=5, window3=9.
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
            source_values=(1.0, 5.0, 9.0),
        )
        outcomes = _run_three_windows(fed)
        assert [o.status for o in outcomes] == ["completed"] * 3
        p2_received = fed.participants[2]._committed_values
        # window1: p2 receives p1's INITIAL (10), not p0's window-1 output (1).
        assert p2_received[0] == 10.0
        # window2: p2 receives p1's window-2 output == p0's window-1 output (1).
        assert p2_received[1] == 1.0
        # window3: p2 receives p1's window-3 output == p0's window-2 output (5),
        # NOT p0's window-3 output (9) -> no same-window feed-through.
        assert p2_received[2] == 5.0


class TestOrderingIndependence:
    def test_registration_order_does_not_change_outcome(self):
        a = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
            source_values=(1.0, 5.0),
        )
        b = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
            source_values=(1.0, 5.0),
            registration_order=("p2", "p1", "p0"),
        )
        oa = _run_three_windows(a)
        ob = _run_three_windows(b)
        assert [(o.status, o.participants, o.committed) for o in oa] == [
            (o.status, o.participants, o.committed) for o in ob
        ]
        for pa, pb in zip(a.participants, b.participants):
            assert pa._committed_values == pb._committed_values
            assert pa._last_emitted == pb._last_emitted

    def test_identical_inputs_identical_results(self):
        a = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
            source_values=(1.0, 5.0, 9.0),
        )
        b = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
            source_values=(1.0, 5.0, 9.0),
        )
        oa = _run_three_windows(a)
        ob = _run_three_windows(b)
        assert [(o.status, o.committed) for o in oa] == [
            (o.status, o.committed) for o in ob
        ]
        for pa, pb in zip(a.participants, b.participants):
            assert pa._committed_values == pb._committed_values


class TestGraphVsExecutionOrder:
    def test_graph_bindings_are_declared_connectivity_not_execution(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        assert len(fed.graph.bindings) == 2
        # The graph carries no execution-order or coupling-policy field.
        assert not hasattr(fed.graph, "execution_order")
        assert not hasattr(fed.graph, "coupling_policy")
        for binding in fed.graph.bindings:
            assert not hasattr(binding, "order")
            assert not hasattr(binding, "coupling_policy")

    def test_coupling_policy_is_orchestration_level(self):
        assert GENERIC_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        # Not a property of graph / ports / bindings / transfers.
        assert not hasattr(fed.graph, "coupling_policy")
        outcome = fed.run_window("window-1", 1.0)
        assert outcome.status == "completed"


class TestDetachedImmutableTransfer:
    def test_transfer_payload_is_detached_and_immutable(self):
        out_ref = PortRef(StructuralPath(("ws-g19", "p0")), "out")
        in_ref = PortRef(StructuralPath(("ws-g19", "p1")), "in")
        payload = {"value": 1.0}
        transfer = BoundaryTransfer(
            transfer_id="t",
            source=out_ref,
            target=in_ref,
            binding_id="b0",
            window_id="window-1",
            simulation_time_s=1.0,
            workspace_id="ws-g19",
            run_id="r",
            payload=payload,
        )
        payload["value"] = 999.0  # mutate the ORIGINAL dict
        assert transfer.payload["value"] == 1.0  # detached copy unaffected
        with pytest.raises(TypeError):
            transfer.payload["value"] = 2.0  # frozen mapping


class TestFailClosedIdentity:
    def test_transfer_workspace_mismatch_fails_closed(self):
        out_ref = PortRef(StructuralPath(("ws-g19", "p0")), "out")
        in_ref = PortRef(StructuralPath(("ws-g19", "p1")), "in")
        with pytest.raises(TransferError):
            BoundaryTransfer(
                transfer_id="t",
                source=out_ref,
                target=in_ref,
                binding_id="b0",
                window_id="window-1",
                simulation_time_s=1.0,
                workspace_id="other-workspace",
                run_id="r",
                payload={"value": 1.0},
            )

    def test_cross_workspace_binding_fails_closed(self):
        with pytest.raises(CompositionError):
            CompositionGraph(
                workspace_id="ws-g19",
                bindings=[CompositionBinding(
                    edge_id="x",
                    source=PortRef(StructuralPath(("ws-g19", "p0")), "out"),
                    target=PortRef(StructuralPath(("other", "p1")), "in"),
                )],
                ports=[
                    BoundaryPort(
                        ref=PortRef(StructuralPath(("ws-g19", "p0")), "out"),
                        direction=PortDirection.OUT,
                        category=PortCategory.MATERIAL,
                    ),
                    BoundaryPort(
                        ref=PortRef(StructuralPath(("other", "p1")), "in"),
                        direction=PortDirection.IN,
                        category=PortCategory.MATERIAL,
                    ),
                ],
            )

    def test_dangling_scope_registration_fails_closed(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        ghost = SyntheticParticipant(
            scope_path=StructuralPath(("ws-g19", "ghost")),
            workspace_id="ws-g19",
            run_id="r",
            out_port=None,
            in_port=PortRef(StructuralPath(("ws-g19", "ghost")), "in"),
            binding_id=None,
            target_ref=None,
            initial_value=1.0,
        )
        coord = Coordinator(fed.workspace, fed.graph)
        with pytest.raises(CoordinationError):
            coord.register(ghost)

    def test_container_only_scope_cannot_register(self):
        ws = build_workspace("ws-c", [
            ScopeSpec(scope_id="container", mode=ScopeMode.CONTAINER_ONLY),
            ScopeSpec(
                scope_id="exec",
                mode=ScopeMode.EXECUTABLE_CAPABLE,
                parent_path=StructuralPath(("ws-c", "container")),
            ),
        ])
        graph = CompositionGraph(workspace_id="ws-c")
        container_participant = SyntheticParticipant(
            scope_path=StructuralPath(("ws-c", "container")),
            workspace_id="ws-c",
            run_id="r",
            out_port=None,
            in_port=PortRef(StructuralPath(("ws-c", "exec")), "in"),
            binding_id=None,
            target_ref=None,
            initial_value=1.0,
        )
        coord = Coordinator(ws, graph)
        with pytest.raises(CoordinationError):
            coord.register(container_participant)


class TestFailedWindowNotCompleted:
    def test_advance_failure_is_not_completed(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        bad = _FaultyParticipant(fed.participants[0].scope_path, fail="advance")
        coord = Coordinator(fed.workspace, fed.graph)
        coord.register(bad)
        for p in fed.participants[1:]:
            p.prepare_window("window-1")
            coord.register(p)
        outcome = coord.run_window("window-1", 1.0)
        assert outcome.status == "failed"
        assert outcome.committed == ()

    def test_undeclared_transfer_fails_closed(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        bad = _UndeclaredTransferParticipant(fed.participants[0].scope_path)
        coord = Coordinator(fed.workspace, fed.graph)
        coord.register(bad)
        for p in fed.participants[1:]:
            p.prepare_window("window-1")
            coord.register(p)
        outcome = coord.run_window("window-1", 1.0)
        assert outcome.status == "failed"
        assert outcome.committed == ()

    def test_commit_failure_stops_commits(self):
        fed = build_synthetic_federation(
            "ws-g19", ("p0", "p1", "p2"), (1.0, 10.0, 100.0),
        )
        bad = _FaultyParticipant(fed.participants[1].scope_path, fail="commit")
        coord = Coordinator(fed.workspace, fed.graph)
        for p in fed.participants:
            p.prepare_window("window-1")
        coord.register(fed.participants[0])
        coord.register(bad)
        coord.register(fed.participants[2])
        outcome = coord.run_window("window-1", 1.0)
        assert outcome.status == "failed"


class _FaultyParticipant:
    """A participant that fails during advance_to or commit_transfers."""

    def __init__(self, scope_path, fail: str):
        self._scope_path = scope_path
        self._fail = fail
        self._time_s = 0.0

    @property
    def scope_path(self):
        return self._scope_path

    @property
    def current_time_s(self):
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        pass

    def advance_to(self, target_time_s: float):
        if self._fail == "advance":
            raise ParticipantError("synthetic advance failure")
        self._time_s = target_time_s
        return ()

    def commit_transfers(self, inbound):
        if self._fail == "commit":
            raise ParticipantError("synthetic commit failure")


class _UndeclaredTransferParticipant:
    """A participant that emits a transfer for an undeclared binding."""

    def __init__(self, scope_path):
        self._scope_path = scope_path
        self._time_s = 0.0

    @property
    def scope_path(self):
        return self._scope_path

    @property
    def current_time_s(self):
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        self._window = window_id

    def advance_to(self, target_time_s: float):
        self._time_s = target_time_s
        return (
            BoundaryTransfer(
                transfer_id="bad",
                source=PortRef(self._scope_path, "out"),
                target=PortRef(StructuralPath(("ws-g19", "p2")), "in"),
                binding_id="undeclared",
                window_id=self._window,
                simulation_time_s=target_time_s,
                workspace_id="ws-g19",
                run_id="r",
                payload={"value": 1.0},
            ),
        )

    def commit_transfers(self, inbound):
        pass


class TestG14G15G18Unchanged:
    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import (
            SHWTP_FEDERATION_COUPLING_POLICY,
            SHWTP_RUNTIME_AUTHORIZATION,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"

    def test_g14a_projection_unchanged(self):
        from virtual_factory.shwtp import build_shwtp_f01_projection
        proj = build_shwtp_f01_projection()
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

    def test_g18_overlay_unchanged(self):
        from virtual_factory.shwtp.overlay import build_shwtp_t108_dist_p108_overlay
        overlay = build_shwtp_t108_dist_p108_overlay()
        assert overlay.edge_count == 1
