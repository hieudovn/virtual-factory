# M6-INT-01 — Evidence (P0 outbound observation)

## Files

- `generate_evidence.py` — reproducible generator (runs the real TIPA ASSY
  composition through the observation bridge).
- `trace-happy-path.txt` — ordered P0 outbound trace, HAPPY_PATH (ASSY-SL01).
- `trace-ap06-fail-retest.txt` — exception trace, AP06_FAIL_RETEST_PASS
  (ASSY-SL03, motor MTR-0002): FAIL attempt 1 → PASS attempt 2.

## Idempotency

`generate_evidence.py` performs a second poll after the first and asserts zero
new deliveries. The happy-path trace footer records this:

```text
[second poll: 0 new deliveries — idempotent]
```

## What the traces prove

- Operation completion (pure-execution stations) → `mes.execution_event`.
- AP04 genealogy → `mes.genealogy_relationship` with authoritative
  `child_wip_id` + `parent_wip_ids` (SSO2 + RSO2).
- AP06 / AP08 quality per attempt → `mes.quality_result` with stable
  `record_id` (`QR-xxxx`) + `attempt_number` + `disposition`.
- AP11 final-QC PASS → `mes.quality_result` (`AP11_FINAL_QC_PASS`) —
  distinct identity from AP11 RELEASE → `mes.release` (`release:MTR-xxxx`).
- `source_event_id` is stable and domain-derived (execution_id, child_wip_id,
  quality record_id, `release:<wip_id>`); no wall-clock / random identity.
