# DDAY-B4-C01 — 03. Tests and regression

## Focused C01 tests

| Test | Result |
|---|---|
| `test_c01_unmet_water_demand_is_preserved_and_later_satisfied` | PASS |
| `test_c01_starved_fill_completions_keep_the_request_ledger` | PASS |
| `test_c01_accepted_b3_evidence_files_match_b3_baseline` | PASS |

JUnit: [`junit-c01.xml`](./junit-c01.xml)

Existing B4 water tests (`b4_11`, `b4_11b`, `b4_12`, `b4_12b`) remain PASS.
B4-11 now also asserts `unmet == 0` and `request == draw + unmet == product / efficiency`
on the nominal trajectory (strengthened, not relaxed).

B4 file: 30/30 PASS. JUnit: [`junit-c01-b4.xml`](./junit-c01-b4.xml)

## Smokes

| ID | Command | Result |
|---|---|---|
| SMOKE-BW-UNMET | `python .ai-harness/sa-review/evidence/DDAY-B4-C01/smoke_unmet_water.py` | PASS |
| SMOKE-BW-FACTORY | `python .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_factory.py` | PASS |
| SMOKE-BW-UI | `python .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_ui.py` | PASS |
| SMOKE-BW | `python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py` | PASS |

## Full suite

`python -m pytest -q` → **1719 passed, 0 failed**, exit 0.

Suite progression: 1647 → 1664 (B2) → 1666 (B2-C01) → 1689 (B3) → 1716 (B4) → **1719 (B4-C01)**.

Delta is exactly the three new C01 tests. No pre-existing test was deleted or
weakened. JUnit: [`junit-c01-full.xml`](./junit-c01-full.xml)
