#!/usr/bin/env python3
"""verify_changed_files.py — Verify changed files against allowlist and blocklist.

Usage:
    python .ai-harness/scripts/verify_changed_files.py \
        --task <task-contract.json> [--changed-files <file>]

Verifies that changed files are within allowed_paths and not in forbidden_paths.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _git_diff(base_sha: str) -> list[str]:
    """Return list of changed files vs base."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base_sha, "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def _matches_prefix(path: str, prefix: str) -> bool:
    """Check if path matches a directory prefix or exact path."""
    if prefix.endswith("/") or prefix.endswith("\\"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "\\")


def verify_changed_files(
    contract: dict,
    changed_files: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Verify changed files. Returns (passed, violations)."""
    violations: list[str] = []

    allowed = contract.get("allowed_paths", [])
    forbidden = contract.get("forbidden_paths", [])

    if changed_files is None:
        base = contract.get("expected_base_sha", "origin/main")
        changed_files = _git_diff(base)

    for path in changed_files:
        # Check forbidden
        for fb in forbidden:
            if _matches_prefix(path, fb):
                violations.append(f"Forbidden path changed: {path} (matches '{fb}')")

        # Check allowed
        if allowed:
            is_allowed = any(_matches_prefix(path, a) for a in allowed)
            if not is_allowed:
                violations.append(f"Path outside allowlist: {path}")

    passed = len(violations) == 0

    if not passed:
        print("FILE VALIDATION FAILED:")
        for v in violations:
            print(f"  - {v}")
    else:
        print(f"FILE VALIDATION PASSED ({len(changed_files)} file(s))")

    return passed, violations


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify changed files against allowlist/blocklist"
    )
    parser.add_argument(
        "--task", required=True, help="Path to task contract JSON"
    )
    parser.add_argument(
        "--changed-files", help="File containing changed files list (one per line)"
    )
    args = parser.parse_args()

    with open(args.task, "r", encoding="utf-8") as f:
        contract = json.load(f)

    changed = None
    if args.changed_files:
        with open(args.changed_files, "r", encoding="utf-8") as f:
            changed = [line.strip() for line in f if line.strip()]

    passed, _ = verify_changed_files(contract, changed)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
