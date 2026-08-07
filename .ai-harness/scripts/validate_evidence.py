#!/usr/bin/env python3
"""validate_evidence.py — Validate evidence JSON schema and semantic consistency.

Usage:
    python .ai-harness/scripts/validate_evidence.py <evidence.json>

Detects contradictions, missing evidence, and status inconsistencies.
Exits 0 when evidence is consistent and valid.
Exits non-zero when contradictions or validation failures are found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_evidence(evidence: dict) -> tuple[bool, list[str]]:
    """Validate evidence JSON and return (is_valid, contradictions).

    A contradiction means the derived status cannot be trusted.
    """
    contradictions: list[str] = []
    valid = True

    # --- Required top-level fields ---
    required_fields = ["task_id", "repository"]
    for field in required_fields:
        if not evidence.get(field):
            contradictions.append(f"Missing required field: {field}")
            valid = False

    # --- IMPLEMENTED check: remote commit ---
    derived = evidence.get("derived_status", "")
    impl = evidence.get("implementation", {})

    if "IMPLEMENTED" in derived and "LOCALLY" not in derived and "NOT PUSHED" not in derived:
        if not impl.get("commit_exists_remotely"):
            contradictions.append(
                "Status claims IMPLEMENTED but commit_exists_remotely is false"
            )
            valid = False

    # --- READY check: PR required ---
    if "READY FOR SA REVIEW" in derived:
        pr = evidence.get("pull_request", {})
        if not pr.get("number"):
            contradictions.append("Status claims READY but PR number is missing")
            valid = False
        if pr.get("draft"):
            contradictions.append("Status claims READY but PR is draft")
            valid = False
        if pr.get("state") != "OPEN":
            contradictions.append(f"Status claims READY but PR state is '{pr.get('state')}'")
            valid = False

        # CI head must match PR head
        ci = evidence.get("ci", {})
        ci_head = ci.get("head_sha", "")
        pr_head = pr.get("head_sha", "")
        if ci_head and pr_head and ci_head != pr_head:
            contradictions.append(
                f"Status claims READY but CI head ({ci_head[:12]}…) "
                f"differs from PR head ({pr_head[:12]}…)"
            )
            valid = False

        # CI must be success
        if ci.get("conclusion") != "success":
            contradictions.append(
                f"Status claims READY but CI conclusion is '{ci.get('conclusion')}'"
            )
            valid = False

    # --- Tool failures vs READY ---
    tool_failures = evidence.get("tool_failures", [])
    if tool_failures and "READY" in derived:
        contradictions.append(
            f"Status claims READY but {len(tool_failures)} tool failure(s) present"
        )
        valid = False

    # --- MERGED check ---
    if "MERGED" in derived:
        pr = evidence.get("pull_request", {})
        if not pr.get("merged"):
            contradictions.append("Status claims MERGED but PR merged is false")
            valid = False
        if not pr.get("merged_at"):
            contradictions.append("Status claims MERGED but merged_at is missing")
            valid = False
        if not pr.get("merge_commit_sha"):
            contradictions.append("Status claims MERGED but merge_commit_sha is missing")
            valid = False

        # Check authorized head matches merged head
        auth = evidence.get("authorization", {})
        if auth.get("merge_authorized"):
            auth_head = auth.get("authorized_head_sha", "")
            if auth_head and pr.get("head_sha") != auth_head:
                contradictions.append(
                    f"Merge authorized for {auth_head[:12]}… but merged head "
                    f"is {pr.get('head_sha', '')[:12]}…"
                )
                valid = False

    # --- POST-MERGE VERIFIED check ---
    if "POST-MERGE VERIFIED" in derived:
        post = evidence.get("post_merge", {})
        if not post.get("ci_run_id"):
            contradictions.append("Status claims POST-MERGE VERIFIED but post-merge CI missing")
            valid = False
        if post.get("ci_head_sha") != post.get("new_main_sha"):
            contradictions.append("Post-merge CI head ≠ new main SHA")
            valid = False
        if not post.get("regression_passed"):
            contradictions.append("Status claims POST-MERGE VERIFIED but regression not passed")
            valid = False

    # --- CLOSED check ---
    if "CLOSED" in derived:
        auth = evidence.get("authorization", {})
        if not auth.get("sa_review_present"):
            contradictions.append("Status claims CLOSED but SA closure evidence is absent")
            valid = False

    # --- Platform controls: desired ≠ actual ---
    pc = evidence.get("platform_controls", {})
    actual = pc.get("actual_state", [])
    pc_evidence = pc.get("evidence", [])

    claims_protection = any(
        "is protected" in a.lower() or ("blocked" in a.lower() and "not" not in a.lower())
        for a in actual
    )

    # Evidence must reference verifiable sources: API responses, error codes,
    # configuration page references, or explicit tool output.
    # Narrative claims without concrete references are insufficient.
    _verifiable_markers = ["403", "401", "404", "200", "api error", "plan",
                            "upgrade", "unavailable", "not supported",
                            "does not support", "restriction", "pro plan",
                            "settings/branches", "protection rule"]

    has_verifiable_evidence = any(
        any(marker in e.lower() for marker in _verifiable_markers)
        for e in pc_evidence
    )

    if claims_protection and not has_verifiable_evidence:
        contradictions.append(
            "Platform controls: actual_state claims protection but evidence "
            "contains no verifiable API response, error code, or configuration "
            "reference. Narrative claims ('enabled and active') are not "
            "acceptable platform state evidence."
        )
        valid = False

    # --- Test count consistency ---
    tests = evidence.get("tests", {})
    if tests.get("collected") is not None and tests.get("passed") is not None:
        if tests.get("failed", 0) > 0:
            if "READY" in derived:
                contradictions.append(
                    f"Status claims READY but {tests['failed']} tests failed"
                )
                valid = False

    # --- UNKNOWN in acceptance ---
    acceptance = evidence.get("acceptance", [])
    for item in acceptance:
        if item.get("result") == "UNKNOWN":
            if "READY" in derived:
                contradictions.append(
                    f"Status claims READY but acceptance item "
                    f"'{item.get('id')}' is UNKNOWN"
                )
                valid = False

    # --- NEXT SLICE check ---
    auth = evidence.get("authorization", {})
    if auth.get("next_task_authorized") and not auth.get("sa_review_present"):
        contradictions.append(
            "next_task_authorized is true but sa_review_present is false "
            "(next slice cannot be self-authorized)"
        )
        valid = False

    # --- CI event: push vs pull_request ---
    ci = evidence.get("ci", {})
    if ci.get("event") == "push":
        # Push CI is acceptable if the task contract permits it
        # but must be recorded factually
        if "READY" in derived:
            # Factual recording — not a contradiction
            pass

    # --- Unknown evidence vs READY ---
    unknown = evidence.get("unknown_evidence", [])
    if unknown and "READY" in derived:
        contradictions.append(
            f"Status claims READY but {len(unknown)} unknown evidence field(s) exist"
        )
        valid = False

    # --- COMPLETE self-certification ---
    if derived == "COMPLETE":
        auth = evidence.get("authorization", {})
        if not auth.get("sa_review_present"):
            contradictions.append(
                "COMPLETE status is self-certified without SA closure evidence"
            )
            valid = False

    # --- Local-only work cannot be READY ---
    if not impl.get("commit_exists_remotely") and "READY" in derived:
        contradictions.append(
            "Status claims READY but no remote commit exists (local-only work)"
        )
        valid = False

    return valid, contradictions


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate evidence JSON for schema and semantic consistency"
    )
    parser.add_argument(
        "evidence_file",
        help="Path to evidence JSON file",
    )
    args = parser.parse_args()

    with open(args.evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    valid, contradictions = validate_evidence(evidence)

    if contradictions:
        print(f"CONTRADICTIONS FOUND ({len(contradictions)}):")
        for i, c in enumerate(contradictions, 1):
            print(f"  {i}. {c}")

    if valid:
        print("Evidence is consistent.")
        sys.exit(0)
    else:
        print("Evidence is INCONSISTENT.")
        sys.exit(1)


if __name__ == "__main__":
    main()
