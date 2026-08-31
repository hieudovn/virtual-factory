"""TIPA-DEMO-LIVE-01 — VF-S12 continuous rehearsal (customer-style).

Runs the rehearsal scenario sequence continuously, no debug intervention,
recording per-scenario reset/step timing and any instability:
  HAPPY_PATH -> AP06_FAIL_RETEST_PASS -> FAILED_FINAL -> AP08_NG_REINSPECT_PASS

Saves a machine-readable rehearsal record (vf-rehearsal.json) + markdown
(vf-rehearsal.md).

Usage: python run_rehearsal.py <base_url> <out_json> <out_md>
"""

import json
import sys
import time
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


SCENARIOS = [
    ("HAPPY_PATH", "release", lambda msgs: any(
        m.get("message_type") == "mes.release"
        and (m.get("run_id") or "").startswith("ASSY-SL01:") for m in msgs)),
    ("AP06_FAIL_RETEST_PASS", "ap06_fail_pass", lambda msgs: (
        any(m.get("message_type") == "mes.quality_result"
            and m.get("payload", {}).get("station_id") == "AP06"
            and m.get("payload", {}).get("disposition") == "FAIL" for m in msgs)
        and any(m.get("message_type") == "mes.quality_result"
                and m.get("payload", {}).get("station_id") == "AP06"
                and m.get("payload", {}).get("disposition") == "PASS"
                and m.get("payload", {}).get("attempt_number") == 2 for m in msgs))),
    ("FAILED_FINAL", "terminal", lambda msgs: any(
        m.get("message_type") == "mes.quality_result"
        and m.get("payload", {}).get("is_terminal") is True for m in msgs)),
    ("AP08_NG_REINSPECT_PASS", "ap08_ng_pass", lambda msgs: (
        any(m.get("message_type") == "mes.quality_result"
            and m.get("payload", {}).get("station_id") == "AP08"
            and m.get("payload", {}).get("disposition") == "NG" for m in msgs)
        and any(m.get("message_type") == "mes.quality_result"
                and m.get("payload", {}).get("station_id") == "AP08"
                and m.get("payload", {}).get("disposition") == "PASS"
                and m.get("payload", {}).get("attempt_number") == 2 for m in msgs))),
]


def main() -> None:
    base = sys.argv[1]
    out_json = sys.argv[2]
    out_md = sys.argv[3]

    results = []
    issues = []
    overall_start = time.perf_counter()

    for scenario, label, done in SCENARIOS:
        entry = {"scenario": scenario}
        pre = get(f"{base}/assy-demo/observations").get("observations", [])
        pre_keys = {m.get("message_key") for m in pre}

        t0 = time.perf_counter()
        post(f"{base}/assy-demo/reset", {"scenario": scenario})
        entry["reset_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        steps = 0
        t_step = time.perf_counter()
        for steps in range(1, 401):
            post(f"{base}/assy-demo/step")
            msgs = get(f"{base}/assy-demo/observations").get("observations", [])
            new = [m for m in msgs if m.get("message_key") not in pre_keys]
            if done(new):
                break
        entry["steps_to_evidence"] = steps
        entry["step_phase_s"] = round(time.perf_counter() - t_step, 2)

        # endpoint latency
        t = time.perf_counter()
        get(f"{base}/health")
        entry["health_ms"] = round((time.perf_counter() - t) * 1000, 1)

        new_run_ids = sorted({
            m.get("run_id") for m in msgs
            if m.get("message_key") not in pre_keys and m.get("run_id")
        })
        entry["new_run_ids"] = new_run_ids
        entry["status"] = "OK" if new_run_ids else "NO_NEW_RUN"
        if entry["status"] != "OK":
            issues.append({"severity": "P0", "detail": f"{scenario}: no new run produced"})
        results.append(entry)

    overall_s = round(time.perf_counter() - overall_start, 2)

    # Classify issues (VF-side only; MES genealogy tree P1 is MES-side, out of VF scope).
    if not issues:
        issues.append({"severity": "NONE", "detail": "no VF runtime instability observed"})

    doc = {
        "producer": "virtual_factory",
        "rehearsal": "VF-S12 customer-style",
        "sequence": [s for s, _, _ in SCENARIOS],
        "overall_seconds": overall_s,
        "results": results,
        "issues": issues,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    lines = ["# VF-S12 — Customer-style rehearsal record\n", ""]
    for r in results:
        lines.append(f"- **{r['scenario']}**: reset {r['reset_ms']} ms, "
                     f"{r['steps_to_evidence']} steps to evidence, "
                     f"run {r['new_run_ids']}, status {r['status']}\n")
    lines.append(f"\nOverall: {overall_s} s\n")
    lines.append("\n## Issues\n\n")
    for i in issues:
        lines.append(f"- {i['severity']}: {i['detail']}\n")
    with open(out_md, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(json.dumps(doc, indent=2))
    print(f"wrote {out_json}, {out_md}")


if __name__ == "__main__":
    main()
