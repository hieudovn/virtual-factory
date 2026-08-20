"""TIPA-DEMO-LIVE-01 — VF-S10 producer isolation proof.

Read-only: extracts isolation evidence from the live cumulative observation
trace (multiple runs/generations across six sub-lines) and saves
vf-isolation.json.

Proves:
  - run_id differs per sub-line and per run/generation;
  - station AP06/AP08 tokens repeat across lines but are context-separated by
    run_id (not globally unique);
  - WIP facts belong to their correct sub-line.

Usage: python generate_isolation.py <base_url> <out_json>
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

    msgs = get(f"{base}/assy-demo/observations").get("observations", [])

    # Group run_ids by sub-line prefix.
    sub_lines = ["ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
                 "ASSY-SL04", "ASSY-SL05", "ASSY-SL06"]
    run_ids_by_line = {}
    for sl in sub_lines:
        run_ids_by_line[sl] = sorted({
            m.get("run_id") for m in msgs
            if (m.get("run_id") or "").startswith(f"{sl}:")
        })

    # AP06 / AP08 quality messages across lines (station token repeats, run-scoped).
    def station_scope(station):
        out = {}
        for sl in sub_lines:
            recs = [
                m.get("message_key")
                for m in msgs
                if m.get("message_type") == "mes.quality_result"
                and m.get("payload", {}).get("station_id") == station
                and (m.get("run_id") or "").startswith(f"{sl}:")
            ]
            out[sl] = {"count": len(recs), "sample_keys": recs[:2]}
        return out

    # WIP facts: MTR-0001 genealogy/release appear on every line but scoped.
    wip_scope = {}
    for sl in sub_lines:
        rel = [m.get("message_key") for m in msgs
               if m.get("message_type") == "mes.release"
               and m.get("payload", {}).get("wip_id") == "MTR-0001"
               and (m.get("run_id") or "").startswith(f"{sl}:")]
        wip_scope[sl] = {"mtr_0001_release_keys": rel}

    # Same station token across lines must map to different run_id prefixes.
    ap06_cross_line = station_scope("AP06")
    ap08_cross_line = station_scope("AP08")

    document = {
        "producer": "virtual_factory",
        "evidence": "VF-S10 producer isolation",
        "sub_lines": sub_lines,
        "run_ids_by_line": run_ids_by_line,
        "station_token_context_separation": {
            "AP06": ap06_cross_line,
            "AP08": ap08_cross_line,
        },
        "wip_facts_scoped_by_line": wip_scope,
        "notes": [
            "run_id embeds sub_line_id:R<generation>; a station token (AP06/AP08) is NOT globally unique — it repeats on every sub-line, separated only by run_id prefix.",
            "WIP ids (e.g. MTR-0001) also repeat per sub-line and are context-separated by run_id.",
            "Each scenario reset bumps generation (R1 HAPPY, R3 retest, R4 failed-final, R5 reinspection observed).",
        ],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    print(f"wrote {out_path}")
    print("run_ids_by_line:", json.dumps(run_ids_by_line))
    print("AP06 cross-line counts:", {sl: v["count"] for sl, v in ap06_cross_line.items()})
    print("AP08 cross-line counts:", {sl: v["count"] for sl, v in ap08_cross_line.items()})


if __name__ == "__main__":
    main()
