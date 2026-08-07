"""VF-AI-HARNESS-C06-C01 — Lifecycle integrity + tested genericity corrections.

Tests:
  A. Real successful final lifecycle (mocked run_task_gate)
  B. P22 stabilization failure path
  C. _resolve_pr with mocked GitHub API
  D. _normalize_smoke_command helper
  E. Pipeline integrity semantics
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure harness scripts are importable
HARNESS_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(HARNESS_SCRIPTS))

from run_task_gate import (
    CANONICAL_IDS,
    PipelineRegistry,
    _resolve_pr,
    _normalize_smoke_command,
    run_task_gate,
)


# ──────────────────────────────────────────────
# Contract fixture
# ──────────────────────────────────────────────

_MINIMAL_CONTRACT = {
    "task_id": "VF-TEST-C06",
    "repository": "hieudovn/virtual-factory",
    "requested_gate": "ready_for_sa_review",
    "objective": "Test contract for C06 lifecycle proof.",
    "explicit_non_objectives": [],
    "required_branch": "feature/test-c06",
    "expected_base_sha": "f8870afd9c630bb00ce9e158c6dff58d58864721",
    "allowed_paths": [".ai-harness/"],
    "forbidden_paths": [],
    "required_deliverables": [],
    "required_tests": [],
    "required_smoke_checks": [],
    "required_remote_evidence": [],
    "forbidden_actions": [],
    "stop_conditions": [],
    "acceptance_criteria": [
        {"id": "A01", "phase": "pre_status",
         "description": "Tests pass", "rule": {"field": "tests.result", "operator": "equals", "expected": "PASS"}},
        {"id": "F01", "phase": "final",
         "description": "Pipeline all steps executed",
         "rule": {"field": "pipeline_integrity.all_required_steps_executed", "operator": "is_true", "expected": None}},
        {"id": "F02", "phase": "final",
         "description": "Pipeline all steps pass",
         "rule": {"field": "pipeline_integrity.all_required_steps_pass", "operator": "is_true", "expected": None}},
    ],
    "authorization": {"may_open_pr": True, "may_merge": False, "may_start_next_task": False},
}


# ──────────────────────────────────────────────
# A. Real lifecycle test
# ──────────────────────────────────────────────

class TestRealLifecycle:
    """C06-C01-A: Controlled run_task_gate path reaches P01-P24 integrity."""

    @patch("run_task_gate._git")
    @patch("run_task_gate._run")
    @patch("run_task_gate._resolve_pr")
    @patch("subprocess.run")
    def test_full_gate_reaches_p01_p24_integrity(
        self, mock_subprocess_run, mock_resolve_pr, mock_run, mock_git
    ):
        """A mocked run_task_gate produces P01-P24 with truthful integrity."""
        mock_git.side_effect = lambda args: {
            "rev-parse --abbrev-ref HEAD": "feature/test-c06",
            "rev-parse HEAD": "f8870afd9c630bb00ce9e158c6dff58d58864721",
            "rev-parse origin/main": "f8870afd9c630bb00ce9e158c6dff58d58864721",
            "status --short": "",
            "diff --name-only origin/main HEAD": ".ai-harness/scripts/run_task_gate.py",
        }.get(" ".join(args), "")
        mock_resolve_pr.return_value = 7
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="701 passed", stderr="")
        # Mock verify_remote_state to populate PR metadata in evidence file
        def _run_side_effect(script, args):
            m = MagicMock(returncode=0,
                stdout="PASS\nDerived status: IMPLEMENTED \u2014 PR OPEN \u2014 READY FOR SA REVIEW",
                stderr="")
            # When verify_remote_state is called, write PR metadata to the evidence file
            if "verify_remote_state" in script:
                ev_path = args[0]
                try:
                    with open(ev_path) as f: ev = json.load(f)
                    ev["pull_request"] = {
                        "number": 7, "state": "open", "base_branch": "main",
                        "base_sha": "f8870afd", "head_branch": "feature/test-c06",
                        "head_sha": "f8870afd9c630bb00ce9e158c6dff58d58864721",
                        "draft": False, "merged": False, "merged_at": None, "merge_commit_sha": "",
                    }
                    ev["implementation"]["commit_exists_remotely"] = True
                    ev["implementation"]["remote_branch_head"] = "f8870afd9c630bb00ce9e158c6dff58d58864721"
                    with open(ev_path, "w") as f: json.dump(ev, f)
                except Exception: pass
            return m
        mock_run.side_effect = _run_side_effect

        # Ensure _parse_junit finds a valid XML so P06 records PASS
        traces_dir = Path(".ai-harness/traces/VF-TEST-C06")
        traces_dir.mkdir(parents=True, exist_ok=True)
        junit_xml = traces_dir / "regression.xml"
        junit_xml.write_text(
            '<?xml version="1.0"?><testsuite tests="701" failures="0" skipped="0"></testsuite>'
        )

        contract_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
                json.dump(_MINIMAL_CONTRACT, tf)
                contract_path = tf.name
            status, evidence, exit_code = run_task_gate(contract_path, report_only=True)
        finally:
            if contract_path and os.path.exists(contract_path):
                try: os.unlink(contract_path)
                except OSError: pass
            try: junit_xml.unlink()
            except OSError: pass

        # Verify pipeline contains P01-P24 exactly once
        step_ids = [s["id"] for s in evidence.get("pipeline_steps", [])]
        assert step_ids == CANONICAL_IDS, f"step_ids={step_ids}"

        # Verify integrity after real flow
        pi = evidence.get("pipeline_integrity", {})
        assert pi["actual_ids"] == CANONICAL_IDS
        assert pi["missing_ids"] == []
        assert pi["duplicate_ids"] == []
        assert pi["unexpected_ids"] == []
        assert pi["all_required_steps_executed"] is True
        assert pi["all_required_steps_pass"] is True


# ──────────────────────────────────────────────
# B. P22 failure path
# ──────────────────────────────────────────────

class TestP22FailurePath:
    """C06-C01-B: Stabilization failure does not duplicate P22."""

    @patch("run_task_gate._git")
    @patch("run_task_gate._run")
    @patch("run_task_gate._resolve_pr")
    @patch("subprocess.run")
    def test_p22_failure_no_duplicate_no_pretend_p23_p24(
        self, mock_subprocess_run, mock_resolve_pr, mock_run, mock_git
    ):
        """When stabilization fails, P22 not duplicated, P23/P24 not claimed."""
        mock_git.side_effect = lambda args: {
            "rev-parse --abbrev-ref HEAD": "feature/test-c06",
            "rev-parse HEAD": "f8870afd9c630bb00ce9e158c6dff58d58864721",
            "rev-parse origin/main": "f8870afd9c630bb00ce9e158c6dff58d58864721",
            "status --short": "",
            "diff --name-only origin/main HEAD": ".ai-harness/scripts/run_task_gate.py",
        }.get(" ".join(args), "")
        mock_resolve_pr.return_value = 7
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="701 passed", stderr="")

        # Ensure _parse_junit finds a valid XML
        traces_dir = Path(".ai-harness/traces/VF-TEST-C06")
        traces_dir.mkdir(parents=True, exist_ok=True)
        junit_xml = traces_dir / "regression.xml"
        junit_xml.write_text(
            '<?xml version="1.0"?><testsuite tests="701" failures="0" skipped="0"></testsuite>'
        )

        # All harness sub-scripts succeed for preflight/P04/P08/P10/P13/P16/P18/P20
        # then P22 validate_evidence and report_consistency always fail
        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] >= 9:  # P22 onward always fail
                return MagicMock(returncode=1, stdout="FAIL", stderr="inconsistency")
            return MagicMock(returncode=0,
                stdout="PASS\nDerived status: NOT READY \u2014 REMOTE STATE MISMATCH",
                stderr="")
        mock_run.side_effect = side_effect

        contract_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
                json.dump(_MINIMAL_CONTRACT, tf)
                contract_path = tf.name
            status, evidence, exit_code = run_task_gate(contract_path, report_only=True)
        finally:
            if contract_path and os.path.exists(contract_path):
                try:
                    os.unlink(contract_path)
                except OSError:
                    pass
            try: junit_xml.unlink()
            except OSError: pass

        assert exit_code == 5  # internal error for unstable

        step_ids = [s["id"] for s in evidence.get("pipeline_steps", [])]
        assert step_ids.count("P22") == 1
        assert "P23" not in step_ids
        assert "P24" not in step_ids
        p22 = [s for s in evidence["pipeline_steps"] if s["id"] == "P22"][0]
        assert p22["result"] == "FAIL"


# ──────────────────────────────────────────────
# C. PR resolver tests
# ──────────────────────────────────────────────

class TestPRResolver:
    """C06-C01-C: _resolve_pr with mocked GitHub API responses."""

    def _make_response(self, prs):
        mock = MagicMock()
        mock.__enter__.return_value.read.return_value = json.dumps(prs).encode()
        return mock

    @patch("urllib.request.urlopen")
    def test_one_matching_pr_returns_number(self, mock_urlopen):
        mock_urlopen.return_value = self._make_response([
            {"number": 6, "head": {"ref": "feature/dm-m2-s06"}, "state": "open",
             "base": {"ref": "main"}},
        ])
        result = _resolve_pr(
            {"required_branch": "feature/dm-m2-s06", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        assert result == 6

    @patch("urllib.request.urlopen")
    def test_zero_matching_pr_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = self._make_response([])
        result = _resolve_pr(
            {"required_branch": "feature/zero", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        assert result is None

    @patch("urllib.request.urlopen")
    def test_multiple_qualifying_prs_returns_none(self, mock_urlopen):
        mock_urlopen.return_value = self._make_response([
            {"number": 20, "head": {"ref": "feature/multi"}, "state": "open",
             "base": {"ref": "main"}},
            {"number": 21, "head": {"ref": "feature/multi"}, "state": "open",
             "base": {"ref": "main"}},
        ])
        result = _resolve_pr(
            {"required_branch": "feature/multi", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        assert result is None

    @patch("urllib.request.urlopen")
    def test_different_branches_resolve_different_prs(self, mock_urlopen):
        r_a_val = 10
        r_b_val = 11

        def side_effect(url, **kw):
            url_str = url if isinstance(url, str) else url.full_url
            if "feature%2Ftest-a" in url_str or "feature/test-a" in url_str:
                return self._make_response([
                    {"number": r_a_val, "head": {"ref": "feature/test-a"}, "state": "open",
                     "base": {"ref": "main"}},
                ])
            return self._make_response([
                {"number": r_b_val, "head": {"ref": "feature/test-b"}, "state": "open",
                 "base": {"ref": "main"}},
            ])
        mock_urlopen.side_effect = side_effect

        r_a = _resolve_pr(
            {"required_branch": "feature/test-a", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        r_b = _resolve_pr(
            {"required_branch": "feature/test-b", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        assert r_a == 10
        assert r_b == 11
        assert r_a != r_b

    def test_no_token_returns_none(self):
        result = _resolve_pr(
            {"required_branch": "feature/x", "repository": "hieudovn/virtual-factory"},
            None
        )
        assert result is None

    def test_no_branch_returns_none(self):
        result = _resolve_pr(
            {"required_branch": "", "repository": "hieudovn/virtual-factory"},
            "fake-token"
        )
        assert result is None


# ──────────────────────────────────────────────
# D. Smoke command normalization
# ──────────────────────────────────────────────

class TestSmokeNormalization:
    """C06-C01-D: _normalize_smoke_command helper."""

    def test_virtual_factory_translated(self):
        result = _normalize_smoke_command(
            ["virtual-factory", "validate", "--config", "foo.yaml"]
        )
        assert result[0] == sys.executable
        assert result[1] == "-c"
        assert "virtual_factory.main" in result[2]

    def test_non_virtual_factory_unchanged(self):
        assert _normalize_smoke_command(["pytest", "-q"]) == ["pytest", "-q"]

    def test_empty_unchanged(self):
        assert _normalize_smoke_command([]) == []

    def test_different_command_unchanged(self):
        assert _normalize_smoke_command(["echo", "hello"]) == ["echo", "hello"]


# ──────────────────────────────────────────────
# E. Pipeline integrity semantics
# ──────────────────────────────────────────────

class TestPipelineIntegrity:
    """C02/C06-C01-E: Pipeline integrity pass/fail semantics."""

    def test_canonical_ids_are_p01_to_p24(self):
        assert len(CANONICAL_IDS) == 24
        assert CANONICAL_IDS[0] == "P01"
        assert CANONICAL_IDS[-1] == "P24"

    def test_canonical_ids_contiguous(self):
        for i, cid in enumerate(CANONICAL_IDS, 1):
            assert cid == f"P{i:02d}"

    def test_full_pipeline_integrity_passes(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["all_required_steps_executed"] is True
        assert pi["all_required_steps_pass"] is True
        assert pi["missing_ids"] == []

    def test_missing_step_fails_integrity(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS[:-1]:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["all_required_steps_executed"] is False
        assert pi["missing_ids"] == ["P24"]

    def test_one_fail_fails_all_pass(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        reg.update_result("P07", "FAIL")
        pi = reg.integrity()
        assert pi["all_required_steps_pass"] is False

    def test_no_duplicates_or_unexpected(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["duplicate_ids"] == []
        assert pi["unexpected_ids"] == []
