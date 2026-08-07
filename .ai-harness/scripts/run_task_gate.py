#!/usr/bin/env python3
"""run_task_gate.py — Orchestrated task gate: preflight → validation → evidence → status.

Usage:
    python .ai-harness/scripts/run_task_gate.py --task <contract.json> [--report-only]

Orchestrates the full gate pipeline and produces a gate report.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HARNESS_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = HARNESS_DIR / "scripts"
TRACES_DIR = HARNESS_DIR / "traces"


def _run_script(script: str, args: list[str]) -> subprocess.CompletedProcess:
    """Run a harness script."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def run_task_gate(
    task_path: str,
    report_only: bool = False,
    token: str | None = None,
) -> tuple[str, dict]:
    """Run the full task gate. Returns (final_status, evidence)."""
    issues: list[str] = []

    # --- Load task contract ---
    with open(task_path, "r", encoding="utf-8") as f:
        contract = json.load(f)

    task_id = contract.get("task_id", "UNKNOWN")

    # --- Ensure traces directory ---
    trace_dir = TRACES_DIR / task_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Schema validation ---
    print("=" * 50)
    print("STEP 1: Task contract schema validation")
    if not contract.get("task_id"):
        issues.append("Missing task_id")
    if not contract.get("objective"):
        issues.append("Missing objective")
    if not contract.get("acceptance_criteria"):
        issues.append("Missing acceptance_criteria")
    print("Schema validation: " + ("PASS" if not issues else "FAIL"))

    # --- Step 2: Preflight ---
    print("\n" + "=" * 50)
    print("STEP 2: Preflight")
    pf_result = _run_script("preflight.py", ["--task", task_path])
    print(pf_result.stdout)
    if pf_result.returncode != 0:
        print(pf_result.stderr)
        issues.append("Preflight failed")

    # --- Step 3: Changed-files ---
    print("\n" + "=" * 50)
    print("STEP 3: Changed-file validation")
    cf_result = _run_script("verify_changed_files.py", ["--task", task_path])
    print(cf_result.stdout)
    if cf_result.returncode != 0:
        issues.append("Changed-file validation failed")

    # --- Step 4: Collect local evidence ---
    print("\n" + "=" * 50)
    print("STEP 4: Local evidence collection")
    evidence = _collect_local_evidence(contract)

    # --- Step 5: Status derivation ---
    print("\n" + "=" * 50)
    print("STEP 5: Status derivation")

    # Write evidence for derive_status
    evidence_path = trace_dir / "evidence.json"
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    ds_result = _run_script("derive_status.py", [str(evidence_path)])
    derived_status = "DERIVATION FAILED"
    for line in ds_result.stdout.split("\n"):
        if line.startswith("Derived status:"):
            derived_status = line.split(":", 1)[1].strip()
    print(f"Derived status: {derived_status}")
    evidence["derived_status"] = derived_status

    # --- Step 6: Evidence validation ---
    print("\n" + "=" * 50)
    print("STEP 6: Evidence validation")
    ev_result = _run_script("validate_evidence.py", [str(evidence_path)])
    print(ev_result.stdout)
    if ev_result.returncode != 0:
        issues.append("Evidence validation found contradictions")

    # --- Step 7: Remote state (if token available) ---
    if token:
        print("\n" + "=" * 50)
        print("STEP 7: Remote state verification")
        rs_result = _run_script(
            "verify_remote_state.py", [str(evidence_path), "--token", token]
        )
        print(rs_result.stdout)
        if rs_result.returncode != 0:
            issues.append("Remote state verification failed")

        print("\n" + "=" * 50)
        print("STEP 8: Exact-head CI verification")
        ci_result = _run_script(
            "verify_exact_head_ci.py", [str(evidence_path), "--token", token]
        )
        print(ci_result.stdout)
        if ci_result.returncode != 0:
            issues.append("CI verification failed")

    # --- Final ---
    print("\n" + "=" * 50)
    print("GATE RESULT")
    print(f"Task: {task_id}")
    print(f"Derived status: {derived_status}")
    print(f"Issues: {len(issues)}")
    for i in issues:
        print(f"  - {i}")

    # Write gate report
    report_path = trace_dir / "gate-report.md"
    _write_report(report_path, task_id, derived_status, issues, evidence)

    return derived_status, evidence


