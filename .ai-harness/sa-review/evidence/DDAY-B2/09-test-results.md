# DDAY-B2 — 09. Test results

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `tests_b2`,
`tests_regression`, `tests_full`; JUnit XML:
[`junit-dday-b2.xml`](./junit-dday-b2.xml),
[`junit-dday-b2-regression.xml`](./junit-dday-b2-regression.xml),
[`junit-dday-b2-full.xml`](./junit-dday-b2-full.xml).

Additive test module: [`tests/test_dday_b2_bottled_water_line.py`](../../../../tests/test_dday_b2_bottled_water_line.py).

| Suite | Collected | Passed | Failed | Result |
|---|---|---|---|---|
| B2 acceptance (T01–T12) | 17 | 17 | 0 | **PASS** |
| Legacy regression subset (T13) | 575 | 575 | 0 | **PASS** |
| Full suite | 1664 | 1664 | 0 | **PASS** |

Baseline before B2: 1647 passed. Delta: **+17** (the new module). No pre-existing
test was modified, skipped, xfailed or removed.

## Required-test mapping (Issue #102)

| ID | Requirement | Test |
|---|---|---|
| T01 | exact 8-station route/order | `test_t01_exact_eight_station_route_and_order` |
| T02 | automatic unit progression | `test_t02_automatic_unit_progression_without_manual_actions` |
| T03 | deterministic replay | `test_t03_deterministic_replay_same_config_seed_initial_state` |
| T04 | PASS reaches good downstream completion | `test_t04_inspection_pass_reaches_good_downstream_completion` |
| T05 | FAIL at Inspection rejects and does not count good | `test_t05_inspection_fail_rejects_and_never_counts_good` |
| T06 | count invariant | `test_t06_count_invariant` (6 parametrised cases) |
| T07 | START | `test_t07_start_begins_automatic_progression` |
| T08 | PAUSE freezes progression | `test_t08_pause_freezes_progression_and_preserves_state` |
| T09 | RESUME continues preserved state | `test_t09_resume_continues_from_preserved_state` |
| T10 | STOP is controlled stop, not FAULT | `test_t10_stop_is_controlled_stop_not_fault` |
| T11 | RESET restores initial state + deterministic rerun | `test_t11_reset_restores_initial_state_and_deterministic_rerun` |
| T12 | no legacy-domain leakage in outward state | `test_t12_no_legacy_domain_leakage_in_outward_surfaces` |
| T13 | relevant legacy regression | legacy suite, reported separately in evidence 08 |

17 tests cover T01–T12 (T06 is parametrised over six scenario/cycle
combinations).

## Required smoke check

Command (also registered as the contract's `required_smoke_checks` entry
`SMOKE-BW`):

```
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
exit_code=0
```

The smoke drives the real runtime through `DemoController` and prints each claim
with a PASS/FAIL marker; it exits non-zero if any claim fails. Covered:
`START → unit progression → Inspection result → good/reject → downstream
completion`, `PAUSE → no progression`, `RESUME → continues`, `STOP → controlled`,
`RESET → known initial state`, plus deterministic replay after RESET.

## Reproducing

```
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python .ai-harness/sa-review/evidence/DDAY-B2/generate_evidence.py
python -m pytest -q
```

`generate_evidence.py` re-derives every number in this pack from a live run; it
is deterministic and safe to re-run.
