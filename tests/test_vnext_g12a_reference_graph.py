"""VF-vNEXT-G12A — Generic Reference Connectivity Graph foundation tests.

Proves (Issue #58 required tests):

1. valid graph builds deterministically;
2. declaration order does not affect serialization/order;
3. endpoint may be a canonical semantic ref with no StructuralPath;
4. graph does not require BoundaryPort/PortRegistry;
5. one-to-many is accepted;
6. many-to-one is accepted;
7. many-to-many is accepted;
8. cycles are accepted;
9. duplicate edge id fails closed;
10. duplicate exact logical relation follows a frozen deterministic rule;
11. empty/invalid endpoint identity fails closed;
12. empty relation type fails closed;
13. evidence/provenance metadata survives deterministic serialization;
14. gaps/status/confidence metadata survives when supplied;
15. every edge is inert (runtime_effect none);
16. no runtime behavior/state propagation API exists;
17. no dependency on SH-WTP ids in the generic module;
18-20. G4 / G11 / G1-G11 canonical baseline stay green (baseline run);
21. no G12B SH-WTP PIM materialization appears;
22. no runtime projection / boundary-port generation appears.
"""

from __future__ import annotations

import inspect
import re

import pytest

from virtual_factory.connectivity import (
    NO_RUNTIME_EFFECT,
    ReferenceConnectivityGraph,
    ReferenceEdge,
    ReferenceEndpoint,
    ReferenceGraphError,
)
from virtual_factory.connectivity import reference_graph as rg_module

AUTHORITY = "urn:example:semantic-authority"


def _ep(entity_id: str, *, authority: str = AUTHORITY, kind: str | None = None):
    return ReferenceEndpoint(authority=authority, entity_id=entity_id, entity_kind=kind)


def _edge(
    edge_id: str,
    source: str,
    target: str,
    relation_type: str = "flows_to",
    *,
    evidence_ref: str = "DOC-EXAMPLE-001",
    confidence: str | None = None,
    status: str | None = None,
    gaps: tuple[str, ...] = (),
):
    return ReferenceEdge(
        edge_id=edge_id,
        source=_ep(source),
        target=_ep(target),
        relation_type=relation_type,
        evidence_ref=evidence_ref,
        confidence=confidence,
        status=status,
        gaps=gaps,
    )


def _module_code(module) -> str:
    """Module source with docstrings stripped (code-only inspection)."""
    return re.sub(r'""".*?"""', '', inspect.getsource(module), flags=re.DOTALL)


class TestEndpointIdentity:
    def test_endpoint_is_external_semantic_ref_without_structural_path(self):
        endpoint = _ep("UNIT-X-01", kind="Unit")
        assert endpoint.authority == AUTHORITY
        assert endpoint.entity_id == "UNIT-X-01"
        assert endpoint.entity_kind == "Unit"
        assert endpoint.key == (AUTHORITY, "UNIT-X-01")
        # no StructuralPath is required or involved
        assert not hasattr(endpoint, "owner_scope")
        assert not hasattr(endpoint, "path")

    def test_endpoint_never_renames_external_id(self):
        endpoint = _ep("canonical-unit-7")
        assert endpoint.entity_id == "canonical-unit-7"
        assert "canonical-unit-7" in endpoint.as_string()

    def test_empty_endpoint_identity_fails_closed(self):
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="", entity_id="x")
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="urn:a", entity_id="")
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="  ", entity_id="x")

    def test_endpoint_separator_rejected_fails_closed(self):
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="a::b", entity_id="x")
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="a", entity_id="x::y")

    def test_optional_entity_kind_validated(self):
        with pytest.raises(ReferenceGraphError):
            ReferenceEndpoint(authority="a", entity_id="x", entity_kind="  ")


