# OPS-04-C01 — Production Decision Semantics & Manual E2E Readiness

Status: **READY FOR SA REVIEW** (machine-derived status follows below)

Baseline: `24d8be7`
Branch: `docs/m6-s01-tipa-baseline`

This slice closes six blockers (A–F) in the ASSY production-decision
semantics so that the Manual E2E run is physically consistent.

---

## 1. Blockers closed

| ID | Blocker | Resolution |
|----|---------|------------|
| A | HOLD was only `routing_action=STAY_AT_STATION`, not a real state | HOLD is now a first-class `HELD` state; explicit `RESUME` recovery (station action). |
| B | `HELD` KPI counted only quality retry statuses | Operator/exception holds are counted separately (`operator_holds`) and block the line. |
| C | Measurements were rewritten out-of-range for FAIL/NG (backwards causality) | Measurements are OBSERVED before the decision and never rewritten. |
| D | No proposal visible before decision | `proposed_quality_result` + pending `measurements` are exposed before the decision. |
| E | Routing was implicit | PASS → `CONTINUE`; FAIL/NG retry and HELD → `STAY_AT_STATION`. |
| F | AP11 conflated final QC with RELEASE | Final QC (CONFIRM + PASS/FAIL) is a distinct step; RELEASE only after QC PASS. |

## 2. Observation / decision split (Blockers C, D)

Each quality station now has two phases:

1. **Observation** — at the `WORKING → AWAITING_DECISION` transition the
   runtime generates the synthetic measurements (AP06 TEST) and the
   scenario-derived proposal, stored on `OperationExecution`:
   - `op.measurements` — pending observed measurements (dicts).
   - `op.proposed_quality_result` — machine proposal (`PASS`/`FAIL`/`NG`).
   Emits `QUALITY_OBSERVED`. No `QualityRecord` is created yet.

2. **Decision** — `submit_operation_command` applies the final disposition:
   - MANUAL: operator `payload.decision` (required).
   - ASSISTED: operator decision, or the stored proposal.
   - AUTO: the stored proposal (scenario).
   The `QualityRecord` is built from the OBSERVED `op.measurements`; FAIL/NG
   never rewrite them.

## 3. HOLD lifecycle (Blockers A, B)

- `submit_station_action(station, wip, "HOLD")` → `AWAITING_COMPLETION` /
  `AWAITING_DECISION` → `HELD`, with `routing_action = STAY_AT_STATION`.
- HELD operations are never eligible; the station never completes; the
  conveyor never indexes past them.
- `submit_station_action(station, wip, "RESUME")` → `HELD` →
  `AWAITING_DECISION` (quality) or `AWAITING_COMPLETION` (non-quality).
- Completion/decision commands while HELD fail closed.
- `ProductionSummary.operator_holds` counts active HELD operations, distinct
  from `active_quality_holds` (RETEST_PENDING / REINSPECT_PENDING /
  FAILED_FINAL).

## 4. Explicit routing (Blocker E)

| Outcome | `routing_action` | Next state |
|---------|------------------|------------|
| PASS / CLEAR (AP06, AP08) | `CONTINUE` | `COMPLETED` → `ELIGIBLE_TO_INDEX` |
| FAIL / NG retry | `STAY_AT_STATION` | `FAILED` → `AWAITING_DECISION` (next attempt) |
| FAILED_FINAL | `STAY_AT_STATION` | `FAILED` (terminal) |
| HELD | `STAY_AT_STATION` | `HELD` (blocked) |
| RELEASE (AP11) | `CONTINUE` | `COMPLETED` → `ELIGIBLE_TO_INDEX` |

## 5. AP11 final QC vs RELEASE (Blocker F)

AP11 contract: `normal_action = CONFIRM`, `required_action = RELEASE`,
`decision_actions = (PASS, FAIL)`, `final_disposition_actions = (RELEASE, HOLD)`.

1. Final QC decision (CONFIRM + PASS/FAIL):
   - PASS → quality `CLEAR`, `operation_result = CONFIRMED`, operation →
     `AWAITING_COMPLETION` (awaiting RELEASE).
   - FAIL → `REINSPECT_PENDING` (or `FAILED_FINAL` when attempts exhausted),
     `STAY_AT_STATION`.
2. RELEASE (distinct final disposition):
   - Allowed only when quality status is `CLEAR` and last disposition is
     `PASS`; blocked otherwise (HELD blocks; FAIL blocks).
   - Marks `WipLifecycle.RELEASED`, `operation_result = RELEASED`,
     `routing_action = CONTINUE`, station complete.

## 6. Semantic state table

| Operation state | Eligible? | Progression |
|-----------------|-----------|-------------|
| ARRIVED / READY / WORKING | no | station work in progress |
| AWAITING_DECISION | no | proposal + measurements observed; awaiting operator/system decision |
| AWAITING_COMPLETION | no | awaiting completion command (DONE / RELEASE / checklist gate) |
| HELD | no | operator hold; explicit RESUME required |
| FAILED (retry) | no | `STAY_AT_STATION`; next attempt re-observes |
| FAILED + FAILED_FINAL | no | terminal; no recovery |
| COMPLETED | no (transient) | → `ELIGIBLE_TO_INDEX` |
| ELIGIBLE_TO_INDEX | yes | conveyor indexes past |

## 7. Conveyor dwell correction

A completed station (e.g. AP04 child waiting for the rest of the line) is no
longer re-processed in a subsequent dwell. `execute_dwell` skips positions
already marked complete until the next synchronized index. This prevents a
stalled line from re-executing AP04 JOIN on its own child.

## 8. Tests

`tests/test_ops04_c01.py` — 29 tests: HOLD lifecycle (10), AP06 causality (8),
AP08 causality (5), AP11 separation (6). Existing OPS-02/OPS-03/quality tests
updated to the new AP11 two-step and HOLD→HELD semantics.

## 9. Files changed

- `src/virtual_factory/assembly/operation_execution.py` — `proposed_quality_result`
  field; `AWAITING_DECISION → AWAITING_COMPLETION` transition; HELD transitions.
- `src/virtual_factory/assembly/station_contracts.py` — AP11 normal/required/decision split.
- `src/virtual_factory/assembly/line_runtime.py` — observation/decision split,
  HOLD/RESUME, command-aware dispatch, release disposition, dwell-loop fix.
- `src/virtual_factory/assembly/demo_snapshot.py` — proposal + pending
  measurements projection; `operator_holds`.
- `.ai-harness/schemas/operation-execution.schema.json` — `proposed_quality_result`.
- `src/virtual_factory/ui/static/assy_demo.js` — proposal display, pending
  measurements, HELD RESUME, hold KPI.
- `docs/design/station-contracts.example.yaml` — AP11 two-step + field.
- `tests/test_ops04_c01.py` — new; plus updated OPS-02/OPS-03/quality tests.
