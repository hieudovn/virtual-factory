"""TIPA-DEMO-LIVE-01 — VF-S7 producer: AP06 FAIL -> PASS (retest).

Drives the running accepted ASSY runtime over HTTP with scenario
AP06_FAIL_RETEST_PASS (target ASSY-SL03), advances until the NEW generation
releases on the target line, and saves the immutable raw observation trace
(new-run messages only, verbatim) + producer summary to vf-retest.json.

The observations endpoint is cumulative, so the new run's messages are
identified as those whose message_key did not exist before the reset.

Usage: python produce_retest.py <base_url> <out_json>
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

    # Pre-reset state (previous run's keys) so we can scope to the new run.
    pre = get(f"{base}/assy-demo/observations").get("observations", [])
    pre_keys = {m.get("message_key") for m in pre}

    post(f"{base}/assy-demo/reset", {"scenario": "AP06_FAIL_RETEST_PASS"})

    msgs = []
    for _ in range(400):
        post(f"{base}/assy-demo/step")
        msgs = get(f"{base}/assy-demo/observations").get("observations", [])
        new_rel_sl03 = [
            m for m in msgs
            if m.get("message_type") == "mes.release"
            and m.get("run_id", "").startswith("ASSY-SL03:")
            and m.get("message_key") not in pre_keys
        ]
        if new_rel_sl03:
            break

    # New-run messages only (message contents untouched).
    new_msgs = [m for m in msgs if m.get("message_key") not in pre_keys]

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
