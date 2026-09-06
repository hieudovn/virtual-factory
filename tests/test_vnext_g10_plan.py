"""VF-vNEXT-G10 — SH-WTP Runtime Readiness & Scope Freeze invariant tests (Issue #55).

PLANNING-ONLY gate. These tests prove the deterministic, evidence-traceable
scope/readiness freeze held in ``configs/vnext/shwtp/shwtp_readiness_scope.json``:

- every inventory entry is traceable to pinned PIM evidence (no invented truth);
- no candidate exceeds its evidence-supported fidelity ceiling;
- no ParameterizedReady / CalibratedReady fabrication;
- ``NOT_AUTHORIZED`` is preserved and still fails closed through the G9 semantic
  admission seam (structural planning is not runtime authorization);
- container vs executable roles are explicit and distinct;
- boundary-contract fields carry provenance (PIM-supported / synthetic / unknown);
- containment is a structural tree distinct from connectivity;
- cross-area relations are allowed to be many-to-many (no A->B->C flattening);
- no G11 runtime / site-faithful execution is authorized by this plan.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from virtual_factory.semantic import (
    CompatibilityDecision,
    RuntimeAuthorization,
    SemanticAdmissionError,
    SemanticAdmissionGate,
    load_binding_artifact,
)

PLAN_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_readiness_scope.json"
)

SEMANTIC_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "semantic"
    / "song_hong_wtp_export_v0_1.yaml"
)

VALID_ROLES = {
    "container_only",
    "object_only",
    "reference_only",
    "executable_candidate",
}

VALID_SUPPORT = {
    "PIM-supported",
    "VF synthetic assumption",
    "unknown/blocking",
}

FIDELITY_ORDER = [
    "NotReady",
    "LogicalOnly",
    "FirstOrderReady",
    "ParameterizedReady",
    "CalibratedReady",
]


@pytest.fixture(scope="module")
def plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _inventory(plan: dict) -> list[dict]:
    return plan["inventory"]


def _fidelity_rank(level: str) -> int:
    return FIDELITY_ORDER.index(level)


class TestEvidenceTraceability:
    def test_every_inventory_entry_has_pim_reference_and_evidence(self, plan):
        for entry in _inventory(plan):
            assert entry["pim_canonical_id"], entry
            assert entry["pim_reference"], entry
            assert entry["evidence"]["status"] in {
                "DocumentConfirmed",
                "PatternInferred",
                "IndustryExpected",
            }, entry

    def test_inventory_ids_are_distinct_and_reference_pim_ids(self, plan):
        ids = [e["id"] for e in _inventory(plan)]
        assert len(ids) == len(set(ids))
        for entry in _inventory(plan):
            assert entry["pim_canonical_id"].startswith(("PLANT-", "AREA-", "UNIT-"))


class TestFidelityFreeze:
    def test_no_entry_exceeds_its_allowed_ceiling(self, plan):
        for entry in _inventory(plan):
            ceiling = entry["fidelity_ceiling"]
            if entry["pim_canonical_id"] in {"UNIT-SHW-L1-T108", "UNIT-SHW-WASH-T110"}:
                assert ceiling == "FirstOrderReady", entry
            elif entry["pim_canonical_id"] == "UNIT-SHW-L1-T106":
                assert ceiling == "LogicalOnly", entry
            else:
                assert _fidelity_rank(ceiling) <= _fidelity_rank("LogicalOnly"), entry

    def test_no_parameterized_or_calibrated_anywhere(self, plan):
        for entry in _inventory(plan):
            assert entry["fidelity_ceiling"] not in {
                "ParameterizedReady",
                "CalibratedReady",
            }, entry
        matrix = plan["fidelity_matrix"]
        assert matrix["ParameterizedReady"]["scope"] == []
        assert matrix["CalibratedReady"]["scope"] == []

    def test_first_order_scope_is_exactly_the_two_simple_tanks(self, plan):
        assert plan["fidelity_matrix"]["FirstOrderReady"]["scope"] == [
            "UNIT-SHW-L1-T108",
            "UNIT-SHW-WASH-T110",
        ]


class TestAuthorizationSeparation:
    def test_not_authorized_preserved(self, plan):
        assert plan["authorization"]["vf_runtime_authorization"] == "NOT_AUTHORIZED"

    def test_structural_planning_is_not_runtime_authorization(self, plan):
        sep = plan["authz_separation"]
        assert sep["structural_planning"] == "ALLOWED_IN_G10_G11"
        assert sep["runtime_authorization"] == "NOT_AUTHORIZED"
        assert sep["site_authorized_execution"] == "NOT_AUTHORIZED"

    def test_pinned_semantic_binding_still_fails_closed(self):
        binding = load_binding_artifact(SEMANTIC_FIXTURE)
        assert binding.compatibility is CompatibilityDecision.COMPATIBLE_WITH_CONSTRAINTS
        assert binding.runtime_authorization is RuntimeAuthorization.NOT_AUTHORIZED
        with pytest.raises(SemanticAdmissionError):
            SemanticAdmissionGate(binding).assert_admittable()


class TestRoleSeparation:
    def test_roles_are_valid_and_both_container_and_executable_exist(self, plan):
        entries = _inventory(plan)
        roles = {e["vf_scope_role"] for e in entries}
        assert roles <= VALID_ROLES
        assert "container_only" in roles
        assert "executable_candidate" in roles

    def test_areas_are_container_only_and_plant_root_is_container_only(self, plan):
        for entry in _inventory(plan):
            cid = entry["pim_canonical_id"]
            if cid == "PLANT-SHW":
                assert entry["vf_scope_role"] == "container_only", entry
            elif cid in {"AREA-SHW-ELECTRICAL", "AREA-SHW-AUTOMATION"}:
                assert entry["vf_scope_role"] == "reference_only", entry
            elif cid.startswith("AREA-"):
                assert entry["vf_scope_role"] == "container_only", entry


class TestBoundaryContractProvenance:
    def test_every_boundary_field_has_valid_support_tag(self, plan):
        contracts = plan["boundary_contracts_v0"]
        assert set(contracts.keys()) == {
            "policy",
            "UNIT-SHW-L1-T108",
            "UNIT-SHW-WASH-T110",
            "UNIT-SHW-L1-T106",
        }
        for key in (
            "UNIT-SHW-L1-T108",
            "UNIT-SHW-WASH-T110",
            "UNIT-SHW-L1-T106",
        ):
            for section in ("inputs", "outputs", "properties", "behavior"):
                for field in contracts[key][section]:
                    assert field["support"] in VALID_SUPPORT, (key, field)

    def test_unknown_fields_are_explicitly_marked_unknown(self, plan):
        contracts = plan["boundary_contracts_v0"]
        supports = [
            f["support"]
            for key in (
                "UNIT-SHW-L1-T108",
                "UNIT-SHW-WASH-T110",
                "UNIT-SHW-L1-T106",
            )
            for section in ("inputs", "outputs", "properties", "behavior")
            for f in contracts[key][section]
        ]
        assert "unknown/blocking" in supports


class TestTopologyRules:
    def test_containment_is_distinct_from_connectivity(self, plan):
        rules = plan["relation_classes"]["topology_rules"]
        assert "containment" in rules["containment_vs_connectivity"].lower()
        assert "connectivity" in rules["containment_vs_connectivity"].lower()

    def test_many_to_many_not_prohibited_and_no_flattening(self, plan):
        rules = plan["relation_classes"]["topology_rules"]
        assert rules["many_to_many_allowed"] is True
        assert rules["no_flattening"]

    def test_relation_classes_include_cross_area_classes(self, plan):
        class_ids = {c["id"] for c in plan["relation_classes"]["classes"]}
        assert {
            "material_flow",
            "chemical_flow",
            "sludge_waste_flow",
            "utility_energy_flow",
            "control_information_flow",
            "dependency_constraint",
        } <= class_ids


class TestNoG11Runtime:
    def test_g11_execution_modes_do_not_authorize_site_execution(self, plan):
        modes = plan["g11_admission_plan"]["execution_modes"]
        assert modes["structural_construction"] == "AUTHORIZED_IN_G11"
        assert modes["synthetic_reference_execution"] == "PENDING_LATER_PIM_REVIEW"
        assert modes["site_authorized_execution"] == "NOT_AUTHORIZED"

    def test_parameterized_and_calibrated_prohibited_in_g11(self, plan):
        prohibited = " ".join(plan["g11_admission_plan"]["prohibited_until_site_evidence"])
        assert "Calibration" in prohibited
        assert "ParameterizedReady" in prohibited
        assert "CalibratedReady" in prohibited
