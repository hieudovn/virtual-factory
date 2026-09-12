"""VF-vNEXT-G12B — SH-WTP PIM reference connectivity materialization tests.

Proves (Issue #59 required tests):

1. exact PIM source pins preserved;
2. selected relationship ids exactly match the pinned slice;
3. endpoints preserve canonical PIM ids;
4. PROC-* endpoints are accepted without becoming G11 Scopes;
5. raw PIM relation types preserved exactly;
6. no six-class runtime semantic reclassification;
7. warning/review/known-but-unconstrained metadata preserved;
8. F06/F07 not classified from names;
9. no relation inferred from PART_OF/containment;
10. no G11 containment change;
11. every edge inert (runtime_effect none);
12. no BoundaryPort/G4/runtime projection generated;
13. vf_runtime_authorization = NOT_AUTHORIZED unchanged;
14. synthetic_reference_execution = PENDING_LATER_PIM_REVIEW unchanged;
15. deterministic serialization independent of declaration order;
16-20. G12A/G11/G4/ASSY/continuous/canonical baseline stay green (baseline run);
21. no G13 work appears.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

import virtual_factory.shwtp.connectivity as conn
from virtual_factory.connectivity import (
    ReferenceConnectivityGraph,
    ReferenceEdge,
    ReferenceEndpoint,
)
from virtual_factory.shwtp.structural import build_shwtp_workspace

G10_PLAN_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_readiness_scope.json"
)

SIX_CLASSES = (
    "material_flow",
    "chemical_flow",
    "sludge_waste_flow",
    "utility_energy_flow",
    "control_information_flow",
    "dependency_constraint",
)


def _module_code(module) -> str:
    return re.sub(r'""".*?"""', "", inspect.getsource(module), flags=re.DOTALL)


@pytest.fixture(scope="module")
def view():
    return conn.build_shwtp_reference_connectivity()


@pytest.fixture(scope="module")
def graph():
    return conn.build_shwtp_reference_graph()


class TestSourcePins:
    def test_exact_pim_source_pins_preserved(self, view):
        pins = view.pins
        assert pins["repository"] == "hieudovn/plant-intelligence-model"
        assert pins["main_sha"] == "ec7f1266d4a19e5201b689874a2a7a75a022fc5c"
        assert pins["package"] == "SHW-PIM-VF-EXPORT-v0.1"
        assert pins["version"] == "v0.1"
        assert pins["source_model_version"] == "SHW-PH03-v0.1"
        assert (
            pins["semantic_identity_sha"]
            == "f23f3c4614f50a1a2e3805f7e887433feb934915"
        )
        assert (
            pins["artifact_hash_sha"]
            == "ea3361a4aca9d25927a4a76c792f3af184e1aabb"
        )
        assert pins["compatibility"] == "compatible_with_constraints"
        assert pins["runtime_authorization"] == "NOT_AUTHORIZED"
        assert pins["model_fixture"] == "examples/song-hong-wtp/model_fixture/model.yaml"

    def test_selected_relationship_ids_exactly_match_slice(self, view):
        assert view.selected_relationship_ids == (
            "REL-SHW-F01",
            "REL-SHW-F02",
            "REL-SHW-F03",
            "REL-SHW-F04",
            "REL-SHW-F05",
            "REL-SHW-F06",
            "REL-SHW-F07",
        )
        assert view.graph.edge_count == 7


class TestEndpoints:
    def test_endpoints_preserve_canonical_pim_ids(self, graph):
        by_id = {e.edge_id: e for e in graph.edges}
        assert by_id["REL-SHW-F01"].source.entity_id == "PROC-SHW-L1-T106-OUT-FLOW"
        assert by_id["REL-SHW-F01"].target.entity_id == "PROC-SHW-L1-T108-IN-FLOW"
        assert by_id["REL-SHW-F02"].source.entity_id == "PROC-SHW-L1-T106-WASH-OUT"
        assert (
            by_id["REL-SHW-F02"].target.entity_id
            == "PROC-SHW-WASH-T110-RECOVERY-RETURN"
        )
        assert by_id["REL-SHW-F07"].source.entity_id == "PROC-SHW-CHEM-DOSING-LINE"
        assert by_id["REL-SHW-F07"].target.entity_id == "PROC-SHW-T100-TO-L1"
        for edge in graph.edges:
            assert edge.source.authority == "hieudovn/plant-intelligence-model"
            assert edge.target.authority == "hieudovn/plant-intelligence-model"
            assert edge.source.entity_kind == "ProcessConnection"
            assert edge.target.entity_kind == "ProcessConnection"

    def test_proc_endpoints_are_not_g11_scopes(self, graph):
        ws = build_shwtp_workspace()
        g11_scope_ids = {
            s.scope_id
            for top in ws.workspace.top_level_scopes
            for s in top.iter_scopes()
        }
        for edge in graph.edges:
            for endpoint in (edge.source, edge.target):
                assert not hasattr(endpoint, "owner_scope")
                assert not hasattr(endpoint, "path")
                assert endpoint.entity_id.startswith("PROC-SHW-")
                # PROC-* never materialized as a G11 scope
                assert endpoint.entity_id not in g11_scope_ids


class TestRawRelationTypes:
    def test_raw_relation_types_preserved_exactly(self, graph):
        types = {e.edge_id: e.relation_type for e in graph.edges}
        assert types["REL-SHW-F01"] == "FLOWS_TO"
        assert types["REL-SHW-F02"] == "DISCHARGES_TO"
        assert types["REL-SHW-F03"] == "CONNECTED_TO"
        assert types["REL-SHW-F04"] == "FLOWS_TO"
        assert types["REL-SHW-F05"] == "FLOWS_TO"
        assert types["REL-SHW-F06"] == "FLOWS_TO"
        assert types["REL-SHW-F07"] == "FLOWS_TO"

    def test_no_six_class_reclassification(self, graph):
        for edge in graph.edges:
            assert edge.relation_type not in SIX_CLASSES

    def test_f06_f07_not_classified_from_names(self, graph):
        types = {e.edge_id: e.relation_type for e in graph.edges}
        # F06 is the sludge line and F07 is the chemical dosing line; both stay
        # raw FLOWS_TO — no name-based sludge/chemical classification.
        assert types["REL-SHW-F06"] == "FLOWS_TO"
        assert types["REL-SHW-F07"] == "FLOWS_TO"
        for token in ("sludge", "chemical"):
            assert token not in types["REL-SHW-F06"].lower()
            assert token not in types["REL-SHW-F07"].lower()


class TestWarningsPreserved:
    def test_review_warning_metadata_preserved(self, graph):
        by_id = {e.edge_id: e for e in graph.edges}
        f02 = by_id["REL-SHW-F02"]
        f03 = by_id["REL-SHW-F03"]
        assert f02.status == "PatternInferred"
        assert f03.status == "PatternInferred"
        for edge in (f02, f03):
            assert any("known-but-unconstrained" in g for g in edge.gaps)
            assert any("REL-006" in g for g in edge.gaps)

    def test_document_confirmed_edges_have_no_warnings(self, graph):
        by_id = {e.edge_id: e for e in graph.edges}
        for rel in ("REL-SHW-F01", "REL-SHW-F04", "REL-SHW-F05"):
            assert by_id[rel].status == "DocumentConfirmed"
            assert by_id[rel].gaps == ()


class TestNoContainmentOrRuntimeCoupling:
    def test_no_part_of_or_containment_derived_edges(self, graph):
        for edge in graph.edges:
            assert edge.relation_type != "PART_OF"
            assert edge.relation_type not in SIX_CLASSES

    def test_no_g11_containment_change(self):
        ws = build_shwtp_workspace()
        assert ws.scope_count == 28
        # the materialization module must not import or build containment
        code = _module_code(conn)
        assert "from virtual_factory.workspace" not in code
        assert "build_workspace" not in code

    def test_every_edge_is_inert(self, graph):
        for edge in graph.edges:
            assert edge.runtime_effect == "none"
        assert graph.runtime_effect == "none"

    def test_no_boundary_port_or_g4_or_runtime_projection(self):
        code = _module_code(conn)
        for token in (
            "BoundaryPort",
            "PortDirection",
            "PortCategory",
            "PortRegistry",
            "CompositionBinding",
            "Coordinator",
            "RunLifecycleService",
        ):
            assert token not in code
        for token in (
            "from virtual_factory.composition",
            "from virtual_factory.runcontrol",
        ):
            assert token not in code


class TestAuthorizationFrozen:
    def test_not_authorized_and_pending_unchanged(self):
        assert conn.SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert conn.SHWTP_SYNTHETIC_REFERENCE_EXECUTION == "PENDING_LATER_PIM_REVIEW"
        assert conn.SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"
        data = conn.build_shwtp_reference_connectivity().serialize()
        assert data["runtime_authorization"] == "NOT_AUTHORIZED"
        assert data["synthetic_reference_execution"] == "PENDING_LATER_PIM_REVIEW"
        assert data["site_authorized_execution"] == "NOT_AUTHORIZED"

    def test_matches_frozen_g10_authorization(self):
        plan = json.loads(G10_PLAN_PATH.read_text(encoding="utf-8"))
        modes = plan["g11_admission_plan"]["execution_modes"]
        assert modes["structural_construction"] == "AUTHORIZED_IN_G11"
        assert (
            modes["synthetic_reference_execution"]
            == conn.SHWTP_SYNTHETIC_REFERENCE_EXECUTION
        )
        assert modes["site_authorized_execution"] == "NOT_AUTHORIZED"
        assert plan["authorization"]["vf_runtime_authorization"] == "NOT_AUTHORIZED"


class TestDeterminism:
    def test_serialization_deterministic(self):
        a = conn.build_shwtp_reference_connectivity().serialize()
        b = conn.build_shwtp_reference_connectivity().serialize()
        assert a == b

    def test_serialization_independent_of_declaration_order(self):
        edges = [
            ReferenceEdge(
                edge_id=r.relationship_id,
                source=ReferenceEndpoint(
                    authority=conn.SHWTP_PIM_AUTHORITY,
                    entity_id=r.source_id,
                    entity_kind=conn.SHWTP_PROCESS_ENTITY_KIND,
                ),
                target=ReferenceEndpoint(
                    authority=conn.SHWTP_PIM_AUTHORITY,
                    entity_id=r.target_id,
                    entity_kind=conn.SHWTP_PROCESS_ENTITY_KIND,
                ),
                relation_type=r.relation_type,
                evidence_ref=f"{conn.SHWTP_PIM_MODEL_FIXTURE}#{r.relationship_id}",
                status=r.evidence_status,
                gaps=r.warnings,
            )
            for r in conn.SHWTP_SELECTED_RELATIONSHIPS
        ]
        forward = ReferenceConnectivityGraph(edges)
        reverse = ReferenceConnectivityGraph(list(reversed(edges)))
        assert forward.serialize() == reverse.serialize()
        assert forward.serialize() == conn.build_shwtp_reference_graph().serialize()

    def test_graph_is_a_g12a_reference_connectivity_graph(self, graph):
        assert isinstance(graph, ReferenceConnectivityGraph)


class TestNoG13:
    def test_no_g13_runtime_implementation(self):
        code = _module_code(conn)
        for token in (
            "def advance",
            "def step",
            "SimulationEngine",
            "RuntimeService",
        ):
            assert token not in code
