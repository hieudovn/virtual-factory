#!/usr/bin/env python3
"""verify_remote_state.py — Verify remote branch, commit, and PR state.

Usage:
    python .ai-harness/scripts/verify_remote_state.py <evidence.json> [--token TOKEN]

Uses GitHub API (or gh CLI as fallback) to verify remote state matches evidence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


def _gh_api(token: str, endpoint: str) -> dict | None:
    """Call GitHub API. Returns parsed JSON or None on failure."""
    import urllib.request
    import urllib.error

    url = f"https://api.github.com/repos/hieudovn/virtual-factory{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ai-harness/1.0")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"GitHub API request failed: {e}")
        return None


def verify_remote_state(
    evidence: dict,
    token: str | None = None,
) -> tuple[bool, list[str]]:
    """Verify remote state. Returns (passed, issues)."""
    issues: list[str] = []

    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        issues.append("No GitHub token available — cannot verify remote state")
        return False, issues

    impl = evidence.get("implementation", {})
    pr = evidence.get("pull_request", {})

    commit_sha = impl.get("commit_sha", "")
    pr_number = pr.get("number")
    branch = pr.get("head_branch", "")

    # --- Verify commit exists remotely ---
    if commit_sha:
        commit_data = _gh_api(token, f"/commits/{commit_sha}")
        if commit_data is None:
            issues.append(f"Remote commit {commit_sha[:12]}… not found")
        else:
            print(f"Commit {commit_sha[:12]}… exists remotely ✓")

    # --- Verify branch exists ---
    if branch:
        branch_data = _gh_api(token, f"/branches/{branch}")
        if branch_data is None:
            issues.append(f"Remote branch '{branch}' not found")
        else:
            remote_sha = branch_data.get("commit", {}).get("sha", "")
            print(f"Branch '{branch}' exists remotely, head: {remote_sha[:12]}…")
            if commit_sha and remote_sha != commit_sha:
                issues.append(
                    f"Branch head {remote_sha[:12]}… ≠ reported commit "
                    f"{commit_sha[:12]}…"
                )

    # --- Verify PR ---
    if pr_number:
        pr_data = _gh_api(token, f"/pulls/{pr_number}")
        if pr_data is None:
            issues.append(f"PR #{pr_number} not found")
        else:
            actual_state = pr_data.get("state", "")
            actual_draft = pr_data.get("draft", False)
            actual_head = pr_data.get("head", {}).get("sha", "")
            actual_base = pr_data.get("base", {}).get("sha", "")
            actual_merged = pr_data.get("merged", False)
            actual_merged_at = pr_data.get("merged_at")

            print(f"PR #{pr_number}: state={actual_state}, draft={actual_draft}, "
                  f"head={actual_head[:12]}…, merged={actual_merged}")

            if evidence.get("pull_request", {}).get("state") != actual_state:
                issues.append(
                    f"PR state mismatch: evidence={pr.get('state')}, "
                    f"actual={actual_state}"
                )
            if evidence.get("pull_request", {}).get("draft") != actual_draft:
                issues.append(
                    f"PR draft mismatch: evidence={pr.get('draft')}, "
                    f"actual={actual_draft}"
                )
            if pr.get("head_sha") != actual_head:
                issues.append(
                    f"PR head SHA mismatch: evidence={pr.get('head_sha', '')[:12]}…, "
                    f"actual={actual_head[:12]}…"
                )
            if evidence.get("pull_request", {}).get("merged") != actual_merged:
                issues.append(
                    f"PR merged mismatch: evidence={pr.get('merged')}, "
                    f"actual={actual_merged}"
                )

    passed = len(issues) == 0
    if not passed:
        print("REMOTE STATE ISSUES:")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Remote state verified ✓")

    return passed, issues


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify remote state against evidence JSON"
    )
    parser.add_argument("evidence_file", help="Path to evidence JSON")
    parser.add_argument("--token", help="GitHub personal access token")
    args = parser.parse_args()

    with open(args.evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    passed, _ = verify_remote_state(evidence, args.token)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
