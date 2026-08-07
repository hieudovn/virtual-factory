"""Test verify_remote_state.py — remote evidence collection."""
import json, sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_remote_commit_evidence_collected():
    from verify_remote_state import collect_remote_state
    with patch.dict("os.environ", {}, clear=True):
        with patch("verify_remote_state._gh_authenticated", return_value=False):
            remote = collect_remote_state("testsha123", "feature/test", None)
            assert remote["evidence_source"] == "none_available"
            assert remote["tool_failures"]


def test_gh_fallback_uses_real_command():
    from verify_remote_state import collect_remote_state
    with patch.dict("os.environ", {}, clear=True):
        with patch("verify_remote_state._gh_authenticated", return_value=True):
            with patch("verify_remote_state._gh") as mock_gh:
                mock_gh.side_effect = [
                    {"sha": "abc123"},
                    {"object": {"sha": "abc123"}},
                    {"state": "OPEN", "isDraft": False, "baseRefName": "main",
                     "baseRefOid": "base123", "headRefName": "ft/test",
                     "headRefOid": "abc123", "mergedAt": None, "mergeCommit": None},
                ]
                remote = collect_remote_state("abc123", "ft/test", 4)
                assert remote["evidence_source"] == "gh_cli_authenticated"
                assert remote["remote_commit_exists"]


def test_pr_metadata_collected():
    # Mock API response
    with patch("verify_remote_state._api") as mock_api:
        mock_api.side_effect = [
            {"sha": "abc123"},  # commit
            {"object": {"sha": "abc123"}},  # branch
            {"state": "OPEN", "draft": False, "base": {"ref": "main", "sha": "base123"},
             "head": {"ref": "ft/test", "sha": "abc123"}, "merged": False, "merged_at": None,
             "merge_commit_sha": ""},
        ]
        from verify_remote_state import collect_remote_state
        remote = collect_remote_state("abc123", "feature/test", 4, token="fake")
        assert remote["evidence_source"] == "github_api_authenticated"
        assert remote["remote_commit_exists"]
        assert remote["remote_branch_head"] == "abc123"
        assert remote["pr"]["state"] == "OPEN"
        assert not remote["pr"]["draft"]


def test_wrong_pr_head_fails():
    with patch("verify_remote_state._api") as mock_api:
        mock_api.side_effect = [
            {"sha": "abc123"},
            {"object": {"sha": "abc123"}},
            {"state": "OPEN", "draft": False, "base": {"ref": "main", "sha": "base123"},
             "head": {"ref": "ft/test", "sha": "DIFFERENT_SHA"}, "merged": False,
             "merged_at": None, "merge_commit_sha": ""},
        ]
        from verify_remote_state import collect_remote_state
        remote = collect_remote_state("abc123", "feature/test", 4, token="fake")
        assert remote["pr"]["head_sha"] != "abc123"


def test_pr_draft_fails():
    with patch("verify_remote_state._api") as mock_api:
        mock_api.side_effect = [
            {"sha": "abc123"},
            {"object": {"sha": "abc123"}},
            {"state": "OPEN", "draft": True, "base": {"ref": "main", "sha": "base123"},
             "head": {"ref": "ft/test", "sha": "abc123"}, "merged": False,
             "merged_at": None, "merge_commit_sha": ""},
        ]
        from verify_remote_state import collect_remote_state
        remote = collect_remote_state("abc123", "feature/test", 4, token="fake")
        assert remote["pr"]["draft"]
