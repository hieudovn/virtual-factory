"""Test evaluate_acceptance.py — rule-based acceptance evaluation."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from evaluate_acceptance import evaluate_acceptance


def _load(name: str) -> dict:
    p = Path(__file__).resolve().parent.parent / "examples" / name
    with open(p) as f:
        return json.load(f)


class TestEvaluateAcceptance:
    def test_equals_operator_passes(self):
        evidence = {"tests": {"passed": 100, "failed": 0}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "tests.passed", "operator": "equals", "expected": 100}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_equals_operator_fails(self):
        evidence = {"tests": {"passed": 50, "failed": 50}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "tests.passed", "operator": "equals", "expected": 100}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "FAIL"

    def test_is_true_operator(self):
        evidence = {"implementation": {"commit_exists_remotely": True}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "implementation.commit_exists_remotely", "operator": "is_true", "expected": None}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_is_false_operator(self):
        evidence = {"forbidden_actions": {"performed": False}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "forbidden_actions.performed", "operator": "is_false", "expected": None}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_unsupported_operator_unknown(self):
        evidence = {"x": 1}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "x", "operator": "fancy_check", "expected": 1}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "UNKNOWN"

    def test_no_rule_unknown(self):
        evidence = {"x": 1}
        contract = {"acceptance_criteria": [
            {"id": "A01", "description": "no rule"}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "UNKNOWN"

    def test_greater_than_or_equal(self):
        evidence = {"tests": {"passed": 668}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "tests.passed", "operator": "greater_than_or_equal", "expected": 668}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_sha_equals(self):
        evidence = {"implementation": {"commit_sha": "abc123DEF"}}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "implementation.commit_sha", "operator": "sha_equals", "expected": "abc123def"}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_contains(self):
        evidence = {"derived_status": "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "derived_status", "operator": "contains", "expected": "READY"}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"

    def test_not_contains(self):
        evidence = {"derived_status": "NOT READY — STALE CI"}
        contract = {"acceptance_criteria": [
            {"id": "A01", "rule": {"field": "derived_status", "operator": "not_contains", "expected": "SA REVIEW"}}
        ]}
        results = evaluate_acceptance(evidence, contract)
        assert results[0]["result"] == "PASS"
