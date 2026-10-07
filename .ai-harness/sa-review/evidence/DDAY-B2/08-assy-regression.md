# DDAY-B2 — 08. Legacy regression (T13)

**Claim:** the reused foundation's legacy behaviour is preserved. The extension
is additive/profile-gated; the legacy path is byte-for-byte equivalent.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`tests_regression`, `junit-dday-b2-regression.xml`

## Commands and results

| Run | Command | Collected | Passed | Failed | Result |
|---|---|---|---|---|---|
| B2 acceptance (T01–T12) | `python -m pytest -q tests/test_dday_b2_bottled_water_line.py` | 17 | 17 | 0 | **PASS** |
| Legacy regression subset (T13) | 23 legacy files — see below | 575 | 575 | 0 | **PASS** |
| Full suite | `python -m pytest -q` | 1664 | 1664 | 0 | **PASS** |

Baseline before any B2 change: **1647 passed**. After B2: **1664 passed**
(1647 + 17 new). No pre-existing test was modified, deleted or skipped.

## Legacy regression subset (23 files, 575 tests)

```
tests/test_assy_line.py                 tests/test_assy_demo.py
tests/test_demo_composition.py          tests/test_demo_overview.py
tests/test_quality.py                   tests/test_ops02_operation_execution.py
tests/test_ops02_schema_contract.py     tests/test_ops03_interaction.py
tests/test_ops03_contract_loader.py     tests/test_ops04_c01.py
tests/test_auto_equiv_01.py             tests/test_auto_timing.py
tests/test_auto_timing_runtime.py       tests/test_auto_timing_snapshot.py
tests/test_assy_mes_bridge_v1.py        tests/test_demo_assy_mes_v1.py
tests/test_assy_mes_03_evidence.py      tests/test_m6_int_01.py
tests/test_sim_val_01_feed.py           tests/test_sub_line_identity.py
tests/test_vf_contract_finality_01.py   tests/test_manual_e2e_01.py
tests/test_m3_s03_tipa.py
```

These cover exactly the surfaces B2 refactored: the indexed line runtime and its
dwell/index semantics, station contracts and capabilities, the operation state
machine, quality observation/decision/release, auto timing, the six-sub-line
composition, MES/observation bridges and the demo snapshot.

## Why the legacy behaviour cannot have drifted

| Refactor | Guard |
|---|---|
| `build_line_station_contracts(config)` replaced a direct `build_default_assy_contracts(...)` call | For a non-generic profile it returns `build_default_assy_contracts(dict(config.station_durations))` — the identical call, unchanged function |
| `_quality_spec(pos)` replaced the raw station-map lookup | For a station without a configured spec it returns the same `(station_key, check_type)` plus `self.config.quality.get(station_key)` and `on_fail="hold"` — the same objects the old code read |
| `pos == "AP11"` → `contract.capabilities.final_disposition` | `AP11` is the only legacy contract with `final_disposition=True`; behaviour is identical for every legacy station |
| `_QUALITY_OPERATION_RESULT.get(pos, TEST_COMPLETE)` → `.get(pos) or <check-type fallback>` | The legacy station ids are all present in the map, so the fallback is unreachable for the legacy profile |
| Empty-carrier handling added in `execute_dwell()` | `place_empty_carrier()` has no caller anywhere in the repository, so no legacy line can contain an empty carrier; the new branch is unreachable for legacy runs |
| `_count_completed_unit()` / counting | Guarded by `config.is_generic_profile`; returns `[]` immediately for the legacy profile |
| New `AssyLineConfig` fields, `WipLifecycle.REJECTED`, new `AssyWipState` fields | All have defaults, and no legacy code path reads them |
| Counting uses `ws.unit_sequence`, which is only set by `produce_unit()` | Legacy WIPs keep `unit_sequence == 0`, so the new `elif` never fires for them |

The entire legacy regression suite passing unmodified is the empirical proof of
these claims.
