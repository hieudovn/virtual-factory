"""Capture a trace from the ACTUAL running API/browser instance.

Uses HTTP endpoints of the live server (same instance Frame B uses),
NOT a separate AssyDemoComposition process.
"""

import json
import time
import urllib.request

BASE = "http://localhost:8091"
OUT = "docs/ui/evidence/sim-val-01-c01/assy_sl01_browser_api_trace.jsonl"


def post(path, body=None):
    data = json.dumps(body).encode() if body is not None else b"{}"
    req = urllib.request.Request(BASE + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def main():
    # Reset to HAPPY_PATH
    post("/assy-demo/reset", {"scenario": "HAPPY_PATH"})

    import os
    os.makedirs("docs/ui/evidence/sim-val-01-c01", exist_ok=True)

    records = []
    released_at = None
    with open(OUT, "w", encoding="utf-8") as fh:
        for i in range(45):
            post("/assy-demo/step")
            snap = get("/assy-demo/sub-line/ASSY-SL01")
            rec = {
                "demo_step": i + 1,
                "simulation_time_s": snap.get("simulation_time_s"),
                "sub_line_id": snap.get("sub_line_id"),
                "line_state": snap.get("line_state"),
                "production": snap.get("production"),
                "occupied_positions": [
                    p for p in snap.get("positions", []) if p.get("is_occupied")
                ],
            }
            fh.write(json.dumps(rec) + "\n")
            records.append(rec)
            if released_at is None and snap["production"]["motors_released"] >= 10:
                released_at = i + 1

    last = records[-1]
    print(json.dumps({
        "steps": len(records),
        "simulation_time_s": last["simulation_time_s"],
        "sub_line_id": last["sub_line_id"],
        "motors_created": last["production"]["motors_created"],
        "motors_released": last["production"]["motors_released"],
        "wips_on_line": last["production"]["wips_on_line"],
        "holds": last["production"]["active_quality_holds"],
        "rso2_buffer": last["production"]["rso2_buffer"],
        "release_10_at_step": released_at,
        "trace": OUT,
    }, indent=2))


if __name__ == "__main__":
    main()
