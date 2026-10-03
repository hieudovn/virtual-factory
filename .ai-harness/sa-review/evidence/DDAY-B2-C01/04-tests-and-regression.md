# DDAY-B2-C01 — 04. Tests and regression

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`tests_b2`, `tests_harness`, `tests_regression`, `tests_full`; JUnit XMLs
[`junit-c01-b2.xml`](./junit-c01-b2.xml),
[`junit-c01-harness.xml`](./junit-c01-harness.xml),
[`junit-c01-regression.xml`](./junit-c01-regression.xml),
[`junit-c01-full.xml`](./junit-c01-full.xml).

| Suite | Collected | Passed | Failed | Result |
|---|---|---|---|---|
| B2 acceptance + C01 tests | 19 | 19 | 0 | **PASS** |
| Harness tests (new + existing validator tests) | 9 | 9 | 0 | **PASS** |
| Legacy regression subset | 575 | 575 | 0 | **PASS** |
| Full repository suite | 1666 | 1666 | 0 | **PASS** |

Progression of the suite across the program:

| Point | Tests passing |
|---|---|
| Before DDAY-B2 | 1647 |
| After DDAY-B2 (+17) | 1664 |
| After DDAY-B2-C01 (+2) | **1666** |

No pre-existing test was modified, skipped, deleted or weakened.

## New tests in this slice

| Test | What it proves |
|---|---|
| `test_c01_a_generic_outward_lifecycle_is_domain_neutral` | neutral status at entry / in-progress / station completion / route completion / reject, with a case-insensitive leak scan at every stage |
| `test_c01_a_legacy_lifecycle_semantics_are_unchanged` | legacy `introduce_to_assy()` still yields `in_assy`; `IN_LINE` is additive, not a rename |

## Strengthened test

`test_t12_no_legacy_domain_leakage_in_outward_surfaces` now matches
case-insensitively against semantic variants (`in_assy`, `PRE-ASSY`,
`ASSY-SLxx`, `TIPA`, `SSO2`, `RSO2`, `APxx`, `AP05_JAM`) instead of exact
uppercase literals. Before the fix this test fails on the entry state — that is
the regression guard the SA asked for.

## New harness tests

`.ai-harness/tests/test_gate_report_provisional.py` — see evidence 02.
Run by CI in the `Harness — self-tests` step and reproducible with:

```
python -m pytest .ai-harness/tests/ -q
```

## Smoke checks (both required, both effective PASS)

```
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python .ai-harness/sa-review/evidence/DDAY-B2-C01/smoke_semantic_isolation.py
```

`SMOKE-BW` is the DDAY-B2 runtime regression (unchanged). `SMOKE-BW-ISO` proves
the semantic isolation across all five generic states plus legacy preservation;
both are registered in the C01 contract's `required_smoke_checks` and recorded in
the gate evidence as `effective_result = PASS`.
