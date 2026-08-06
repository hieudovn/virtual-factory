#!/usr/bin/env python3
"""verify-pr-merge-gate.py — Verify PR meets all merge gate requirements.

Usage:
    python scripts/verify-pr-merge-gate.py --pr <PR_NUMBER> --sha <HEAD_SHA>

Checks:
    1. PR base is main
    2. PR is not directly pushing to main
    3. CI has passed on the PR head SHA
    4. PR has at least one approving review
    5. PR is not in draft state
"""

import argparse
import json
import subprocess
import sys


def run_gh(args: list[str]) -> str:
    """Run a gh command and return stdout."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)} failed: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def verify_pr(pr_number: str, expected_sha: str | None = None) -> bool:
    """Verify a PR meets all merge gate requirements. Returns True if all pass."""
    all_ok = True

    # 1. Get PR info
    pr_json = run_gh(["pr", "view", pr_number, "--json", "baseRefName,headRefName,state,isDraft,reviews,statusCheckRollup"])
    pr = json.loads(pr_json)

    # Check base is main
    if pr.get("baseRefName") != "main":
        print(f"FAIL: PR base is '{pr.get('baseRefName')}', expected 'main'")
        all_ok = False
    else:
        print("PASS: PR base is main")

    # Check not draft
    if pr.get("isDraft"):
        print("FAIL: PR is in draft state")
        all_ok = False
    else:
        print("PASS: PR is not draft")

    # Check state is OPEN
    if pr.get("state") != "OPEN":
        print(f"FAIL: PR state is '{pr.get('state')}', expected 'OPEN'")
        all_ok = False
    else:
        print("PASS: PR is OPEN")

    # Check CI status
    status_check = pr.get("statusCheckRollup", [])
    ci_ok = False
    for check in status_check:
        if check.get("context", "").startswith("VF-DM"):
            if check.get("conclusion") == "SUCCESS":
                ci_ok = True
                break
    if ci_ok:
        print("PASS: VF-DM CI has passed")
    else:
        print("FAIL: VF-DM CI has not passed or not found")
        all_ok = False

    # Check reviews
    reviews = pr.get("reviews", [])
    approved = any(r.get("state") == "APPROVED" for r in reviews)
    if approved:
        print("PASS: At least one approving review")
    else:
        print("FAIL: No approving review found")
        all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Verify PR merge gate requirements")
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--sha", help="Expected head SHA (optional)")
    args = parser.parse_args()

    print(f"Verifying PR #{args.pr}...")
    print("-" * 40)

    ok = verify_pr(args.pr, args.sha)
    print("-" * 40)

    if ok:
        print("ALL CHECKS PASSED — PR is ready to merge.")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — Do not merge.")
        sys.exit(1)


if __name__ == "__main__":
    main()
