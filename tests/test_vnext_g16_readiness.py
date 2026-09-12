"""VF-vNEXT-G16 — SH-WTP whole-plant federation expansion readiness tests.

Proves (Issue #67 required tests): source pins exact; every reviewed unit has
exactly one decision; all G10 first-slice candidates represented; T106/T108
remain accepted existing runtime candidates; T110 blocked; no
PatternInferred/IndustryExpected unit promoted to next slice; every future
candidate has a boundary-contract plan; unknowns explicit; no fabricated site
values; projection candidates reference exact PIM relation ids; no G4 binding
created in G16; no generic FLOWS_TO auto-projection; whole-plant runtime remains
NOT_AUTHORIZED/NOT_IMPLEMENTED; exactly one next-slice recommendation; next slice
not T110; no G14/G15 behavior changed; no G4/G7/PIM modification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from virtual_factory.shwtp import (
    ShwtpEvaluator,
    ShwtpFederationConfig,
    build_shwtp_f01_projection,
    build_shwtp_workspace,
)
from virtual_factory.shwtp.connectivity import (
    SHWTP_PIM_AUTHORITY,
    SHWTP_PIM_MAIN_SHA,
    SHWTP_SELECTED_RELATIONSHIPS,
    SHWTP_SYNTHETIC_REFERENCE_EXECUTION,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = REPO_ROOT / "configs" / "vnext" / "shwtp" / "shwtp_expansion_readiness.json"
G10_PATH = REPO_ROOT / "configs" / "vnext" / "shwtp" / "shwtp_readiness_scope.json"
G12C_PATH = REPO_ROOT / "configs" / "vnext" / "shwtp" / "shwtp_synthetic_runtime_admission.json"

DECISIONS = {
    "NEXT_SLICE_CANDIDATE",
    "LATER_CANDIDATE",
    "STRUCTURAL_ONLY",
    "REFERENCE_ONLY",
    "BLOCKED_PENDING_EVIDENCE",
}

FIRST_SLICE_CANDIDATES = {
    "UNIT-SHW-L1-T106",
    "UNIT-SHW-L1-T108",
    "UNIT-SHW-WASH-T110",
}

REVIEWED_UNIT_CANONICAL_IDS = {
    # main spine
    "UNIT-SHW-RAW-INTAKE",
    "UNIT-SHW-T100",
    "UNIT-SHW-L1-T101",
    "UNIT-SHW-L1-T109",
    "UNIT-SHW-L1-T102",
    "UNIT-SHW-L1-T103",
    "UNIT-SHW-L1-T104",
    "UNIT-SHW-L1-T105",
    "UNIT-SHW-L1-T106",
    "UNIT-SHW-L1-T107",
    "UNIT-SHW-L1-T108",
    "UNIT-SHW-DIST-P108",
    # side systems
    "UNIT-SHW-WASH-T110",
    "UNIT-SHW-SLUDGE-T201",
    "UNIT-SHW-CHEM-DOSING",
    # reference domains
    "UNIT-SHW-L2-T101",
    "UNIT-SHW-L2-T105",
    "UNIT-SHW-L2-T106",
    "UNIT-SHW-L2-T108",
    "UNIT-SHW-ELEC-MCC",
    "UNIT-SHW-AUTO-PLC",
}


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(READINESS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def g10() -> dict:
    return json.loads(G10_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def g12c() -> dict:
    return json.loads(G12C_PATH.read_text(encoding="utf-8"))


def _unit_by_id(artifact, canonical_id):
    for u in artifact["reviewed_units"]:
        if u["canonical_id"] == canonical_id:
            return u
    raise KeyError(canonical_id)


class TestSourcePins:
    def test_pim_pins_match_g10(self, artifact, g10):
        g10_src = g10["pim_source"]
        pins = artifact["source_pins"]
        assert pins["pim_repository"] == g10_src["repository"]
        assert pins["pim_main_sha"] == g10_src["repository_base_sha"]
        assert pins["pim_package"] == g10_src["export_package_id"]
        assert pins["pim_version"] == g10_src["export_version"]
        assert pins["pim_source_model"] == g10_src["source_model_version"]
        assert pins["pim_semantic_identity_sha"] == g10_src["semantic_model_identity_sha"]
        assert pins["pim_artifact_hash_sha"] == g10_src["export_artifact_hash_baseline_sha"]

    def test_pim_pins_match_g12b(self, artifact):
        pins = artifact["source_pins"]
        assert pins["pim_repository"] == SHWTP_PIM_AUTHORITY
        assert pins["pim_main_sha"] == SHWTP_PIM_MAIN_SHA
        assert pins["g12b_selected_relationship_ids"] == [
            rel.relationship_id for rel in SHWTP_SELECTED_RELATIONSHIPS
        ]


class TestDecisionCompleteness:
    def test_every_reviewed_unit_exactly_one_decision(self, artifact):
        reviewed_ids = {
            u["canonical_id"]
            for u in artifact["reviewed_units"]
            if u["canonical_id"] in REVIEWED_UNIT_CANONICAL_IDS
        }
        assert reviewed_ids == REVIEWED_UNIT_CANONICAL_IDS
        for u in artifact["reviewed_units"]:
            if u["canonical_id"] in REVIEWED_UNIT_CANONICAL_IDS:
                assert u["decision"] in DECISIONS
                # exactly one decision field (single value)
                assert isinstance(u["decision"], str)

    def test_first_slice_candidates_represented(self, artifact):
        represented = {u["canonical_id"] for u in artifact["reviewed_units"]}
        assert FIRST_SLICE_CANDIDATES <= represented

    def test_t106_t108_accepted_runtime_candidates(self, artifact):
        t106 = _unit_by_id(artifact, "UNIT-SHW-L1-T106")
        t108 = _unit_by_id(artifact, "UNIT-SHW-L1-T108")
        assert t106["runtime_status"] == "IMPLEMENTED_ACCEPTED"
        assert t108["runtime_status"] == "IMPLEMENTED_ACCEPTED"
        assert t106["fidelity_ceiling"] == "LogicalOnly"
        assert t108["fidelity_ceiling"] == "FirstOrderReady"

    def test_t110_blocked(self, artifact):
        t110 = _unit_by_id(artifact, "UNIT-SHW-WASH-T110")
        assert t110["decision"] == "BLOCKED_PENDING_EVIDENCE"
        assert t110["runtime_status"] == "BLOCKED_PENDING_EVIDENCE"

    def test_no_pattern_inferred_promoted_to_next_slice(self, artifact):
        next_ids = [
            u["canonical_id"]
            for u in artifact["reviewed_units"]
            if u["decision"] == "NEXT_SLICE_CANDIDATE"
        ]
        for cid in next_ids:
            u = _unit_by_id(artifact, cid)
            assert u["evidence_status"] == "DocumentConfirmed"
            assert u["confidence"] in ("medium", "high")
            assert "PatternInferred" != u["evidence_status"]
            assert "IndustryExpected" != u["evidence_status"]

    def test_decision_counts_consistent(self, artifact):
        counts = {}
        for u in artifact["reviewed_units"]:
            counts[u["decision"]] = counts.get(u["decision"], 0) + 1
        assert counts["NEXT_SLICE_CANDIDATE"] == 1
        assert counts["BLOCKED_PENDING_EVIDENCE"] == 1


class TestBoundaryContracts:
    def test_every_future_candidate_has_plan(self, artifact):
        for u in artifact["reviewed_units"]:
            if (
                u["decision"] in ("NEXT_SLICE_CANDIDATE", "LATER_CANDIDATE")
                and u["runtime_status"] == "NOT_IMPLEMENTED"
            ):
                plan = u.get("boundary_contract_v0_plan")
                assert plan is not None, u["canonical_id"]
                for key in (
                    "inputs",
                    "outputs",
                    "supported_properties",
                    "synthetic_assumptions",
                    "unknown_blocking",
                    "fidelity_ceiling",
                ):
                    assert key in plan, (u["canonical_id"], key)
                # unknowns explicit
                assert plan["unknown_blocking"]

    def test_no_fabricated_site_values(self, artifact):
        for u in artifact["reviewed_units"]:
            plan = u.get("boundary_contract_v0_plan")
            if plan is None:
                continue
            for text in (
                plan["inputs"] + plan["outputs"] + plan["supported_properties"]
                + plan["synthetic_assumptions"] + plan["unknown_blocking"]
            ):
                assert isinstance(text, str)
                # no numeric site truth asserted
                assert "measured" not in text.lower()
                assert "site value" not in text.lower()

    def test_t106_t108_contracts_are_implemented_not_replanned(self, artifact):
        for cid in ("UNIT-SHW-L1-T106", "UNIT-SHW-L1-T108"):
            u = _unit_by_id(artifact, cid)
            assert u["boundary_contract_status"] == "present_g10_v0_implemented"
            assert u["boundary_contract_v0_plan"] is None


class TestRelationProjectionPlan:
    def test_projection_plan_covers_exact_f01_f07(self, artifact):
        plan_ids = {
            r["relationship_id"]
            for r in artifact["relation_projection_plan"]
            if r["relationship_id"].startswith("REL-SHW-F")
        }
        assert plan_ids == {
            "REL-SHW-F01",
            "REL-SHW-F02",
            "REL-SHW-F03",
            "REL-SHW-F04",
            "REL-SHW-F05",
            "REL-SHW-F06",
            "REL-SHW-F07",
        }

    def test_f01_projected_g14a(self, artifact):
        f01 = next(
            r
            for r in artifact["relation_projection_plan"]
            if r["relationship_id"] == "REL-SHW-F01"
        )
        assert f01["projection_status"] == "PROJECTED_G14A"

    def test_no_generic_flows_to_auto_projection(self, artifact):
        # F06 and F07 are FLOWS_TO but REFERENCE_ONLY -> no auto FLOWS_TO rule.
        for rid in ("REL-SHW-F06", "REL-SHW-F07"):
            rel = next(
                r
                for r in artifact["relation_projection_plan"]
                if r["relationship_id"] == rid
            )
            assert rel["relation_type"] == "FLOWS_TO"
            assert rel["projection_status"] == "REFERENCE_ONLY"

    def test_no_g4_binding_created_in_g16(self, artifact):
        # G16 is a JSON planning artifact; it must not create G4 bindings/ports.
        proj = build_shwtp_f01_projection()
        assert len(proj.graph.bindings) == 1
        assert len(proj.ports) == 2
        # No conceptual port materialization beyond the planning text.
        for rel in artifact["relation_projection_plan"]:
            for key in ("source_id", "target_id"):
                # endpoints remain PIM ids, never fabricated VF PortRef strings.
                value = rel.get(key)
                if value and value.startswith("PROC-"):
                    assert "#" not in value


class TestNextSlice:
    def test_exactly_one_next_slice(self, artifact):
        next_ids = [
            u["canonical_id"]
            for u in artifact["reviewed_units"]
            if u["decision"] == "NEXT_SLICE_CANDIDATE"
        ]
        assert len(next_ids) == 1
        ns = artifact["next_slice"]
        assert ns["selected"] == next_ids[0]

    def test_next_slice_not_t110(self, artifact):
        assert artifact["next_slice"]["selected"] != "UNIT-SHW-WASH-T110"

    def test_next_slice_documented_and_bounded(self, artifact):
        ns = artifact["next_slice"]
        u = _unit_by_id(artifact, ns["selected"])
        assert u["decision"] == "NEXT_SLICE_CANDIDATE"
        assert u["fidelity_ceiling"] == "LogicalOnly"
        assert u["evidence_status"] == "DocumentConfirmed"
        assert u["requires_pim_decision_before_runtime"] is True
        assert u["boundary_contract_v0_plan"] is not None


class TestWholePlantStatus:
    def test_whole_plant_not_authorized(self, artifact):
        assert artifact["authority"]["whole_plant_runtime"] == "NOT_AUTHORIZED / NOT_IMPLEMENTED"
        assert artifact["authority"]["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert artifact["authority"]["site_authorized_execution"] == "NOT_AUTHORIZED"
        assert artifact["coverage_matrix"]["whole_plant_runtime"] == "NOT_AUTHORIZED / NOT_IMPLEMENTED"

    def test_vf_paths_resolve_in_g11(self, artifact):
        ws = build_shwtp_workspace()
        from virtual_factory.workspace import StructuralPath

        for u in artifact["reviewed_units"]:
            if u["vf_path"] is None:
                continue
            path = StructuralPath.from_string(u["vf_path"])
            assert ws.workspace.find_scope_by_path(path) is not None, u["vf_path"]


class TestNoBehaviorChange:
    def test_g14a_projection_unchanged(self):
        proj = build_shwtp_f01_projection()
        assert proj.record.projection_id == "PROJ-SHW-F01-T106-T108"
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

    def test_g15_evaluator_still_works(self):
        cfg = ShwtpFederationConfig(
            communication_step_s=1.0,
            initial_t108_inflow_m3_s=1.0,
            t106_inflow_m3_s=2.0,
            t108_requested_outflow_m3_s=0.5,
            t108_capacity_m3=100.0,
            t108_tank_area_m2=10.0,
            t108_initial_volume_m3=50.0,
        )
        ev = ShwtpEvaluator(cfg, window_count=2).run()
        assert len(ev.rows) == 2
        assert ev.summary.lag_windows == 1
        assert ev.summary.max_abs_mass_balance_residual_m3 == 0.0

    def test_authority_and_admission_unchanged(self, artifact, g12c):
        assert artifact["authority"]["vf_runtime_authorization"] == g12c["authority"]["vf_runtime_authorization"]
        assert g12c["authority"]["authorized_candidates"] == ["UNIT-SHW-L1-T106", "UNIT-SHW-L1-T108"]
        assert g12c["authority"]["blocked_candidates"] == ["UNIT-SHW-WASH-T110"]
        assert SHWTP_SYNTHETIC_REFERENCE_EXECUTION == "PENDING_LATER_PIM_REVIEW"
