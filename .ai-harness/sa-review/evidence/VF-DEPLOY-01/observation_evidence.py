"""VF-DEPLOY-01 — extract E2/E3/E4 observation evidence (read-only).

Queries /assy-demo/observations from a runtime that has already been driven
(no re-stepping) and prints machine-readable evidence:
  - per-attempt quality records for AP06 (FAIL attempt 1, PASS attempt 2)
  - per-attempt quality records for AP08 (NG attempt 1, PASS attempt 2)
  - AP11 final-QC PASS vs AP11 RELEASE (distinct facts)
  - a sample of each of the 4 message types (envelope fields)

Usage: python observation_evidence.py <base_url>  (writes JSON to stdout)
"""

from __future__ import annotations

import json
import sys
import urllib.request


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def compact(m: dict) -> dict:
    p = m.get("payload", {})
    return {
        "message_key": m.get("message_key"),
        "message_type": m.get("message_type"),
        "schema_name": m.get("schema_name"),
        "run_id": p.get("run_id"),
        "station_id": p.get("station_id"),
        "event_type": p.get("event_type"),
        "record_id": p.get("record_id"),
        "disposition": p.get("disposition"),
        "attempt_number": p.get("attempt_number"),
        "subject_id": p.get("subject_id"),
        "simulation_time_s": p.get("simulation_time_s"),
        "release_time_s": p.get("release_time_s"),
        "child_wip_id": p.get("child_wip_id"),
        "parent_wip_ids": p.get("parent_wip_ids"),
    }


def main() -> None:
    base = sys.argv[1]
    obs = get(f"{base}/assy-demo/observations")
    msgs = obs.get("observations", [])

    def quality_at(station: str, disp: str | None = None):
        out = []
        for m in msgs:
            if m.get("message_type") != "mes.quality_result":
                continue
            p = m.get("payload", {})
            if p.get("station_id") != station:
                continue
            if disp is not None and p.get("disposition") != disp:
                continue
            out.append(compact(m))
        return out

    ap06_fail = quality_at("AP06", "FAIL")
    ap06_pass = quality_at("AP06", "PASS")
    ap08_ng = quality_at("AP08", "NG")
    ap08_pass = quality_at("AP08", "PASS")
    ap11_qc = quality_at("AP11", "PASS")

    execution = next((compact(m) for m in msgs
                      if m.get("message_type") == "mes.execution_event"), None)
    genealogy = next((compact(m) for m in msgs
                      if m.get("message_type") == "mes.genealogy_relationship"), None)
    release = next((compact(m) for m in msgs
                    if m.get("message_type") == "mes.release"), None)

    result = {
        "observation_count": len(msgs),
        "message_type_counts": {},
        "ap06_fail_attempt1_sample": ap06_fail[:1],
        "ap06_pass_attempt2_sample": [m for m in ap06_pass if m["attempt_number"] == 2][:1],
        "ap08_ng_attempt1_sample": ap08_ng[:1],
        "ap08_pass_attempt2_sample": [m for m in ap08_pass if m["attempt_number"] == 2][:1],
        "ap11_final_qc_pass_sample": ap11_qc[:1],
        "ap11_release_sample": release,
        "sample_execution_event": execution,
        "sample_genealogy_relationship": genealogy,
        "ap06_attempt1_keys_unique": len({m["message_key"] for m in ap06_fail}),
        "ap06_attempt2_keys_unique": len({m["message_key"] for m in ap06_pass if m["attempt_number"] == 2}),
        "ap08_attempt1_keys_unique": len({m["message_key"] for m in ap08_ng}),
        "ap08_attempt2_keys_unique": len({m["message_key"] for m in ap08_pass if m["attempt_number"] == 2}),
    }
    for m in msgs:
        t = m.get("message_type")
        if t:
            result["message_type_counts"][t] = result["message_type_counts"].get(t, 0) + 1
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
