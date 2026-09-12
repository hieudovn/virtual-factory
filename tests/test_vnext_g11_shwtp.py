"""VF-vNEXT-G11 — SH-WTP structural Workspace construction: structural tests.

Proves (Issue #56 required tests):

1. exactly one SH-WTP Workspace root created deterministically;
2. every materialized Area/Unit is traceable to the frozen G10 inventory;
3. no unsupported Area/Unit is invented;
4. each node has exactly one containment parent except the Workspace root;
5. container-only Areas are non-executable;
6. object-only / reference-only nodes are non-executable;
7. T106/T108/T110 retain `executable_candidate` role with zero runtime
   behavior/bridge/engine;
8. VF local IDs / StructuralPath stay distinct from PIM canonical IDs;
9. canonical PIM references are explicit read-only metadata;
10. readiness/fidelity ceilings are preserved exactly from G10;
11. `NOT_AUTHORIZED` is preserved;
12. containment is not interpreted as connectivity;
13. no SH-WTP runtime participant appears in G7 run-control;
14. no SH-WTP domain state can advance;
15. TIPA/continuous existing behavior remains unchanged;
16. no G12 connectivity/runtime implementation appears.

(G1-G10 canonical baseline green is proven by the complete baseline run.)
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from virtual_factory.runcontrol import build_continuous_workspace
from virtual_factory.shwtp import (
    SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS,
    SHWTP_PLANT_CANONICAL_ID,
    SHWTP_RUNTIME_AUTHORIZATION,
    SHWTP_SITE_AUTHORIZED_EXECUTION,
    SHWTP_STRUCTURAL_AUTHORIZED_IN_G11,
    SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW,
    SHWTP_WORKSPACE_ID,
    ShwtpWorkspace,
    build_shwtp_workspace,
    vf_local_id,
)
from virtual_factory.shwtp import structural as shwtp_structural
from virtual_factory.workspace import (
    ScopeMode,
    StructuralPath,
    Workspace,
)

PLAN_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_readiness_scope.json"
)


@pytest.fixture(scope="module")
def plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def view() -> ShwtpWorkspace:
    return build_shwtp_workspace(PLAN_PATH)


def _inventory_by_id(plan: dict) -> dict[str, dict]:
    return {e["id"]: e for e in plan["inventory"]}


def _scopes_with_parents(workspace: Workspace):
    """Yield (scope, parent_path_or_None) pre-order."""
    for top in workspace.top_level_scopes:
        yield top, None
        for nested in top.iter_scopes():
            if nested is top:
                continue
            yield nested, nested.path.parent


class TestWorkspaceRoot:
    def test_exactly_one_deterministic_workspace_root(self, plan, view):
        assert view.workspace_id == SHWTP_WORKSPACE_ID == "shwtp"
        assert isinstance(view.workspace, Workspace)
        assert view.workspace.path == StructuralPath(("shwtp",))
        assert view.workspace.path.is_workspace_root
        assert view.plant_meta.canonical_id == SHWTP_PLANT_CANONICAL_ID == "PLANT-SHW"
        # deterministic: two builds serialize identically
        again = build_shwtp_workspace(PLAN_PATH)
        assert view.serialize() == again.serialize()

    def test_scope_count_matches_inventory_minus_plant(self, plan, view):
        inventory = plan["inventory"]
        assert view.scope_count == len(inventory) - 1 == 28


class TestTraceability:
    def test_every_area_and_unit_traceable_to_g10_inventory(self, plan, view):
        inventory = {e["pim_canonical_id"]: e for e in plan["inventory"]}
        assert SHWTP_PLANT_CANONICAL_ID in inventory
        # every scope node maps to an inventory entry by canonical id
        for meta in view.iter_scope_metas():
            assert meta.canonical_id in inventory
            assert meta.inventory_id == inventory[meta.canonical_id]["id"]
        # every non-plant inventory entry is materialized exactly once
        materialized = {meta.canonical_id for meta in view.iter_scope_metas()}
        expected = set(inventory) - {SHWTP_PLANT_CANONICAL_ID}
        assert materialized == expected

    def test_no_unsupported_area_or_unit_invented(self, plan, view):
        inventory = {e["pim_canonical_id"]: e for e in plan["inventory"]}
        for meta in view.iter_scope_metas():
            assert meta.canonical_id in inventory
        # no object-level leaves are invented below unit scope nodes
        for scope in view.workspace.top_level_scopes:
            for nested in scope.iter_scopes():
                assert nested.objects == ()


class TestContainment:
    def test_each_node_has_exactly_one_containment_parent(self, view):
        for scope, parent_path in _scopes_with_parents(view.workspace):
            if parent_path is None:
                # top-level scope: single parent is the workspace root
                assert scope.path.parent == StructuralPath((SHWTP_WORKSPACE_ID,))
            else:
                assert scope.path.parent == parent_path
                parent = view.workspace.find_scope_by_path(parent_path)
                assert parent is not None
                assert scope.path in {c.path for c in parent.children}

    def test_containment_is_a_tree_no_shared_children(self, view):
        seen: set[StructuralPath] = set()
        for scope, _parent in _scopes_with_parents(view.workspace):
            assert scope.path not in seen, "node reachable from two parents"
            seen.add(scope.path)


class TestRolesAndModes:
    def test_container_only_areas_are_non_executable(self, view):
        for meta in view.iter_scope_metas():
            if meta.canonical_id.startswith("AREA-"):
                # process areas are container_only; ELECTRICAL/AUTOMATION are
                # reference_only areas — all are CONTAINER_ONLY structural mode.
                assert meta.role in {"container_only", "reference_only"}, meta
                scope = view.workspace.find_scope_by_path(meta.path)
                assert scope is not None
                assert scope.mode is ScopeMode.CONTAINER_ONLY
                assert scope.is_container_only
                assert not scope.is_executable_capable

    def test_object_and_reference_only_nodes_are_non_executable(self, view):
        for meta in view.iter_scope_metas():
            if meta.role in {"object_only", "reference_only"}:
                scope = view.workspace.find_scope_by_path(meta.path)
                assert scope is not None
                assert scope.mode is ScopeMode.CONTAINER_ONLY
                assert not scope.is_executable_capable

    def test_executable_candidates_classification_only(self, view):
        candidates = set()
        for meta in view.iter_scope_metas():
            if meta.role == "executable_candidate":
                candidates.add(meta.canonical_id)
                scope = view.workspace.find_scope_by_path(meta.path)
                assert scope is not None
                # classification only: capability declared, nothing runtime
                assert scope.mode is ScopeMode.EXECUTABLE_CAPABLE
                assert scope.is_executable_capable
                assert not scope.is_container_only
                assert scope.objects == ()
                assert scope.children == ()
        assert candidates == set(SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS) == {
            "UNIT-SHW-L1-T106",
            "UNIT-SHW-L1-T108",
            "UNIT-SHW-WASH-T110",
        }


class TestIdentitySeparation:
    def test_local_ids_distinct_from_canonical_ids(self, view):
        for meta in view.iter_scope_metas():
            assert meta.scope_id != meta.canonical_id
            assert meta.scope_id == vf_local_id(meta.canonical_id)
            scope = view.workspace.find_scope_by_path(meta.path)
            assert scope is not None
            assert scope.scope_id == meta.scope_id
            assert scope.path.as_string().startswith("shwtp/")

    def test_no_scope_is_identified_by_a_canonical_id(self, view):
        canonical_ids = {meta.canonical_id for meta in view.iter_scope_metas()}
        canonical_ids.add(SHWTP_PLANT_CANONICAL_ID)
        for scope, _parent in _scopes_with_parents(view.workspace):
            assert scope.scope_id not in canonical_ids


class TestMetadata:
    def test_canonical_pim_references_are_explicit_read_only(self, plan, view):
        inventory = _inventory_by_id(plan)
        for meta in view.iter_scope_metas():
            assert meta.canonical_id
            assert meta.inventory_id in inventory
            assert meta.pim_reference  # points back to pinned PIM artifact
            # role/fidelity/evidence/gaps exactly preserved from G10
            entry = inventory[meta.inventory_id]
            assert meta.role == entry["vf_scope_role"]
            assert meta.fidelity_ceiling == entry["fidelity_ceiling"]
            assert meta.evidence_status == entry["evidence"]["status"]
            assert meta.confidence == entry["evidence"]["confidence"]
            assert tuple(sorted(meta.gaps)) == tuple(sorted(entry.get("gaps", [])))

    def test_fidelity_ceilings_preserved_exactly(self, view):
        allowed = {
            "UNIT-SHW-L1-T106": "LogicalOnly",
            "UNIT-SHW-L1-T108": "FirstOrderReady",
            "UNIT-SHW-WASH-T110": "FirstOrderReady",
        }
        for meta in view.iter_scope_metas():
            if meta.canonical_id in allowed:
                assert meta.fidelity_ceiling == allowed[meta.canonical_id]
            else:
                assert meta.fidelity_ceiling in {
                    "LogicalOnly",
                    "NotReady",
                }, meta
        # no ParameterizedReady / CalibratedReady anywhere in SH-WTP
        for meta in view.iter_scope_metas():
            assert meta.fidelity_ceiling not in {
                "ParameterizedReady",
                "CalibratedReady",
            }


class TestAuthorization:
    def test_not_authorized_preserved(self, view):
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert view.plant_meta.runtime_authorization == "NOT_AUTHORIZED"
        for meta in view.iter_scope_metas():
            assert meta.runtime_authorization == "NOT_AUTHORIZED"
        auth = view.serialize()["authorization"]
        assert auth["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert auth["structural_construction"] == SHWTP_STRUCTURAL_AUTHORIZED_IN_G11 == "AUTHORIZED_IN_G11"
        assert (
            auth["synthetic_reference_execution"]
            == SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW
            == "PENDING_LATER_PIM_REVIEW"
        )
        assert auth["site_authorized_execution"] == SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"


class TestNoConnectivity:
    def test_containment_not_interpreted_as_connectivity(self, view):
        blob = json.dumps(view.serialize())
        for token in ("connectivity", "edge", "material_flow", "chemical_flow"):
            assert token.lower() not in blob.lower()

    def test_no_flow_inferred_from_containment(self, view):
        for scope, _parent in _scopes_with_parents(view.workspace):
            # a child scope is a contained unit, never a flow destination
            assert "flow" not in scope.scope_id.lower()


class TestNoRuntime:
    def test_no_fake_runtime_attached_to_nodes(self, view):
        # generic G1 model fields only; no runtime fields may exist
        for scope, _parent in _scopes_with_parents(view.workspace):
            for attr in (
                "engine",
                "bridge",
                "solver",
                "behavior",
                "advance",
                "step",
                "runtime",
            ):
                assert not hasattr(scope, attr)
            assert scope.objects == ()

    def test_no_shwtp_runtime_participant_in_g7_run_control(self):
        import virtual_factory.runcontrol as rc

        assert not any("shwtp" in name.lower() for name in dir(rc))
        source = inspect.getsource(shwtp_structural)
        for token in ("RunLifecycleService", "ExecutionBridge", "RunRecord"):
            assert token not in source

    def test_no_shwtp_domain_state_can_advance(self, view):
        source = inspect.getsource(shwtp_structural)
        for token in ("def advance", "def step", "RuntimeService", "SimulationEngine"):
            assert token not in source
        # nothing here creates a lifecycle/run-control service
        assert not hasattr(view.workspace, "start")
        assert not hasattr(view.workspace, "advance")

    def test_no_g12_connectivity_or_runtime_implementation(self):
        source = inspect.getsource(shwtp_structural)
        # the structural module must not import runtime/connectivity modules
        for token in (
            "from virtual_factory.runcontrol",
            "from virtual_factory.composition",
            "from virtual_factory.semantic",
            "from virtual_factory.equipment",
            "from virtual_factory.control",
        ):
            assert token not in source
        # no runtime/connectivity classes or state functions are defined here
        runtime_class_tokens = {
            "engine",
            "bridge",
            "solver",
            "coordinator",
            "connectivity",
            "participant",
        }
        defined_classes = {
            name
            for name, obj in vars(shwtp_structural).items()
            if inspect.isclass(obj)
        }
        assert not runtime_class_tokens & {n.lower() for n in defined_classes}
        defined_funcs = {
            name
            for name, obj in vars(shwtp_structural).items()
            if inspect.isfunction(obj)
        }
        assert not (defined_funcs & {"advance", "step", "start", "run"})


class TestExistingBehaviorUnchanged:
    def test_tipa_continuous_behavior_unchanged_by_shwtp_construction(self):
        continuous = build_continuous_workspace()
        assert continuous.workspace_id == "continuous"
        assert [s.scope_id for s in continuous.top_level_scopes] == ["PROCESS"]
        proc = continuous.find_scope("PROCESS")
        assert proc is not None
        assert proc.is_executable_capable

    def test_shwtp_is_not_registered_anywhere_in_runcontrol(self):
        import virtual_factory.runcontrol as rc

        assert "shwtp" not in dir(rc)
