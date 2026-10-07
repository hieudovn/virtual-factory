# DDAY-B5-C01 — Compressor 5-phase Causal Correction — SA Review Report

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B5-C01/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B5-C01` |
| Authority | SA Issue `#108` (correction only); parent `#107`; SA review on PR `#101` at `cced390` |
| Issue #108 access | GitHub Issues API returned 403 / GraphQL unresolved for this token; contract authored from the SA review comment (2026-10-04T05:55:36Z, CORRECTION REQUIRED at `cced390`) plus the explicit user execution order |
| Objective | Restore Compressor to the Issue #107 5-phase causal story with real production/FG impact. Keep Capper unchanged unless a regression fix is strictly required. |
| Conservative note | UNDERSUPPLY inhibits `_produce_one_cycle()` at the composition layer. No compressor downtime pair. Default compressor NORMAL stays 240 s. |
| Non-deliverables | B6 PlantOS/MQTT, B7 deploy, merge, compressor thermodynamics, generic scenario framework, Capper redesign, KPI/health/RUL |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-reviewed B5 head / C01 baseline | `cced390cfad5c9a40361cf2caf6f1916e7003f59` — match at C01 start |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight before first C01 implementation write | `PRECHECK PASSED` after the contract commit `2cef859` |
| PR | `#101` OPEN, base `main` |

---

## Correction

Rejected 3-phase story at `cced390`:

`NORMAL → PRESSURE_SAG → RECOVERY` with `production_inhibited() = False`

Restored Issue #107 story:

`NORMAL → DEGRADING → LOW_PRESSURE_WARNING → UNDERSUPPLY → RECOVERY`

Causal chain: compressor degrades → pressure falls → low-pressure warning →
UNDERSUPPLY deterministic micro-stop → production/FG freeze → recovery.

Capper files unchanged vs `cced390`:

- `src/virtual_factory/workspaces/capper_degradation.py`
- `configs/workspaces/bottled-water-dday/scenarios/capper_degradation.contract.yaml`
- `configs/workspaces/bottled-water-dday/scenarios/capper_degradation.runtime.yaml`
- `tests/test_dday_b5_capper_scenario.py`

---

## Default-demo proof

| t | compressor | air_pressure | total | good | fg | capper |
|---|---|---|---|---|---|---|
| 150 | NORMAL | 6.4 | — | — | — | INTERMITTENT_STOP |
| 240 | DEGRADING | 6.4 | 9 | 2 | 2 | RECOVERY |
| 264 | LOW_PRESSURE_WARNING | 6.1 | 10 | 3 | 3 | RECOVERY |
| 284 | UNDERSUPPLY | 5.8 | 11 | 4 | 4 | RECOVERY |
| 304 | RECOVERY | 5.6 | 11 | 4 | 4 | RECOVERY |

UNDERSUPPLY freezes counts and FG. FG receipts equal good throughout.
One low-pressure alarm, no compressor downtime pair.

---

## Tests and smokes

| Scope | Result |
|---|---|
| C01 compressor tests | 10/10 PASS |
| Capper tests (unchanged helper) | PASS |
| B3 + B4 files | PASS |
| Full suite | **1740/1740 PASS**, exit 0 |
| SMOKE-BW-B5 | PASS |
| SMOKE-BW-FACTORY | PASS |
| SMOKE-BW-UI | PASS |
| SMOKE-BW | PASS |

---

## Governance

- **Merge NOT authorized.** No merge performed.
- **No B6 started.**
- Issue #108 / #107 / PR #101 are the report surfaces requested by SA.

Evidence: `.ai-harness/sa-review/evidence/DDAY-B5-C01/`
Visuals: `.ai-harness/sa-review/evidence/DDAY-B5/10-visual-*.png`
Report: `.ai-harness/sa-review/reports/DDAY-B5-C01.md`
