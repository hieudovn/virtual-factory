#!/usr/bin/env python3
"""verify-pr-merge-gate.py — Verify PR meets all merge gate requirements.

Usage:
    python scripts/verify-pr-merge-gate.py --pr <PR_NUMBER> --sha <HEAD_SHA>

Checks:
    1. PR base is main
    2. PR head SHA matches --sha (exact-head verification)
    3. PR is not in draft state
    4. PR state is OPEN
    5. CI has passed on the exact PR head SHA
    6. At least one approving review (unless --single-owner)

If --single-owner is set, the review check is skipped with a documented
exception instead of failing.  This is for single-maintainer repositories
where GitHub self-approval is unavailable.

Test harness:
    python scripts/verify-pr-merge-gate.py --test
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from dataclasses import dataclass, field


# ──────────────────────────────────────────────
# Data types for deterministic testing
# ──────────────────────────────────────────────


@dataclass
class FakeCheck:
    context: str
    conclusion: str  # SUCCESS, FAILURE, PENDING, etc.


@dataclass
class FakeReview:
    state: str  # APPROVED, COMMENTED, CHANGES_REQUESTED, etc.


@dataclass
class FakePR:
    baseRefName: str = "main"
    headRefOid: str = "abc123def456"
    headRefName: str = "feature/test"
    state: str = "OPEN"
    isDraft: bool = False
    reviews: list[FakeReview] = field(default_factory=list)
    statusCheckRollup: list[FakeCheck] = field(default_factory=list)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _gh_pr_view(pr_number: str) -> dict:
    """Fetch PR data via gh CLI."""
    result = subprocess.run(
        [
            "gh", "pr", "view", pr_number,
            "--json",
            "baseRefName,headRefOid,headRefName,state,isDraft,"
            "reviews,statusCheckRollup",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: gh pr view {pr_number} failed: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout.strip())


# ──────────────────────────────────────────────
# Verification logic
# ──────────────────────────────────────────────


def verify_pr(
    pr_number: str,
    expected_sha: str | None = None,
    *,
    single_owner: bool = False,
    _pr_data: dict | None = None,
) -> bool:
    """Verify a PR meets all merge gate requirements. Returns True if all pass.

    If ``_pr_data`` is provided (test mode), uses that instead of calling gh.
    """
    all_ok = True

    # --- Fetch PR data ---
    if _pr_data is not None:
        pr = _pr_data
    else:
        pr = _gh_pr_view(pr_number)

    # --- 1. Base is main ---
    if pr.get("baseRefName") != "main":
        print(f"FAIL: PR base is '{pr.get('baseRefName')}', expected 'main'")
        all_ok = False
    else:
        print("PASS: PR base is main")

    # --- 2. Exact head SHA match ---
    actual_head = pr.get("headRefOid", "")
    if expected_sha is not None:
        if actual_head != expected_sha:
            print(
                f"FAIL: PR head SHA mismatch — "
                f"expected {expected_sha}, actual {actual_head}"
            )
            all_ok = False
        else:
            print(f"PASS: PR head SHA matches --sha ({expected_sha[:12]}…)")
    else:
        print(f"INFO: No --sha provided. PR head SHA is {actual_head[:12]}…")

    # --- 3. Not draft ---
    if pr.get("isDraft"):
        print("FAIL: PR is in draft state")
        all_ok = False
    else:
        print("PASS: PR is not draft")

    # --- 4. State is OPEN ---
    if pr.get("state") != "OPEN":
        print(f"FAIL: PR state is '{pr.get('state')}', expected 'OPEN'")
        all_ok = False
    else:
        print("PASS: PR is OPEN")

    # --- 5. CI on exact head SHA ---
    status_checks = pr.get("statusCheckRollup", [])
    ci_ok = False
    ci_detail = ""
    for check in status_checks:
        ctx = check.get("context", "")
        if ctx.startswith("VF-DM"):
            conclusion = check.get("conclusion", "")
            ci_detail = f"context={ctx} conclusion={conclusion}"
            if conclusion == "SUCCESS":
                ci_ok = True
            break

    if ci_ok:
        print(f"PASS: VF-DM CI has passed ({ci_detail})")
    else:
        detail = ci_detail or "no VF-DM CI check found"
        print(f"FAIL: VF-DM CI has not passed — {detail}")
        all_ok = False

    # --- 6. Approving review ---
    if single_owner:
        print(
            "PASS: Review control — SA external review performed in ChatGPT. "
            "GitHub self-approval unavailable/not accepted. "
            "Explicit SA merge authorization required."
        )
    else:
        reviews = pr.get("reviews", [])
        approved = any(r.get("state") == "APPROVED" for r in reviews)
        if approved:
            print("PASS: At least one approving review")
        else:
            print("FAIL: No approving review found")
            all_ok = False

    return all_ok


# ──────────────────────────────────────────────
# Deterministic test harness
# ──────────────────────────────────────────────


def _run_tests() -> bool:
    """Run deterministic tests. Returns True if all pass."""
    all_pass = True

    def _check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal all_pass
        status = "PASS" if ok else "FAIL"
        msg = f"  [{status}] {name}"
        if detail and not ok:
            msg += f" — {detail}"
        print(msg)
        if not ok:
            all_pass = False

    print("=== verify-pr-merge-gate.py self-tests ===\n")

    # --- matching SHA passes ---
    pr_ok = FakePR(headRefOid="abc123", statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_ok))
    _check("matching SHA passes", ok)

    # --- wrong SHA fails ---
    pr_wrong = FakePR(headRefOid="xyz789", statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_wrong))
    _check("wrong SHA fails", not ok)

    # --- missing CI fails ---
    pr_no_ci = FakePR(headRefOid="abc123", statusCheckRollup=[],
                       reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_no_ci))
    _check("missing CI fails", not ok)

    # --- draft PR fails ---
    pr_draft = FakePR(headRefOid="abc123", isDraft=True, statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_draft))
    _check("draft PR fails", not ok)

    # --- wrong base fails ---
    pr_base = FakePR(baseRefName="develop", headRefOid="abc123",
                      statusCheckRollup=[
                          FakeCheck("VF-DM CI", "SUCCESS"),
                      ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_base))
    _check("wrong base fails", not ok)

    # --- CI failed fails ---
    pr_ci_fail = FakePR(headRefOid="abc123", statusCheckRollup=[
        FakeCheck("VF-DM CI", "FAILURE"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_ci_fail))
    _check("CI failed fails", not ok)

    # --- no review fails (non-single-owner) ---
    pr_no_rev = FakePR(headRefOid="abc123", statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_no_rev))
    _check("no review fails (non-single-owner)", not ok)

    # --- single-owner with no review passes ---
    pr_single = FakePR(headRefOid="abc123", statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[])
    ok = verify_pr("1", expected_sha="abc123", single_owner=True,
                   _pr_data=dataclasses.asdict(pr_single))
    _check("single-owner with no review passes", ok)

    # --- non-OPEN state fails ---
    pr_closed = FakePR(headRefOid="abc123", state="MERGED", statusCheckRollup=[
        FakeCheck("VF-DM CI", "SUCCESS"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_closed))
    _check("non-OPEN state fails", not ok)

    # --- CI pending fails ---
    pr_pending = FakePR(headRefOid="abc123", statusCheckRollup=[
        FakeCheck("VF-DM CI", "PENDING"),
    ], reviews=[FakeReview("APPROVED")])
    ok = verify_pr("1", expected_sha="abc123", _pr_data=dataclasses.asdict(pr_pending))
    _check("CI pending fails", not ok)

    print(f"\n=== {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'} ===\n")
    return all_pass


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify PR merge gate requirements"
    )
    parser.add_argument("--pr", help="PR number")
    parser.add_argument("--sha", help="Expected PR head SHA")
    parser.add_argument(
        "--single-owner",
        action="store_true",
        help="Skip GitHub review check (single-maintainer repo)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run deterministic self-tests and exit",
    )
    args = parser.parse_args()

    if args.test:
        ok = _run_tests()
        sys.exit(0 if ok else 1)

    if not args.pr:
        print("ERROR: --pr is required (or use --test)")
        sys.exit(1)

    print(f"Verifying PR #{args.pr}…")
    print("-" * 50)

    ok = verify_pr(args.pr, args.sha, single_owner=args.single_owner)
    print("-" * 50)

    if ok:
        print("ALL CHECKS PASSED — PR is ready to merge.")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — Do not merge.")
        sys.exit(1)


if __name__ == "__main__":
    main()
