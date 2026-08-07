#!/usr/bin/env python3
"""validate_report_consistency.py — Ensure report matches final evidence.

Usage:
    python .ai-harness/scripts/validate_report_consistency.py <evidence.json> <report.md>
"""

from __future__ import annotations
import json, re, sys
from pathlib import Path


def _extract_section(report: str, heading: str) -> str:
    """Extract a markdown section."""
    m = re.search(rf"#+\s*{re.escape(heading)}.*?\n(.*?)(?=\n#+\s|\Z)", report, re.DOTALL)
    return (m.group(1) if m else "").strip()


def validate(evidence: dict, report: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    status = evidence.get("derived_status", "")

    # ---- VSCode/file links ----
    for pattern in ["vscode-file://", "file:///"]:
        if pattern in report:
            issues.append(f"Report contains editor-local link: {pattern}")

    # ---- CI pending + READY ----
    ci = evidence.get("ci", {})
    if ci.get("status") != "completed" and "READY" in status and "NOT READY" not in status:
        issues.append(f"Status is '{status}' but CI status is '{ci.get('status')}' (not completed)")

    # ---- CI failed + READY ----
    if ci.get("conclusion") not in ("success", "") and "READY" in status and "NOT READY" not in status:
        issues.append(f"Status is '{status}' but CI conclusion is '{ci.get('conclusion')}'")

    # ---- Acceptance pending + READY ----
    acc = evidence.get("acceptance", [])
    has_pending = any(a.get("result") in ("UNKNOWN", "") for a in acc)
    if has_pending and "READY" in status and "NOT READY" not in status:
        issues.append("READY status with pending acceptance criteria")

    # ---- UNKNOWN evidence + READY ----
    unknown = evidence.get("unknown_evidence", [])
    if unknown and "READY" in status and "NOT READY" not in status:
        issues.append(f"READY status with {len(unknown)} unknown evidence fields")

    # ---- Tool failures + READY ----
    tf = evidence.get("tool_failures", [])
    if tf and "READY" in status and "NOT READY" not in status:
        issues.append(f"READY status with {len(tf)} tool failures")

    # ---- Contradictions + READY ----
    contradictions = evidence.get("contradictions", [])
    if contradictions and "READY" in status and "NOT READY" not in status:
        issues.append(f"READY status with {len(contradictions)} contradictions")

    # ---- Blocking issues + READY ----
    blocking = evidence.get("blocking_issues", [])
    if blocking and "READY" in status and "NOT READY" not in status:
        issues.append(f"READY status with {len(blocking)} blocking issues")

    # ---- Requested gate satisfied mismatch ----
    gate_sat = evidence.get("requested_gate_satisfied", False)
    if "READY" in status and "NOT READY" not in status and not gate_sat:
        issues.append("READY status but requested_gate_satisfied is false")

    # ---- Check if report references the evidence SHA ----
    head = evidence.get("implementation", {}).get("commit_sha", "")[:12]
    if head and head not in report:
        issues.append(f"Report does not reference head SHA {head}")

    # ---- Required pipeline steps ----
    steps = evidence.get("pipeline_steps", [])
    for ps in steps:
        if ps.get("required") and ps.get("result") in ("FAIL", "UNKNOWN", "SKIPPED"):
            if "READY" in status and "NOT READY" not in status:
                issues.append(f"READY status but required step '{ps.get('name')}' is {ps.get('result')}")

    passed = len(issues) == 0
    if issues:
        print(f"REPORT INCONSISTENCIES ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Report is consistent with evidence.")
    return passed, issues


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("evidence_file")
    p.add_argument("report_file", nargs="?", default=None)
    args = p.parse_args()

    with open(args.evidence_file) as f:
        evidence = json.load(f)

    if args.report_file and Path(args.report_file).exists():
        with open(args.report_file) as f:
            report = f.read()
    else:
        # Auto-find report
        tid = evidence.get("task_id", "")
        rp = Path(args.evidence_file).parent / "gate-report.md"
        if rp.exists():
            report = rp.read_text()
        else:
            print("No report file found")
            sys.exit(2)

    ok, _ = validate(evidence, report)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
