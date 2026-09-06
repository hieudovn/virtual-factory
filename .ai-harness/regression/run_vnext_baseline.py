#!/usr/bin/env python3
"""run_vnext_baseline.py — canonical G8 Platform vNext regression baseline.

Deterministic, repo-native entrypoint for the accepted vNext regression
baseline (GitHub Issue #53). It runs every required group defined in the
machine-readable manifest (``vnext_baseline_manifest.json``) with the existing
``python -m pytest -q -p no:cacheprovider`` invocation, reports a per-group
result (clearly identifying the failing group), and exits non-zero if any
required group fails.

Exit codes:
    0  all required groups green
    1  one or more required groups failed
    2  manifest/usage error

Usage:
    python .ai-harness/regression/run_vnext_baseline.py
    python .ai-harness/regression/run_vnext_baseline.py --groups g1_workspace,g7_run_control
    python .ai-harness/regression/run_vnext_baseline.py --json-output .ai-harness/traces/g8_baseline.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_MANIFEST = HERE / "vnext_baseline_manifest.json"


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError(f"manifest has no groups: {path}")
    return manifest


def _pytest_command(group: dict) -> list[str]:
    """Build the existing-pytest invocation for one manifest group."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if group.get("directory"):
        cmd.append(str(group["directory"]))
    else:
        for rel in group.get("files", []):
            cmd.append(str(rel))
    return cmd


def _result_tail(proc: subprocess.CompletedProcess) -> str:
    """Return the last non-empty output lines for reporting."""
    out = (proc.stdout or "").splitlines()
    lines = [ln for ln in out if ln.strip()]
    return "\n".join(lines[-6:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", default=str(DEFAULT_MANIFEST), help="path to the baseline manifest"
    )
    parser.add_argument(
        "--groups", default="", help="comma-separated subset of group ids to run"
    )
    parser.add_argument(
        "--json-output", default="", help="write machine-readable results JSON here"
    )
    args = parser.parse_args()

    try:
        manifest = _load_manifest(Path(args.manifest))
    except (FileNotFoundError, ValueError) as exc:
        print(f"BASELINE ERROR: {exc}")
        return 2

    groups = manifest["groups"]
    if args.groups:
        wanted = {g.strip() for g in args.groups.split(",") if g.strip()}
        groups = [g for g in groups if g["id"] in wanted]
        if not groups:
            print("BASELINE ERROR: no requested groups matched the manifest")
            return 2

    results: list[dict] = []
    failed_groups: list[str] = []
    print("=" * 72)
    print("VF vNext Regression Baseline (Issue #53)")
    print(f"manifest: {Path(args.manifest).resolve()}")
    print("=" * 72)
    for group in groups:
        gid = group["id"]
        cmd = _pytest_command(group)
        print(f"\n[baseline] running group '{gid}' ...")
        print("    " + " ".join(cmd))
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        tail = _result_tail(proc)
        ok = proc.returncode == 0
        status = "PASS" if ok else "FAIL"
        print(f"[baseline] group '{gid}': {status} (exit {proc.returncode})")
        if tail:
            print(f"    {tail}")
        if not ok:
            failed_groups.append(gid)
        results.append(
            {
                "id": gid,
                "gate": group.get("gate", ""),
                "status": status,
                "exit_code": proc.returncode,
                "tail": tail,
            }
        )

    if args.json_output:
        summary = {
            "entrypoint": "python .ai-harness/regression/run_vnext_baseline.py",
            "manifest": str(Path(args.manifest).resolve()),
            "overall": "FAIL" if failed_groups else "PASS",
            "failed_groups": failed_groups,
            "results": results,
        }
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"\n[baseline] machine-readable results written to {out_path}")

    print("\n" + "=" * 72)
    if failed_groups:
        print("BASELINE FAILED groups: " + ", ".join(failed_groups))
        print("=" * 72)
        return 1
    print("BASELINE PASSED: all required groups green")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
