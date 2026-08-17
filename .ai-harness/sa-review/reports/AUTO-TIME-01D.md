# AUTO-TIME-01D — SA Review Report

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01D` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline (authorized from 01C) | `4e12239be6d71977780d73fc762a47096672e5b6` |
| Head (evidence under review) | `c707f23659d9a8a8d4e3fd8d4d033a3b3d43ba7e` |

## Production code changed

**NO.** AUTO-TIME-01D is a validation/evidence gate. No production code was
modified. Only evidence/fixtures added under
`.ai-harness/sa-review/evidence/AUTO-TIME-01D/`.

## Changed files (evidence only)

- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/validate_timing_01d.py` — backend V1–V10 matrix runner
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/timing-validation.md` — consolidated evidence
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui-validation.md` — UI smoke matrix
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s1_baseline.png` (+ `_populated`)
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s2_ap05_135.png`
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s3_ap05_065.png`
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s4_speed5x.png`
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s5_variable.png`
- `.ai-harness/sa-review/evidence/AUTO-TIME-01D/ui/ui_s6_manual.png`
- Fixture configs (validation-only): `ui/config_ap05_135.yaml`, `ui/config_ap05_065.yaml`, `ui/config_variable.yaml`

## Automated test results

| Suite | Result |
|---|---|
| `test_auto_timing.py` (01A) | pass |
| `test_auto_timing_runtime.py` (01B) | pass |
| `test_auto_timing_snapshot.py` (01C) | pass |
| `test_assy_line.py`, `test_auto_equiv_01.py`, `test_manual_e2e_01.py`, `test_ops02_operation_execution.py`, `test_ops02_schema_contract.py`, `test_ops04_c01.py`, `test_demo_composition.py`, `test_quality.py`, `test_quality_records_projection.py`, `test_demo_overview.py`, `test_assy_demo.py`, `test_sub_line_identity.py`, `test_config_validation.py`, `test_ops03_contract_loader.py`, `test_ops03_interaction.py`, `test_sim_val_01_feed.py` | **471 passed, 2 failed** |

The 2 failures are the same pre-existing, baseline-reproduced failures documented
in 01A/01B/01C:
- `test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`
- `test_ops04_c01.py::TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

Failure count/type unchanged → no new regressions.

## Backend validation matrix (V1–V10) — all PASS

See `timing-validation.md`. Highlights:
- V1: AP05 nominal=effective=90, dwell=120, no bottleneck.
- V2: AP05=135 → first dwell=135, overrun=15, bottleneck=AP05 (not 120+120).
- V3: seed 42 reproducible; seed 43 differs.
- V4: snapshot polling does not re-sample (single value, same execution_id).
- V5/V6: MANUAL/ASSISTED legacy fixed duration, timing null.
- V7/V8: AP06 retry / AP08 reinspect — same op, same sample.
- V9: AP11 CONFIRMED → RELEASED.
- V10: six sub-lines derived seeds [42..47], re-init reproducible.

## UI validation matrix (UI-S1..S8) — all PASS (with documented visibility limits)

See `ui-validation.md`. Validated on the **canonical 14/8 UI** (provenance
re-verified: served === workspace === `docs/m6-s01-tipa-baseline`; the unapproved
`agent/assy-uiux-improvements` 13/8 version is NOT served; `main` has no
`assy_demo.*`).

- UI-S1 baseline: normal 120s cadence, no bottleneck.
- UI-S2 AP05=135: t=1005 @ dwell8, genealogy join gaps 135s; snapshot
  actual=135/overrun=15/bottleneck=AP05.
- UI-S3 AP05=65: back to 120s cadence; snapshot overrun=0, bottleneck="".
- UI-S4 speed 1x→5x: runtime values unchanged.
- UI-S5 VARIABLE: snapshot polling stable; reset reproducible.
- UI-S6 MANUAL: PRE-ASSY waits (AWAITING_COMPLETION, legacy 30s, timing null).
- UI-S7 retry: API/backend verified (same op/sample); exception scenario targets
  SL03 (SINGLE_TARGET_EXCEPTION) so not shown on selected SL01 detail.
- UI-S8 AP11: AUTO happy path released a motor; CONFIRMED→RELEASED.

**Visibility note:** the current UI does not render the 01C timing/bottleneck
fields (API/snapshot-only). The bottleneck is observable in the UI via the
genealogy join cadence and the simulation clock. No UI was modified to make
validation pass.

## Architecture closure checklist

| # | Invariant | Status |
|---|---|---|
| 1 | Timing profile is config-driven | CONFIRMED |
| 2 | AUTO sampling is sample-once per OperationExecution | CONFIRMED |
| 3 | Frozen `op.work_duration_s` is runtime truth | CONFIRMED |
| 4 | Operation exists before dwell sizing | CONFIRMED |
| 5 | Dwell reflects bottleneck timing | CONFIRMED |
| 6 | MANUAL/ASSISTED ignore AUTO profiles | CONFIRMED |
| 7 | Seed/reset is reproducible | CONFIRMED |
| 8 | Snapshot is side-effect free | CONFIRMED |
| 9 | Retry/reinspect does not re-sample in P1 | CONFIRMED |
| 10 | AP11 RELEASE has no separate timing in P1 | CONFIRMED |
| 11 | UI presentation consistent with snapshot/runtime truth | CONFIRMED (with noted visibility limits) |
| 12 | Presentation speed does not alter simulation timing truth | CONFIRMED |
| 13 | No MES semantics introduced | CONFIRMED |

All 13 invariants CONFIRMED → no rejection.

## Known limitations

- UI does not surface `actual_dwell_s`/overrun/bottleneck/timing (API-only; 01C scope, no UI redesign per gate).
- Pre-existing scenario-targeting behavior (`TestVScenarioSwitch`) and a benign page-load 404 (missing auxiliary resource).
- `simulation_time_multiplier` remains dead config (out of scope, untouched).

## Statement

No production-code correction was required. AUTO-TIME (01A→01D) is validated
end-to-end and, per this gate's evidence, **ready for SA closure**. (Final
COMPLETE/CLOSED remains an SA decision.)

## Next steps (not self-authorization)

- SA closure of the AUTO-TIME gate.
- M6-INT-01 (MES integration) only under separate SA authorization.
