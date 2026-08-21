"""Regenerate VF-DM-DEMO-ASSY-MES-03 evidence by overwrite.

Produces, under this directory:
  demo-run.jsonl      — one line per projected message (full message record)
  message-counts.json — machine-derived counts + contract samples

Run:  python generate_evidence.py
Idempotent: always overwrites (never appends).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from virtual_factory.assembly.assy_mes_bridge import (
    CONTRACT_VERSION,
    _demo_run,
)

HERE = Path(__file__).resolve().parent
CONFIG_PATH = str(
    HERE.parent.parent.parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


def _message_record(m) -> dict:
    """Serialize a ProjectedMessage to the demo-run.jsonl record shape."""
    return {
        "message_key": m.key,
        "projection_id": getattr(m, "projection_id", "mes"),
        "message_type": m.message_type,
        "schema_name": m.schema_name,
        "schema_version": getattr(m, "schema_version", "1.0"),
        "headers": dict(getattr(m, "headers", {}) or {}),
        "payload": dict(m.payload),
    }


def _ap08_ng_observation_sample() -> dict:
    """Focused AP08 NG → reinspect PASS on one bare sub-line.

    Proves the retested NG attempt's anomaly observation is frozen on the
    record (per-attempt immutability) rather than being overwritten by the
    later PASS re-observation.
    """
    import types

    from virtual_factory.assembly.assy_mes_bridge import build_assy_mes_pipeline
    from virtual_factory.assembly.line_runtime import (
        AssyLineConfig,
        AssyLineRuntime,
        ConveyorState,
        WipLifecycle,
    )
    from virtual_factory.assembly.station_contracts import CompletionMode

    cfg = AssyLineConfig()
    cfg.conveyor.nominal_line_dwell_time_s = 10.0
    cfg.conveyor.index_movement_duration_s = 0.0
    for k in cfg.station_durations:
        cfg.station_durations[k] = 5.0
    cfg.quality.ap06.scenario = "PASS"
    cfg.quality.ap08.scenario = "FAIL_FIRST_THEN_PASS"

    line = AssyLineRuntime(config=cfg)
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")

    bridge = build_assy_mes_pipeline().bridge
    identity = types.SimpleNamespace(
        sub_line_id="ASSY-SL01", variant="hydraulic", production_line_id="ASSY")
    composition = types.SimpleNamespace(
        contexts={"ASSY-SL01": types.SimpleNamespace(runtime=line, identity=identity)},
        demo_step_number=0)

    for _ in range(300):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        bridge.poll(composition)
        ws = line.get_wip("MTR-0001")
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break

    ng = [
        dict(m.payload)
        for m in bridge.projected_messages
        if m.message_type == "mes.quality_result"
        and dict(m.payload).get("station_id") == "AP08"
        and dict(m.payload).get("disposition") == "NG"
    ]
    passed = [
        dict(m.payload)
        for m in bridge.projected_messages
        if m.message_type == "mes.quality_result"
        and dict(m.payload).get("station_id") == "AP08"
        and dict(m.payload).get("disposition") == "PASS"
    ]
    return {
        "scenario": "AP08 FAIL_FIRST_THEN_PASS (motor 1: NG attempt 1, PASS attempt 2)",
        "ng_attempt": ng[0] if ng else None,
        "pass_attempt": passed[-1] if passed else None,
        "ng_observation_preserved": bool(
            ng and ng[0].get("observations")
            and any(o["result"] == "anomaly" for o in ng[0]["observations"])),
        "ng_proposal_separate_from_disposition": bool(
            ng and "proposed_quality_result" in ng[0]
            and "disposition" in ng[0]
            and ng[0]["proposed_quality_result"] == ng[0]["disposition"] == "NG"),
    }


def main() -> int:
    bridge, counts = _demo_run(CONFIG_PATH, max_steps=24)
    messages = bridge.projected_messages
    keys = [m.key for m in messages]
    unique = len(set(keys))
    duplicate = len(keys) - unique

    # Overwrite demo-run.jsonl
    run_lines = [
        json.dumps(_message_record(m), ensure_ascii=False, sort_keys=True)
        for m in messages
    ]
    (HERE / "demo-run.jsonl").write_text("\n".join(run_lines) + "\n", encoding="utf-8")

    payloads = [dict(m.payload) for m in messages]

    def _of_type(etype: str):
        return [p for p in payloads if p.get("event_type") == etype]

    checklist = _of_type("CHECKLIST_CONFIRMED")
    measurements = _of_type("MEASUREMENT_RESULT")
    quality = _of_type("QUALITY_RESULT")
    quality_ng = [p for p in quality if p.get("disposition") == "NG"]
    quality_with_obs = [p for p in quality if p.get("observations")]
    ap08_obs = [p for p in quality_with_obs if p.get("check_type") == "VISUAL_INSPECTION"]
    ap11_obs = [
        p for p in payloads
        if p.get("check_type") == "FINAL_QC" and p.get("observations")
    ]
    ap06_fail = [
        p for p in measurements
        if p.get("measurement_code") == "R_U-V" and p.get("in_spec") is False
    ]
    ap06_pass = [
        p for p in measurements
        if p.get("measurement_code") == "R_U-V" and p.get("in_spec") is True
    ]

    # Sub-line / run breakdown
    by_subline: dict[str, dict[str, int]] = {}
    for m in messages:
        p = dict(m.payload)
        key = f"{p.get('subline_id')}|{p.get('run_id')}"
        bucket = by_subline.setdefault(key, {})
        bucket[m.message_type] = bucket.get(m.message_type, 0) + 1

    # Evidence integrity
    raw_line_count = len(run_lines)

    result = {
        "contract_version": CONTRACT_VERSION,
        "total_messages": len(messages),
        "unique_message_keys": unique,
        "duplicate_message_keys": duplicate,
        "raw_jsonl_lines": raw_line_count,
        "integrity_ok": raw_line_count == unique == len(messages) and duplicate == 0,
        "sub_line_count": len({p.get("subline_id") for p in payloads}),
        "run_ids": sorted({p.get("run_id") for p in payloads}),
        "counts_by_message_type": counts,
        "counts_by_subline_run": by_subline,
        "checklist_result_count": len(checklist),
        "measurement_result_count": len(measurements),
        "quality_result_count": len(quality),
        "quality_result_with_observations": len(quality_with_obs),
        "ap06_fail_measurements": len(ap06_fail),
        "checklist_sample": checklist[0] if checklist else None,
        "ap06_pass_sample": ap06_pass[0] if ap06_pass else None,
        "ap06_fail_sample": ap06_fail[0] if ap06_fail else None,
        "ap08_observation_sample": ap08_obs[0] if ap08_obs else None,
        "ap11_observation_sample": ap11_obs[0] if ap11_obs else None,
        "quality_ng_sample": quality_ng[0] if quality_ng else None,
    }
    (HERE / "message-counts.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    # Focused AP08 NG → reinspect PASS: prove the NG attempt's anomaly
    # observation is frozen per-attempt (never rewritten by the later PASS).
    ng_sample = _ap08_ng_observation_sample()
    (HERE / "ap08-ng-observation.json").write_text(
        json.dumps(ng_sample, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")

    print(json.dumps({
        "contract_version": CONTRACT_VERSION,
        "total": len(messages),
        "unique": unique,
        "duplicate": duplicate,
        "integrity_ok": result["integrity_ok"],
        "checklist_result": len(checklist),
        "measurement_result": len(measurements),
        "quality_result": len(_of_type("QUALITY_RESULT")),
        "quality_with_observations": len(quality_with_obs),
        "ap06_fail": len(ap06_fail),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