def _collect_local_evidence(contract: dict) -> dict:
    """Collect local evidence from git and filesystem."""
    import subprocess as sp

    def git(args: list[str]) -> str:
        r = sp.run(["git"] + args, capture_output=True, text=True)
        return r.stdout.strip()

    evidence: dict = {
        "task_id": contract.get("task_id", ""),
        "repository": contract.get("repository", ""),
        "interpretation": {
            "objective": contract.get("objective", ""),
            "deliverables": contract.get("required_deliverables", []),
            "non_deliverables": contract.get("explicit_non_objectives", []),
            "forbidden_actions": contract.get("forbidden_actions", []),
            "stop_conditions": contract.get("stop_conditions", []),
        },
        "preflight": {
            "current_branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "working_tree_clean": git(["status", "--short"]) == "",
            "local_head": git(["rev-parse", "HEAD"]),
            "remote_branch_head": "",
            "remote_main_head": git(["rev-parse", "origin/main"]),
            "expected_base_sha": contract.get("expected_base_sha", ""),
            "baseline_match": git(["rev-parse", "origin/main"]) == contract.get("expected_base_sha", ""),
        },
        "implementation": {
            "post_execution_local_head": git(["rev-parse", "HEAD"]),
            "commit_sha": git(["rev-parse", "HEAD"]),
            "commit_exists_locally": True,
            "commit_exists_remotely": False,
            "changed_files": git(["diff", "--name-only", "origin/main", "HEAD"]).split("\n") if git(["diff", "--name-only", "origin/main", "HEAD"]) else [],
            "remote_branch_head": "",
        },
        "pull_request": {
            "number": None,
            "state": "",
            "base_branch": "main",
            "base_sha": "",
            "head_branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "head_sha": git(["rev-parse", "HEAD"]),
            "draft": None,
            "merged": None,
            "merged_at": None,
            "merge_commit_sha": "",
        },
        "tests": {
            "collected": None,
            "passed": None,
            "failed": None,
            "warnings": None,
            "commands": ["python -m pytest -q --tb=short"],
        },
        "ci": {
            "run_id": None,
            "event": "",
            "workflow": "VF-DM CI",
            "branch": "",
            "head_sha": "",
            "conclusion": "",
            "annotations": None,
            "required_steps": [],
        },
        "post_merge": {
            "required": False,
            "new_main_sha": "",
            "main_contains_change": None,
            "ci_run_id": None,
            "ci_head_sha": "",
            "ci_conclusion": "",
            "regression_passed": None,
        },
        "platform_controls": {
            "required_policy": ["All changes to main must go through PR"],
            "actual_state": ["main is NOT protected (GitHub plan limitation)"],
            "evidence": ["GitHub API 403"],
            "residual_gaps": ["Direct main pushes technically possible"],
            "compensating_controls": [
                "pre-push hook",
                "mandatory PR workflow",
                "verify-pr-merge-gate.py",
                "explicit SA merge authorization",
                "expected-head-SHA merge",
                "post-merge verification",
            ],
            "revisit_triggers": ["Repository plan upgraded or made public"],
        },
        "authorization": contract.get("authorization", {
            "sa_review_present": False,
            "merge_authorized": False,
            "authorized_head_sha": "",
            "next_task_authorized": False,
        }),
        "forbidden_actions": {
            "performed": False,
            "details": [],
        },
        "acceptance": [
            {"id": item["id"], "result": "UNKNOWN", "evidence": ""}
            for item in contract.get("acceptance_criteria", [])
        ],
        "unknown_evidence": [],
        "tool_failures": [],
        "contradictions": [],
        "derived_status": "",
    }
    return evidence


def _write_report(
    path: Path, task_id: str, status: str, issues: list[str], evidence: dict,
) -> None:
    """Write gate report markdown."""
    lines = [
        f"# Gate Report — {task_id}",
        f"",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"**Derived status**: {status}",
        f"",
        f"## Issues ({len(issues)})",
    ]
    for i in issues:
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## Evidence Summary")
    lines.append(f"- Branch: {evidence.get('preflight', {}).get('current_branch', 'N/A')}")
    lines.append(f"- Local HEAD: {evidence.get('implementation', {}).get('commit_sha', 'N/A')[:12]}…")
    lines.append(f"- Baseline match: {evidence.get('preflight', {}).get('baseline_match', False)}")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run full task gate")
    parser.add_argument("--task", required=True, help="Path to task contract JSON")
    parser.add_argument("--report-only", action="store_true", help="Report-only mode")
    parser.add_argument("--token", help="GitHub personal access token")
    args = parser.parse_args()

    status, evidence = run_task_gate(args.task, args.report_only, args.token)
    sys.exit(0 if "READY" in status else 1)


if __name__ == "__main__":
    main()
