#!/usr/bin/env python3
"""Fail-closed SA design PR scope gate; never substitutes for PM execution gate.

Usage:
  python .ai-harness/scripts/sa_design_gate.py --base <SHA> --head <SHA>
      --branch sa/design/example --repository hieudovn/virtual-factory
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = ".ai-harness/sa-design/tasks/"
DESIGN_PREFIXES = (
    "docs/architecture/", "docs/design/", "docs/plans/",
    "docs/reports/", "docs/governance/",
    ".ai-harness/sa-design/tasks/",
    ".ai-harness/sa-design/reports/",
)
GOVERNANCE_EXTRAS = {
    "AGENTS.md",
    ".ai-harness/README.md",
    ".ai-harness/SA-DESIGN-WORKFLOW.md",
    ".ai-harness/scripts/sa_design_gate.py",
    ".ai-harness/tests/test_sa_design_gate.py",
    ".github/workflows/sa-design-gate.yml",
}
SHA = re.compile(r"^[a-f0-9]{40}$")
REPO = "hieudovn/virtual-factory"


class DesignGateError(ValueError):
    pass


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise DesignGateError("git " + " ".join(args) + ": " +
                              result.stderr.decode(errors="replace")[:300])
    return result.stdout.decode("utf-8")


def changed_files(base: str, head: str) -> list[str]:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise DesignGateError("invalid SHA")
    _git("merge-base", "--is-ancestor", base, head)
    output = _git("diff", "--no-renames", "--name-only", "-z", base, head)
    paths = [p for p in output.split("\0") if p]
    if not paths or len(paths) != len(set(paths)):
        raise DesignGateError("empty or duplicate diff")
    return paths


def validate_contract(task: dict, *, branch: str, repository: str,
                      base: str, paths: list[str]) -> dict:
    if repository != REPO or task.get("repository") != REPO:
        raise DesignGateError("repository mismatch")
    kind = task.get("class")
    prefix = {"design": "sa/design/", "governance": "sa/governance/"}.get(kind)
    if not prefix or not branch.startswith(prefix) or task.get("branch") != branch:
        raise DesignGateError("branch/class mismatch")
    if not SHA.fullmatch(base) or task.get("expected_base_sha") != base:
        raise DesignGateError("expected main baseline mismatch")
    if not isinstance(task.get("approval_issue"), int) or isinstance(task["approval_issue"], bool) or task["approval_issue"] <= 0:
        raise DesignGateError("missing authority issue")
    authority = task.get("authority")
    if kind == "governance" and authority != "PO_APPROVED_GOVERNANCE":
        raise DesignGateError("governance requires PO authority")
    if kind == "design" and authority not in ("SA_DESIGN_DRAFT", "SA_APPROVED_DESIGN"):
        raise DesignGateError("design authority invalid")
    task_id = task.get("task_id")
    if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{4,100}", task_id):
        raise DesignGateError("invalid task id")
    task_path = TASK_DIR + task_id + ".json"
    allowed = task.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed or any(
        not isinstance(p, str) or not p or p.endswith("/") for p in allowed
    ) or len(allowed) != len(set(allowed)):
        raise DesignGateError("allowlist must contain unique exact paths")
    if task_path not in paths or task_path not in allowed:
        raise DesignGateError("task contract must be part of the PR diff and allowlist")
    for path in paths:
        # Hardcoded class boundary takes precedence over self-authored manifest.
        safe = path.startswith(DESIGN_PREFIXES)
        if kind == "governance":
            safe = safe or path in GOVERNANCE_EXTRAS
        if not safe or path not in allowed:
            raise DesignGateError("forbidden or unapproved path: " + path)
        if path.startswith(".github/") and kind != "governance":
            raise DesignGateError("design may not modify workflows")
    if kind == "design" and not any(p.startswith("docs/") for p in paths):
        raise DesignGateError("design PR must include documentation")
    return {"task_id": task_id, "class": kind, "authority": authority,
            "changed_paths": paths, "base_sha": base, "branch": branch}


def run(base: str, head: str, branch: str, repository: str) -> dict:
    paths = changed_files(base, head)
    if _git("rev-parse", "HEAD").strip() != head:
        raise DesignGateError("checkout not at declared exact PR head")
    task_paths = [p for p in paths if p.startswith(TASK_DIR) and p.endswith(".json")]
    if len(task_paths) != 1:
        raise DesignGateError("expected exactly one SA task contract changed")
    path = ROOT / task_paths[0]
    try:
        task = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise DesignGateError("unreadable SA task contract: " + str(err)) from err
    return validate_contract(task, branch=branch, repository=repository, base=base, paths=paths)


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("base", "head", "branch", "repository"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        result = run(args.base, args.head, args.branch, args.repository)
    except DesignGateError as err:
        print("SA_DESIGN_GATE=FAIL " + str(err))
        return 1
    print("SA_DESIGN_GATE=PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
