#!/usr/bin/env python3
"""verify_exact_head_ci.py — Collect CI workflow evidence for exact head SHA.

Uses: GitHub API (token) → gh CLI (authenticated) → fail closed.
Outputs structured JSON evidence block.
"""

from __future__ import annotations
import json, os, subprocess, sys

REPO = "hieudovn/virtual-factory"


def _api(token: str, endpoint: str) -> dict | list | None:
    import urllib.request, urllib.error
    url = f"https://api.github.com/repos/{REPO}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ai-harness/2.0")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        return None


def _gh_json(*args: str) -> dict | list | None:
    try:
        r = subprocess.run(["gh"] + list(args), capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def _find_run(sha: str, token: str | None = None) -> dict | None:
    """Find the most recent completed workflow run for exact SHA."""
    # Try API
    if token:
        data = _api(token, f"/actions/runs?head_sha={sha}&per_page=5")
        if isinstance(data, dict):
            runs = data.get("workflow_runs", [])
            for run in runs:
                if run.get("status") == "completed":
                    return run
            if runs:
                return runs[0]
    # Try gh CLI
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            data = _gh_json("run", "list", "--repo", REPO, "--commit", sha,
                            "--json", "databaseId,event,headBranch,headSha,status,conclusion,workflowName",
                            "--limit", "5")
            if isinstance(data, list) and data:
                for run in data:
                    if run.get("status") == "completed":
                        return {"id": run.get("databaseId"), "event": run.get("event"),
                                "head_branch": run.get("headBranch"), "head_sha": run.get("headSha"),
                                "status": run.get("status"), "conclusion": run.get("conclusion"),
                                "workflow_name": run.get("workflowName")}
                first = data[0]
                return {"id": first.get("databaseId"), "event": first.get("event"),
                        "head_branch": first.get("headBranch"), "head_sha": first.get("headSha"),
                        "status": first.get("status"), "conclusion": first.get("conclusion"),
                        "workflow_name": first.get("workflowName")}
    except Exception:
        pass
    return None


def _get_jobs(run_id: int, token: str | None = None) -> list[dict]:
    """Get jobs and steps for a run."""
    jobs: list[dict] = []
    if token:
        data = _api(token, f"/actions/runs/{run_id}/jobs")
        if isinstance(data, dict):
            for j in data.get("jobs", []):
                steps = []
                for s in j.get("steps", []):
                    name = s.get("name", "")
                    if name and "Set up" not in name and "Post" not in name and "Complete" not in name and "Run actions" not in name:
                        steps.append({"name": name, "conclusion": s.get("conclusion", "")})
                jobs.append({"id": j.get("id"), "name": j.get("name", ""), "conclusion": j.get("conclusion", ""), "steps": steps})
    else:
        data = _gh_json("run", "view", str(run_id), "--repo", REPO, "--json", "jobs")
        if isinstance(data, dict):
            for j in data.get("jobs", []):
                steps = []
                for s in j.get("steps", []):
                    name = s.get("name", "")
                    if name and "Set up" not in name and "Post" not in name and "Complete" not in name:
                        steps.append({"name": name, "conclusion": s.get("conclusion", "")})
                jobs.append({"id": j.get("databaseId"), "name": j.get("name", ""), "conclusion": j.get("conclusion", ""), "steps": steps})
    return jobs


def collect_ci_evidence(sha: str, branch: str, required_steps: list[str] | None, token: str | None = None) -> dict:
    """Collect CI evidence for exact head SHA."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")

    result: dict = {
        "evidence_source": "none",
        "run_id": None, "event": "", "workflow": "", "branch": branch,
        "head_sha": sha, "status": "", "conclusion": "",
        "jobs": [], "required_steps": required_steps or [],
        "missing_required_steps": [], "failed_required_steps": [],
        "annotations": 0, "tool_failures": [], "unknown_evidence": [],
    }

    run = _find_run(sha, token)
    if not run:
        result["tool_failures"].append({"tool": "ci_finder", "detail": f"No workflow run found for {sha[:12]}", "execution_stopped": False})
        result["unknown_evidence"].append("ci_run")
        return result

    result["evidence_source"] = "github_api_authenticated" if token else "gh_cli_authenticated"
    result["run_id"] = run.get("id", run.get("databaseId"))
    result["event"] = run.get("event", "")
    result["workflow"] = run.get("workflow_name", run.get("name", ""))
    result["branch"] = run.get("head_branch", branch)
    result["head_sha"] = run.get("head_sha", sha)
    result["status"] = run.get("status", "")
    result["conclusion"] = run.get("conclusion", "")

    print(f"CI run #{result['run_id']}: event={result['event']} conclusion={result['conclusion']}")

    # Get jobs
    if result["run_id"]:
        result["jobs"] = _get_jobs(int(result["run_id"]), token)
        all_step_names: list[str] = []
        for j in result["jobs"]:
            for s in j.get("steps", []):
                all_step_names.append(s["name"])
        print(f"  Steps: {all_step_names}")

        # Check required steps
        for rs in (required_steps or []):
            found = any(rs in sn for jj in result["jobs"] for sn in [s["name"] for s in jj.get("steps", [])])
            passed = any(rs in sn and s.get("conclusion") == "success"
                        for jj in result["jobs"] for s in jj.get("steps", [])
                        for sn in [s.get("name", "")])
            if not found:
                result["missing_required_steps"].append(rs)
            elif not passed:
                result["failed_required_steps"].append(rs)

    return result


def _merge_into(evidence: dict, ci: dict) -> dict:
    ec = evidence.setdefault("ci", {})
    for k in ["run_id", "event", "workflow", "branch", "head_sha", "status", "conclusion", "required_steps"]:
        if ci.get(k) is not None:
            ec[k] = ci[k]
    ec["jobs"] = ci.get("jobs", [])
    ec["annotations"] = ci.get("annotations", 0)
    evidence.setdefault("tool_failures", []).extend(ci.get("tool_failures", []))
    evidence.setdefault("unknown_evidence", []).extend(ci.get("unknown_evidence", []))
    if ci.get("missing_required_steps"):
        evidence.setdefault("blocking_issues", []).append(f"Missing CI steps: {ci['missing_required_steps']}")
    if ci.get("failed_required_steps"):
        evidence.setdefault("blocking_issues", []).append(f"Failed CI steps: {ci['failed_required_steps']}")
    return evidence


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("evidence_file", help="Path to evidence JSON")
    p.add_argument("--token")
    p.add_argument("--sha")
    p.add_argument("--branch")
    p.add_argument("--json-output")
    args = p.parse_args()

    with open(args.evidence_file) as f:
        evidence = json.load(f)

    sha = args.sha or evidence.get("pull_request", {}).get("head_sha", "") or evidence.get("implementation", {}).get("commit_sha", "")
    branch = args.branch or evidence.get("pull_request", {}).get("head_branch", "")
    required = evidence.get("ci", {}).get("required_steps", [])

    ci = collect_ci_evidence(sha, branch, required, args.token)
    evidence = _merge_into(evidence, ci)

    with open(args.evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(ci, f, indent=2)

    sys.exit(0 if ci.get("conclusion") == "success" and not ci.get("missing_required_steps") else 1)


if __name__ == "__main__":
    main()
