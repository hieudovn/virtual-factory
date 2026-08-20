"""TIPA-DEMO-LIVE-01 — VF-S8 producer: FAILED_FINAL.

Drives the running accepted ASSY runtime over HTTP with scenario FAILED_FINAL
(target ASSY-SL03), advances until the authoritative terminal fact appears, and
saves the immutable raw observation trace (new-run messages only, verbatim) +
producer summary to vf-failed-final.json.

Usage: python produce_failed_final.py <base_url> <out_json>
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

    post(f"{base}/assy-demo/reset", {"scenario": "FAILED_FINAL"})

    msgs = []
    for _ in range(400):
        post(f"{base}/assy-demo/step")
        msgs = get(f"{base}/assy-demo/observations").get("observations", [])
        new = [m for m in msgs if m.get("message_key") not in pre_keys]
        terminal = [m for m in new
                    if m.get("message_type") == "mes.quality_result"
                    and m.get("payload", {}).get("is_terminal") is True]
        if terminal:
            break

    new_msgs = [m for m in msgs if m.get("message_key") not in pre_keys]
    new_run_ids = sorted({m.get("run_id") for m in new_msgs if m.get("run_id")})

    # Target-line AP06 attempts.
    target = [m for m in new_msgs
              if m.get("message_type") == "mes.quality_result"
              and m.get("payload", {}).get("station_id") == "AP06"
              and m.get("run_id", "").startswith("ASSY-SL03:")]
    terminal = [m for m in target if m.get("payload", {}).get("is_terminal") is True]
    attempt1 = [m for m in target
                if m.get("payload", {}).get("attempt_number") == 1]
    attempt2 = [m for m in target
                if m.get("payload", {}).get("attempt_number") == 2]
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
        "scenario": "FAILED_FINAL",
        "target_sub_line": "ASSY-SL03",
        "new_run_ids": new_run_ids,
        "message_type_counts": by_type,
        "total_message_count": len(new_msgs),
        "message_keys": [m.get("message_key") for m in new_msgs],
        "ap06_attempt1": [compact(m) for m in attempt1],
        "ap06_attempt2": [compact(m) for m in attempt2],
        "terminal_facts": [compact(m) for m in terminal],
        "ap11_release_count": len(releases),
        "ap11_release": [
            {
                "message_key": m.get("message_key"),
                "run_id": m.get("run_id"),
                "wip_id": m.get("payload", {}).get("wip_id"),
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
    print("attempt1:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["disposition"], m["payload"]["is_terminal"], m["payload"]["terminal_state"]) for m in attempt1])
    print("attempt2:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["disposition"], m["payload"]["is_terminal"], m["payload"]["terminal_state"]) for m in attempt2])
    print("terminal_facts:", [(m["payload"]["record_id"], m["payload"]["wip_id"], m["payload"]["terminal_state"]) for m in terminal])
    print("AP11 RELEASE count:", len(releases))


if __name__ == "__main__":
    main()
