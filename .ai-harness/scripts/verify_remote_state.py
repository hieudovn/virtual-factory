#!/usr/bin/env python3
"""verify_remote_state.py — Collect remote branch, commit, and PR evidence.

Uses: GitHub API (token) → gh CLI (authenticated) → fail closed.
Outputs structured JSON evidence block.
"""

from __future__ import annotations
import json, os, subprocess, sys

REPO = "hieudovn/virtual-factory"


def _api(token: str, endpoint: str) -> dict | None:
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


def _gh(*args: str) -> dict | None:
    try:
        r = subprocess.run(["gh"] + list(args), capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout.strip() else None
    except Exception:
        pass
    return None


def _gh_authenticated() -> bool:
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def collect_remote_state(commit_sha: str, branch: str, pr_number: int | None, token: str | None = None) -> dict:
    """Collect all remote evidence. Returns structured dict."""
    result: dict = {
        "evidence_source": "none",
        "remote_commit_exists": False,
        "remote_branch_exists": False,
        "remote_branch_head": "",
        "pr": {
            "number": pr_number,
            "state": "", "draft": None, "base_branch": "", "base_sha": "",
            "head_branch": "", "head_sha": "", "merged": None, "merged_at": None,
            "merge_commit_sha": "",
        },
        "tool_failures": [],
        "unknown_evidence": [],
    }

    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")

    # ---- Try API ----
    if token:
        print("Using GitHub API (authenticated)...")
        result["evidence_source"] = "github_api_authenticated"
        commit_data = _api(token, f"/commits/{commit_sha}")
        if commit_data:
            result["remote_commit_exists"] = True
            print(f"  Commit verified: {commit_sha[:12]}...")
        else:
            result["tool_failures"].append({"tool": "github_api_commit", "detail": f"Commit {commit_sha[:12]} not found"})
            result["unknown_evidence"].append("remote_commit_exists")

        branch_data = _api(token, f"/git/ref/heads/{branch}")
        if branch_data:
            result["remote_branch_exists"] = True
            result["remote_branch_head"] = branch_data.get("object", {}).get("sha", "")
            print(f"  Branch '{branch}' head: {result['remote_branch_head'][:12]}...")
        else:
            result["tool_failures"].append({"tool": "github_api_branch", "detail": f"Branch {branch} not found"})
            result["unknown_evidence"].append("remote_branch_head")

        if pr_number:
            pr_data = _api(token, f"/pulls/{pr_number}")
            if pr_data:
                result["pr"]["state"] = pr_data.get("state", "")
                result["pr"]["draft"] = pr_data.get("draft", False)
                result["pr"]["base_branch"] = pr_data.get("base", {}).get("ref", "")
                result["pr"]["base_sha"] = pr_data.get("base", {}).get("sha", "")
                result["pr"]["head_branch"] = pr_data.get("head", {}).get("ref", "")
                result["pr"]["head_sha"] = pr_data.get("head", {}).get("sha", "")
                result["pr"]["merged"] = pr_data.get("merged", False)
                result["pr"]["merged_at"] = pr_data.get("merged_at")
                result["pr"]["merge_commit_sha"] = pr_data.get("merge_commit_sha", "")
                print(f"  PR #{pr_number}: state={result['pr']['state']}, head={result['pr']['head_sha'][:12]}...")
            else:
                result["tool_failures"].append({"tool": "github_api_pr", "detail": f"PR #{pr_number} not found"})
                result["unknown_evidence"].append("pr_exists")
        return result

    # ---- Fallback: gh CLI ----
    if _gh_authenticated():
        print("Using gh CLI (authenticated)...")
        result["evidence_source"] = "gh_cli_authenticated"

        commit_data = _gh("api", f"repos/{REPO}/commits/{commit_sha}")
        if commit_data:
            result["remote_commit_exists"] = True
        else:
            result["unknown_evidence"].append("remote_commit_exists")

        branch_data = _gh("api", f"repos/{REPO}/git/ref/heads/{branch}")
        if branch_data:
            result["remote_branch_exists"] = True
            result["remote_branch_head"] = branch_data.get("object", {}).get("sha", "")
        else:
            result["unknown_evidence"].append("remote_branch_head")

        if pr_number:
            pr_data = _gh("pr", "view", str(pr_number), "--repo", REPO, "--json",
                          "number,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,mergedAt,mergeCommit")
            if pr_data:
                result["pr"]["state"] = pr_data.get("state", "")
                result["pr"]["draft"] = pr_data.get("isDraft", False)
                result["pr"]["base_branch"] = pr_data.get("baseRefName", "")
                result["pr"]["base_sha"] = pr_data.get("baseRefOid", "")
                result["pr"]["head_branch"] = pr_data.get("headRefName", "")
                result["pr"]["head_sha"] = pr_data.get("headRefOid", "")
                result["pr"]["merged"] = pr_data.get("mergedAt") is not None
                result["pr"]["merged_at"] = pr_data.get("mergedAt")
                result["pr"]["merge_commit_sha"] = pr_data.get("mergeCommit", {}).get("oid", "") if pr_data.get("mergeCommit") else ""
        return result

    # ---- Fail closed ----
    print("FAIL: No GitHub token and gh CLI not authenticated.")
    result["evidence_source"] = "none_available"
    result["tool_failures"].append({
        "tool": "remote_verification", "detail": "No credentials available", "execution_stopped": True,
    })
    result["unknown_evidence"].extend(["remote_commit_exists", "remote_branch_head", "pr_exists"])
    return result


def _merge_into(evidence: dict, remote: dict) -> dict:
    evidence["evidence_sources"] = [remote.get("evidence_source", "none")]
    impl = evidence.setdefault("implementation", {})
    impl["commit_exists_remotely"] = remote["remote_commit_exists"]
    impl["remote_branch_head"] = remote.get("remote_branch_head", "")
    pr = evidence.setdefault("pull_request", {})
    rpr = remote.get("pr", {})
    for k in ["number", "state", "draft", "base_branch", "base_sha", "head_branch", "head_sha", "merged", "merged_at", "merge_commit_sha"]:
        if rpr.get(k) is not None:
            pr[k] = rpr[k]
    evidence.setdefault("tool_failures", []).extend(remote.get("tool_failures", []))
    evidence.setdefault("unknown_evidence", []).extend(remote.get("unknown_evidence", []))
    return evidence


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("evidence_file", help="Path to evidence JSON (read and update)")
    p.add_argument("--token")
    p.add_argument("--commit-sha")
    p.add_argument("--branch")
    p.add_argument("--pr")
    p.add_argument("--json-output", help="Write standalone remote JSON")
    args = p.parse_args()

    with open(args.evidence_file) as f:
        evidence = json.load(f)

    commit = args.commit_sha or evidence.get("implementation", {}).get("commit_sha", "")
    branch = args.branch or evidence.get("pull_request", {}).get("head_branch", "") or evidence.get("preflight", {}).get("current_branch", "")
    pr_num = int(args.pr) if args.pr else evidence.get("pull_request", {}).get("number")

    remote = collect_remote_state(commit, branch, pr_num, args.token)
    evidence = _merge_into(evidence, remote)

    with open(args.evidence_file, "w") as f:
        json.dump(evidence, f, indent=2)

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(remote, f, indent=2)

    has_blocking = any(tf.get("execution_stopped") for tf in remote.get("tool_failures", []))
    sys.exit(1 if has_blocking else 0)


if __name__ == "__main__":
    main()
