# MANUAL-E2E-01 — Full Human-Operated ASSY Production Journey (Acceptance)

Status: **MANUAL-E2E-01 — READY FOR SA / STAKEHOLDER ACCEPTANCE**

Baseline: `5318bdb` (no production-code change was required by this gate)

## 1. Setup

- Mode: `MANUAL` | Scenario: `HAPPY_PATH` | Target sub-line: `ASSY-SL01`
- Source WIP: `SSO2-0001` (carrier `PAL-001`) → child `MTR-0001` after AP04 JOIN
- The whole browser run remained MANUAL. Other occupied positions were resolved
  manually before indexing (synchronized logical-conveyor behavior).

## 2. Primary target genealogy handoff

```
SSO2-0001 (parent A) + RSO2-0001 (parent B) → MTR-0001 @ AP04
```

Exactly one JOIN; no duplicate child. After AP04 the target identity switched
explicitly from `SSO2-0001` to `MTR-0001`.

## 3. Station-by-station manual interaction matrix (primary target)

| Station | Manual control | Evidence before action | Action | Expected semantic outcome | Physical move allowed? | PASS |
|---|---|---|---|---|---|---|
| PRE-ASSY | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP01 | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP02 | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP03 | checklist + CONFIRM & COMPLETE | incomplete checklist (disabled) | check all → CONFIRM & COMPLETE | CONFIRMED / quality null / CONTINUE / eligible | after index only | ✅ |
| AP04 | JOIN COMPLETE | SSO2 parent + JOIN | JOIN COMPLETE | JOIN_COMPLETE / child MTR / CONTINUE | child at AP04 then index | ✅ |
| AP05 | DONE | child MTR + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP06 | PASS/FAIL | measurements + proposal + reason + controls | PASS | TEST_COMPLETE / PASS / CLEAR / CONTINUE / eligible | after index only | ✅ |
| AP07 | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP08 | PASS/NG | observations + proposal + reason + controls | PASS | INSPECTION_COMPLETE / PASS / CLEAR / CONTINUE / eligible | after index only | ✅ |
| AP09 | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP10 | DONE | AWAITING_COMPLETION + DONE | DONE | DONE / CONTINUE / eligible | after index only | ✅ |
| AP11 stage 1 | PASS (QC) | observations + proposal + PASS | PASS | CONFIRMED / PASS / CLEAR / AWAITING_COMPLETION | **no** (not released) | ✅ |
| AP11 stage 2 | RELEASE | RELEASE only after QC PASS | RELEASE | RELEASED / lifecycle RELEASED / CONTINUE / output | off-line | ✅ |

## 4. HOLD / RESUME matrix

| Step | Control | Expected | PASS |
|---|---|---|---|
| AWAITING_COMPLETION (AP03) | HOLD | HELD + STAY_AT_STATION + operator_holds++ | ✅ |
| HELD blocked | — | conveyor cannot index; completion fails closed | ✅ |
| RESUME | RESUME | exact pre_hold_state restored | ✅ |

## 5. AP06 FAIL → RETEST → PASS matrix (ASSY-SL03, MANUAL)

| Step | Expected | PASS |
|---|---|---|
| attempt 1 observation | proposal FAIL + anomaly + reason visible | ✅ |
| operator FAIL | FAIL / RETEST_PENDING / STAY_AT_STATION / WIP stays AP06 | ✅ |
| attempt 2 observation | fresh evidence, proposal PASS, attempt #2 | ✅ |
| operator PASS | CLEAR / CONTINUE / eligible | ✅ |

## 6. AP08 NG → REINSPECT → PASS matrix (ASSY-SL02, MANUAL)

| Step | Expected | PASS |
|---|---|---|
| attempt 1 observation | neutral observations + proposal NG | ✅ |
| operator NG | NG / REINSPECT_PENDING / STAY_AT_STATION / WIP stays AP08 | ✅ |
| attempt 2 observation | fresh evidence, proposal PASS | ✅ |
| operator PASS | CLEAR / CONTINUE / eligible | ✅ |

## 7. Unsupported AP11 negative final QC (fail-closed)

FAIL request / negative proposal → rejected; no QualityRecord; no status/routing
mutation; no accepted command/input; non-eligible. (Atomicity proven in
OPS-04-C01-R2 tests; re-verified by `TestAP11AtomicRejection`.)

## 8. Stale / duplicate command fail-closed

`test_stale_duplicate_command_rejected_and_unchanged` — a duplicate DONE on an
already-eligible operation is rejected; occupancy truth unchanged.

## 9. Automated E2E support (no runtime bypass)

`tests/test_manual_e2e_01.py`:
- `test_full_manual_journey_releases_motor` — MANUAL, public surfaces only;
  SSO2 → MTR → RELEASE; genealogy exactly once; quality records exactly once;
  AP11 two-stage CONFIRMED → RELEASED.
- `test_stale_duplicate_command_rejected_and_unchanged`
- `test_manual_mode_no_auto_completion`

## 10. Evidence package

`docs/ui/evidence/manual-e2e-01/`
- `TRACE.md` — authoritative per-station truth trace (13 rows).
- `01_*` … `18_*` — full primary-journey screenshots.
- `H01/H02/H03` — HOLD → HELD → RESUME.
- `Q01/Q02` — AP06 FAIL → RETEST PASS.
- `V01/V02` — AP08 NG → REINSPECT PASS.

## 11. Regression

- Full suite: `1445 passed, 1 failed` (pre-existing `test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`, unchanged).
- Focused OPS-02/03/04 + quality + schema + feed: `207 passed`.
