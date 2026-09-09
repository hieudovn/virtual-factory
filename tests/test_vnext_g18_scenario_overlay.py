"""VF-vNEXT-G18 — Scenario-Assumed Topology Overlay tests.

Proves (Issue #69 required): authoritative vs assumed topology distinguishable;
assumed edge has explicit id/version/provenance; deterministic round-trip
serialization; malformed/ambiguous overlay fails closed; removing/replacing an
assumption does not alter the PIM/reference baseline; no runtime/site
authorization broadened; T108->DIST-P108 fixture is assumed-only (never
DocumentConfirmed/site-verified); and G14/G15/G17A behavior remains unchanged.
"""

from __future__ import annotations

import pytest

from virtual_factory.connectivity.scenario_overlay import (
    ASSUMED_SOURCE_KIND,
    ASSUMED_STATUS,
    ASSUMED_TOPOLOGY_SCHEMA,
    AssumedTopologyEdge,
    ScenarioTopologyOverlay,
    ScenarioTopologyOverlayError,
)
from virtual_factory.shwtp.overlay import (
    SHWTP_DIST_P108_VF_PATH,
    SHWTP_T108_DIST_P108_ASSUMPTION_ID,
    build_shwtp_t108_dist_p108_assumption,
    build_shwtp_t108_dist_p108_overlay,
)
from virtual_factory.shwtp import (
    SHWTP_FEDERATION_COUPLING_POLICY,
    SHWTP_T108_SCOPE_PATH,
    build_shwtp_f01_projection,
    build_shwtp_reference_graph,
)


def _edge(**overrides) -> AssumedTopologyEdge:
    fields = dict(
        assumption_id="ASSUME-X",
        version="1",
        source="shwtp/a",
        target="shwtp/b",
        relation_type="ASSUMED_FLOWS_TO",
        rationale="test assumption",
    )
    fields.update(overrides)
    return AssumedTopologyEdge(**fields)


class TestEdgeIdentityAndProvenance:
    def test_fixture_has_explicit_id_and_version(self):
        edge = build_shwtp_t108_dist_p108_assumption()
        assert edge.assumption_id == SHWTP_T108_DIST_P108_ASSUMPTION_ID
        assert edge.version == "1"

    def test_fixture_uses_vf_local_identity_not_pim(self):
        edge = build_shwtp_t108_dist_p108_assumption()
        assert edge.source == SHWTP_T108_SCOPE_PATH.as_string()
        assert edge.target == SHWTP_DIST_P108_VF_PATH
        # VF-local paths, never PIM canonical ids.
        assert not edge.source.startswith("PROC-")
        assert not edge.target.startswith("PROC-")
        assert not edge.source.startswith("UNIT-")
        assert not edge.target.startswith("UNIT-")

    def test_source_kind_and_status_frozen_assumed(self):
        edge = build_shwtp_t108_dist_p108_assumption()
        assert edge.source_kind == ASSUMED_SOURCE_KIND == "vf_scenario_assumption"
        assert edge.status == ASSUMED_STATUS == "assumed/synthetic"

    def test_non_assumed_source_kind_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            _edge(source_kind="pim")

    def test_site_verified_status_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            _edge(status="site-verified")

    def test_non_reversible_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            _edge(reversible=False)


class TestFailClosed:
    @pytest.mark.parametrize("field", [
        "assumption_id", "version", "source", "target", "relation_type",
        "rationale",
    ])
    def test_empty_required_field_fails_closed(self, field):
        with pytest.raises(ScenarioTopologyOverlayError):
            _edge(**{field: ""})

    def test_duplicate_assumption_id_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            ScenarioTopologyOverlay(
                overlay_id="o", version="1", domain="d",
                edges=(_edge(), _edge()),
            )

    def test_ambiguous_duplicate_logical_assumption_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            ScenarioTopologyOverlay(
                overlay_id="o", version="1", domain="d",
                edges=(
                    _edge(assumption_id="A"),
                    _edge(assumption_id="B"),  # same source/target/relation
                ),
            )

    def test_from_dict_wrong_schema_fails_closed(self):
        with pytest.raises(ScenarioTopologyOverlayError):
            ScenarioTopologyOverlay.from_dict({"schema": "wrong"})


