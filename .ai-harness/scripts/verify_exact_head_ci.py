#!/usr/bin/env python3
"""verify_exact_head_ci.py — Verify CI ran on the exact expected head SHA.

Usage:
    python .ai-harness/scripts/verify_exact_head_ci.py <evidence.json> [--token TOKEN]

Verifies the CI head SHA matches the expected head and required steps are present.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def _gh_api(token: str, endpoint: str) -> dict | None:
    """Call GitHub API."""
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
    except Exception as e:
        print(f"GitHub API error: {e}")
        return None


def verify_exact_head_ci(
    evidence: dict,
    token: str | None = None,
) -> tuple[bool, list[str]]:
    """Verify CI. Returns (passed, issues)."""
    issues: list[str] = []

    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        issues.append("No GitHub token — cannot verify CI")
        return False, issues

    ci = evidence.get("ci", {})
    pr = evidence.get("pull_request", {})
    post = evidence.get("post_merge", {})

    ci_run_id = ci.get("run_id")
    ci_head = ci.get("head_sha", "")
    pr_head = pr.get("head_sha", "")
    expected_head = ci_head or pr_head

    # --- Verify CI run ---
    if ci_run_id:
        run_data = _gh_api(token, f"/actions/runs/{ci_run_id}")
        if run_data is None:
            issues.append(f"CI run #{ci_run_id} not found")
        else:
            actual_event = run_data.get("event", "")
            actual_head = run_data.get("head_sha", "")
            actual_conclusion = run_data.get("conclusion", "")
            actual_branch = run_data.get("head_branch", "")

            print(f"CI run #{ci_run_id}: event={actual_event}, "
                  f"head={actual_head[:12]}…, conclusion={actual_conclusion}")

            # Check event — push is acceptable but must be factual
            if ci.get("event") and ci["event"] != actual_event:
                issues.append(
                    f"CI event mismatch: evidence={ci['event']}, "
                    f"actual={actual_event}"
                )

            # Exact head SHA
            if expected_head and actual_head != expected_head:
                issues.append(
                    f"CI head SHA mismatch: expected {expected_head[:12]}…, "
                    f"actual {actual_head[:12]}…"
                )

            # Conclusion
            if actual_conclusion != "success":
                issues.append(f"CI conclusion is '{actual_conclusion}', not 'success'")

            # Check jobs/steps
            jobs_data = _gh_api(token, f"/actions/runs/{ci_run_id}/jobs")
            if jobs_data:
                step_names: list[str] = []
                for job in jobs_data.get("jobs", []):
                    for step in job.get("steps", []):
                        name = step.get("name", "")
                        if name and "Set up" not in name and "Post" not in name and "Complete" not in name:
                            step_names.append(name)
                print(f"CI steps: {step_names}")

                required_steps = ci.get("required_steps", [])
                for req_step in required_steps:
                    if not any(req_step in s for s in step_names):
                        issues.append(f"Required CI step missing: '{req_step}'")
    else:
        # Check post-merge CI
        post_ci_run = post.get("ci_run_id")
        if post_ci_run:
            run_data = _gh_api(token, f"/actions/runs/{post_ci_run}")
            if run_data is None:
                issues.append(f"Post-merge CI run #{post_ci_run} not found")
            else:
                actual_head = run_data.get("head_sha", "")
                actual_conclusion = run_data.get("conclusion", "")
                new_main = post.get("new_main_sha", "")
                print(f"Post-merge CI #{post_ci_run}: head={actual_head[:12]}…, "
                      f"conclusion={actual_conclusion}")
                if new_main and actual_head != new_main:
                    issues.append(
                        f"Post-merge CI head {actual_head[:12]}… ≠ "
                        f"new main {new_main[:12]}…"
                    )
                if actual_conclusion != "success":
                    issues.append(
                        f"Post-merge CI conclusion '{actual_conclusion}' ≠ 'success'"
                    )

    passed = len(issues) == 0
    if not passed:
        print("CI VERIFICATION ISSUES:")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Exact-head CI verified ✓")

    return passed, issues


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify CI ran on exact head SHA"
    )
    parser.add_argument("evidence_file", help="Path to evidence JSON")
    parser.add_argument("--token", help="GitHub personal access token")
    args = parser.parse_args()

    with open(args.evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    passed, _ = verify_exact_head_ci(evidence, args.token)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
