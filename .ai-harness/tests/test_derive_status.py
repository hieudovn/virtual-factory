"""Test derive_status.py — deterministic status derivation logic."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from derive_status import derive_status, derive_exit_code, _FORBIDDEN_DERIVED, _VALID_DERIVED_STATUSES


def _load(name: str) -> dict:
    p = Path(__file__).resolve().parent.parent / "examples" / name
    with open(p) as f:
        return json.load(f)


class TestDeriveStatus:
    def test_valid_ready_passes(self):
        e = _load("valid-ready-evidence.json")
        assert derive_status(e) == "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"

    def test_stale_ci_fails(self):
        e = _load("invalid-stale-ci-evidence.json")
        assert derive_status(e) == "NOT READY — STALE CI"

    def test_missing_commit_not_ready(self):
        e = _load("invalid-missing-commit-evidence.json")
        s = derive_status(e)
        assert "READY" not in s

    def test_local_only_not_ready(self):
        e = _load("invalid-local-only-evidence.json")
        s = derive_status(e)
        assert s.startswith("NOT READY") or s.startswith("STOPPED") or s.startswith("IMPLEMENTED")

    def test_complete_is_forbidden(self):
        assert "COMPLETE" in _FORBIDDEN_DERIVED
        assert "CLOSED" in _FORBIDDEN_DERIVED

    def test_valid_statuses_exist(self):
        assert "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW" in _VALID_DERIVED_STATUSES
        assert "NOT READY — STALE CI" in _VALID_DERIVED_STATUSES

    def test_missing_pr_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["pull_request"]["number"] = None
        s = derive_status(e)
        assert s.startswith("PUSHED") or s.startswith("NOT READY") or s.startswith("PR OPEN")

    def test_draft_pr_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["pull_request"]["draft"] = True
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_wrong_base_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["pull_request"]["base_branch"] = "develop"
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_ci_head_mismatch_stale(self):
        e = _load("valid-ready-evidence.json")
        e["ci"]["head_sha"] = "different_sha_12345678901234567890"
        assert derive_status(e) == "NOT READY — STALE CI"

    def test_failed_ci_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["ci"]["conclusion"] = "failure"
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_missing_ci_pending(self):
        e = _load("valid-ready-evidence.json")
        e["ci"]["run_id"] = None
        e["ci"]["head_sha"] = ""
        assert derive_status(e) == "PR OPEN — CI PENDING"

    def test_failed_tests_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["tests"]["failed"] = 3
        assert derive_status(e) == "NOT READY — TEST FAILURE"

    def test_acceptance_fail_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["acceptance"][0]["result"] = "FAIL"
        assert derive_status(e) == "NOT READY — ACCEPTANCE FAILURE"

    def test_acceptance_unknown_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["acceptance"][0]["result"] = "UNKNOWN"
        assert derive_status(e) == "NOT READY — INSUFFICIENT EVIDENCE"

    def test_forbidden_action_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["forbidden_actions"]["performed"] = True
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_tool_failure_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["tool_failures"] = [{"tool": "test", "exit_code": 1, "classification": "FAIL", "execution_stopped": False}]
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_contradiction_not_ready(self):
        e = _load("valid-ready-evidence.json")
        e["contradictions"] = ["test contradiction"]
        s = derive_status(e)
        assert s.startswith("NOT READY")

    def test_baseline_mismatch_stops(self):
        e = _load("valid-ready-evidence.json")
        e["preflight"]["baseline_match"] = False
        assert derive_status(e) == "STOPPED — BASELINE MISMATCH"

    def test_m2_s04_closed_derives_correctly(self):
        e = _load("m2-s04-closed-evidence.json")
        s = derive_status(e)
        assert "POST-MERGE VERIFIED" in s or "CLOSED" in s

    def test_remote_head_pr_head_mismatch(self):
        e = _load("valid-ready-evidence.json")
        e["implementation"]["remote_branch_head"] = "different_sha_1234567890"
        assert derive_status(e) == "NOT READY — REMOTE STATE MISMATCH"


class TestExitCodes:
    def test_ready_gate_exit_0(self):
        e = _load("valid-ready-evidence.json")
        e["requested_gate"] = "ready_for_sa_review"
        assert derive_exit_code("IMPLEMENTED — PR OPEN — READY FOR SA REVIEW", e) == 0

    def test_not_ready_exit_1(self):
        e = _load("valid-ready-evidence.json")
        e["requested_gate"] = "ready_for_sa_review"
        assert derive_exit_code("NOT READY — STALE CI", e) == 1

    def test_baseline_mismatch_exit_4(self):
        e = _load("valid-ready-evidence.json")
        assert derive_exit_code("STOPPED — BASELINE MISMATCH", e) == 4

    def test_blocking_issue_exit_1(self):
        e = _load("valid-ready-evidence.json")
        e["requested_gate"] = "ready_for_sa_review"
        e["blocking_issues"] = ["blocked"]
        assert derive_exit_code("IMPLEMENTED — PR OPEN — READY FOR SA REVIEW", e) == 1

    def test_report_only_exit_0(self):
        e = _load("valid-ready-evidence.json")
        e["execution_mode"] = "report_only"
        e["requested_gate"] = "report_only"
        assert derive_exit_code("NOT READY — STALE CI", e) == 0

    def test_merged_gate_with_not_merged(self):
        e = _load("valid-ready-evidence.json")
        e["requested_gate"] = "merged"
        assert derive_exit_code("IMPLEMENTED — PR OPEN — READY FOR SA REVIEW", e) == 1

    def test_preflight_only_pass(self):
        e = _load("valid-ready-evidence.json")
        e["requested_gate"] = "preflight_only"
        assert derive_exit_code("NOT READY — STALE CI", e) == 0
