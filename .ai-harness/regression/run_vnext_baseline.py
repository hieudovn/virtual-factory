#!/usr/bin/env python3
"""run_vnext_baseline.py — canonical G8 Platform vNext regression baseline.

Deterministic, repo-native entrypoint for the accepted vNext regression
baseline (GitHub Issue #53). It runs EVERY required group defined in the
machine-readable manifest (``vnext_baseline_manifest.json``) and reports a
per-group PASS/FAIL, clearly naming the failing group. Manifest groups are
first-class and may be either:

* ``type: "pytest"``  — the existing ``python -m pytest -q -p no:cacheprovider``
  invocation over ``files`` or a ``directory``; or
* ``type: "command"`` — an explicit repo-native command (argv) run from the repo
  root, e.g. compile / static / preflight / changed-file harness checks.

Two bounded substitutions are available in a ``command`` group's ``cmd``:
``{python}`` -> the running interpreter, and ``{changed_files_file}`` -> a
materialized ``git diff --name-only <changed_files_base> HEAD`` artifact file
(for a ``kind: "changed_files"`` command). The default invocation runs the
COMPLETE required baseline (pytest groups AND non-pytest checks) and exits
non-zero if any required group fails.

Exit codes:
    0  all required groups green
    1  one or more required groups failed
    2  manifest/usage error

Usage:
    python .ai-harness/regression/run_vnext_baseline.py
    python .ai-harness/regression/run_vnext_baseline.py --groups g1_workspace,checks_compile
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
CHANGED_FILES_DEFAULT = ".ai-harness/traces/g8_changed_files.txt"


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError(f"manifest has no groups: {path}")
    return manifest


def _materialize_changed_files(group: dict, manifest: dict) -> Path:
    """Materialize ``git diff --name-only <base> HEAD`` into a UTF-8 file.

    Used by ``kind: "changed_files"`` command groups so the repo's
    ``verify_changed_files.py`` can validate exactly the current-gate delta.
    The base resolves from the group or the manifest gate context.
    """
    base = group.get("changed_files_base") or manifest.get("gate", {}).get(
        "changed_files_base"
    )
    if not base:
        raise ValueError("changed_files command group requires changed_files_base")
    out_rel = group.get("changed_files_output", CHANGED_FILES_DEFAULT)
    out_path = ROOT / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git diff {base}..HEAD failed: {proc.stderr.strip()}"
        )
    out_path.write_text(proc.stdout, encoding="utf-8")
    return out_path


def _group_command(group: dict, manifest: dict) -> list[str]:
    """Build the executable command for one manifest group."""
    gtype = group.get("type", "pytest")
    if gtype == "pytest":
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        if group.get("directory"):
            cmd.append(str(group["directory"]))
        else:
            for rel in group.get("files", []):
                cmd.append(str(rel))
        return cmd
    if gtype == "command":
        raw = [str(arg) for arg in group.get("cmd", [])]
        if not raw:
            raise ValueError(f"command group {group.get('id', '?')} has empty cmd")
        cmd: list[str] = []
        changed_file: Path | None = None
        if group.get("kind") == "changed_files":
            changed_file = _materialize_changed_files(group, manifest)
        for arg in raw:
            if arg == "{python}":
                cmd.append(sys.executable)
            elif arg == "{changed_files_file}":
                if changed_file is None:
                    raise ValueError(
                        f"command group {group.get('id', '?')} uses "
                        f"{{changed_files_file}} but is not kind=changed_files"
                    )
                cmd.append(str(changed_file))
            elif arg == "{task_contract}":
                task = manifest.get("gate", {}).get("task_contract")
                if not task:
                    raise ValueError("command group uses {task_contract} but manifest has no gate.task_contract")
                cmd.append(str(task))
            else:
                cmd.append(arg)
        return cmd
    raise ValueError(
        f"unsupported group type {gtype!r} for group {group.get('id', '?')}"
    )


def _result_tail(proc: subprocess.CompletedProcess) -> str:
    """Return the last non-empty output lines for reporting."""
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    lines = [ln for ln in out.splitlines() if ln.strip()]
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
        try:
            cmd = _group_command(group, manifest)
        except ValueError as exc:
            print(f"\n[baseline] group '{gid}': ERROR ({exc})")
            failed_groups.append(gid)
            results.append(
                {
                    "id": gid,
                    "gate": group.get("gate", ""),
                    "type": group.get("type", "pytest"),
                    "status": "ERROR",
                    "exit_code": -1,
                    "tail": str(exc),
                }
            )
            continue
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
                "type": group.get("type", "pytest"),
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
