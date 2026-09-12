"""VF-vNEXT-G21 — SH-WTP Functional Simulation Expansion tests.

Proves (Issue #72 required): a coherent runnable multi-scope SH-WTP slice
materially larger than T106->T108; >=4 executable scopes; assumed links
explicit/versioned/reversible and distinct from PIM truth; fidelity/status
explicit per scope; deterministic multi-window execution; no same-window
feed-through under explicit_lagged; no mutable cross-scope state; no authority
broadening; T106/T108 behavior unchanged; existing G20/G19/G18/G14/G15 behavior
unchanged.
"""

from __future__ import annotations

import pytest

from virtual_factory.shwtp.expansion import (
    BIND_RAW_T100,
    BIND_T100_T106,
    BIND_T108_DIST,
    PLANT_SLICE_SCOPES,
    SHWTP_PLANT_SLICE_COUPLING_POLICY,
    build_shwtp_plant_slice,
)
from virtual_factory.shwtp.projection import SHWTP_F01_BINDING_ID


def _slice(**kwargs):
    defaults = dict(
        initial_inflow_m3_s=3.0,
        t100_initial_inflow_m3_s=5.0,
        t106_initial_inflow_m3_s=7.0,
        t108_initial_inflow_m3_s=0.0,
        t108_requested_outflow_m3_s=1.5,
    )
    defaults.update(kwargs)
    return build_shwtp_plant_slice(**defaults)


def _t106(slice_):
    return slice_.participants["shwtp/line1/l1_t106"]

def _t108(slice_):
    return slice_.participants["shwtp/line1/l1_t108"]

def _dist(slice_):
    return slice_.participants["shwtp/dist_p108"]


class TestSliceCoverage:
    def test_at_least_four_executable_scopes(self):
        assert len(PLANT_SLICE_SCOPES) >= 4
        assert len(PLANT_SLICE_SCOPES) == 5

    def test_slice_spans_treatment_and_distribution(self):
        roles = {s.role for s in PLANT_SLICE_SCOPES}
        assert "source" in roles
        assert "junction" in roles
        assert "filter" in roles
        assert "clean_water_tank" in roles
        assert "distribution_sink" in roles

    def test_fidelity_and_status_explicit_per_scope(self):
        for scope in PLANT_SLICE_SCOPES:
            assert scope.fidelity in {"logical_only", "first_order"}
            assert scope.status in {"accepted", "scenario_assumed"}

    def test_t110_not_used_as_runtime(self):
        canonical = {s.canonical_id for s in PLANT_SLICE_SCOPES}
        assert "UNIT-SHW-WASH-T110" not in canonical


class TestTopology:
    def test_graph_has_four_bindings(self):
        slice_ = _slice()
        assert len(slice_.graph.bindings) == 4

    def test_authoritative_f01_link_present(self):
        slice_ = _slice()
        edge_ids = {b.edge_id for b in slice_.graph.bindings}
        assert SHWTP_F01_BINDING_ID in edge_ids

    def test_assumed_links_are_explicit_versioned_reversible(self):
        slice_ = _slice()
        assert slice_.overlay.edge_count == 3
        for edge in slice_.overlay.edges:
            assert edge.source_kind == "vf_scenario_assumption"
            assert edge.status == "assumed/synthetic"
            assert edge.reversible is True
            assert edge.assumption_id
            assert edge.version

    def test_assumed_topology_distinct_from_pim(self):
        slice_ = _slice()
        assert slice_.overlay.serialize()["schema"] == (
            "vf.vnext.g18.scenario_assumed_topology_overlay.v1"
        )
        # The three assumed edges never use PIM relation ids.
        for edge in slice_.overlay.edges:
            assert not edge.relation_type.startswith("REL-SHW-")

    def test_composition_graph_not_execution_order(self):
        slice_ = _slice()
        assert not hasattr(slice_.graph, "execution_order")
        assert not hasattr(slice_.graph, "coupling_policy")
        assert slice_.coupling_policy == SHWTP_PLANT_SLICE_COUPLING_POLICY == "explicit_lagged"


