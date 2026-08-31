"""TIPA-DEMO-LIVE-01 — finalize vf-retest.json from the live cumulative trace.

Extracts the NEW-run messages (identified by run generation) and writes the
complete VF-S7 evidence. No reset is performed (no further generation bump).

Usage: python finalize_retest.py <base_url> <out_json> <new_generation>
"""

import json
import sys
import urllib.request


def get(url: str):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    base = sys.argv[1]
    out_path = sys.argv[2]
    gen = sys.argv[3]  # e.g. "R3"

    msgs = get(f"{base}/assy-demo/observations").get("observations", [])
    new_msgs = [m for m in msgs if (m.get("run_id") or "").endswith(f":{gen}")]

    new_run_ids = sorted({m.get("run_id") for m in new_msgs if m.get("run_id")})

    target = [m for m in new_msgs
              if m.get("message_type") == "mes.quality_result"
              and m.get("payload", {}).get("station_id") == "AP06"
              and m.get("run_id", "").startswith("ASSY-SL03:")]
    fail_attempts = [m for m in target
                     if m.get("payload", {}).get("disposition") == "FAIL"]
    pass_attempt2 = [m for m in target
                     if m.get("payload", {}).get("disposition") == "PASS"
                     and m.get("payload", {}).get("attempt_number") == 2]
    releases = [m for m in new_msgs
                if m.get("message_type") == "mes.release"
                and m.get("run_id", "").startswith("ASSY-SL03:")]

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
        "scenario": "AP06_FAIL_RETEST_PASS",
        "target_sub_line": "ASSY-SL03",
        "new_run_ids": new_run_ids,
        "message_type_counts": by_type,
        "total_message_count": len(new_msgs),
        "message_keys": [m.get("message_key") for m in new_msgs],
        "ap06_fail_attempt1": [compact(m) for m in fail_attempts],
        "ap06_pass_attempt2": [compact(m) for m in pass_attempt2],
        "distinct_record_ids": {
            "fail": sorted({m.get("payload", {}).get("record_id") for m in fail_attempts}),
            "pass_attempt2": sorted({m.get("payload", {}).get("record_id") for m in pass_attempt2}),
        },
        "distinct_message_keys_per_attempt": {
            "fail": sorted({m.get("message_key") for m in fail_attempts}),
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
    print("FAIL attempts:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["attempt_number"], m["payload"]["is_terminal"]) for m in fail_attempts])
    print("PASS attempt2:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["attempt_number"], m["payload"]["is_terminal"]) for m in pass_attempt2])
    print("all_non_terminal:", document["all_non_terminal"])
    print("releases:", document["ap11_release"])


if __name__ == "__main__":
    main()
