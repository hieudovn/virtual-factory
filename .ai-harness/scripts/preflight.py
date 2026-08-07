#!/usr/bin/env python3
"""preflight.py — Validate task contract, baseline, branch, and working tree.

Usage:
    python .ai-harness/scripts/preflight.py --task <task-contract.json>

Inspects repository state without modifying it.
Exits non-zero when preflight fails.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _git(args: list[str]) -> str:
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _git_maybe(args: list[str]) -> str:
    """Run a git command, return '' on failure."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    return result.stdout.strip()


def run_preflight(task_contract: dict) -> tuple[bool, dict]:
    """Run preflight checks. Returns (passed, evidence_dict)."""
    evidence: dict = {
        "current_branch": "",
        "working_tree_clean": False,
        "local_head": "",
        "remote_branch_head": "",
        "remote_main_head": "",
        "expected_base_sha": "",
        "baseline_match": False,
    }
    failures: list[str] = []

    repo_root = Path(__file__).resolve().parent.parent.parent

    # --- Repository check ---
    expected_repo = task_contract.get("repository", "")
    if expected_repo:
        remote_url = _git_maybe(["remote", "get-url", "origin"])
        if expected_repo not in remote_url:
            failures.append(
                f"Repository mismatch: expected '{expected_repo}' in remote "
                f"'{remote_url}'"
            )

    # --- Working tree ---
    status = _git_maybe(["status", "--short"])
    evidence["working_tree_clean"] = (status == "")
    if status:
        failures.append(f"Working tree is not clean:\n{status}")

    # --- Current branch ---
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    evidence["current_branch"] = branch

    expected_branch = task_contract.get("required_branch", "")
    if expected_branch and branch != expected_branch:
        failures.append(
            f"Branch mismatch: on '{branch}', expected '{expected_branch}'"
        )

    # --- Local HEAD ---
    local_head = _git(["rev-parse", "HEAD"])
    evidence["local_head"] = local_head

    # --- Remote main ---
    _git(["fetch", "origin", "main"])
    remote_main = _git(["rev-parse", "origin/main"])
    evidence["remote_main_head"] = remote_main

    # --- Expected baseline ---
    expected_base = task_contract.get("expected_base_sha", "")
    evidence["expected_base_sha"] = expected_base

    if expected_base:
        if remote_main != expected_base:
            failures.append(
                f"Baseline mismatch: expected {expected_base[:12]}…, "
                f"actual origin/main is {remote_main[:12]}…"
            )
        else:
            evidence["baseline_match"] = True

    # --- Target branch ---
    try:
        _git(["fetch", "origin", expected_branch])
        remote_branch_head = _git(["rev-parse", f"origin/{expected_branch}"])
        evidence["remote_branch_head"] = remote_branch_head
    except RuntimeError:
        evidence["remote_branch_head"] = ""

    # --- Task contract validation ---
    if not task_contract.get("task_id"):
        failures.append("Task contract missing task_id")
    if not task_contract.get("objective"):
        failures.append("Task contract missing objective")
    if not task_contract.get("acceptance_criteria"):
        failures.append("Task contract missing acceptance_criteria")

    # --- Authorization validation ---
    auth = task_contract.get("authorization", {})
    if auth.get("may_merge") and not auth.get("may_open_pr"):
        failures.append("Contract authorizes merge but not PR creation")

    passed = len(failures) == 0

    if failures:
        print("PRECHECK FAILED:")
        for f in failures:
            print(f"  - {f}")
    else:
        print("PRECHECK PASSED")

    return passed, evidence


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Preflight task contract and repository state validation"
    )
    parser.add_argument(
        "--task", required=True, help="Path to task contract JSON"
    )
    parser.add_argument(
        "--json-output", help="Write evidence JSON to file",
    )
    args = parser.parse_args()

    with open(args.task, "r", encoding="utf-8") as f:
        contract = json.load(f)

    passed, evidence = run_preflight(contract)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