class TestDeterministicRun:
    def test_multi_window_completes_deterministically(self):
        a = _slice()
        b = _slice()
        outcomes_a = [a.run_window(f"window-{i}") for i in range(1, 4)]
        outcomes_b = [b.run_window(f"window-{i}") for i in range(1, 4)]
        assert [o.status for o in outcomes_a] == ["completed"] * 3
        assert [(o.committed, o.participants) for o in outcomes_a] == [
            (o.committed, o.participants) for o in outcomes_b
        ]

    def test_identical_inputs_identical_tank_state(self):
        a = _slice()
        b = _slice()
        for i in range(1, 4):
            a.run_window(f"window-{i}")
            b.run_window(f"window-{i}")
        assert _t108(a)._runtime.state.volume_m3 == _t108(b)._runtime.state.volume_m3

    def test_four_transfers_commit_per_window(self):
        slice_ = _slice()
        outcome = slice_.run_window("window-1")
        assert len(outcome.committed) == 4


class TestNoFeedThrough:
    def test_explicit_lagged_no_same_window_feed_through(self):
        slice_ = _slice()
        slice_.run_window("window-1")
        # Window 1: T106 emitted its INITIAL inflow (7.0), not RAW's window-1
        # output (3.0).
        assert _t106(slice_)._runtime.state.last_output_flow_m3_s == 7.0
        slice_.run_window("window-2")
        # Window 2: T106 emitted T100's window-1 committed value (5.0), NOT
        # T100's window-2 value (3.0) -> no same-window feed-through.
        assert _t106(slice_)._runtime.state.last_output_flow_m3_s == 5.0

    def test_distribution_receives_t108_outflow(self):
        slice_ = _slice()
        for i in range(1, 4):
            slice_.run_window(f"window-{i}")
        # DIST receives T108's applied outflow each window (1.5 m3/s).
        assert _dist(slice_)._received == [1.5, 1.5, 1.5]


class TestNoMutableCrossScopeState:
    def test_transfer_payload_is_detached(self):
        slice_ = _slice()
        t106 = _t106(slice_)
        t106.prepare_window("window-1")
        transfers = t106.advance_to(1.0)
        payload = transfers[0].payload
        with pytest.raises(TypeError):
            payload["volumetric_flow_m3_s"] = 99.0


class TestAuthorityUnchanged:
    def test_no_runtime_authority_broadening(self):
        from virtual_factory.shwtp import (
            SHWTP_RUNTIME_AUTHORIZATION,
            SHWTP_SITE_AUTHORIZED_EXECUTION,
        )
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"


class TestT106T108Unchanged:
    def test_t106_standalone_behavior_unchanged(self):
        from virtual_factory.shwtp import T106Config, T106LogicalRuntime
        from virtual_factory.provenance import RunContextV2
        from virtual_factory.shwtp.logical_runtime import SHWTP_T106_SCOPE_PATH
        rt = T106LogicalRuntime(
            T106Config(dt_s=1.0),
            RunContextV2(workspace_id="shwtp", run_id="r", scope_path=SHWTP_T106_SCOPE_PATH),
        )
        step = rt.step(4.0)
        assert step.output_flow_m3_s == 4.0  # pass-through

    def test_t108_standalone_behavior_unchanged(self):
        from virtual_factory.shwtp import T108Config, T108TankRuntime
        from virtual_factory.provenance import RunContextV2
        from virtual_factory.shwtp.runtime import SHWTP_T108_SCOPE_PATH
        rt = T108TankRuntime(
            T108Config(capacity_m3=100.0, tank_area_m2=20.0, initial_volume_m3=50.0, dt_s=1.0),
            RunContextV2(workspace_id="shwtp", run_id="r", scope_path=SHWTP_T108_SCOPE_PATH),
        )
        step = rt.step(2.0, 1.5)
        assert step.applied_outflow_m3_s == 1.5


class TestG20G19G18G14G15Unchanged:
    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import SHWTP_FEDERATION_COUPLING_POLICY
        from virtual_factory.federation.generic import (
            GENERIC_FEDERATION_COUPLING_POLICY,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert GENERIC_FEDERATION_COUPLING_POLICY == "explicit_lagged"

    def test_g18_overlay_unchanged(self):
        from virtual_factory.shwtp.overlay import build_shwtp_t108_dist_p108_overlay
        overlay = build_shwtp_t108_dist_p108_overlay()
        assert overlay.edge_count == 1

    def test_g14a_projection_unchanged(self):
        from virtual_factory.shwtp import build_shwtp_f01_projection
        proj = build_shwtp_f01_projection()
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1
