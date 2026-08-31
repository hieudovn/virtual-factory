# VF-CONTRACT-FINALITY-01 — contract-decision.md

## Decision: enrich the final attempt's `mes.quality_result` (additive)

The second FAIL quality record and the transition to FAILED_FINAL are **one
atomic authoritative quality outcome** (same `_execute_quality_disposition`
call, driven by the same `attempt >= max_attempts` condition). Per the gate §4
SA preference, the terminal finality is therefore **enriched on that final
attempt's quality observation** rather than emitted as a separate redundant
event.

## Semantic fields (generic, non-TIPA, non-MES)

Added to every `mes.quality_result` (AP06/AP08 quality-result path):

| field | type | semantics |
|---|---|---|
| `is_terminal` | bool | `true` iff this record is the authoritative terminal failure (attempts exhausted) |
| `terminal_state` | str | `"failed_final"` when terminal, `""` otherwise (generic quality-status vocabulary, not TIPA/AP06-specific) |

Non-terminal records carry `is_terminal=false`, `terminal_state=""`. Existing
fields (`disposition`, `attempt_number`, `check_type`, `reason_code`,
`record_id`, …) are unchanged — strictly additive.

## Why stamp the record (atomic, authoritative)

The `terminal` flag is set on the `QualityRecord` **at the exact moment the
runtime makes the FAILED_FINAL decision** (same condition as the existing
transition). This:

- keeps the bridge a pure reader of runtime truth (its locked invariant);
- makes the flag immutable and idempotent (frozen record, never changes);
- avoids any consumer/bridge guessing about retry limits;
- does NOT change transition logic (same `attempt >= max_attempts` test).

## Contract evolution

Additive fields only. `schema_version` stays `1.0` (additive, backward
compatible). No `2.0`. Existing consumers that read only
`disposition`/`attempt_number`/`check_type`/`reason_code` keep working.

## Message identity / idempotency (unchanged)

`message_key` = `run_id|record_id|assy.quality_result|1.0` — the terminal fact
is the SAME message as the final FAIL attempt (same `record_id`, same
`message_key`), now carrying `is_terminal=true`. Prior FAIL attempt keeps its
own `record_id` / `message_key` with `is_terminal=false`. Poll/replay stays
idempotent (delivery checkpoint unchanged).

## NOT done (out of scope)

- No distinct `mes.<state>` event for FAILED_FINAL.
- No MES/Odoo IDs.
- No AP06-specific field name (e.g. `ap06_retry_exhausted`).
- No change to max attempts / retry / reinspection / release / routing /
  timing / AUTO-MANUAL semantics.
