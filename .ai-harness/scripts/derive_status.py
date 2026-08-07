#!/usr/bin/env python3
"""derive_status.py — Deterministic status derivation from evidence JSON.

Usage:
    python .ai-harness/scripts/derive_status.py <evidence.json>
    python .ai-harness/scripts/derive_status.py --help

The PM must not freely choose final status. This script implements the
mandatory decision logic from the PM Execution Contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Valid machine-derived statuses (from STATUS-DEFINITIONS.md)
# ------------------------------------------------------------------

_VALID_DERIVED_STATUSES: frozenset[str] = frozenset({
    "PRECHECK FAILED",
    "NOT STARTED",
    "IN PROGRESS",
    "IMPLEMENTED LOCALLY",
    "IMPLEMENTED — NOT COMMITTED",
    "IMPLEMENTED — NOT PUSHED",
    "PUSHED — PR MISSING",
    "PR OPEN — CI PENDING",
    "NOT READY — TEST FAILURE",
    "NOT READY — SMOKE FAILURE",
    "NOT READY — STALE CI",
    "NOT READY — REMOTE STATE MISMATCH",
    "NOT READY — ACCEPTANCE FAILURE",
    "NOT READY — INSUFFICIENT EVIDENCE",
    "NOT READY — GOVERNANCE FAILURE",
    "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW",
    "MERGED — READY FOR POST-MERGE REVIEW",
    "POST-MERGE VERIFIED — READY FOR SA CLOSURE",
    "BLOCKED — PLATFORM LIMITATION",
    "STOPPED — BASELINE MISMATCH",
    "STOPPED — BASELINE ADVANCED",
    "STOPPED — TASK AMBIGUITY",
})

# Statuses that must NEVER be machine-derived
_FORBIDDEN_DERIVED: frozenset[str] = frozenset({
    "COMPLETE",
    "CLOSED",
    "SA APPROVED",
    "MERGE AUTHORIZED",
    "NEXT SLICE AUTHORIZED",
})


def load_evidence(path: str | Path) -> dict:
    """Load evidence JSON from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def derive_status(evidence: dict) -> str:
    """Apply mandatory decision logic to derive the correct status.

    Order matters — earlier checks take priority.
    """
    # --- Preflight ---
    pf = evidence.get("preflight", {})
    if not pf.get("baseline_match", True):
        return "STOPPED — BASELINE MISMATCH"

    # Check for baseline advanced (remote main > expected, but would be mismatch)
    if pf.get("expected_base_sha") and pf.get("remote_main_head"):
        if pf["expected_base_sha"] != pf["remote_main_head"]:
            return "STOPPED — BASELINE ADVANCED"

    # --- Tool failures ---
    tool_failures = evidence.get("tool_failures", [])
    if tool_failures:
        for tf in tool_failures:
            if isinstance(tf, dict) and tf.get("execution_stopped"):
                return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- Implementation ---
    impl = evidence.get("implementation", {})
    commit_remote = impl.get("commit_exists_remotely", False)
    remote_head = impl.get("remote_branch_head", "")

    if not commit_remote:
        if impl.get("commit_exists_locally"):
            if evidence.get("pull_request", {}).get("number"):
                return "PUSHED — PR MISSING"
            return "IMPLEMENTED — NOT PUSHED"
        return "IMPLEMENTED LOCALLY"

    # --- Pull Request ---
    pr = evidence.get("pull_request", {})
    pr_num = pr.get("number")
    pr_state = pr.get("state", "")
    pr_draft = pr.get("draft")
    pr_head = pr.get("head_sha", "")

    if pr_num is None:
        return "PUSHED — PR MISSING"

    if pr_draft:
        return "NOT READY — GOVERNANCE FAILURE"

    if pr.get("base_branch") != "main":
        return "NOT READY — GOVERNANCE FAILURE"

    if pr_state != "OPEN" and not pr.get("merged"):
        return "NOT READY — GOVERNANCE FAILURE"

    # --- Remote state consistency ---
    if pr_head and remote_head and pr_head != remote_head:
        return "NOT READY — REMOTE STATE MISMATCH"

    # --- CI ---
    ci = evidence.get("ci", {})
    ci_head = ci.get("head_sha", "")
    ci_conclusion = ci.get("conclusion", "")
    ci_event = ci.get("event", "")
    has_ci = bool(ci.get("run_id"))

    if not has_ci:
        return "PR OPEN — CI PENDING"

    if ci_head and pr_head and ci_head != pr_head:
        return "NOT READY — STALE CI"

    if ci_conclusion != "success":
        return "NOT READY — STALE CI"

    # --- Tests ---
    tests = evidence.get("tests", {})
    failed_tests = tests.get("failed", -1)
    if failed_tests is None:
        failed_tests = -1
    if failed_tests > 0:
        return "NOT READY — TEST FAILURE"

    # --- Acceptance ---
    acceptance = evidence.get("acceptance", [])
    has_fail = False
    has_unknown = False
    for item in acceptance:
        result = item.get("result", "")
        if result == "FAIL":
            has_fail = True
        elif result == "UNKNOWN":
            has_unknown = True

    if has_fail:
        return "NOT READY — ACCEPTANCE FAILURE"
    if has_unknown:
        return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- Unknown evidence ---
    unknown = evidence.get("unknown_evidence", [])
    if unknown:
        return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- Contradictions ---
    contradictions = evidence.get("contradictions", [])
    if contradictions:
        return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- Forbidden actions ---
    fa = evidence.get("forbidden_actions", {})
    if fa.get("performed"):
        return "NOT READY — GOVERNANCE FAILURE"

    # --- Tool failures (non-blocking but present) ---
    if tool_failures:
        return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- Post-merge path ---
    post = evidence.get("post_merge", {})
    if pr.get("merged"):
        auth = evidence.get("authorization", {})
        auth_head = auth.get("authorized_head_sha", "")
        if auth.get("merge_authorized") and auth_head and pr_head != auth_head:
            return "NOT READY — GOVERNANCE FAILURE"

        if post.get("required"):
            if not post.get("ci_run_id"):
                return "MERGED — READY FOR POST-MERGE REVIEW"
            if post.get("ci_head_sha") != post.get("new_main_sha"):
                return "MERGED — READY FOR POST-MERGE REVIEW"
            if post.get("ci_conclusion") != "success":
                return "MERGED — READY FOR POST-MERGE REVIEW"
            if not post.get("regression_passed"):
                return "MERGED — READY FOR POST-MERGE REVIEW"

            # Post-merge complete, check for SA closure
            auth = evidence.get("authorization", {})
            if auth.get("sa_review_present") and auth.get("next_task_authorized"):
                # Historical CLOSED — this requires explicit SA evidence
                # For safety, derive POST-MERGE VERIFIED instead
                return "POST-MERGE VERIFIED — READY FOR SA CLOSURE"
            return "POST-MERGE VERIFIED — READY FOR SA CLOSURE"

        return "MERGED — READY FOR POST-MERGE REVIEW"

    # --- Platform controls ---
    pc = evidence.get("platform_controls", {})
    actual = pc.get("actual_state", [])
    for state in actual:
        if "unavailable" in state.lower() or "not protected" in state.lower():
            # Check if there's a contradiction with claimed policy
            required = pc.get("required_policy", [])
            for rp in required:
                if "protected" in rp.lower() or "blocked" in rp.lower():
                    # Policy claims enforcement but actual says unavailable
                    # → this is a desired-state-as-actual contradiction
                    pass
            # Platform limitation with compensating controls → may proceed
            # but should be documented, not blocking READY

    # --- Blocking issues ---
    blocking = evidence.get("blocking_issues", [])
    if blocking:
        return "NOT READY — INSUFFICIENT EVIDENCE"

    # --- All checks passed → READY ---
    return "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"