class TestDeterminismAndSerialization:
    def test_serialization_is_deterministic_regardless_of_input_order(self):
        a = _edge(assumption_id="A", source="shwtp/x")
        b = _edge(assumption_id="B", source="shwtp/y")
        ov1 = ScenarioTopologyOverlay(
            overlay_id="o", version="1", domain="d", edges=(b, a),
        )
        ov2 = ScenarioTopologyOverlay(
            overlay_id="o", version="1", domain="d", edges=(a, b),
        )
        assert ov1.serialize() == ov2.serialize()
        assert ov1.assumption_ids == ov2.assumption_ids

    def test_round_trip_serialization(self):
        ov = build_shwtp_t108_dist_p108_overlay()
        restored = ScenarioTopologyOverlay.from_dict(ov.serialize())
        assert restored.serialize() == ov.serialize()
        assert restored.edge_count == 1

    def test_schema_marker(self):
        assert build_shwtp_t108_dist_p108_overlay().serialize()["schema"] == (
            ASSUMED_TOPOLOGY_SCHEMA
        )


class TestReversibleReplaceable:
    def test_remove_returns_new_overlay_without_mutating(self):
        ov = build_shwtp_t108_dist_p108_overlay()
        removed = ov.remove(SHWTP_T108_DIST_P108_ASSUMPTION_ID)
        assert removed.edge_count == 0
        assert ov.edge_count == 1  # original unchanged

    def test_replace_returns_new_overlay_without_mutating(self):
        ov = build_shwtp_t108_dist_p108_overlay()
        new_edge = _edge(
            assumption_id="ASSUME-SHW-T108-DIST-P108",
            version="2",
            source=SHWTP_T108_SCOPE_PATH.as_string(),
            target=SHWTP_DIST_P108_VF_PATH,
            rationale="revised assumption",
        )
        replaced = ov.replace(new_edge)
        assert replaced.edge_count == 1
        assert replaced.edges[0].version == "2"
        assert ov.edges[0].version == "1"  # original unchanged

    def test_replace_with_replaces_assumption_id(self):
        ov = build_shwtp_t108_dist_p108_overlay()
        new_edge = _edge(
            assumption_id="ASSUME-SHW-T108-DIST-P108-V2",
            version="2",
            source=SHWTP_T108_SCOPE_PATH.as_string(),
            target=SHWTP_DIST_P108_VF_PATH,
            rationale="revised assumption",
            replaces_assumption_id=SHWTP_T108_DIST_P108_ASSUMPTION_ID,
        )
        replaced = ov.replace(new_edge)
        assert replaced.edge_count == 1
        assert replaced.edges[0].assumption_id == "ASSUME-SHW-T108-DIST-P108-V2"


class TestDistinctFromAuthoritative:
    def test_authoritative_graph_unchanged_by_overlay(self):
        auth = build_shwtp_reference_graph()
        before = auth.serialize()
        build_shwtp_t108_dist_p108_overlay()
        assert auth.serialize() == before

    def test_schemas_are_distinct(self):
        auth_schema = build_shwtp_reference_graph().serialize()["schema"]
        overlay_schema = build_shwtp_t108_dist_p108_overlay().serialize()["schema"]
        assert auth_schema != overlay_schema
        assert auth_schema == "vf.vnext.g12a.reference_connectivity_graph.v1"
        assert overlay_schema == ASSUMED_TOPOLOGY_SCHEMA


class TestNoOrderNoCoupling:
    def test_overlay_serialization_has_no_order_field(self):
        data = build_shwtp_t108_dist_p108_overlay().serialize()
        assert "order" not in data
        assert "execution_order" not in data
        for edge in data["edges"]:
            assert "order" not in edge

    def test_overlay_has_no_coupling_policy_field(self):
        data = build_shwtp_t108_dist_p108_overlay().serialize()
        assert "coupling_policy" not in data
        for edge in data["edges"]:
            assert "coupling_policy" not in edge

    def test_coupling_policy_still_frozen_orchestration_policy(self):
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"


class TestNoAuthorizationBroadening:
    def test_authorization_marker_not_authorized(self):
        ov = build_shwtp_t108_dist_p108_overlay()
        assert ov.authorization() == {
            "runtime": "NOT_AUTHORIZED",
            "site_execution": "NOT_AUTHORIZED",
        }
        assert ov.serialize()["authorization"] == ov.authorization()


class TestG14G15G17ABehaviorUnchanged:
    def test_g14a_projection_unchanged(self):
        proj = build_shwtp_f01_projection()
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

    def test_fixture_does_not_touch_pim_relation_ids(self):
        edge = build_shwtp_t108_dist_p108_assumption()
        assert edge.relation_type == "ASSUMED_FLOWS_TO"
        assert not edge.relation_type.startswith("REL-SHW-")
