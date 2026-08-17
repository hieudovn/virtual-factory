# VF-CONTRACT-FINALITY-01 — before-after-contract.md

## BEFORE (accepted P0, `mes.quality_result` for AP06/AP08)

```json
{
  "message_key": "ASSY-SL03:R1|QR-0002|assy.quality_result|1.0",
  "message_type": "mes.quality_result",
  "schema_name": "vf.mes.quality_result",
  "schema_version": "1.0",
  "payload": {
    "event_type": "QUALITY_RESULT",
    "record_id": "QR-0002",
    "wip_id": "MTR-0001",
    "station_id": "AP06",
    "check_type": "TEST",
    "disposition": "FAIL",
    "attempt_number": 2,
    "simulation_time_s": 960.0,
    "reason_code": ""
  }
}
```

A consumer cannot tell whether attempt 2 is "FAIL awaiting retest" or
"FAIL terminal / FAILED_FINAL" without guessing the retry limit.

## AFTER (additive only — two new fields on the same message)

```json
{
  "message_key": "ASSY-SL03:R1|QR-0002|assy.quality_result|1.0",
  "message_type": "mes.quality_result",
  "schema_name": "vf.mes.quality_result",
  "schema_version": "1.0",
  "payload": {
    "event_type": "QUALITY_RESULT",
    "record_id": "QR-0002",
    "wip_id": "MTR-0001",
    "station_id": "AP06",
    "check_type": "TEST",
    "disposition": "FAIL",
    "attempt_number": 2,
    "simulation_time_s": 960.0,
    "reason_code": "",
    "is_terminal": true,
    "terminal_state": "failed_final"
  }
}
```

Prior non-terminal attempt:

```json
{ "...": "...", "is_terminal": false, "terminal_state": "" }
```

## What changed / what did NOT

| Aspect | Status |
|---|---|
| `is_terminal` + `terminal_state` added to `mes.quality_result` | ADDITIVE |
| `disposition`, `attempt_number`, `check_type`, `reason_code`, `record_id`, `wip_id`, `station_id`, `event_type`, `simulation_time_s` | UNCHANGED |
| `message_type` / `schema_name` / `schema_version` | UNCHANGED (`mes.quality_result`, `vf.mes.quality_result`, `1.0`) |
| `message_key` / idempotency identity | UNCHANGED |
| Other message types (execution_event, genealogy_relationship, release) | UNCHANGED |
| Runtime transition / retry / release / routing semantics | UNCHANGED |
