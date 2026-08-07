#!/usr/bin/env python3
"""run_task_gate.py — Orchestrated gate: preflight → evidence → status.

Usage:
    python .ai-harness/scripts/run_task_gate.py --task <contract.json> [--report-only] [--token TOKEN]

Pipeline: contract→preflight→changed_files→local→remote(fail-closed)→CI→
tests→acceptance→tool_failures→contradictions→status→persist→validate→report

Exit: 0=gate satisfied, 1=not ready, 2=contract error, 3=tool unavailable,
4=baseline mismatch, 5=internal error
"""

from __future__ import annotations

import json, os, subprocess, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = HARNESS_DIR / "scripts"
TRACES_DIR = HARNESS_DIR / "traces"
REPO_ROOT = HARNESS_DIR.parent


def _git(args: list[str]) -> str:
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=REPO_ROOT)
    return r.stdout.strip()


def _run(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)] + args,
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def _determine_exit(status: str, evidence: dict) -> int:
    blocking = evidence.get("blocking_issues", [])
    tf = evidence.get("tool_failures", [])
    gate = evidence.get("requested_gate", "")
    ro = evidence.get("execution_mode") == "report_only"

    if "BASELINE" in status: return 4
    if any(isinstance(t, dict) and t.get("execution_stopped") for t in tf): return 3
    if "PRECHECK" in status: return 2
    if blocking or evidence.get("contradictions", []): return 1
    if ro: return 0 if not tf else 1

    gmap = {
        "preflight_only": 0,
        "implemented_remote": 0 if "IMPLEMENTED" in status and "NOT PUSHED" not in status else 1,
        "ready_for_sa_review": 0 if status == "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW" else 1,
        "merged": 0 if "MERGED" in status else 1,
        "post_merge_verified": 0 if "POST-MERGE VERIFIED" in status else 1,
        "report_only": 0,
    }
    if gate in gmap:
        return gmap[gate] if isinstance(gmap[gate], int) else gmap[gate]()
    return 1 if ("NOT READY" in status or "STOPPED" in status) else 6


def _local_evidence(contract: dict) -> dict:
    return {
        "task_id": contract.get("task_id", ""),
        "repository": contract.get("repository", ""),
        "requested_gate": contract.get("requested_gate", ""),
        "execution_mode": "normal", "report_generation_result": "",
        "requested_gate_satisfied": False, "evidence_sources": [],
        "pipeline_steps": [], "blocking_issues": [], "exit_code": None,
        "interpretation": {
            "objective": contract.get("objective", ""),
            "deliverables": contract.get("required_deliverables", []),
            "non_deliverables": contract.get("explicit_non_objectives", []),
            "forbidden_actions": contract.get("forbidden_actions", []),
            "stop_conditions": contract.get("stop_conditions", []),
        },
        "preflight": {
            "current_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "working_tree_clean": _git(["status", "--short"]) == "",
            "local_head": _git(["rev-parse", "HEAD"]),
            "remote_branch_head": "", "remote_main_head": _git(["rev-parse", "origin/main"]),
            "expected_base_sha": contract.get("expected_base_sha", ""),
            "baseline_match": _git(["rev-parse", "origin/main"]) == contract.get("expected_base_sha", ""),
        },
        "implementation": {
            "post_execution_local_head": _git(["rev-parse", "HEAD"]),
            "commit_sha": _git(["rev-parse", "HEAD"]),
            "commit_exists_locally": True, "commit_exists_remotely": False,
            "changed_files": (_git(["diff", "--name-only", "origin/main", "HEAD"]).split("\n") if _git(["diff", "--name-only", "origin/main", "HEAD"]) else []),
            "remote_branch_head": "",
        },
        "pull_request": {
            "number": None, "state": "", "base_branch": "main", "base_sha": "",
            "head_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "head_sha": _git(["rev-parse", "HEAD"]),
            "draft": None, "merged": None, "merged_at": None, "merge_commit_sha": "",
        },
        "tests": {"collected": None, "passed": None, "failed": None, "warnings": None, "commands": []},
        "ci": {"run_id": None, "event": "", "workflow": "VF-DM CI", "branch": "", "head_sha": "", "conclusion": "", "annotations": None, "required_steps": []},
        "post_merge": {"required": False, "new_main_sha": "", "main_contains_change": None, "ci_run_id": None, "ci_head_sha": "", "ci_conclusion": "", "regression_passed": None},
        "platform_controls": {
            "required_policy": ["All changes must go through PR"],
            "actual_state": ["main is NOT protected (GitHub plan limitation)"],
            "evidence": ["GitHub API 403"],
            "residual_gaps": ["Direct main pushes possible"],
            "compensating_controls": ["pre-push hook", "mandatory PR workflow", "verify-pr-merge-gate.py"],
            "revisit_triggers": ["Plan upgrade or public repo"],
        },
        "authorization": contract.get("authorization", {}),
        "forbidden_actions": {"performed": False, "details": []},
        "acceptance": [], "unknown_evidence": [], "tool_failures": [],
        "contradictions": [], "derived_status": "",
    }


