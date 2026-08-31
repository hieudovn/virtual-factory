# AUTO-EQUIV-01 — Automated Execution Semantic Equivalence (Acceptance)

Status: **AUTO-EQUIV-01-R1 — READY FOR SA REVIEW**

Baseline: `d574faf` (no production-code change was required — the current baseline
already passes AUTO equivalence, including ordered lifecycle equivalence).

## R1 — Ordered lifecycle trace equivalence (added)

R1 hardens the proof from "same final outcome" to "same ordered semantic
lifecycle". A read-only instrumentation (monkey-patching
`OperationExecution.transition` + `AssyLineRuntime._make_event` in tests, never
in production) records the ordered sequence of state transitions and
`QUALITY_OBSERVED → QUALITY_START → QUALITY_RESULT` events.

Result: MANUAL and AUTO ordered lifecycle traces are **identical** for the happy
path, AP06 fail/retest, and AP08 NG/reinspect. Evidence: `MANUAL_LIFECYCLE_TRACE.json`,
`AUTO_LIFECYCLE_TRACE.json`, `LIFECYCLE_DIFF.md` (identical),
`AP06_RETRY_LIFECYCLE.json`, `AP08_REINSPECT_LIFECYCLE.json`.

Key ordered proofs:
- AP06: `WORKING → AWAITING_DECISION → QUALITY_OBSERVED → QUALITY_START → QUALITY_RESULT → COMPLETED` (observation before decision before result).
- AP11: `… → AWAITING_DECISION → QUALITY_OBSERVED → QUALITY_START → QUALITY_RESULT → AWAITING_COMPLETION (QC PASS) → COMPLETED (RELEASE) → ELIGIBLE` (two-stage, QC before RELEASE).
- Retry boundary: `… → AWAITING_DECISION → QUALITY_RESULT(FAIL) → FAILED → AWAITING_DECISION (retry) → …`.
- Physical station order: PRE-ASSY → AP01 → … → AP11; identity switch `SSO2-0001 → MTR-0001` at AP04.

Speed: **Case B** — `presentation_speed` is UI pacing only; it does not alter
runtime step/dwell semantics (`test_speed_is_presentation_only`).

## 1. Conclusion

AUTO is an automation of the same production semantics, never a shortcut. For
identical deterministic scenarios, the normalized authoritative outcome of
MANUAL and AUTO is **identical** (DIFF: only `completion_mode` / timing /
source differ, which are excluded by normalization).

## 2. Equivalence dimensions verified

- station visit order (AP01..AP11 + PRE-ASSY, each exactly once);
- WIP identity transition at AP04 (`SSO2-0001` → `MTR-0001`);
- genealogy (`MTR-0001 ← SSO2-0001 + RSO2-0001 @ AP04`);
- `OperationResult` by station;
- `QualityRecord` count/attempts;
- quality result/status;
- routing action;
- final lifecycle (`RELEASED`);
- released motor count (1);
- no skipped station.

## 3. Same OperationExecution lifecycle in AUTO

- Pure exec: `WORKING → AWAITING_COMPLETION → (runtime) DONE → COMPLETED → ELIGIBLE`.
- AP03: checklist payload generated → `CONFIRM_AND_COMPLETE` → `CONFIRMED`.
- AP06: observation/proposal first → decision → `TEST_COMPLETE` → quality/status/routing.
- AP08: vision observation/proposal → decision → `INSPECTION_COMPLETE`.
- AP11: final-QC decision → `CONFIRMED` → `AWAITING_COMPLETION` → `RELEASE` → `RELEASED`
  (two-stage, proven by `QUALITY_RESULT` + `STATION_COMPLETE RELEASED` events).

## 4. Failure-path equivalence

- AP06 `FAIL_FIRST_THEN_PASS`: both modes → `[FAIL#1, PASS#2]`, no skip of attempt 1.
- AP08 `FAIL_FIRST_THEN_PASS`: both modes → `[NG#1, PASS#2]`.
- Attempt identities remain distinct; no physical movement between attempts.

## 5. HOLD containment in AUTO

- An existing `HELD` operation remains `HELD` after switching to AUTO.
- AUTO never silently RESUME a human-held operation (`RESUME` is still explicit).
- Conveyor cannot index past a held position.

## 6. AP11 negative final QC in AUTO

Scenario proposal FAIL at AP11 remains fail-closed: no QualityRecord, no
REINSPECT/REWORK/SCRAP/LINE_OUT, no RELEASE, no attempt accumulation; operation
remains unresolved/non-eligible. AUTO never "fixes" it by silently choosing PASS.

## 7. Acceleration

AUTO acceleration (presentation speed / repeated STEP) does not alter the
normalized semantic trace: two identical AUTO runs produce identical traces.
The runtime always applies the full configured work duration and the same
operation stages regardless of presentation pacing.

## 8. Tests

`tests/test_auto_equiv_01.py` — 13 tests:
- happy path full release; normalized MANUAL/AUTO equality; station visit once;
  AP04 genealogy equality; AP06/AP08 PASS record equality; AP11 two-stage;
- AP06 fail/retest equality; AP08 NG/reinspect equality;
- HELD non-bypass; AP11 negative fail-closed; accelerated equivalence;
- public-surfaces-only journey.

## 9. Evidence

`docs/ui/evidence/auto-equiv-01/`
- `MANUAL_TRACE.json` / `AUTO_TRACE.json` — normalized traces.
- `DIFF.md` — identical (no semantic differences).
- `AP06_RETRY_TRACE.json`, `AP08_REINSPECT_TRACE.json` — failure-path equivalence.
- `ACCELERATED.json` — accelerated AUTO equality.

## 10. Regression

- Full suite: see final report (only pre-existing scenario-switch failure).
- AUTO-EQUIV: 13 passed; MANUAL-E2E: 3 passed; OPS/quality/schema/feed: 207 passed.
