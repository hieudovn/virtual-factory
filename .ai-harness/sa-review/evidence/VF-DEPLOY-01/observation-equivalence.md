# VF-DEPLOY-01 — observation-equivalence.md

Machine-readable evidence extracted from `/assy-demo/observations` on both
runtimes (full JSON: `docker-observation-evidence.json`,
`native-observation-evidence.json`). All four P0 message types are present and
identical in structure.

## Message type distribution (Docker, fresh identical drive = native)

| message_type | count (native fresh drive) |
|---|---|
| `mes.execution_event` | 2342 |
| `mes.genealogy_relationship` | 304 |
| `mes.quality_result` | 680 |
| `mes.release` | 168 |
| **total** | 3494 |

## E2 — AP06 FAIL attempt 1 / PASS attempt 2 (distinct identity)

Both runtimes emit (identical):

```json
// FAIL attempt 1
{"message_key": "ASSY-SL03:R2|QR-0002|assy.quality_result|1.0",
 "station_id": "AP06", "event_type": "QUALITY_RESULT",
 "disposition": "FAIL", "attempt_number": 1, "simulation_time_s": 960.0}
// PASS attempt 2
{"message_key": "ASSY-SL03:R2|QR-0003|assy.quality_result|1.0",
 "station_id": "AP06", "event_type": "QUALITY_RESULT",
 "disposition": "PASS", "attempt_number": 2, "simulation_time_s": 1080.0}
```

- Distinct `record_id` (QR-0002 vs QR-0003) → distinct `message_key` per
  attempt. FAIL attempt 1 and PASS attempt 2 never share identity.

## E3 — AP08 NG attempt 1 / PASS attempt 2

```json
// NG attempt 1
{"message_key": "ASSY-SL02:R3|QR-0006|assy.quality_result|1.0",
 "station_id": "AP08", "event_type": "QUALITY_RESULT",
 "disposition": "NG", "attempt_number": 1, "simulation_time_s": 1200.0}
// PASS attempt 2
{"message_key": "ASSY-SL02:R3|QR-0007|assy.quality_result|1.0",
 "station_id": "AP08", "event_type": "QUALITY_RESULT",
 "disposition": "PASS", "attempt_number": 2, "simulation_time_s": 1320.0}
```

## E4 — AP11 final-QC PASS vs RELEASE (distinct facts)

```json
// FINAL_QC PASS -> mes.quality_result
{"message_key": "ASSY-SL01:R1|QR-0011|assy.ap11_final_qc|1.0",
 "station_id": "AP11", "event_type": "AP11_FINAL_QC_PASS",
 "disposition": "PASS", "attempt_number": 1, "simulation_time_s": 1440.0}
// RELEASE -> mes.release
{"message_key": "ASSY-SL01:R1|release:MTR-0001|assy.ap11_release|1.0",
 "station_id": "AP11", "event_type": "AP11_RELEASE",
 "release_time_s": 1680.0, "simulation_time_s": 1680.0}
```

## Contract invariants preserved (E4)

- `message_key` = `run_id|source_event_id|point_id|schema_version`
  (`schema_version` = `1.0`).
- `run_id` = `sub_line_id:R<gen>`; one generation bump per reset
  (R1 HAPPY → R2 AP06 → R3 AP08 observed in the driven sequence).
- Per-attempt quality identity distinct (`record_id` per attempt).
- AP04 genealogy cardinality: one message per child, both parents in
  `parent_wip_ids` (verified equal native vs Docker).
- AP11 FINAL_QC (quality) and RELEASE (release) are two distinct message types
  with distinct keys.

Containerization did not alter the accepted P0 producer contract.