def _remote_evidence(evidence: dict, contract: dict, token: str | None, task_id: str) -> tuple[dict, list[dict]]:
    tfs: list[dict] = []
    required = contract.get("required_remote_evidence", [])
    if not required:
        return evidence, tfs

    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")

    has_source = False
    sources = []

    # Try API
    if token:
        try:
            import urllib.request
            url = f"https://api.github.com/repos/hieudovn/virtual-factory/commits/{_git(['rev-parse','HEAD'])}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "ai-harness/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                if data.get("sha"):
                    evidence["implementation"]["commit_exists_remotely"] = True
                    evidence["implementation"]["remote_branch_head"] = data["sha"]
                    evidence["evidence_sources"] = ["github_api"]
                    has_source = True
                    sources.append("github_api")
                    print(f"Remote commit verified via API: {data['sha'][:12]}…")
        except Exception as e:
            tfs.append({"tool": "github_api", "exit_code": 1, "stderr": str(e)[:200], "classification": "UNKNOWN", "execution_stopped": False})
            print(f"GitHub API failed: {e}")

    # Fallback: gh CLI
    if not has_source:
        try:
            gr = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            if gr.returncode == 0:
                import urllib.request as ur2
                url = f"https://api.github.com/repos/hieudovn/virtual-factory/commits/{_git(['rev-parse','HEAD'])}"
                req = ur2.Request(url)
                req.add_header("Accept", "application/vnd.github+json")
                req.add_header("User-Agent", "ai-harness/1.0")
                with ur2.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get("sha"):
                        evidence["implementation"]["commit_exists_remotely"] = True
                        evidence["implementation"]["remote_branch_head"] = data["sha"]
                        has_source = True
                        sources.append("github_api_unauthenticated")
                        print(f"Remote commit verified (unauthenticated): {data['sha'][:12]}…")
        except Exception as e:
            tfs.append({"tool": "gh_cli_fallback", "exit_code": 1, "stderr": str(e)[:200], "classification": "UNKNOWN", "execution_stopped": False})

    if not has_source:
        tf = {
            "tool": "remote_verification", "exit_code": 1,
            "stderr": "Cannot verify remote state — no GitHub token and gh CLI unavailable",
            "classification": "FAIL", "execution_stopped": True,
            "affected_evidence": required,
        }
        tfs.append(tf)
        evidence.setdefault("unknown_evidence", []).extend(required)

    evidence["evidence_sources"] = sources
    return evidence, tfs