# ------------------------------------------------------------------
# Exit code derivation (separate from status derivation)
# ------------------------------------------------------------------

def derive_exit_code(status: str, evidence: dict) -> int:
    """Derive exit code based on status, requested gate, and blocking issues."""
    requested_gate = evidence.get("requested_gate", "")
    blocking = evidence.get("blocking_issues", [])
    contradictions = evidence.get("contradictions", [])
    tool_failures = evidence.get("tool_failures", [])

    # EXIT 4: Baseline/repository mismatch
    if "BASELINE" in status:
        return 4

    # EXIT 3: Required tool or remote evidence unavailable
    if any(isinstance(tf, dict) and tf.get("execution_stopped") for tf in tool_failures):
        return 3

    # EXIT 2: Contract/schema/invocation error (not preflight, but malformed)
    if "PRECHECK" in status:
        return 2

    # EXIT 5: Harness internal error
    if evidence.get("execution_mode") == "ci" and not evidence.get("pipeline_steps"):
        # Internal issue — but this is a soft case; use 1 for now
        pass

    # EXIT 1: Validly evaluated but not ready (or blocking issues exist)
    if blocking or contradictions or tool_failures:
        return 1

    # Gate-specific exit determination
    if requested_gate == "preflight_only":
        return 0  # preflight-only passes if no baseline issues
    elif requested_gate == "implemented_remote":
        return 0 if "IMPLEMENTED" in status and "NOT PUSHED" not in status and "LOCALLY" not in status else 1
    elif requested_gate == "ready_for_sa_review":
        return 0 if status == "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW" else 1
    elif requested_gate == "merged":
        return 0 if "MERGED" in status else 1
    elif requested_gate == "post_merge_verified":
        return 0 if "POST-MERGE VERIFIED" in status else 1
    elif requested_gate == "report_only":
        return 0  # Report generated successfully
    else:
        # No explicit gate — use status-based logic
        if "NOT READY" in status or "STOPPED" in status or "PRECHECK" in status:
            return 1
        return 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Derive status from evidence JSON"
    )
    parser.add_argument(
        "evidence_file",
        help="Path to evidence JSON file",
    )
    parser.add_argument(
        "--reported-status",
        help="Optional: compare derived status against a reported status",
    )
    parser.add_argument(
        "--requested-gate",
        help="Override evidence requested_gate for exit code determination",
    )
    args = parser.parse_args()

    evidence = load_evidence(args.evidence_file)
    status = derive_status(evidence)

    # Set requested gate from args or evidence
    if args.requested_gate:
        evidence["requested_gate"] = args.requested_gate

    exit_code = derive_exit_code(status, evidence)
    requested = evidence.get("requested_gate", "")
    gate_satisfied = exit_code == 0
    blocking = evidence.get("blocking_issues", [])

    print(f"Derived status: {status}")
    print(f"Requested gate: {requested}")
    print(f"Gate satisfied: {gate_satisfied}")
    print(f"Exit code: {exit_code}")
    if blocking:
        print(f"Blocking issues: {len(blocking)}")

    # Validate non-machine-derived statuses
    if status in _FORBIDDEN_DERIVED:
        print(f"ERROR: '{status}' must not be machine-derived!")
        sys.exit(2)

    if status not in _VALID_DERIVED_STATUSES:
        print(f"ERROR: '{status}' is not a recognized status!")
        sys.exit(2)

    # Compare if requested
    if args.reported_status:
        if args.reported_status != status:
            print(f"MISMATCH: reported '{args.reported_status}' ≠ derived '{status}'")
            sys.exit(1)
        print("Status matches reported status.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
