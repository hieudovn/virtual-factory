"""Test run_task_gate.py — pipeline and exit codes."""
import json, sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_exit_code_ready_gate_satisfied():
    from run_task_gate import _exit_code
    assert _exit_code("IMPLEMENTED — PR OPEN — READY FOR SA REVIEW", {"blocking_issues": [], "tool_failures": [], "contradictions": []}, "ready_for_sa_review", False) == 0


def test_exit_code_not_ready():
    from run_task_gate import _exit_code
    assert _exit_code("NOT READY — STALE CI", {"blocking_issues": [], "tool_failures": [], "contradictions": []}, "ready_for_sa_review", False) == 1


def test_exit_code_baseline_mismatch():
    from run_task_gate import _exit_code
    assert _exit_code("STOPPED — BASELINE MISMATCH", {}, "ready_for_sa_review", False) == 4


def test_exit_code_blocking_issue():
    from run_task_gate import _exit_code
    assert _exit_code("IMPLEMENTED — PR OPEN — READY FOR SA REVIEW", {"blocking_issues": ["x"], "tool_failures": [], "contradictions": []}, "ready_for_sa_review", False) == 1


def test_exit_code_tool_blocked():
    from run_task_gate import _exit_code
    assert _exit_code("ANY", {"tool_failures": [{"execution_stopped": True}], "blocking_issues": [], "contradictions": []}, "ready_for_sa_review", False) == 3


def test_junit_parsing():
    from run_task_gate import _parse_junit
    from pathlib import Path
    import xml.etree.ElementTree as ET
    p = Path(__file__).parent / "fixtures" / "test_junit.xml"
    p.parent.mkdir(exist_ok=True)
    root = ET.Element("testsuite", {"name": "pytest", "tests": "100", "failures": "3", "skipped": "2", "errors": "0"})
    ET.ElementTree(root).write(str(p), encoding="utf-8", xml_declaration=True)
    result = _parse_junit(p)
    assert result["collected"] == 100
    assert result["failed"] == 3
    assert result["passed"] == 95
    assert result["result"] == "FAIL"
    p.unlink()


def test_junit_all_pass():
    from run_task_gate import _parse_junit
    from pathlib import Path
    import xml.etree.ElementTree as ET
    p = Path(__file__).parent / "fixtures" / "test_junit_pass.xml"
    p.parent.mkdir(exist_ok=True)
    root = ET.Element("testsuite", {"name": "pytest", "tests": "50", "failures": "0", "skipped": "0", "errors": "0"})
    ET.ElementTree(root).write(str(p), encoding="utf-8", xml_declaration=True)
    result = _parse_junit(p)
    assert result["result"] == "PASS"
    p.unlink()


def test_report_only_exit():
    from run_task_gate import _exit_code
    assert _exit_code("NOT READY — STALE CI", {"tool_failures": [], "blocking_issues": [], "contradictions": []}, "ready_for_sa_review", True) == 0
