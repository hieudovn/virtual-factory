"""TIPA-DEMO-LIVE-01 — VF-S9 producer: AP08 NG -> PASS (reinspection).

Drives the running accepted ASSY runtime over HTTP with scenario
AP08_NG_REINSPECT_PASS (target ASSY-SL02), advances until the reinspection WIP
releases, and saves the immutable raw observation trace (new-run messages only,
verbatim) + producer summary to vf-reinspection.json.

Usage: python produce_reinspection.py <base_url> <out_json>
"""

import json
import sys
import urllib.request


def post(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def get(url: str):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    base = sys.argv[1]
    out_path = sys.argv[2]

    pre = get(f"{base}/assy-demo/observations").get("observations", [])
    pre_keys = {m.get("message_key") for m in pre}

    post(f"{base}/assy-demo/reset", {"scenario": "AP08_NG_REINSPECT_PASS"})

    msgs = []
    reinspect_wip = None
    for _ in range(400):
        post(f"{base}/assy-demo/step")
        msgs = get(f"{base}/assy-demo/observations").get("observations", [])
        new = [m for m in msgs if m.get("message_key") not in pre_keys]
        ng = [m for m in new
              if m.get("message_type") == "mes.quality_result"
              and m.get("payload", {}).get("station_id") == "AP08"
              and m.get("payload", {}).get("disposition") == "NG"]
        if ng and reinspect_wip is None:
            reinspect_wip = ng[0]["payload"]["wip_id"]
        if reinspect_wip:
            rel = [m for m in new
                   if m.get("message_type") == "mes.release"
                   and m.get("payload", {}).get("wip_id") == reinspect_wip
                   and m.get("run_id", "").startswith("ASSY-SL02:")]
            if rel:
                break

    new_msgs = [m for m in msgs if m.get("message_key") not in pre_keys]
    new_run_ids = sorted({m.get("run_id") for m in new_msgs if m.get("run_id")})

    target = [m for m in new_msgs
              if m.get("message_type") == "mes.quality_result"
              and m.get("payload", {}).get("station_id") == "AP08"
              and m.get("run_id", "").startswith("ASSY-SL02:")]
    ng_attempt1 = [m for m in target
                   if m.get("payload", {}).get("disposition") == "NG"]
    pass_attempt2 = [m for m in target
                     if m.get("payload", {}).get("disposition") == "PASS"
                     and m.get("payload", {}).get("attempt_number") == 2]
    releases = [m for m in new_msgs
                if m.get("message_type") == "mes.release"
                and m.get("run_id", "").startswith("ASSY-SL02:")]

    def compact(m):
        p = m.get("payload", {})
        return {
            "message_key": m.get("message_key"),
            "message_type": m.get("message_type"),
            "schema_name": m.get("schema_name"),
            "schema_version": "1.0",
            "run_id": m.get("run_id"),
            "station_id": p.get("station_id"),
            "record_id": p.get("record_id"),
            "wip_id": p.get("wip_id"),
            "disposition": p.get("disposition"),
            "attempt_number": p.get("attempt_number"),
            "is_terminal": p.get("is_terminal"),
            "terminal_state": p.get("terminal_state"),
            "simulation_time_s": p.get("simulation_time_s"),
        }

    by_type: dict = {}
    for m in new_msgs:
        t = m.get("message_type")
        by_type[t] = by_type.get(t, 0) + 1

    document = {
        "producer": "virtual_factory",
        "scenario": "AP08_NG_REINSPECT_PASS",
        "target_sub_line": "ASSY-SL02",
        "reinspect_wip": reinspect_wip,
        "new_run_ids": new_run_ids,
        "message_type_counts": by_type,
        "total_message_count": len(new_msgs),
        "message_keys": [m.get("message_key") for m in new_msgs],
        "ap08_ng_attempt1": [compact(m) for m in ng_attempt1],
        "ap08_pass_attempt2": [compact(m) for m in pass_attempt2],
        "distinct_record_ids": {
            "ng": sorted({m.get("payload", {}).get("record_id") for m in ng_attempt1}),
            "pass_attempt2": sorted({m.get("payload", {}).get("record_id") for m in pass_attempt2}),
        },
        "distinct_message_keys_per_attempt": {
            "ng": sorted({m.get("message_key") for m in ng_attempt1}),
            "pass_attempt2": sorted({m.get("message_key") for m in pass_attempt2}),
        },
        "all_non_terminal": all(
            m.get("payload", {}).get("is_terminal") is False
            and m.get("payload", {}).get("terminal_state") == ""
            for m in target),
        "ap11_release": [
            {
                "message_key": m.get("message_key"),
                "run_id": m.get("run_id"),
                "wip_id": m.get("payload", {}).get("wip_id"),
                "release_time_s": m.get("payload", {}).get("release_time_s"),
            }
            for m in releases
        ],
        "messages": new_msgs,  # immutable raw observation trace (verbatim)
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    print(f"wrote {out_path}")
    print("new_run_ids:", new_run_ids)
    print("total new messages:", len(new_msgs), "types:", by_type)
    print("reinspect WIP:", reinspect_wip)
    print("NG attempt1:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["attempt_number"], m["payload"]["is_terminal"]) for m in ng_attempt1])
    print("PASS attempt2:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["attempt_number"], m["payload"]["is_terminal"]) for m in pass_attempt2])
    print("all_non_terminal:", document["all_non_terminal"])
    print("releases:", document["ap11_release"])


if __name__ == "__main__":
    main()
