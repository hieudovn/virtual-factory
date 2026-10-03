# DDAY-B3 — 04. Tests, regression and scope audit

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`tests_b3`, `tests_ui_regression`, `tests_full`, `static_audit`

## Tests

| Suite | Collected | Passed | Failed | Result |
|---|---|---|---|---|
| B3 acceptance tests | 23 | 23 | 0 | **PASS** |
| UI/API/runtime regression subset | 141 | 141 | 0 | **PASS** |
| Full repository suite | 1689 | 1689 | 0 | **PASS** |

Suite progression: 1647 (pre-B2) → 1664 (B2) → 1666 (B2-C01) → **1689** (B3,
+23). No pre-existing test was modified, skipped or deleted.

### Required-test mapping (Issue #104)

| ID | Requirement | Test |
|---|---|---|
| B3-1 | dedicated UI route reachable and bound to the B2 runtime | `test_b3_01_ui_route_and_static_assets_are_served`, `test_b3_01b_state_is_bound_to_the_b2_runtime_not_mocked` |
| B3-2 | all 8 frozen stations visible in correct order | `test_b3_02_all_eight_stations_in_frozen_order`, `test_b3_02b_skin_defines_distinct_artwork_for_every_station` |
| B3-3 | workspace-specific skin, no foreign vocabulary | `test_b3_03_*`, `test_b3_03b_*`, `test_b3_03c_*` |
| B3-4 | unit movement corresponds to runtime positions | `test_b3_04_occupied_stations_match_advancing_runtime_positions`, `test_b3_04b_units_progress_downstream_between_ticks` |
| B3-5 | START/PAUSE/RESUME/STOP/RESET preserve B2 semantics | `test_b3_05_start_pause_resume_stop_reset_preserve_b2_semantics`, `test_b3_05b_control_surface_exposes_only_the_allowed_operator_controls` |
| B3-6 | counts and line state track runtime facts | `test_b3_06_counts_and_state_track_the_runtime`, `test_b3_06b_projection_publishes_no_calculated_kpi` |
| B3-7 | Inspection PASS/FAIL/reject observable without manual disposition | `test_b3_07_inspection_pass_is_observable`, `test_b3_07b_inspection_failure_and_reject_are_observable`, `test_b3_07c_event_window_covers_a_whole_production_cycle` |
| B3-8 | station/unit selection opens useful context, read-only | `test_b3_08_*`, `test_b3_08b_*`, `test_b3_08c_*` |
| B3-9 | no B4/B5/B6/B7 implementation mixed in | `test_b3_09_no_later_slice_implementation_in_the_skin`, `test_b3_09b_api_exposes_no_later_slice_endpoint` |
| B3-10 | relevant UI/API/runtime regression passes | `test_b3_10_*`, `test_b3_10b_*` + the regression subset above |
| B3-11 | full suite passes / flaky failure disclosed and rerun green | full suite 1689/0 failed; disclosure below |

### Smoke checks (both required, both effective PASS)

```
python .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py   -> 45/45 claims, exit 0
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py      -> exit 0 (B2 runtime unchanged)
```

`SMOKE-BW-UI` starts the real app on a real socket and drives it over real HTTP:
page and assets, state binding, frozen route, control semantics, inspection
PASS + reject, read-only selection, and the isolation scan.

## Pre-existing flaky test — disclosure (B3-11)

`tests/test_demo_composition.py::TestReset::test_reset_creates_fresh_configs`
asserts that `id()` values of per-context config objects are disjoint before and
after `reset()`. `id()` is a memory address and the old objects become
unreachable, so CPython may reuse those addresses; the assertion is not
guaranteed.

- **Observed:** it failed once during evidence generation (junit recorded
  `assert False where False = <built-in method isdisjoint …>`) while the full
  suite passed in the same run, and the subset passed when re-run (141/141).
- **Root cause demonstrated deterministically** by
  [`flaky_reset_disclosure.py`](./flaky_reset_disclosure.py) /
  [`flaky-reset-disclosure.txt`](./flaky-reset-disclosure.txt): `id()` reuse is
  demonstrable, so disjointness cannot be asserted.
- **Scope:** `tests/test_demo_composition.py` is outside the B3 allowlist, and
  Issue #104 explicitly says *"do not fix the unrelated flaky reset test … inside
  B3"*. It was therefore neither modified nor worked around.
- **Acceptance:** the full suite passes (1689/1689) and the exact-head CI run is
  green, satisfying B3-11.

## Scope audit

| SA-allowed path (Issue #104) | Used |
|---|---|
| `src/virtual_factory/ui/static/` | yes — 3 new workspace assets |
| `src/virtual_factory/ui/api.py` | yes — Bottled Water endpoints only |
| `src/virtual_factory/assembly/demo_controller.py` | **not needed, not modified** |
| relevant `tests/` | yes — 1 new module |
| `.ai-harness/tasks/DDAY-B3.json`, evidence/report/CURRENT | yes |

| Forbidden / out of scope | Status |
|---|---|
| B2 line semantics (`line_runtime.py`) | unmodified — B2 smoke re-run green |
| Existing TIPA ASSY UI assets (`assy_demo.*`, `index.html`, `app.js`) | unmodified |
| `ui/runtime_service.py`, `core/`, `telemetry/`, `protocols/`, `scenarios/` | unmodified |
| Capper degradation (B5) | not implemented — verified absent from the skin |
| Water Treatment / Utilities / Warehouse (B4) | not implemented — verified absent |
| PlantOS integration / MQTT redesign (B6), deployment (B7) | not implemented — verified absent |
| OEE / KPI calculation | none — verified by test and by projection shape |
| Manual MES/operator workflows | none — exactly 5 operator controls, no decision surface |
| Flaky reset test / PR-state normalization debt | not touched (explicitly excluded) |

Later-slice terms scanned in the skin (`degradation`, `degrading`,
`water treatment`, `utilities`, `warehouse`, `mqtt`, `opcua`, `plantos`,
`dockerfile`): **none present**. Allowlist diffs:
`verify_changed_files.py` vs `origin/main` and vs the B3 baseline both PASS.
