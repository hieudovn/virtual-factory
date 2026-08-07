"""Test validate_report_consistency.py."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_ready_with_ci_pending_rejected():
    from validate_report_consistency import validate
    e = {"derived_status": "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
         "ci": {"status": "in_progress"}, "acceptance": [], "unknown_evidence": [],
         "tool_failures": [], "contradictions": [], "blocking_issues": [],
         "implementation": {"commit_sha": "abc123"}, "pipeline_steps": [],
         "requested_gate_satisfied": True}
    ok, issues = validate(e, "Report for abc123")
    assert not ok
    assert any("CI" in i for i in issues)


def test_ready_with_unknown_rejected():
    from validate_report_consistency import validate
    e = {"derived_status": "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
         "ci": {"status": "completed", "conclusion": "success"}, "acceptance": [],
         "unknown_evidence": ["missing_field"], "tool_failures": [],
         "contradictions": [], "blocking_issues": [],
         "implementation": {"commit_sha": "abc123"}, "pipeline_steps": [],
         "requested_gate_satisfied": True}
    ok, issues = validate(e, "Report abc123")
    assert not ok


def test_vscode_link_rejected():
    from validate_report_consistency import validate
    e = {"derived_status": "NOT READY — STALE CI",
         "ci": {}, "acceptance": [], "unknown_evidence": [],
         "tool_failures": [], "contradictions": [], "blocking_issues": [],
         "implementation": {"commit_sha": "abc123"}, "pipeline_steps": [],
         "requested_gate_satisfied": False}
    report = "See vscode-file://path/to/file for details"
    ok, issues = validate(e, report)
    assert not ok


def test_clean_report_passes():
    from validate_report_consistency import validate
    e = {"derived_status": "NOT READY — STALE CI",
         "ci": {"status": "completed", "conclusion": "failure"}, "acceptance": [],
         "unknown_evidence": [], "tool_failures": [], "contradictions": [],
         "blocking_issues": [], "implementation": {"commit_sha": "abc123def456"},
         "pipeline_steps": [], "requested_gate_satisfied": False}
    ok, issues = validate(e, "Report for abc123def456 — CI failed")
    assert ok
