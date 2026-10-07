"""Focused harness test for the C01-B gate report contract.

`run_task_gate.py` P22 validates the provisional gate report against the evidence
via ``validate_report_consistency.py``, which fails closed when the report does
not reference ``implementation.commit_sha``. P21 therefore has to put the exact
implementation SHA into the report it generates. This test pins that contract on
the shared report writer.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))

SHA = "0123456789abcdef0123456789abcdef01234567"
STATUS = "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"


def _ready_evidence() -> dict:
    return {
        "derived_status": STATUS,
        "ci": {"status": "completed", "conclusion": "success"},
        "acceptance": [{"id": "A01", "result": "PASS"}],
        "unknown_evidence": [],
        "tool_failures": [],
        "contradictions": [],
        "blocking_issues": [],
        "implementation": {"commit_sha": SHA},
        "pipeline_steps": [],
        "requested_gate_satisfied": True,
    }


def test_provisional_report_references_implementation_sha():
    """The P21 artefact must satisfy P22 (validate_report_consistency)."""
    from run_task_gate import _write_gate_report
    from validate_report_consistency import validate

    with tempfile.TemporaryDirectory(prefix="c01-gate-report-") as tmp:
        path = Path(tmp) / "gate-report.provisional.md"
        _write_gate_report(
            path, "Gate Report (Provisional)", "DDAY-B2-C01", STATUS,
            "ready_for_sa_review", True, 0,
            [{"result": "PASS", "id": "P01", "name": "Load contract"}],
            SHA,
        )
        # Read exactly as run_task_gate / validate_report_consistency do
        # (platform default encoding = the encoding the gate writer uses).
        report = path.read_text()

    assert SHA in report, "report must contain the full implementation SHA"
    assert SHA[:12] in report, "report must contain the abbreviated head SHA"

    ok, issues = validate(_ready_evidence(), report)
    assert ok, f"provisional report still inconsistent: {issues}"


def test_report_without_sha_fails_closed():
    """Validation must keep failing closed — the repair is in the writer."""
    from validate_report_consistency import validate

    report = "# Gate Report (Provisional) — DDAY-B2-C01\n\n**Status**: READY\n"
    ok, issues = validate(_ready_evidence(), report)
    assert not ok
    assert any("SHA" in issue for issue in issues)


def test_final_report_references_sha_and_pipeline():
    from run_task_gate import _write_gate_report

    with tempfile.TemporaryDirectory(prefix="c01-gate-report-") as tmp:
        path = Path(tmp) / "gate-report.md"
        _write_gate_report(
            path, "Gate Report", "DDAY-B2-C01", STATUS, "ready_for_sa_review",
            True, 0, [{"result": "PASS", "id": "P01", "name": "Load contract"}],
            SHA,
            pipeline_integrity={"actual_ids": ["P01"], "missing_ids": [],
                                "duplicate_ids": []},
        )
        report = path.read_text()

    assert SHA in report
    assert "**Pipeline**" in report
    assert "[PASS] P01" in report


# ── C01-B2: PR state representation alignment ──────────────────────────────

def test_pr_state_is_normalized_to_harness_convention():
    """The REST API reports 'open'; derive_status.py and the harness fixtures
    use 'OPEN'. Only the representation is aligned."""
    from run_task_gate import _normalize_pr_state

    assert _normalize_pr_state(
        {"pull_request": {"state": "open"}})["pull_request"]["state"] == "OPEN"
    assert _normalize_pr_state(
        {"pull_request": {"state": "closed"}})["pull_request"]["state"] == "CLOSED"
    # Idempotent and harmless for the already-canonical form.
    assert _normalize_pr_state(
        {"pull_request": {"state": "OPEN"}})["pull_request"]["state"] == "OPEN"
    assert _normalize_pr_state(
        {"pull_request": {"state": ""}})["pull_request"]["state"] == ""
    assert _normalize_pr_state({}) == {}


def test_closed_pr_still_fails_closed_after_normalization():
    """Guards against the alignment being used to relax the open-PR check."""
    from derive_status import derive_status
    from run_task_gate import _normalize_pr_state

    evidence = {
        "preflight": {"baseline_match": True, "expected_base_sha": "a" * 40,
                      "remote_main_head": "a" * 40},
        "tool_failures": [],
        "implementation": {"commit_exists_remotely": True,
                           "remote_branch_head": "b" * 40},
        "pull_request": {"number": 101, "state": "closed", "draft": False,
                         "base_branch": "main", "head_sha": "b" * 40,
                         "merged": False},
        "ci": {"run_id": 1, "head_sha": "b" * 40, "conclusion": "success"},
        "tests": {"failed": 0},
        "acceptance": [],
        "unknown_evidence": [],
        "contradictions": [],
        "blocking_issues": [],
        "forbidden_actions": {"performed": False},
    }
    _normalize_pr_state(evidence)
    assert evidence["pull_request"]["state"] == "CLOSED"
    assert derive_status(evidence) == "NOT READY — GOVERNANCE FAILURE"

    # The same evidence with an open PR derives READY, proving the alignment is
    # representation-only.
    evidence["pull_request"]["state"] = "open"
    _normalize_pr_state(evidence)
    assert derive_status(evidence) == "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"
