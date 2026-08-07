"""Test verify_exact_head_ci.py — CI evidence collection."""
import json, sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_exact_head_ci_collected():
    with patch("verify_exact_head_ci._find_run") as mock_find:
        mock_find.return_value = {
            "id": 12345, "event": "push", "workflow_name": "VF-DM CI",
            "head_branch": "ft/test", "head_sha": "abc123",
            "status": "completed", "conclusion": "success",
        }
        with patch("verify_exact_head_ci._get_jobs", return_value=[
            {"id": 1, "name": "test", "conclusion": "success",
             "steps": [{"name": "Test", "conclusion": "success"},
                       {"name": "Smoke", "conclusion": "success"}]}
        ]):
            from verify_exact_head_ci import collect_ci_evidence
            ci = collect_ci_evidence("abc123", "ft/test", ["Test", "Smoke"], token="fake")
            assert ci["conclusion"] == "success"
            assert ci["status"] == "completed"
            assert ci["run_id"] == 12345
            assert not ci["missing_required_steps"]


def test_pending_ci_detected():
    with patch("verify_exact_head_ci._find_run") as mock_find:
        mock_find.return_value = {
            "id": 12345, "event": "push", "status": "in_progress", "conclusion": None,
            "head_sha": "abc123",
        }
        from verify_exact_head_ci import collect_ci_evidence
        ci = collect_ci_evidence("abc123", "ft/test", [], token="fake")
        assert ci["status"] == "in_progress"
        assert ci["conclusion"] is None


def test_failed_ci_detected():
    with patch("verify_exact_head_ci._find_run") as mock_find:
        mock_find.return_value = {
            "id": 12345, "event": "push", "status": "completed", "conclusion": "failure",
            "head_sha": "abc123",
        }
        from verify_exact_head_ci import collect_ci_evidence
        ci = collect_ci_evidence("abc123", "ft/test", [], token="fake")
        assert ci["conclusion"] == "failure"


def test_missing_required_step():
    with patch("verify_exact_head_ci._find_run") as mock_find:
        mock_find.return_value = {
            "id": 12345, "event": "push", "status": "completed", "conclusion": "success",
            "head_sha": "abc123",
        }
        with patch("verify_exact_head_ci._get_jobs", return_value=[
            {"id": 1, "name": "test", "conclusion": "success",
             "steps": [{"name": "Test", "conclusion": "success"}]}
        ]):
            from verify_exact_head_ci import collect_ci_evidence
            ci = collect_ci_evidence("abc123", "ft/test", ["MissingStep"], token="fake")
            assert "MissingStep" in ci["missing_required_steps"]
