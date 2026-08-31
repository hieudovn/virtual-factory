"""VF-DEPLOY-01 — native vs Docker ASSY runtime equivalence driver (E1-E4).

Drives a running ASSY FastAPI runtime (native or Docker) over HTTP and returns
a normalized P0-contract fingerprint. The same script is run against the native
runtime and the Docker runtime; the fingerprints are then diffed.

Endpoints used (all accepted): reset, step, observations.

Usage:
    python equivalence_check.py <base_url> <scenario> <steps>

Produces a JSON fingerprint on stdout. No production code is touched.
"""

from __future__ import annotations

import json
import sys
import urllib.request

SCENARIOS = [
    "HAPPY_PATH",
    "AP06_FAIL_RETEST_PASS",
    "AP08_NG_REINSPECT_PASS",
]


def post(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else b"{}"
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def has_release(msgs: list[dict]) -> bool:
    return any(m.get("message_type") == "mes.release" for m in msgs)


def has_ap06_pair(msgs: list[dict]) -> bool:
    ap06 = [m for m in msgs
            if m.get("message_type") == "mes.quality_result"
            and m.get("payload", {}).get("station_id") == "AP06"]
    disps = {m["payload"].get("disposition") for m in ap06}
    return {"FAIL", "PASS"} <= disps


def has_ap08_pair(msgs: list[dict]) -> bool:
    ap08 = [m for m in msgs
            if m.get("message_type") == "mes.quality_result"
            and m.get("payload", {}).get("station_id") == "AP08"]
    disps = {m["payload"].get("disposition") for m in ap08}
    return {"NG", "PASS"} <= disps


def fingerprint(base: str, scenario: str, max_steps: int) -> dict:
    post(f"{base}/assy-demo/reset", {"scenario": scenario})
    done_cond = {"HAPPY_PATH": has_release,
                 "AP06_FAIL_RETEST_PASS": has_ap06_pair,
                 "AP08_NG_REINSPECT_PASS": has_ap08_pair}[scenario]
    steps = 0
    for steps in range(1, max_steps + 1):
        post(f"{base}/assy-demo/step")
        if steps % 50 == 0:
            print(f"  [{scenario}] step {steps}", file=sys.stderr, flush=True)
        obs = get(f"{base}/assy-demo/observations")
        if done_cond(obs.get("observations", [])):
            for _ in range(20):
                post(f"{base}/assy-demo/step")
            break

    obs = get(f"{base}/assy-demo/observations")
    msgs = obs.get("observations", [])
    # Normalize: only the P0 contract-relevant fields
    norm = []
    for m in msgs:
        p = m.get("payload", {})
        norm.append({
            "message_type": m.get("message_type"),
            "message_key": m.get("message_key"),
            "schema_name": m.get("schema_name"),
            "run_id": p.get("run_id"),
            "station_id": p.get("station_id"),
            "event_type": p.get("event_type"),
            "subject_id": p.get("subject_id"),
            "disposition": p.get("disposition"),
            "attempt_number": p.get("attempt_number"),
            "record_id": p.get("record_id"),
            "child_wip_id": p.get("child_wip_id"),
            "parent_wip_ids": p.get("parent_wip_ids"),
            "release_time_s": p.get("release_time_s"),
        })

    by_type: dict[str, int] = {}
    for m in norm:
        by_type[m["message_type"]] = by_type.get(m["message_type"], 0) + 1

    # AP04 genealogy cardinality: distinct child_wip_id per run
    genealogy = [m for m in norm if m["message_type"] == "mes.genealogy_relationship"]
    ap04_children = sorted({m["child_wip_id"] for m in genealogy})

    # quality attempt identity: distinct (record_id) per message_key
    quality = [m for m in norm if m["message_type"] == "mes.quality_result"]
    quality_keys = [m["message_key"] for m in quality]
    quality_records = [m["record_id"] for m in quality]

    releases = [m for m in norm if m["message_type"] == "mes.release"]

    return {
        "scenario": scenario,
        "steps_driven": steps,
        "observation_count": len(obs.get("observations", [])),
        "message_type_counts": by_type,
        "run_ids": sorted({m["run_id"] for m in norm if m["run_id"]}),
        "station_ids": sorted({m["station_id"] for m in norm if m["station_id"]}),
        "ap04_children": ap04_children,
        "genealogy_parents": sorted({str(m["parent_wip_ids"]) for m in genealogy}),
        "quality_keys_distinct": len(set(quality_keys)),
        "quality_records_distinct": len(set(quality_records)),
        "release_keys": [m["message_key"] for m in releases],
        "release_times": [m["release_time_s"] for m in releases],
        "message_keys": [m["message_key"] for m in norm],
    }


def main() -> None:
    base = sys.argv[1]
    max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    out: dict = {}
    for scenario in SCENARIOS:
        print(f"== {scenario} @ {base} ==", file=sys.stderr, flush=True)
        out[scenario] = fingerprint(base, scenario, max_steps)
        with open(f"vf-fingerprint-{scenario}.json", "w", encoding="utf-8") as f:
            json.dump(out[scenario], f, indent=2)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
