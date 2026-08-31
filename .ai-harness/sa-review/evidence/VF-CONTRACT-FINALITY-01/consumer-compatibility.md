# VF-CONTRACT-FINALITY-01 — consumer-compatibility.md

## Existing (non-upgraded) consumers keep working

- All pre-existing `mes.quality_result` payload fields remain present and
  unchanged: `event_type`, `record_id`, `wip_id`, `station_id`, `check_type`,
  `disposition`, `attempt_number`, `simulation_time_s`, `reason_code`
  (test `test_existing_payload_fields_intact`).
- `message_type`, `schema_name`, `schema_version` are unchanged
  (`mes.quality_result` / `vf.mes.quality_result` / `1.0`) — additive fields,
  no version bump, no `2.0` (test `test_message_type_and_schema_unchanged`).
- `message_key` / idempotency identity unchanged (per-attempt distinct).
- Other message types (execution_event, genealogy_relationship, release) are
  untouched.

## No MES/Odoo IDs

- No integer `*_id` field introduced; identity keys are stable external codes
  (`QR-xxxx`, `MTR-xxxx`, `AP06`, `ASSY-SL03:R1`)
  (test `test_no_mes_odoo_ids`).
- The enrichment introduces no Odoo concepts.

## Generic vocabulary (not consumer-specific)

- `is_terminal` / `terminal_state` are generic quality-outcome semantics.
- Forbidden names avoided: no `mes_failed_final`, no Odoo field names, no
  `ap06_retry_exhausted`, no TIPA-specific projection code in generic core.

## MES guidance (cross-system fixture)

`failed-final-projected-message.json` records:
- fields MES SHOULD use: `message_key`, `message_type`, `schema_name`,
  `payload.is_terminal`, `payload.terminal_state`, `payload.station_id`,
  `payload.wip_id`, `payload.record_id`, `payload.disposition`,
  `payload.attempt_number`, `payload.simulation_time_s`, `payload.run_id`.
- fields MES must NOT infer: finality (not from `attempt_number` or silence),
  retry limit (not guessed), scrap/rework routing.
