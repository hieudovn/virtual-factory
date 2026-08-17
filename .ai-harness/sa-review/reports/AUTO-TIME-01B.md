# AUTO-TIME-01B — SA Review Report

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01B` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline (authorized from 01A) | `68cd7f1990cbe93a88338568e4474bb90520413a` |
| Head (implementation under review) | `52d3fb9171eb4d97d561ff8ddcc071554e0acab9` |

## Exact changed files

- `src/virtual_factory/assembly/auto_timing.py` — added `parse_timing_config`
  (single parse path from an already-loaded mapping); `load_auto_timing_config`
  now delegates to it.
- `src/virtual_factory/assembly/operation_execution.py` — added frozen
  `timing: Optional[TimingSample]` provenance field (not serialized).
- `src/virtual_factory/assembly/line_runtime.py` — timing config fields on
  `AssyLineConfig`; `load_assy_config_from_yaml` parses timing via
  `auto_timing.parse_timing_config`; isolated `TimingResolver`; op creation
  before dwell sizing; frozen-duration dwell semantics; reset re-seeds resolver.
- `src/virtual_factory/assembly/demo_composition.py` — per-sub-line derived
  seed (`base_seed + ordinal`).
- `tests/test_auto_timing_runtime.py` — new focused runtime suite.
- `.ai-harness/tasks/AUTO-TIME-01B.json` — task contract (new).

Forbidden paths untouched: `demo_snapshot.py`, `station_contracts.py`,
`.ai-harness/schemas/`, `configs/plants/tipa_assy_demo.yaml`.

## Exact runtime timing path after change

```text
execute_dwell()
  ├─ for each occupied unresolved position:
  │    _ensure_operation_for_position(pos, wip_id)
  │      ├─ locate contract
  │      ├─ resolve mode once
  │      ├─ if AUTO and profile exists: resolve TimingSample once → freeze
  │      │     op.work_duration_s = sample.effective_duration_s
  │      │     op.timing = sample
  │      ├─ else: op.work_duration_s = contract.work_duration_s (legacy fixed)
  │      └─ create op via OperationRegistry.start() (state READY, no domain action)
  ├─ max_remaining = max over positions of
  │     max(0, op.work_duration_s − elapsed)
  ├─ actual_dwell = max(nominal_dwell, max_remaining)
  └─ advance elapsed by actual_dwell → _advance_operation() (existing lifecycle)
```

## Operation creation vs dwell sizing

Operation creation now occurs **before** `max_remaining` / `actual_dwell` is
calculated. The helper `_ensure_operation_for_position` performs no domain
action and does not advance state past READY. This satisfies the SA invariant:
"the active OperationExecution and its frozen effective timing MUST exist before
max_remaining / actual_dwell is calculated."

Acceptance case verified by test:

```text
nominal dwell = 120, legacy AP05 = 90, sampled AP05 = 135
→ first active dwell = 135, AP05 completes in that dwell
  (NOT 120 followed by another 120)
```

## Source-of-truth decision

- `station_durations` → legacy/nominal source used to build contracts.
- At op creation the duration is frozen on `OperationExecution.work_duration_s`.
- `op.work_duration_s` is the single runtime truth for `max_remaining` and
  `work_done` gating. `self.config.station_durations` is no longer re-read once
  an active op exists (fallback only for the safety path where no op exists).

## RNG / sub-line strategy

- Each `AssyLineRuntime` owns an isolated `TimingResolver` seeded from
  `config.random_seed`; no global `random`.
- `AssyDemoComposition` derives a stable per-sub-line seed:
  `base_seed + ordinal` (ordinal = sub-line index, stable YAML order). No
  reliance on Python's salted `hash()`.
- Sub-line streams are structurally uncoupled (each context owns its own
  resolver).

## Reset evidence

- `AssyLineRuntime.reset()` rebuilds the resolver from `config.random_seed`.
- Test verifies: run → capture first AUTO VARIABLE sample → `reset()` → same
  first sample.
- DETERMINISTIC mode does not consume RNG draws (no dependence on draw state).

## Test results

| Suite | Result |
|---|---|
| `tests/test_auto_timing_runtime.py` (new) | **17 passed** |
| `test_auto_timing, test_assy_line, test_ops02_operation_execution, test_ops02_schema_contract, test_auto_equiv_01, test_manual_e2e_01, test_ops04_c01, test_quality` | **225 passed, 1 failed** |
| `test_demo_composition, test_ops03_contract_loader, test_ops03_interaction, test_sub_line_identity, test_config_validation, test_quality_records_projection, test_demo_overview, test_assy_demo, test_sim_val_01_feed` | **214 passed, 1 failed** |

The 2 failures are the same **pre-existing** failures documented in AUTO-TIME-01A
(verified on baseline by reverting the YAML change; neither touches 01B code):

- `test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`
- `test_ops04_c01.py::TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

No new regressions.

## Retry / AP11 confirmation

- **Retry/reinspect (AP06/AP08):** same `OperationExecution` reused, station
  elapsed reset, transition back to `AWAITING_DECISION`, no re-entry to WORKING,
  no new timing sample. Verified by test (same `execution_id`, same `timing`
  object across retry).
- **AP11:** AUTO profile covers final-QC WORKING duration only. QC →
  `AWAITING_COMPLETION` → RELEASE remains intact. Verified by test
  (`CONFIRMED` then `RELEASED`).

## Deviations

None beyond the two pre-existing test failures reproduced on baseline and
documented above. `operation_execution.to_dict()` is unchanged (timing
provenance is runtime-only until 01C), so no schema change was needed.

## Known issues

- `simulation_time_multiplier` remains dead config (out of scope, not
  activated/removed).
- Two pre-existing test failures unrelated to this slice (see above).

## STOP conditions

None triggered: no domain action required before dwell sizing; lifecycle
semantics preserved; MANUAL/AUTO equivalence preserved beyond timing; reset
reproducible; sub-line streams deterministic; no broad schema change required.

## Next-step recommendation (not self-authorization)

AUTO-TIME-01C — snapshot/bottleneck metrics: persist `actual_dwell_s`,
`dwell_overrun_s`, `bottleneck_station_id`, `bottleneck_duration_s`, and expose
the frozen `timing` object on the OperationExecution snapshot/schema.
