# VF-DM-DEMO-ASSY-MES-03 — Detailed Operation Evidence Contract

`tipa-assy-demo-v1.1` · additive evidence extension on top of the
six-sub-line MES contract bridge (MES-02). Completes the one-way VF→MES
contract with detailed operation evidence. No MES implementation; no parallel
simulation; no redesign of the observation pipeline core.

## What it adds (vs v1)

Three new evidence surfaces, all derived from authoritative runtime /
operation-execution data (never fabricated in the bridge):

1. **AP03 checklist evidence — `mes.checklist_result`**
   - Event `CHECKLIST_CONFIRMED` once an AP03 checklist operation is CONFIRMED.
   - Payload: `items[]` (`item_id`, `required=true`, `completed`),
     `required_count`, `completed_count`, `status="confirmed"`,
     `source="DEMO_SYNTHETIC"`.
   - Item ids come from the station contract
     (`DEMO_CHECKLIST_ITEM_IDS = demo_item_1..3`).
   - No quality disposition is fabricated: checklist completion is NOT a
     PASS/FAIL; the message carries no `disposition`.

2. **AP06 numerical measurement evidence — `mes.measurement_result`**
   - One `MEASUREMENT_RESULT` per resistance measurement per attempt:
     `R_U-V`, `R_V-W`, `R_W-U`.
   - Payload: `measurement_code`, `value`, `unit` (Ω), `lower_limit`,
     `upper_limit`, `in_spec` (inclusive limits), `evidence_source`,
     `execution_id`, `record_id`, `attempt_number`.
   - A FAIL attempt's measurement (R_U-V = 0.29 below lower limit 0.30) is
     preserved verbatim — measurements are never rewritten by the eventual
     disposition.

3. **AP08 / AP11 structured observations — `observations[]` on
   `mes.quality_result`**
   - `QUALITY_RESULT` now carries `observations[]`
     (`observation_id` + `result` ∈ {`ok`, `anomaly`}) for
     `VISUAL_INSPECTION` (AP08) and `FINAL_QC` (AP11).
   - `proposed_quality_result` and `proposed_quality_reason` are separate
     fields from the final `disposition`.

## Per-attempt immutability (justified additive runtime change)

The gate requires that observations are NOT rewritten after the decision is
recorded. The authoritative per-attempt observation result and machine
proposal were previously not exposed in a stable form:

- `QualityRecord.checklist_items` stored only observation-id strings (no
  result), and
- `op.observations` / `op.proposed_quality_result` are overwritten on every
  re-observation, so a retested attempt's NG evidence was lost.

Minimal additive fix (no behavior change):

- `QualityRecord` gains default-valued fields `observations`,
  `proposed_quality_result`, `proposed_quality_reason`.
- `line_runtime._apply_quality_decision` passes the already-observed values
  into the frozen record at decision time (one additive constructor call).

The bridge then reads the frozen record fields first, so a retested NG attempt
keeps its `anomaly` observation and its `NG` proposal even after a later PASS.

## Provenance

Every message still carries `message_key` (= `payload.idempotency_key`),
`contract_version=tipa-assy-demo-v1.1`, `run_id=ASSY-SLxx:R<n>`, explicit
`subline_id`, `station_id` where applicable, `simulation_time_s`, and a
deterministic ISO-8601 `occurred_at`.

`GET /assy-demo/version` returns `contract_version: tipa-assy-demo-v1.1`.

## Bounded demo evidence

`python -m virtual_factory.assembly.assy_mes_bridge`:

- 666 messages, 666 unique message keys, 0 duplicate keys
- `mes.checklist_result`: 49 · `mes.measurement_result`: 96
- `mes.quality_result`: 57 (52 QUALITY_RESULT + 5 AP11 final-QC)
- MES-02 business facts unchanged (execution_event 399, run_status 9,
  issue 2, oee_summary 6, release 5, genealogy 43)

## Run locally

```bash
python -m virtual_factory.assembly.assy_mes_bridge                    # smoke
python -m pytest tests/test_assy_mes_03_evidence.py -q                # focused
python -m pytest tests -q                                              # full
python .ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-03/generate_evidence.py
```

## Scope

No MES implementation, no MES→VF, no MQTT/broker, no parallel simulation,
no rewrite of the six-sub-line runtime/topology, no change to
`operation_execution.py` or `station_contracts.py`.
