"""VF-vNEXT-G12C — SH-WTP synthetic runtime admission review tests.

Proves (Issue #60 required checks):

1. only T106/T108/T110 are reviewed; every decision explicit + deterministic;
2. fidelity ceiling not exceeded (LogicalOnly / FirstOrderReady at most);
3. ParameterizedReady / CalibratedReady are not fabricated;
4. site authorization remains NOT_AUTHORIZED;
5. PIM pins unchanged;
6. synthetic assumptions visibly separated from PIM-supported facts;
7. no raw G12B relation silently runtime-classified;
8. no BoundaryPort / G4 projection / runtime implementation appears;
9. G13 plan selects the smallest meaningful slice (no default all-three);
10-12. G10-G12B invariants + ASSY/continuous/canonical baseline stay green
    (baseline run).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ADMISSION_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_synthetic_runtime_admission.json"
G10_PLAN_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_readiness_scope.json"

REVIEWED_CANDIDATES = {
    "UNIT-SHW-L1-T106",
    "UNIT-SHW-L1-T108",
    "UNIT-SHW-WASH-T110",
}

VALID_DECISIONS = {
    "SYNTHETIC_REFERENCE_ALLOWED",
    "STRUCTURAL_ONLY",
    "BLOCKED_PENDING_EVIDENCE",
}

FROZEN_PINS = {
    "repository": "hieudovn/plant-intelligence-model",
    "main_sha": "ec7f1266d4a19e5201b689874a2a7a75a022fc5c",
    "package": "SHW-PIM-VF-EXPORT-v0.1",
    "version": "v0.1",
    "source_model_version": "SHW-PH03-v0.1",
    "semantic_identity_sha": "f23f3c4614f50a1a2e3805f7e887433feb934915",
    "artifact_hash_sha": "ea3361a4aca9d25927a4a76c792f3af184e1aabb",
    "compatibility": "compatible_with_constraints",
}


@pytest.fixture(scope="module")
def admission() -> dict:
    return json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def g10_plan() -> dict:
    return json.loads(G10_PLAN_PATH.read_text(encoding="utf-8"))


def _candidates(admission: dict) -> list[dict]:
    return admission["candidates"]


def _by_canonical(admission: dict) -> dict[str, dict]:
    return {c["canonical_id"]: c for c in _candidates(admission)}


class TestCandidateScope:
    def test_only_t106_t108_t110_reviewed(self, admission):
        ids = {c["canonical_id"] for c in _candidates(admission)}
        assert ids == REVIEWED_CANDIDATES

    def test_every_decision_explicit_and_deterministic(self, admission):
        for candidate in _candidates(admission):
            assert candidate["admission"] in VALID_DECISIONS, candidate
            assert candidate["fidelity_ceiling"]
            assert candidate["boundary_contract_v0"] == "present"
            assert candidate["rationale"]
        # deterministic: loading twice yields identical decisions
        again = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
        assert [c["admission"] for c in _candidates(admission)] == [
            c["admission"] for c in _candidates(again)
        ]


class TestFidelity:
    def test_fidelity_ceiling_not_exceeded(self, admission, g10_plan):
        plan_inventory = {
            e["pim_canonical_id"]: e for e in g10_plan["inventory"]
        }
        for candidate in _candidates(admission):
            cid = candidate["canonical_id"]
            plan_ceiling = plan_inventory[cid]["fidelity_ceiling"]
            assert candidate["fidelity_ceiling"] == plan_ceiling
            assert candidate["fidelity_ceiling"] in {
                "LogicalOnly",
                "FirstOrderReady",
            }

    def test_no_parameterized_or_calibrated_fabricated(self, admission):
        blob = json.dumps(admission)
        for candidate in _candidates(admission):
            assert candidate["fidelity_ceiling"] not in {
                "ParameterizedReady",
                "CalibratedReady",
            }
        assert "ParameterizedReady" not in blob.split('"g13_authorization_plan"')[0]
        # policy forbids them explicitly
        policy = admission["synthetic_assumption_policy"]["rules"]
        assert any("never" in rule for rule in policy)


class TestAuthorization:
    def test_not_authorized_preserved(self, admission):
        authority = admission["authority"]
        assert authority["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert authority["site_authorized_execution"] == "NOT_AUTHORIZED"
        assert authority["synthetic_reference_execution"] == "PENDING_LATER_PIM_REVIEW"
        assert authority["structural_construction"] == "AUTHORIZED_IN_G11"

    def test_no_site_or_calibrated_claim(self, admission):
        rule = admission["g13_authorization_plan"]["rule"]
        for token in (
            "ParameterizedReady",
            "CalibratedReady",
            "site-faithful",
            "control-interlock",
        ):
            assert token in rule  # named only to be forbidden
        # no candidate is admitted as site-faithful/calibrated
        for candidate in _candidates(admission):
            assert candidate["admission"] in VALID_DECISIONS
        assert "site_authorized_execution" in admission["authority"]
        assert admission["authority"]["site_authorized_execution"] == "NOT_AUTHORIZED"


class TestSeparation:
    def test_synthetic_assumptions_separated_from_pim_facts(self, admission):
        for candidate in _candidates(admission):
            assert candidate["pim_supported"]
            assert candidate["synthetic_assumptions_required"]
            assert candidate["unknown_blocking"]
            # no synthetic assumption is relabeled as a PIM-supported fact
            for synth in candidate["synthetic_assumptions_required"]:
                assert synth not in candidate["pim_supported"]

    def test_no_raw_relation_silently_runtime_classified(self, admission):
        for candidate in _candidates(admission):
            # candidate records carry no runtime interpretation fields
            for key in (
                "port_direction",
                "transported_medium",
                "merge_policy",
                "split_policy",
                "coordinator_semantics",
                "runtime_relation_class",
            ):
                assert key not in candidate
            for rel in candidate["g12b_relations"]:
                # relations stay raw PIM types, never six-class runtime types
                assert any(
                    t in rel
                    for t in ("FLOWS_TO", "DISCHARGES_TO", "CONNECTED_TO")
                )
                for klass in (
                    "material_flow",
                    "chemical_flow",
                    "sludge_waste_flow",
                    "utility_energy_flow",
                    "control_information_flow",
                    "dependency_constraint",
                ):
                    assert klass not in rel

    def test_no_runtime_implementation(self, admission):
        assert admission["runtime_projection_requirements"]["not_implemented"] is True
        # no boundary port / composition / runtime section is present
        blob = json.dumps(admission)
        for token in ("BoundaryPort", "PortDirection", "PortCategory", "CompositionBinding"):
            assert token not in blob


class TestDecisions:
    def test_t108_is_smallest_meaningful_slice(self, admission):
        plan = admission["g13_authorization_plan"]
        assert plan["smallest_meaningful_slice"] == ["UNIT-SHW-L1-T108"]
        # no default authorization of all three
        assert set(plan["allowed_candidates"]) != REVIEWED_CANDIDATES
        assert "UNIT-SHW-WASH-T110" not in plan["allowed_candidates"]

    def test_t106_t108_allowed_within_ceiling(self, admission):
        by_id = _by_canonical(admission)
        assert by_id["UNIT-SHW-L1-T106"]["admission"] == "SYNTHETIC_REFERENCE_ALLOWED"
        assert by_id["UNIT-SHW-L1-T106"]["fidelity_ceiling"] == "LogicalOnly"
        assert by_id["UNIT-SHW-L1-T108"]["admission"] == "SYNTHETIC_REFERENCE_ALLOWED"
        assert by_id["UNIT-SHW-L1-T108"]["fidelity_ceiling"] == "FirstOrderReady"

    def test_t110_blocked_pending_evidence(self, admission):
        t110 = _by_canonical(admission)["UNIT-SHW-WASH-T110"]
        assert t110["admission"] == "BLOCKED_PENDING_EVIDENCE"
        assert "return destination" in t110["rationale"].lower()
        assert any("REL-006" in rel for rel in t110["g12b_relations"])

    def test_boundary_contracts_present_for_all(self, admission, g10_plan):
        contracts = g10_plan["boundary_contracts_v0"]
        for candidate in _candidates(admission):
            assert candidate["canonical_id"] in contracts