class TestEndpointIdentityConsistency:
    """G12A-C01: frozen endpoint identity is (authority, entity_id); entity_kind
    is descriptive metadata excluded from equality/hash and fail-closed on
    conflict."""

    def test_equality_and_hash_ignore_entity_kind(self):
        unit = ReferenceEndpoint(authority=AUTHORITY, entity_id="X", entity_kind="Unit")
        conn = ReferenceEndpoint(
            authority=AUTHORITY, entity_id="X", entity_kind="ProcessConnection"
        )
        assert unit == conn
        assert hash(unit) == hash(conn)
        assert unit.key == conn.key == (AUTHORITY, "X")

    def test_same_identity_same_kind_allowed(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "X", "Y", relation_type="flows_to"),
                _edge("e2", "Y", "Z", relation_type="flows_to"),
            ]
        )
        # endpoint Y appears as target of e1 and source of e2 with the same
        # (None) entity_kind -> allowed
        assert graph.edge_count == 2

    def test_conflicting_entity_kind_fails_closed(self):
        e1 = ReferenceEdge(
            edge_id="e1",
            source=_ep("X", kind="Unit"),
            target=_ep("Y"),
            relation_type="flows_to",
            evidence_ref="DOC",
        )
        e2 = ReferenceEdge(
            edge_id="e2",
            source=_ep("X", kind="ProcessConnection"),
            target=_ep("Z"),
            relation_type="flows_to",
            evidence_ref="DOC",
        )
        with pytest.raises(ReferenceGraphError) as exc:
            ReferenceConnectivityGraph([e1, e2])
        assert "conflicting entity_kind" in str(exc.value)

    def test_missing_vs_known_entity_kind_fails_closed(self):
        e1 = ReferenceEdge(
            edge_id="e1",
            source=_ep("X", kind=None),
            target=_ep("Y"),
            relation_type="flows_to",
            evidence_ref="DOC",
        )
        e2 = ReferenceEdge(
            edge_id="e2",
            source=_ep("X", kind="Unit"),
            target=_ep("Z"),
            relation_type="flows_to",
            evidence_ref="DOC",
        )
        with pytest.raises(ReferenceGraphError) as exc:
            ReferenceConnectivityGraph([e1, e2])
        assert "conflicting entity_kind" in str(exc.value)

    def test_inbound_outbound_use_frozen_identity_not_entity_kind(self):
        graph = ReferenceConnectivityGraph(
            [_edge("e1", "X", "Y", relation_type="flows_to")]
        )
        query = ReferenceEndpoint(
            authority=AUTHORITY, entity_id="X", entity_kind="Unit"
        )
        assert [e.edge_id for e in graph.outbound(query)] == ["e1"]
        # identical result regardless of the query endpoint's entity_kind
        assert graph.outbound(_ep("X")) == graph.outbound(query)


class TestEdge:
    def test_edge_requires_nonempty_relation_type(self):
        with pytest.raises(ReferenceGraphError):
            _edge("e1", "a", "b", relation_type="")
        with pytest.raises(ReferenceGraphError):
            _edge("e1", "a", "b", relation_type="   ")

    def test_edge_requires_nonempty_evidence_ref(self):
        with pytest.raises(ReferenceGraphError):
            _edge("e1", "a", "b", evidence_ref="")

    def test_edge_runtime_effect_must_be_none(self):
        with pytest.raises(ReferenceGraphError):
            ReferenceEdge(
                edge_id="e1",
                source=_ep("a"),
                target=_ep("b"),
                relation_type="flows_to",
                evidence_ref="DOC",
                runtime_effect="propagate",
            )

    def test_edge_default_is_inert(self):
        edge = _edge("e1", "a", "b")
        assert edge.runtime_effect == NO_RUNTIME_EFFECT == "none"

    def test_logical_key_ignores_edge_id_and_evidence(self):
        e1 = _edge("e-1", "a", "b", relation_type="flows_to")
        e2 = _edge("e-2", "a", "b", relation_type="flows_to")
        assert e1.logical_key == e2.logical_key


class TestGraphShapes:
    def test_one_to_many_accepted(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "b"),
                _edge("e2", "a", "c"),
            ]
        )
        assert graph.edge_count == 2
        assert len(graph.outbound(_ep("a"))) == 2

    def test_many_to_one_accepted(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "c"),
                _edge("e2", "b", "c"),
            ]
        )
        assert len(graph.inbound(_ep("c"))) == 2

    def test_many_to_many_accepted(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "x"),
                _edge("e2", "a", "y"),
                _edge("e3", "b", "x"),
                _edge("e4", "b", "y"),
            ]
        )
        assert graph.edge_count == 4
        assert len(graph.inbound(_ep("x"))) == 2
        assert len(graph.outbound(_ep("b"))) == 2

    def test_cycles_accepted(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "b"),
                _edge("e2", "b", "c"),
                _edge("e3", "c", "a"),
            ]
        )
        assert graph.edge_count == 3

    def test_multiple_relation_classes_between_same_endpoints_allowed(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "b", relation_type="flows_to"),
                _edge("e2", "a", "b", relation_type="dependency_constraint"),
            ]
        )
        assert graph.edge_count == 2


