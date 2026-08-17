# VF-CONTRACT-FINALITY-01 — identity-idempotency.md

## Identity (unchanged)

The terminal fact belongs to the SAME authoritative WIP/station/run context as
the final FAIL attempt:

| Field | Terminal fact value |
|---|---|
| `message_key` | `ASSY-SL03:R1\|QR-0002\|assy.quality_result\|1.0` |
| `run_id` | `ASSY-SL03:R1` |
| `subject_id` / `wip_id` | `MTR-0001` |
| `station_id` | `AP06` |
| `record_id` (source identity) | `QR-0002` |
| `attempt_number` | 2 |
| `simulation_time_s` | 960.0 |

`message_key` is unchanged from the pre-enrichment contract: the terminal fact
is the SAME message as the final FAIL attempt, now carrying
`is_terminal=true`. Prior FAIL attempt keeps its own distinct `record_id`
(`QR-0001`) / `message_key` with `is_terminal=false`.

## Idempotency

- Poll/replay: the delivery checkpoint keys on `(run_id, source_event_id,
  gateway_id)`; a second `poll()` returns `[]` and does NOT re-deliver the
  terminal fact (test `test_poll_replay_no_duplicate_terminal_fact`).
- The `terminal` flag is stamped on the immutable `QualityRecord` at the exact
  transition decision — it never changes on replay/late discovery.
- No duplicate terminal fact on repeated polling.

## Stability across runs/resets

`run_id` generation (`ASSY-SL03:R1` → `R2` on reset) is unchanged; the
terminal fact re-baselines to the new run exactly like every other P0 fact.