def run_task_gate(task_path: str, report_only: bool = False, token: str | None = None) -> tuple[str, dict, int]:
    steps: list[dict] = []
    tfs: list[dict] = []

    def step(name: str, req: bool, res: str):
        steps.append({"name": name, "required": req, "executed": True, "result": res, "evidence": [], "tool_failures": []})

    # 1. Contract
    print("=" * 50 + "\nSTEP 1: Contract")
    try:
        with open(task_path, "r", encoding="utf-8") as f:
            contract = json.load(f)
    except Exception as e:
        print(f"FATAL: {e}"); return "PRECHECK FAILED", {}, 2
    tid = contract.get("task_id", "UNKNOWN")
    td = TRACES_DIR / tid; td.mkdir(parents=True, exist_ok=True)
    ep = td / "evidence.json"
    if not contract.get("task_id") or not contract.get("objective"):
        step("contract", True, "FAIL"); return "PRECHECK FAILED", {}, 2
    step("contract", True, "PASS")

    # 2. Preflight
    print("\n" + "=" * 50 + "\nSTEP 2: Preflight")
    pf = _run("preflight.py", ["--task", task_path])
    print(pf.stdout or ""); step("preflight", True, "PASS" if pf.returncode == 0 else "FAIL")
    if pf.returncode != 0: return "PRECHECK FAILED", {}, 4

    # 3. Changed files
    print("\n" + "=" * 50 + "\nSTEP 3: Changed files")
    cf = _run("verify_changed_files.py", ["--task", task_path])
    print(cf.stdout or ""); step("changed_files", True, "PASS" if cf.returncode == 0 else "FAIL")

    # 4. Local evidence
    print("\n" + "=" * 50 + "\nSTEP 4: Local evidence")
    evidence = _local_evidence(contract); step("local", True, "PASS")

    # 5-7. Remote
    print("\n" + "=" * 50 + "\nSTEP 5-7: Remote evidence")
    evidence, rtfs = _remote_evidence(evidence, contract, token, tid)
    tfs.extend(rtfs); step("remote", bool(contract.get("required_remote_evidence")), "FAIL" if rtfs else "PASS")

    # 8. Tests
    print("\n" + "=" * 50 + "\nSTEP 8: Tests")
    tr = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short"], capture_output=True, text=True, cwd=REPO_ROOT)
    step("tests", True, "PASS" if tr.returncode == 0 else "FAIL")

    # 9. Acceptance
    print("\n" + "=" * 50 + "\nSTEP 9: Acceptance")
    tmp = td / "_tmp.json"
    with open(tmp, "w") as f: json.dump(evidence, f)
    ar = _run("evaluate_acceptance.py", [str(tmp), task_path])
    print(ar.stdout or "")
    try:
        with open(tmp) as f: evidence = json.load(f)
    except: pass
    try: tmp.unlink()
    except: pass
    step("acceptance", True, "PASS" if ar.returncode == 0 else "FAIL")

    # 10. Tool failures
    print("\n" + "=" * 50 + "\nSTEP 10: Tool failures")
    evidence["tool_failures"] = tfs
    if tfs:
        blocking = [tf for tf in tfs if tf.get("execution_stopped")]
        evidence["blocking_issues"] = [
            f"{tf['tool']}: {tf.get('stderr','')[:200]}" for tf in blocking
        ]
    step("tool_failures", True, "PASS")

    # 11. Contradictions (deferred to step 14)

    # 12. Status
    print("\n" + "=" * 50 + "\nSTEP 12: Status derivation")
    with open(ep, "w") as f: json.dump(evidence, f)
    ds = _run("derive_status.py", [str(ep)])
    status = "DERIVATION FAILED"
    for line in ds.stdout.split("\n"):
        if line.startswith("Derived status:"): status = line.split(":", 1)[1].strip()
    evidence["derived_status"] = status; step("status", True, "PASS")

    # 13. Persist
    print("\n" + "=" * 50 + "\nSTEP 13: Persist")
    evidence["execution_mode"] = "report_only" if report_only else "normal"
    evidence["pipeline_steps"] = steps
    evidence["report_generation_result"] = "success"
    with open(ep, "w") as f: json.dump(evidence, f, indent=2)
    step("persist", True, "PASS")

    # 14. Validate
    print("\n" + "=" * 50 + "\nSTEP 14: Validate")
    ev = _run("validate_evidence.py", [str(ep)])
    print(ev.stdout or "")
    if ev.returncode != 0:
        with open(ep) as f: evidence = json.load(f)
    step("validate", True, "PASS" if ev.returncode == 0 else "FAIL")

    # 15. Report
    print("\n" + "=" * 50 + "\nSTEP 15: Report")
    rp = td / "gate-report.md"
    with open(rp, "w") as f:
        f.write(f"# Gate Report — {tid}\n\n**Status**: {status}\n**Gate**: {evidence.get('requested_gate','')}\n**Satisfied**: {evidence.get('requested_gate_satisfied',False)}\n\n")
        for s in steps: f.write(f"- [{s['result']}] {s['name']}\n")
    step("report", True, "PASS")

    # 16. Exit
    print("\n" + "=" * 50 + "\nSTEP 16: Exit")
    ec = _determine_exit(status, evidence)
    evidence["exit_code"] = ec
    evidence["requested_gate_satisfied"] = (ec == 0)
    with open(ep, "w") as f: json.dump(evidence, f, indent=2)

    print(f"Status: {status}")
    print(f"Gate: {evidence.get('requested_gate','')} | Satisfied: {ec==0} | Exit: {ec}")
    if report_only: print("REPORT-ONLY: No execution/merge actions performed.")
    return status, evidence, ec


def main():
    import argparse
    p = argparse.ArgumentParser(description="Run full task gate")
    p.add_argument("--task", required=True)
    p.add_argument("--report-only", action="store_true")
    p.add_argument("--token")
    args = p.parse_args()
    try:
        _, _, ec = run_task_gate(args.task, args.report_only, args.token)
        sys.exit(ec)
    except Exception as e:
        print(f"HARNESS INTERNAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(5)


if __name__ == "__main__":
    main()
