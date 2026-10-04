# DDAY-B4-C01 — 04. Scope audit

**Machine evidence:** [`implementation.patch`](./implementation.patch),
[`scope-contract-c01-baseline.json`](./scope-contract-c01-baseline.json).

## Complete C01 change set (vs the C01 baseline `0f9606b`)

Implementation / restore / tests (before this evidence pack):

```
M  .ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py      (restore to 23b6208)
M  .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py (restore to 23b6208)
A  .ai-harness/sa-review/evidence/DDAY-B4-C01/smoke_unmet_water.py
A  .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_ui.py
A  .ai-harness/tasks/DDAY-B4-C01.json
M  src/virtual_factory/workspaces/bottled_water.py
M  tests/test_dday_b4_bottled_water_factory.py
```

7 files, +719 / −10 (implementation commits). Evidence/report/inbox files in
this pack are additional C01-owned artifacts.

| SA-allowed path | Used |
|---|---|
| `src/virtual_factory/workspaces/bottled_water.py` | yes — pending ledger + published unmet/request |
| `tests/test_dday_b4_bottled_water_factory.py` | yes — 3 C01 tests; B4-11 identities strengthened |
| B3 `generate_evidence.py` | yes — restored exactly to 23b6208 |
| B3 `smoke_bottled_water_ui.py` | yes — restored exactly to 23b6208 |
| B4-owned evidence/tests | yes — `evidence/DDAY-B4/smoke_bottled_water_ui.py` |
| `.ai-harness/tasks/DDAY-B4-C01.json` | yes |
| `.ai-harness/sa-review/evidence/DDAY-B4-C01/` | yes |
| `.ai-harness/sa-review/reports/DDAY-B4-C01.md` | yes |
| `.ai-harness/sa-review/CURRENT.md` | yes |

**Not modified:** `line_runtime.py`, `demo_controller.py`, `ui/api.py`,
`bottled_water_demo.js/.html/.css`, `core/`, `telemetry/`, `protocols/`,
`scenarios/`, `validate_report_consistency.py`, `derive_status.py`,
`PM-EXECUTION-CONTRACT.md`.

## Allowlist verification

| Check | Baseline | Result |
|---|---|---|
| Harness allowlist diff | `origin/main` (`f5261c8`) | `FILE VALIDATION PASSED (113 files)`, exit 0 |
| C01-scope diff | C01 baseline (`0f9606b`) | `FILE VALIDATION PASSED (7 files)`, exit 0 |

No forbidden path was touched. No merge. No B5 work.
