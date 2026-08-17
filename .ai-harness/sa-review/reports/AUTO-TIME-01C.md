# AUTO-TIME-01C — SA Review Report

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01C` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline (authorized from 01B) | `52d3fb9171eb4d97d561ff8ddcc071554e0acab9` |
| Head (implementation under review) | `4e12239be6d71977780d73fc762a47096672e5b6` |

## Changed files

- `src/virtual_factory/assembly/line_runtime.py` — `DwellPerformance` immutable
  dataclass; `_dwell_performance` field + `dwell_performance` property; persist
  last-dwell metrics in `execute_dwell()`; deterministic bottleneck driver;
  reset restores neutral metrics.
- `src/virtual_factory/assembly/operation_execution.py` — `to_dict()` now emits
  `timing` (`TimingSample.to_dict()` or `null`).
- `src/virtual_factory/assembly/demo_snapshot.py` — `AssyDemoSnapshot` +
  `ActiveOperationView` extended (dwell metrics + `work_duration_s`/`timing`).
- `.ai-harness/schemas/operation-execution.schema.json` — additive optional /
  nullable `timing` (`$defs.timingSample`, `timingSubActionSample`).
- `tests/test_ops02_schema_contract.py` — `base_payload` + ActiveOperationView
  exact-key set updated.
- `tests/test_quality_records_projection.py` — snapshot exact-key set updated
  with additive metrics.
- `tests/test_auto_timing_snapshot.py` — new focused suite.
- `.ai-harness/tasks/AUTO-TIME-01C.json` — task contract (new).

Forbidden paths untouched: `station_contracts.py`, `demo_composition.py`,
`auto_timing.py`, `configs/plants/tipa_assy_demo.yaml`.

## Metric definitions

```text
actual_dwell_s       = actual dwell chosen for the last executed dwell
dwell_overrun_s      = max(0, actual_dwell_s − nominal_dwell_s)
remaining_i          = max(0, op.work_duration_s − elapsed_i_before_dwell)
driver_station       = unresolved occupied station with maximum remaining_i
bottleneck_station_id = driver_station  only if max_remaining > nominal_dwell_s
                        else ""
bottleneck_duration_s = frozen effective op.work_duration_s of the driver
                        (not sum of all stations), else 0.0
```

`bottleneck_duration_s` means the frozen effective `op.work_duration_s` of the
station that caused the overrun, not a sum of all station durations.

## Tie rule

Deterministic: scan `max_remaining` in **configured conveyor position order**
(`self.conveyor.positions`); the first position with the maximum remaining is
the driver. No random, no dictionary ordering. Tested: AP01 vs AP02 tie → AP01.

## Serialization shape

```json
"timing": null
```
or
```json
"timing": {
  "profile_id": "AP05_AUTO_V1",
  "timing_behavior": "VARIABLE",
  "nominal_duration_s": 90.0,
  "effective_duration_s": 87.4,
  "sub_actions": [
    {"id": "a", "policy": "normal", "nominal_duration_s": 60.0,
     "effective_duration_s": 57.4, "mean_s": 60.0, "stddev_s": 6.0,
     "min_s": 48.0, "max_s": 78.0}
  ]
}
```

Uses `TimingSample.to_dict()` (no duplicated serialization logic). Optional:
MANUAL/ASSISTED and AUTO no-profile fallback emit `null`. `work_duration_s`
remains the authoritative scalar.

## Snapshot example

```json
"nominal_dwell_s": 120.0,
"actual_dwell_s": 135.0,
"dwell_overrun_s": 15.0,
"bottleneck_station_id": "AP05",
"bottleneck_duration_s": 135.0
```

Active operations now carry `work_duration_s` and `timing` (detached dict).
`positions[]` remains the authoritative physical occupancy.

## Schema impact

- `operation-execution.schema.json`: `timing` added as optional nullable
  `anyOf [null, timingSample]`; `$defs.timingSample` + `timingSubActionSample`
  with strict `additionalProperties: false`; existing `additionalProperties`
  rules preserved.
- Old payloads without `timing` remain valid (field optional). Malformed
  `timing` payloads fail closed.
- No snapshot JSON schema exists; no unrelated schema changed.

## Tests / Results

| Suite | Result |
|---|---|
| `tests/test_auto_timing_snapshot.py` (new) | **15 passed** |
| Full relevant set (all 01A/01B/01C + assy/ops/quality/demo/config suites) | **471 passed, 2 failed** |

The 2 failures are the same **pre-existing** failures documented in AUTO-TIME-01A
(verified on baseline; neither touches 01C code):

- `test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`
- `test_ops04_c01.py::TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

No new regressions. Two exact-key tests were updated in-scope to include the
authorized additive fields (`test_ops02_schema_contract.py::case10`,
`test_quality_records_projection.py::test_existing_keys_unchanged`).

## Deviations / Known issues

- `simulation_time_multiplier` remains dead config (out of scope, untouched).
- Two pre-existing test failures reproduced on baseline and documented exactly
  (see above).
- `OperationExecution.timing` is runtime + serialized now; no snapshot schema
  exists to update.

## STOP conditions

None triggered: metric computation required no dwell-semantics change from 01B;
snapshot construction is side-effect free (no re-sample); timing serialization
required only the one additive operation-execution schema; no new regressions
outside the documented pre-existing failures.

## Next-step recommendation (not self-authorization)

AUTO-TIME-01D — tests/evidence consolidation and full gate, or proceed to
M6-INT-01 (MES integration) only under separate SA authorization.
