# VF-CONTRACT-FINALITY-01 — Terminal Quality Evidence Enrichment

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-CONTRACT-FINALITY-01` (additive producer contract enrichment) |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Producer Baseline | `f72cc9564b251c3812c2b6070bddd37e479d5ea5` |
| Demo Baseline | `494c12e265d297a389e4463848b9c0b6aafed0b1` |
| Docker Baseline | `6e68ec957a925c32999644f315fcd234245bef50` |
| MES Blocker | `b9cc69a1321766334acea2e69eb1be6036d0acac` |
| Baseline (tip before work) | `e3c3807` |
| Head | `<set at commit>` |
| Production code changed | **YES** (additive only) |
| Runtime transition semantics changed | **NO** |
| Existing payload fields removed/renamed | **NO** |
| MES/Odoo IDs introduced | **NO** |
| FAILED_FINAL authoritative evidence exposed | **YES** |
| Contract evolution | **ADDITIVE** |

## 2. Problem & outcome

The accepted FAILED_FINAL runtime truth (`quality_status=FAILED_FINAL`,
`release=false`, AP06 attempt1 FAIL + attempt2 FAIL) was only exposed as two
ordinary `mes.quality_result` FAIL facts; a consumer could not distinguish
"FAIL awaiting retest" from "FAIL terminal" without guessing the retry limit.

Outcome: the final attempt's `mes.quality_result` now carries the
authoritative terminal outcome additively:

```text
is_terminal: true
terminal_state: "failed_final"
```

Prior attempts carry `is_terminal=false`, `terminal_state=""`.

## 3. Authoritative source (verified, not reconstructed)

`AssyLineRuntime._execute_quality_disposition` already emits the authoritative
transition `QUALITY_FAILED_FINAL` when `disposition in ("FAIL","NG") and
attempt >= max_attempts`. The record creation and the FAILED_FINAL transition
are one atomic outcome in the same call. See `runtime-source.md`.

The terminal flag is **stamped on the `QualityRecord` at that exact decision**
(same condition), so the bridge stays a pure reader and finality is never
guessed by the consumer.

## 4. Contract decision (see `contract-decision.md`)

Enrich the final attempt's `mes.quality_result` (one atomic outcome) rather
than add a redundant distinct event. Generic fields `is_terminal` +
`terminal_state`; no TIPA/AP06-specific or MES-specific naming. Additive,
schema_version stays `1.0`.

## 5. Implementation (additive only)

- `quality_records.py`: `QualityRecord.terminal: bool = False` (+ `to_dict`).
- `line_runtime.py`: stamp `terminal` using the SAME condition as the existing
  FAILED_FINAL transition (no transition-logic change).
- `observation_bridge.py`: `_quality_fact` emits `is_terminal` +
  `terminal_state`; `assy.quality_result` allow-list extended.
- `tests/test_vf_contract_finality_01.py`: 16 tests (gate §12 1–16).

No change to MESProjection (already generic pass-through), no change to any
other message type, no MES repo change.

## 6. Required FAILED_FINAL journey (§7) — verified

```text
AP06 FAIL attempt 1  → is_terminal=false            (QR-0001)
AP06 FAIL attempt 2  → is_terminal=true, failed_final (QR-0002)
AP11 RELEASE         → absent
```

Real machine evidence: `failed-final-journey.json`.

## 7. Non-terminal journeys (§8) — verified

- AP06 FAIL1 → PASS2: 0 terminal facts, release present.
- AP08 NG1 → PASS2: 0 terminal facts, release present.
- HAPPY_PATH: 0 terminal facts across sub-lines.
- Six-line isolation: exactly one terminal fact, on ASSY-SL03 only.

## 8. Identity / idempotency (§9) — preserved

Terminal fact has the same `message_key`, `run_id`, `subject_id`,
`station_id`, `attempt_number`, `simulation_time_s` as the final FAIL attempt
(same `record_id`). Poll/replay does not duplicate the terminal fact
(test-verified).

## 9. Projection path (§10) — verified

`ASSY runtime → AssyObservationBridge → RealityInput → ObservationService →
ObservationEnvelope → MESProjection → ProjectedMessage` — the enriched fields
reach the ProjectedMessage payload unchanged (test
`test_terminal_fields_flow_through_mes_projection`). No MES branching in the
runtime state machine; no Odoo IDs.

## 10. Generic semantics (§11) — satisfied

Generic quality-outcome vocabulary only (`is_terminal`, `terminal_state` with
the existing `QualityStatus.FAILED_FINAL.value`). No `mes_failed_final`, no
Odoo fields, no AP06-specific consumer logic, no TIPA-specific code in generic
observation core.

## 11. Cross-system fixture for MES (§13)

`.ai-harness/sa-review/evidence/VF-CONTRACT-FINALITY-01/failed-final-projected-message.json`
— a real sanitized ProjectedMessage fixture with the semantic fields MES
SHOULD use and the fields it MUST NOT infer.

## 12. Regression (§14) — green

- New tests: **16 passed**.
- Targeted ASSY/observation/quality: **535 passed, 2 failed** (pre-existing).
- Full suite: **1570 passed, 2 failed** (pre-existing; = 1554 baseline + 16).
- Docker/native enriched equivalence: **OK** (rebuilt image emits identical
  terminal fact).

## 13. STOP conditions (§16) — none triggered

Runtime already exposes the authoritative transition; finality is not
reconstructed by counting attempts; no existing field/message identity broken;
no quality/runtime semantics changed; the terminal fact is WIP-scoped and
idempotent.

## 14. Evidence

`.ai-harness/sa-review/evidence/VF-CONTRACT-FINALITY-01/`:

`runtime-source.md`, `contract-decision.md`, `before-after-contract.md`,
`failed-final-journey.md`, `non-terminal-journeys.md`, `identity-idempotency.md`,
`six-line-isolation.md`, `consumer-compatibility.md`, `regression.md`,
`changed-files.md` + machine outputs (`failed-final-journey.json`,
`non-terminal-journeys.json`, `failed-final-projected-message.json`,
`regression-full.txt`) and reproducible scripts (`generate_finality_evidence.py`,
`verify_docker_enriched.py`).

## 15. Recommendation

```text
VF-CONTRACT-FINALITY-01 — READY FOR SA REVIEW
Contract evolution: ADDITIVE
```

MES is untouched; no HTTP gateway or MES→VF context was begun.
