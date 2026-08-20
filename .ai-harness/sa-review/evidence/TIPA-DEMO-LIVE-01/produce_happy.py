"""TIPA-DEMO-LIVE-01 — VF-S5 producer: generate and save REAL HAPPY_PATH messages.

Drives the running accepted ASSY runtime over HTTP (HAPPY_PATH), advances until
release, and saves the immutable raw observation trace + a producer summary to
vf-happy.json. Message contents are NOT rewritten.

Usage: python produce_happy.py <base_url> <out_json>
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

    post(f"{base}/assy-demo/reset", {"scenario": "HAPPY_PATH"})

    # Advance until the demo reference line (ASSY-SL01) releases MTR-0001.
    for _ in range(400):
        post(f"{base}/assy-demo/step")
        obs = get(f"{base}/assy-demo/observations")
        msgs = obs.get("observations", [])
        released = [m for m in msgs
                    if m.get("message_type") == "mes.release"
                    and m.get("run_id", "").startswith("ASSY-SL01:")]
        if released:
            break

    obs = get(f"{base}/assy-demo/observations")
    msgs = obs.get("observations", [])

    # Producer summary (derived, but never alters the raw messages)
    by_type: dict = {}
    for m in msgs:
        t = m.get("message_type")
        by_type[t] = by_type.get(t, 0) + 1

    run_ids = sorted({m.get("run_id") for m in msgs if m.get("run_id")})
    released_mtr = sorted({
        m.get("payload", {}).get("wip_id")
        for m in msgs if m.get("message_type") == "mes.release"
    })
    # AP04 genealogy for ASSY-SL01 (the reference line)
    ap04 = [m for m in msgs
            if m.get("message_type") == "mes.genealogy_relationship"
            and m.get("run_id", "").startswith("ASSY-SL01:")]
    ap06_pass = [m for m in msgs
                 if m.get("message_type") == "mes.quality_result"
                 and m.get("payload", {}).get("station_id") == "AP06"
                 and m.get("payload", {}).get("disposition") == "PASS"
                 and m.get("run_id", "").startswith("ASSY-SL01:")]
    ap08_pass = [m for m in msgs
                 if m.get("message_type") == "mes.quality_result"
                 and m.get("payload", {}).get("station_id") == "AP08"
                 and m.get("payload", {}).get("disposition") == "PASS"
                 and m.get("run_id", "").startswith("ASSY-SL01:")]
    ap11_qc = [m for m in msgs
               if m.get("message_type") == "mes.quality_result"
               and m.get("payload", {}).get("station_id") == "AP11"
               and m.get("payload", {}).get("event_type") == "AP11_FINAL_QC_PASS"
               and m.get("run_id", "").startswith("ASSY-SL01:")]
    ap11_release = [m for m in msgs
                    if m.get("message_type") == "mes.release"
                    and m.get("run_id", "").startswith("ASSY-SL01:")]

    document = {
        "producer": "virtual_factory",
        "scenario": "HAPPY_PATH",
        "message_type_counts": by_type,
        "run_ids": run_ids,
        "reference_sub_line": "ASSY-SL01",
        "released_wips": released_mtr,
        "total_message_count": len(msgs),
        "message_keys": [m.get("message_key") for m in msgs],
        "ap04_genealogy_reference_line": [
            {
                "message_key": m.get("message_key"),
                "child_wip_id": m.get("payload", {}).get("child_wip_id"),
                "parent_wip_ids": m.get("payload", {}).get("parent_wip_ids"),
                "station_id": m.get("payload", {}).get("station_id"),
            }
            for m in ap04
        ],
        "ap06_pass_reference_line": [m.get("message_key") for m in ap06_pass],
        "ap08_pass_reference_line": [m.get("message_key") for m in ap08_pass],
        "ap11_final_qc_pass_reference_line": [m.get("message_key") for m in ap11_qc],
        "ap11_release_reference_line": [
            {
                "message_key": m.get("message_key"),
                "wip_id": m.get("payload", {}).get("wip_id"),
                "release_time_s": m.get("payload", {}).get("release_time_s"),
            }
            for m in ap11_release
        ],
        "messages": msgs,  # immutable raw observation trace (verbatim)
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    print(f"wrote {out_path}")
    print("total messages:", len(msgs))
    print("message types:", by_type)
    print("run_ids:", run_ids)
    print("released wips:", released_mtr)
    print("AP04 (SL01) children:", [m["payload"].get("child_wip_id") for m in ap04])
    print("AP04 (SL01) parents:", [m["payload"].get("parent_wip_ids") for m in ap04])
    print("AP06 PASS (SL01):", len(ap06_pass), "AP08 PASS (SL01):", len(ap08_pass),
          "AP11 QC PASS (SL01):", len(ap11_qc), "AP11 RELEASE (SL01):", len(ap11_release))


if __name__ == "__main__":
    main()
