# AUTO-TIME-01A — SA Review Report

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01A` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline (authorized) | `33cb2b7` |
| Head (implementation under review) | `68cd7f1990cbe93a88338568e4474bb90520413a` |

## Changed files

- `src/virtual_factory/assembly/auto_timing.py` — new module (timing domain + resolver + config parsing)
- `configs/plants/tipa_assy_demo.yaml` — additive `simulation.timing_behavior` / `random_seed` + `auto_timing_profiles`
- `tests/test_auto_timing.py` — new focused test suite
- `.ai-harness/tasks/AUTO-TIME-01A.json` — task contract (new)
- `docs/reports/AUTO-TIME-00_SA_REVIEW_REPORT.md` — prior gate report (docs only, committed alongside)

Forbidden paths untouched: `line_runtime.py`, `operation_execution.py`,
`station_contracts.py`, `demo_snapshot.py`, `.ai-harness/schemas/`.

## Implementation

Pure domain + config parsing, in isolation. No runtime wiring.

- `TimingBehavior` (`DETERMINISTIC`, `VARIABLE`)
- `DurationPolicyType` (`FIXED`, `NORMAL`)
- `DurationPolicy` — fail-closed validation (FIXED: `seconds > 0`; NORMAL:
  `mean_s > 0`, `stddev_s >= 0`, `min_s > 0`, `max_s >= min_s`,
  `mean_s ∈ [min_s, max_s]`)
- `SubActionTiming`, `AutoTimingProfile` (non-empty `profile_id`, ≥1 sub-action,
  unique non-empty sub-action ids)
- `TimingSubActionSample`, `TimingSample` (frozen; effective duration = exact
  sum of resolved sub-action durations; nominal = sum of nominal sub-actions)
- `TimingResolver` — isolated `random.Random(seed)`; never global random state
  - DETERMINISTIC: FIXED → `seconds`; NORMAL → `mean_s` (no draw)
  - VARIABLE: FIXED → `seconds`; NORMAL → seeded bounded normal clamped to
    `[min_s, max_s]`
- Config parsing: `parse_timing_behavior` (default DETERMINISTIC),
  `parse_random_seed` (default 42), `parse_duration_policy`,
  `parse_auto_timing_profiles`, `check_profiles_against_positions`,
  `load_auto_timing_config`.

## Config example (additive)

```yaml
simulation:
  time_multiplier: 1.0
  timing_behavior: DETERMINISTIC
  random_seed: 42

auto_timing_profiles:
  AP03:
    profile_id: AP03_AUTO_V1
    sub_actions:
      - id: mechanical_check
        duration: { type: fixed, seconds: 25 }
      - id: checklist_execution
        duration: { type: normal, mean_s: 15, stddev_s: 3, min_s: 10, max_s: 25 }
      - id: confirmation
        duration: { type: fixed, seconds: 5 }
```

Profiles provided for AP03, AP04, AP05, AP06, AP08, AP11 (AP11 final QC only).
All values `DEMO_SYNTHETIC — NOT TIPA-CONFIRMED`. Nominal profile sums align
with `station_durations` (45/60/90/60/30/30) for clean future fallback
equivalence.

## Invariants

- Same seed / profile / call sequence → same samples (reproducible).
- Different seed → different NORMAL realization (deterministic under MT19937).
- FIXED never varies under VARIABLE.
- DETERMINISTIC NORMAL always equals `mean_s`.
- VARIABLE NORMAL clamped to `[min_s, max_s]`.
- Malformed config fails closed (no silent repair).
- No profile → defaults (`DETERMINISTIC`, seed 42, `{}`) — backward compatible.
- Runtime loader `load_assy_config_from_yaml` unchanged and still parses the
  additive YAML (new keys ignored).

## Tests / Results

| Suite | Result |
|---|---|
| `tests/test_auto_timing.py` | **29 passed** |
| `test_assy_line, test_config_validation, test_ops02_operation_execution, test_ops02_schema_contract, test_ops03_contract_loader, test_auto_equiv_01, test_manual_e2e_01, test_sub_line_identity` | **173 passed** |
| `test_assy_demo, test_demo_composition, test_demo_overview, test_quality_records_projection, test_ops03_interaction, test_ops04_c01, test_quality, test_sim_val_01_feed` | **237 passed, 2 failed** |

The 2 failures are **pre-existing** (verified by reverting the YAML change to
baseline and re-running — identical failures):

- `test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`
- `test_ops04_c01.py::TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

Neither touches code or config modified by AUTO-TIME-01A.

## Deviations

1. **Harness preflight** reported failure on:
   - untracked files (pre-existing `docs/ui/evidence/.../EV1_frame_b_clean.png`
     from task I09, plus new AUTO-TIME-01A artifacts), and
   - `expected_base_sha` vs `origin/main` comparison — the harness compares the
     contract baseline against `origin/main`, but this task's authorized
     baseline is the feature-branch head.

   Compensating evidence (direct git): `HEAD` =
   `origin/docs/m6-s01-tipa-baseline` = `33cb2b7…`, matching the authorized
   baseline. Recorded as a harness workflow limitation, not a real baseline
   drift.
2. `pytest`'s `tmp_path` fixture fails in this Windows environment
   (`PermissionError` on the temp dir). The "no profiles → backward-compatible"
   test was written in-memory (no file fixture) to remain deterministic.

## Known issues

- `simulation_time_multiplier` remains dead config (explicitly not activated /
  removed / repurposed per task scope).
- Two pre-existing test failures unrelated to this slice (see above).

## STOP conditions

None triggered:

- Baseline matched (`33cb2b7`) ✓
- No runtime semantic changes required ✓
- Backward compatibility preserved (runtime loader ignores additive keys) ✓
- Deterministic sampling reproducible ✓
- Malformed config fails closed ✓

## Next-step recommendation (not self-authorization)

AUTO-TIME-01B — wire frozen AUTO timing at operation creation **before** dwell
duration is calculated. Per the SA correction in AUTO-TIME-00: ensure the active
`OperationExecution` with frozen timing exists before `max_remaining` is
computed, so the first dwell uses the sampled effective duration (e.g. AP05=135
→ first dwell 135s, not 120s then 120s).
