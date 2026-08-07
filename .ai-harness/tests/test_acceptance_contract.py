"""Test acceptance contract completeness and phase-aware evaluation."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from evaluate_acceptance import evaluate_acceptance


class TestC04ContractCompleteness:
    def test_c04_has_executable_rules(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C04.json") as f:
            contract = json.load(f)
        for c in contract["acceptance_criteria"]:
            assert "rule" in c, f"{c['id']} missing rule"

    def test_c04_no_duplicate_in_classifications(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C04.json") as f:
            contract = json.load(f)
        rule_ids = {c["id"] for c in contract["acceptance_criteria"]}
        classified = set(contract.get("_classifications", {}).keys())
        overlap = rule_ids & classified
        assert not overlap, f"IDs in both rules and classifications: {overlap}"
    def test_c03_has_executable_rules(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        criteria = contract["acceptance_criteria"]
        for c in criteria:
            assert "rule" in c, f"{c['id']} missing rule"
            assert "field" in c["rule"], f"{c['id']} missing field"
            assert "operator" in c["rule"], f"{c['id']} missing operator"

    def test_c03_no_unsupported_operators(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        from evaluate_acceptance import _OPERATORS
        for c in contract["acceptance_criteria"]:
            op = c["rule"]["operator"]
            assert op in _OPERATORS, f"{c['id']}: unsupported operator '{op}'"

    def test_c03_no_duplicate_ids(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        ids = [c["id"] for c in contract["acceptance_criteria"]]
        assert len(ids) == len(set(ids)), f"Duplicates: {[x for x in ids if ids.count(x) > 1]}"

    def test_c03_phases_are_valid(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        for c in contract["acceptance_criteria"]:
            assert c["phase"] in ("pre_status", "final"), f"{c['id']}: invalid phase '{c['phase']}'"

    def test_c04_all_f01_f80_accounted_once(self):
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C04.json") as f:
            contract = json.load(f)
        rule_ids = {c["id"] for c in contract["acceptance_criteria"]}
        classified = set(contract.get("_classifications", {}).keys())
        # No ID in both
        overlap = rule_ids & classified
        assert not overlap, f"IDs in both rules and classifications: {overlap}"
        # All F01-F80 accounted
        all_ids = rule_ids | classified
        for i in range(1, 81):
            fid = f"F{i:02d}"
            assert fid in all_ids, f"{fid} not accounted for"


class TestPhaseAwareEvaluation:
    def test_pre_status_evaluates_before_derivation(self):
        evidence = {"repository": "hieudovn/virtual-factory", "pull_request": {"state": "OPEN", "merged": False, "number": 4},
                     "forbidden_actions": {"performed": False}, "preflight": {"current_branch": "chore/test", "working_tree_clean": True, "baseline_match": True},
                     "implementation": {"commit_exists_remotely": True, "remote_branch_head": "abc123"},
                     "tests": {"collected": 100, "result": "PASS"}, "ci": {"run_id": 123, "conclusion": "success", "head_sha": "abc"},
                     "smoke_checks": [{"result": "PASS"}], "pipeline_steps": [{"name": "x"}],
                     "tool_failures": [], "blocking_issues": [], "unknown_evidence": [], "contradictions": [],
                     "exit_code": None, "requested_gate_satisfied": False, "derived_status": "", "requested_gate": ""}
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        results = evaluate_acceptance(evidence, contract, phase="pre_status")
        fails = [r for r in results if r["result"] == "FAIL"]
        unknowns = [r for r in results if r["result"] == "UNKNOWN"]
        assert len(fails) == 0, [r["id"] for r in fails]
        assert len(unknowns) == 0, [r["id"] for r in unknowns]
        assert len(results) > 0

    def test_final_assertion_evaluated_after_exit(self):
        evidence = {"exit_code": 0, "requested_gate_satisfied": True,
                     "derived_status": "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
                     "requested_gate": "ready_for_sa_review", "pull_request": {"merged": False}}
        with open(Path(__file__).parent.parent / "tasks" / "VF-AI-HARNESS-01-C03.json") as f:
            contract = json.load(f)
        results = evaluate_acceptance(evidence, contract, phase="final")
        fails = [r for r in results if r["result"] == "FAIL"]
        unknowns = [r for r in results if r["result"] == "UNKNOWN"]
        assert len(fails) == 0, [r["id"] for r in fails]
        assert len(unknowns) == 0, [r["id"] for r in unknowns]
        assert len(results) > 0

    def test_unknown_pre_status_prevents_ready(self):
        evidence = {"repository": "wrong/repo"}
        contract = {"acceptance_criteria": [
            {"id": "F01", "phase": "pre_status", "rule": {"field": "repository", "operator": "equals", "expected": "hieudovn/virtual-factory"}}
        ]}
        results = evaluate_acceptance(evidence, contract, phase="pre_status")
        assert results[0]["result"] == "FAIL"
