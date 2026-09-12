"""VF-vNEXT-G17A — Post-G16 Platform Workstream Independence Review tests.

Proves (Issue #68 required): external PIM blocker reference + verdict recorded;
required VF base pinned; every required workstream has exactly one classification
with a full decision record; all 23 workstreams present; topology distinction
(PIM_AUTHORITATIVE_TOPOLOGY vs VF_SCENARIO_ASSUMED_TOPOLOGY) present; exactly one
recommended next gate satisfying all seven selection criteria; authority
unchanged (vf_runtime_authorization / site_authorized_execution /
whole_plant_runtime all NOT_AUTHORIZED); and G17A itself did NOT change runtime
behavior (frozen G4/G7/G14A/G14B/G15 constants and structures unchanged).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from virtual_factory.shwtp import (
    SHWTP_FEDERATION_COUPLING_POLICY,
    ShwtpEvaluator,
    ShwtpFederationConfig,
    build_shwtp_f01_projection,
    build_shwtp_workspace,
)
from virtual_factory.shwtp.connectivity import (
    SHWTP_PIM_AUTHORITY,
    SHWTP_PIM_MAIN_SHA,
    SHWTP_SYNTHETIC_REFERENCE_EXECUTION,
)
from virtual_factory.shwtp.projection import SHWTP_F01_BINDING_ID
from virtual_factory.shwtp.structural import (
    SHWTP_RUNTIME_AUTHORIZATION,
    SHWTP_SITE_AUTHORIZED_EXECUTION,
    SHWTP_WORKSPACE_ID,
)
from virtual_factory.composition import (
    BoundaryTransfer,
    CompositionGraph,
    Coordinator,
    ExecutableParticipant,
)
from virtual_factory.runcontrol import RunState

REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    REPO_ROOT / "configs" / "vnext" / "shwtp"
    / "shwtp_workstream_independence_review.json"
)

CLASSIFICATIONS = {
    "CAN_PROCEED_INDEPENDENTLY",
    "BLOCKED_BY_PIM_EVIDENCE",
    "SHOULD_WAIT_FOR_RUNTIME_EXPANSION",
}

REQUIRED_RECORD_FIELDS = {
    "id",
    "name",
    "classification",
    "readiness",
    "dependencies",
    "plant_truth_required",
    "architecture_risk_if_done_now",
    "rationale",
    "priority",
    "future_model",
}

REQUIRED_WORKSTREAM_IDS = {f"WS-{i:02d}" for i in range(1, 24)}

BLOCKED_IDS = {"WS-19", "WS-20", "WS-21", "WS-22", "WS-23"}
SHOULD_WAIT_IDS = {"WS-11", "WS-12"}

SEVEN_CRITERIA = [
    "independent of unresolved T108->DIST-P108 semantic authority",
    "materially reduces risk for future whole-plant federation",
    "does not broaden SH-WTP runtime authorization",
    "does not require new plant physics or topology truth",
    "preserves CompositionGraph != execution order",
    "preserves coupling policy as orchestration policy",
    "does not redesign G4",
]

FIVE_CONSTRAINTS = [
    "PIM relation != VF scenario assumption",
    "assumption is explicit / versioned / provenanced / reversible",
    "CompositionGraph != semantic authority",
    "no broad whole-plant runtime authorization",
    "no silent promotion of assumption to site truth",
]


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def _ws_by_id(review: dict, ws_id: str) -> dict:
    for w in review["workstreams"]:
        if w["id"] == ws_id:
            return w
    raise KeyError(ws_id)


class TestArtifactIdentity:
    def test_schema_and_gate(self, review):
        assert review["schema"] == "vf.vnext.g17a.workstream_independence_review.v1"
        assert review["gate"] == "VF-vNEXT-G17A"
        assert review["kind"] == "PLANNING_REVIEW_ONLY"
        assert review["version"] == "1.0.0"

    def test_base_is_g16_accepted_head(self, review):
        assert review["base"] == "732decd68a02af6f0ee1de1e830631747a99d060"

    def test_external_pim_blocker_reference(self, review):
        pins = review["external_pim_evidence"]
        assert pins["pim_repository"] == "hieudovn/plant-intelligence-model"
        assert pins["pim_evidence_commit"] == "d10049801a1eb022a7fa2e83badabefb92fb7412"
        assert pins["evidence_verdict"] == "T108-DIST-EVIDENCE — STILL_INSUFFICIENT"
        assert pins["blocked_dependency"] == "UNIT-SHW-L1-T108 -> UNIT-SHW-DIST-P108"
        assert pins["pim_not_modified"] is True

    def test_authority_unchanged(self, review):
        auth = review["authority"]
        assert auth["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert auth["site_authorized_execution"] == "NOT_AUTHORIZED"
        assert auth["whole_plant_runtime"] == "NOT_AUTHORIZED / NOT_IMPLEMENTED"

    def test_classification_vocabulary_exact(self, review):
        assert set(review["classification_vocabulary"]["values"]) == CLASSIFICATIONS


class TestWorkstreamCoverage:
    def test_all_23_workstreams_present(self, review):
        actual = {w["id"] for w in review["workstreams"]}
        assert actual == REQUIRED_WORKSTREAM_IDS

    def test_each_workstream_has_full_record(self, review):
        for w in review["workstreams"]:
            assert REQUIRED_RECORD_FIELDS <= set(w.keys()), w["id"]
            assert w["classification"] in CLASSIFICATIONS, w["id"]
            assert isinstance(w["dependencies"], list)
            assert isinstance(w["plant_truth_required"], bool)
            assert w["future_model"] in {"Flash", "Pro"}

    def test_classification_counts(self, review):
        counts = {c: 0 for c in CLASSIFICATIONS}
        for w in review["workstreams"]:
            counts[w["classification"]] += 1
        assert counts["CAN_PROCEED_INDEPENDENTLY"] == 16
        assert counts["BLOCKED_BY_PIM_EVIDENCE"] == 5
        assert counts["SHOULD_WAIT_FOR_RUNTIME_EXPANSION"] == 2

    def test_blocked_set_exact(self, review):
        blocked = {
            w["id"]
            for w in review["workstreams"]
            if w["classification"] == "BLOCKED_BY_PIM_EVIDENCE"
        }
        assert blocked == BLOCKED_IDS
        for ws_id in blocked:
            assert _ws_by_id(review, ws_id)["plant_truth_required"] is True

    def test_should_wait_set_exact(self, review):
        wait = {
            w["id"]
            for w in review["workstreams"]
            if w["classification"] == "SHOULD_WAIT_FOR_RUNTIME_EXPANSION"
        }
        assert wait == SHOULD_WAIT_IDS


class TestTopologyDistinction:
    def test_topology_distinction_present(self, review):
        topo = review["topology_distinction"]
        assert "PIM_AUTHORITATIVE_TOPOLOGY" in topo
        assert "VF_SCENARIO_ASSUMED_TOPOLOGY" in topo

    def test_pim_authoritative_blocked(self, review):
        pim_topo = review["topology_distinction"]["PIM_AUTHORITATIVE_TOPOLOGY"]
        assert pim_topo["status_for_t108_to_dist_p108"] == (
            "STILL_BLOCKED — exact relation and ProcessConnection endpoint "
            "NOT ESTABLISHED by PIM."
        )

    def test_scenario_assumed_constraints(self, review):
        vf_topo = review["topology_distinction"]["VF_SCENARIO_ASSUMED_TOPOLOGY"]
        assert set(vf_topo["constraints"]) == set(FIVE_CONSTRAINTS)
        assert vf_topo["no_back_propagation"]


class TestRecommendedNextGate:
    def test_exactly_one_recommended_next_gate(self, review):
        gate = review["recommended_next_gate"]
        assert gate["id"] == "VF-vNEXT-G18"
        assert gate["not_authorized_in_g17a"] is True
        assert gate["future_model"] == "Pro"

    def test_all_seven_criteria_satisfied(self, review):
        gate = review["recommended_next_gate"]
        got = [c["criterion"] for c in gate["criteria_satisfaction"]]
        assert got == SEVEN_CRITERIA
        assert all(c["satisfied"] is True for c in gate["criteria_satisfaction"])

    def test_must_preserve_constraints(self, review):
        gate = review["recommended_next_gate"]
        assert set(gate["must_preserve"]) == set(FIVE_CONSTRAINTS)

    def test_next_gate_is_not_blocked_plant_work(self, review):
        title = review["recommended_next_gate"]["title"].lower()
        for banned in ("dist-p108", "t110", "whole-plant", "line 2", "chemical",
                       "electrical", "automation"):
            assert banned not in title


class TestNoRuntimeChange:
    def test_coupling_policy_frozen(self):
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"

    def test_g14a_f01_binding_frozen(self):
        proj = build_shwtp_f01_projection()
        assert proj.binding.edge_id == SHWTP_F01_BINDING_ID
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

    def test_authority_flags_frozen(self):
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"
        assert SHWTP_SYNTHETIC_REFERENCE_EXECUTION == "PENDING_LATER_PIM_REVIEW"
        assert SHWTP_WORKSPACE_ID == "shwtp"

    def test_pim_authority_pins_frozen(self):
        assert SHWTP_PIM_AUTHORITY == "hieudovn/plant-intelligence-model"
        assert SHWTP_PIM_MAIN_SHA == "ec7f1266d4a19e5201b689874a2a7a75a022fc5c"

    def test_g4_and_g7_surfaces_importable(self):
        assert ExecutableParticipant is not None
        assert BoundaryTransfer is not None
        assert CompositionGraph is not None
        assert Coordinator is not None
        assert {s.value for s in RunState} == {
            "created", "running", "paused", "stopped", "failed",
        }

    def test_g15_evaluator_surface_importable(self):
        assert ShwtpEvaluator is not None
        assert ShwtpFederationConfig is not None

    def test_shwtp_workspace_still_builds(self):
        ws = build_shwtp_workspace()
        assert ws.workspace_id == "shwtp"
