# TIPA ASSY Customer Demo Scenario v1 — End-to-End Demo Guide

`VF-DM-DEMO-ASSY-MES-01` · contract version `tipa-assy-demo-v1`.

A deterministic, resettable single-sub-line (`ASSY-SL01`) VF→MES demo:
`SSO2+RSO2 → PRE-ASSY → AP01..AP11 → LINE_OUT`, routed through the existing
M5 observation pipeline (`RealityInput → ObservationService →
ObservationRouter → MESProjection → JSONL/MQTT gateways`).

## Prerequisites

- Python 3.11+, repo installed: `pip install -e ".[dev]"`

## Run the demo end-to-end (one command)

```bash
python -m virtual_factory.assembly.demo_assy_mes \
  --jsonl out/demo-assy-mes.jsonl \
  --fixtures out/demo-assy-mes-fixtures
```

This:
1. Runs the full deterministic scenario once (4 WIPs, AP05 jam fault/recovery,
   LINE_OUT GOOD/REJECT, OEE summary).
2. Writes the 63 `ProjectedMessage`s as JSONL (`out/demo-assy-mes.jsonl`).
3. Writes categorized contract fixtures under `out/demo-assy-mes-fixtures/`.

Expected output ends with an OEE summary:

```json
{
  "planned_s": 1200.0, "downtime_s": 120.0, "run_s": 1080.0,
  "ideal_cycle_s": 240.0, "actual_count": 4, "good_count": 3, "reject_count": 1,
  "availability": 0.9, "performance": 0.888889, "quality": 0.75, "oee": 0.6
}
```

## The four deterministic WIPs

| WIP | Journey | LINE_OUT |
|---|---|---|
| `MTR-DEMO-001` | happy: AP04 join, AP06/AP08/AP11 PASS | GOOD |
| `MTR-DEMO-002` | AP06 FAIL attempt 1 → rework → PASS attempt 2 | GOOD |
| `MTR-DEMO-003` | AP05 jam → FAULT → STOPPED → recover → RUNNING | GOOD |
| `MTR-DEMO-004` | AP11 final-QC FAIL (terminal) | REJECT |

## Minimal control surface (FastAPI)

The control surface is also available through the existing `serve` app:

| Endpoint | Action |
|---|---|
| `POST /demo-assy-mes/reset` | Reset demo |
| `POST /demo-assy-mes/start` | Start (run to completion) |
| `POST /demo-assy-mes/pause` | Pause |
| `POST /demo-assy-mes/step` | Single-fact step |
| `POST /demo-assy-mes/jam` | Trigger AP05 jam |
| `POST /demo-assy-mes/recover` | Recover line |
| `GET /demo-assy-mes/snapshot` | line state, WIP tokens, recent events, OEE |
| `GET /demo-assy-mes/messages` | Delivered ProjectedMessages |

```bash
python -m virtual_factory.main serve   # then curl the endpoints above
```

## Message contract

Every message carries: stable idempotency key, `contract_version`
(`tipa-assy-demo-v1`), `run_id` (`ASSY-SL01:R<n>`), `subline_id` (`ASSY-SL01`),
station identity, WIP identity, and `simulation_time_s`.

Message types emitted:

- `mes.run_status` (line state)
- `mes.issue` (exception raised/resolved `AP05_JAM`)
- `mes.execution_event` (WIP enter, operation completion, rework, downtime, LINE_OUT)
- `mes.quality_result` (AP06/AP08/AP11)
- `mes.genealogy_relationship` (AP04 join)
- `mes.oee_summary` (end-of-run OEE)
