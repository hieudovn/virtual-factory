#!/usr/bin/env python3
"""G26 demo stability smoke (D) — runs against a LIVE server.

Not a load/performance benchmark. Demo-scale stability only:
- cold start responsiveness
- repeated switching
- repeated step / reset / replay / new_attempt
- a few hundred steps in total
- bad requests do not kill the server
- browser-facing API stays responsive afterwards

Usage:
    python -m virtual_factory.main serve --host 127.0.0.1 --port 8099
    python .ai-harness/sa-review/evidence/VF-vNEXT-G26/stability_smoke.py --base http://127.0.0.1:8099
Writes: stability-results.json (deterministic structure; durations are timing
observations only, not assertions).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent

TIPA_STEPS = 120
SHWTP_STEPS = 150
SWITCHES = 20


def wait_ready(base: str, timeout_s: float = 30.0) -> bool:
    """Bounded readiness poll (cold start) — no assumption the server is up."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if httpx.get(base + "/health", timeout=2.0).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8099")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    results: dict = {"base": base, "checks": [], "statuses": {}}
    t0 = time.time()

    if not wait_ready(base):
        results["checks"].append({"check": "cold_start_ready", "ok": False, "detail": "server not ready"})
        (HERE / "stability-results.json").write_text(
            json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("server not ready")
        return 1

    def call(method: str, path: str, **kw):
        return httpx.request(method, base + path, timeout=20.0, **kw)

    def record(name: str, ok: bool, detail: str = "") -> None:
        results["checks"].append({"check": name, "ok": bool(ok), "detail": detail})

    # --- cold start / registry ---
    r = call("GET", "/vnext/workspaces")
    ids = r.json().get("workspace_ids") if r.status_code == 200 else None
    record("cold_start_registry", r.status_code == 200 and ids == ["TIPA", "shwtp"], str(ids))

    # --- TIPA: select + repeated steps + lifecycle ---
    r = call("POST", "/vnext/workspaces/select", json={"workspace_id": "TIPA"})
    record("select_tipa", r.status_code == 200 and r.json()["workspace_id"] == "TIPA")
    # start from a fresh, non-terminal attempt (robust from any prior state)
    record("tipa_prepare_new_attempt", call("POST", "/vnext/workspaces/TIPA/control", json={"action": "new_attempt"}).status_code == 200)
    bad_step = 0
    for i in range(TIPA_STEPS):
        r = call("POST", "/vnext/workspaces/TIPA/control", json={"action": "step"})
        if r.status_code != 200:
            bad_step += 1
    record("tipa_steps", bad_step == 0, f"{TIPA_STEPS} steps, {bad_step} non-200")
    record("tipa_reset", call("POST", "/vnext/workspaces/TIPA/control", json={"action": "reset"}).status_code == 200)
    rr = call("POST", "/vnext/workspaces/TIPA/control", json={"action": "replay"})
    record("tipa_replay", rr.status_code == 200, "")
    record("tipa_new_attempt", call("POST", "/vnext/workspaces/TIPA/control", json={"action": "new_attempt"}).status_code == 200)

    # --- SH-WTP: select + repeated steps + lifecycle ---
    record("select_shwtp", call("POST", "/vnext/workspaces/select", json={"workspace_id": "shwtp"}).status_code == 200)
    record("shwtp_prepare_new_attempt", call("POST", "/vnext/workspaces/shwtp/control", json={"action": "new_attempt"}).status_code == 200)
    bad_step = 0
    for i in range(SHWTP_STEPS):
        r = call("POST", "/vnext/workspaces/shwtp/control", json={"action": "step"})
        if r.status_code != 200:
            bad_step += 1
    record("shwtp_steps", bad_step == 0, f"{SHWTP_STEPS} steps, {bad_step} non-200")
    record("shwtp_reset", call("POST", "/vnext/workspaces/shwtp/control", json={"action": "reset"}).status_code == 200)
    record("shwtp_replay", call("POST", "/vnext/workspaces/shwtp/control", json={"action": "replay"}).status_code == 200)
    record("shwtp_new_attempt", call("POST", "/vnext/workspaces/shwtp/control", json={"action": "new_attempt"}).status_code == 200)

    # --- repeated switching (no mutation expected) ---
    ok_switch = True
    tipa_run = None
    for i in range(SWITCHES):
        wid = "TIPA" if i % 2 == 0 else "shwtp"
        r = call("POST", "/vnext/workspaces/select", json={"workspace_id": wid})
        if r.status_code != 200:
            ok_switch = False
        run_id = r.json()["session"]["run_id"]
        if wid == "TIPA" and tipa_run is None:
            tipa_run = run_id
        if wid == "TIPA" and run_id != tipa_run:
            ok_switch = False  # switched-away TIPA session identity must persist
    record("repeated_switching", ok_switch, f"{SWITCHES} switches")

    # --- bad requests must not kill the server ---
    s1 = call("GET", "/vnext/workspaces/does-not-exist/view").status_code
    s2 = call("POST", "/vnext/workspaces/shwtp/control", json={"action": "nope"}).status_code
    s3 = call("POST", "/vnext/workspaces/select", json={}).status_code
    s4 = call("POST", "/vnext/workspaces/TIPA/control", json={}).status_code
    results["statuses"] = {
        "unknown_workspace_view": s1,
        "unknown_action": s2,
        "missing_workspace_id": s3,
        "missing_action": s4,
    }
    record("bad_requests_handled", s1 == 404 and s2 == 400 and s3 == 400 and s4 == 400)

    # --- still responsive after everything ---
    r = call("GET", "/vnext/workspaces")
    record("responsive_after", r.status_code == 200 and r.json().get("workspace_ids") == ["TIPA", "shwtp"])
    r = call("GET", "/vnext/workspaces/TIPA/view")
    record("monitor_still_serves", r.status_code == 200)

    results["steps_total"] = TIPA_STEPS + SHWTP_STEPS
    results["switches"] = SWITCHES
    results["all_ok"] = all(c["ok"] for c in results["checks"])
    results["elapsed_s"] = round(time.time() - t0, 3)

    (HERE / "stability-results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"all_ok": results["all_ok"], "steps_total": results["steps_total"],
                      "elapsed_s": results["elapsed_s"]}, indent=2))
    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