class TestFailClosed:
    def test_duplicate_edge_id_fails_closed(self):
        with pytest.raises(ReferenceGraphError) as exc:
            ReferenceConnectivityGraph(
                [_edge("dup", "a", "b"), _edge("dup", "c", "d")]
            )
        assert "duplicate edge id" in str(exc.value)

    def test_duplicate_logical_relation_fails_closed(self):
        with pytest.raises(ReferenceGraphError) as exc:
            ReferenceConnectivityGraph(
                [_edge("e1", "a", "b"), _edge("e2", "a", "b")]
            )
        assert "duplicate exact logical relation" in str(exc.value)

    def test_duplicate_logical_relation_is_type_sensitive(self):
        # same endpoints, different relation type -> NOT a duplicate
        graph = ReferenceConnectivityGraph(
            [
                _edge("e1", "a", "b", relation_type="flows_to"),
                _edge("e2", "a", "b", relation_type="controls"),
            ]
        )
        assert graph.edge_count == 2

    def test_non_edge_rejected(self):
        with pytest.raises(ReferenceGraphError):
            ReferenceConnectivityGraph(["not-an-edge"])  # type: ignore[list-item]


class TestDeterminism:
    def test_build_is_deterministic_and_order_independent(self):
        edges = [
            _edge("e4", "d", "e"),
            _edge("e1", "a", "b"),
            _edge("e3", "c", "a"),
            _edge("e2", "b", "c"),
        ]
        g1 = ReferenceConnectivityGraph(edges)
        g2 = ReferenceConnectivityGraph(reversed(edges))
        assert g1.serialize() == g2.serialize()
        assert [e.edge_id for e in g1.edges] == ["e1", "e2", "e3", "e4"]

    def test_serialization_is_stable_and_complete(self):
        graph = ReferenceConnectivityGraph(
            [
                _edge(
                    "e1",
                    "a",
                    "b",
                    relation_type="flows_to",
                    confidence="high",
                    status="DocumentConfirmed",
                    gaps=("GAP-1", "GAP-2"),
                )
            ]
        )
        data = graph.serialize()
        assert data["schema"].startswith("vf.vnext.g12a")
        assert data["edge_count"] == 1
        assert data["runtime_effect"] == "none"
        edge = data["edges"][0]
        assert edge["source"]["authority"] == AUTHORITY
        assert edge["source"]["entity_id"] == "a"
        assert edge["target"]["entity_id"] == "b"
        assert edge["relation_type"] == "flows_to"
        assert edge["evidence_ref"] == "DOC-EXAMPLE-001"
        assert edge["confidence"] == "high"
        assert edge["status"] == "DocumentConfirmed"
        assert tuple(edge["gaps"]) == ("GAP-1", "GAP-2")
        assert edge["runtime_effect"] == "none"

    def test_gaps_serialized_in_sorted_order(self):
        graph = ReferenceConnectivityGraph(
            [_edge("e1", "a", "b", gaps=("GAP-Z", "GAP-A"))]
        )
        assert tuple(graph.serialize()["edges"][0]["gaps"]) == ("GAP-A", "GAP-Z")


class TestNoRuntime:
    def test_graph_has_no_runtime_or_propagation_api(self):
        graph = ReferenceConnectivityGraph([_edge("e1", "a", "b")])
        for attr in ("advance", "step", "run", "propagate", "execute", "start"):
            assert not hasattr(graph, attr)

    def test_module_imports_no_runtime_or_composition_ports(self):
        code = _module_code(rg_module)
        for token in (
            "from virtual_factory.composition",
            "from virtual_factory.runcontrol",
            "from virtual_factory.workspace",
        ):
            assert token not in code
        for name in (
            "BoundaryPort",
            "PortDirection",
            "PortCategory",
            "PortRegistry",
            "Coordinator",
            "RunLifecycleService",
            "StructuralPath",
        ):
            assert name not in vars(rg_module)

    def test_module_is_plant_agnostic(self):
        code = _module_code(rg_module)
        for token in (
            "SH-WTP",
            "SHW",
            "PROC-SHW",
            "GAP-SHW",
            "UNIT-SHW",
            "AREA-SHW",
        ):
            assert token not in code

    def test_no_runtime_projection_or_boundary_port_generation(self):
        code = _module_code(rg_module)
        for token in (
            "def project",
            "def map_to",
            "def to_ports",
            "BoundaryPort(",
        ):
            assert token not in code
