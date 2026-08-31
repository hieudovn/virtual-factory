# AUTO-TIME-00 — Codebase Audit & Implementation Plan (PM READ-ONLY REVIEW GATE)

**Repository:** `hieudovn/virtual-factory`
**Branch:** `docs/m6-s01-tipa-baseline`
**Authorized baseline:** `33cb2b7`
**Date:** 2026-08-17
**Gate type:** Read-only analysis and planning. No production code change.

---

## 0. Execution-contract record

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-00` |
| Objective | Read-only audit + implementation plan for AUTO timing profiles |
| Deliverables | PM report only (Q1–Q7, randomness audit, schema/metrics impact, test plan, risk matrix, task plan) |
| Non-deliverables | No production code, schema, config-behavior, or timing changes |
| Allowed paths | `src/`, `configs/`, `tests/`, `.ai-harness/schemas/`, docs (read-only) |
| Forbidden paths | None modified |
| Required tests | None executed (read-only gate) |
| Stop conditions | Baseline mismatch, task ambiguity, forbidden action |
| SA authorization boundary | No implementation; no merge; no next-slice start |

### Baseline verification (machine-derived)

- `git branch --show-current` → `docs/m6-s01-tipa-baseline`
- `git rev-parse HEAD` → `33cb2b7bc6f68f8ff0d8700aacd32165ebf98578` — matches authorized `33cb2b7`
- Working tree: one untracked PNG (`docs/ui/evidence/i09-p02-c03r/EV1_frame_b_clean.png`); no tracked modifications.
- **Baseline: MATCH.** No preflight blocker for a read-only gate.

### Governance note

No `.ai-harness/tasks/AUTO-TIME-00.json` contract exists yet. The attached PM prompt is the
contract of record for this gate. Creating harness artifacts is outside the read-only
allowlist, so none were written. If a formal task-contract JSON is required before
`AUTO-TIME-01`, it must be authored under separate authorization.

---

## 1. Current timing path (YAML → config → contract → OperationExecution → dwell)

```text
configs/plants/tipa_assy_demo.yaml
  station_durations: { PRE-ASSY:30, AP01:60, ..., AP11:30 }
        │ load_assy_config_from_yaml()           (line_runtime.py:170-181)
        ▼
AssyLineConfig.station_durations                 (line_runtime.py:103)
        │ __post_init__ → build_default_assy_contracts(dict(station_durations))
        ▼
StationContract.work_duration_s                  (station_contracts.py:72, 128-203)
        │ OperationRegistry.start()              (operation_execution.py:202-208)
        ▼
OperationExecution.work_duration_s               (operation_execution.py:103)   [WRITE-ONLY]
        │
        ▼  ✗ NOT read back for gating
execute_dwell()  →  required = self.config.station_durations.get(pos, 60.0)
        │            (line_runtime.py:465 max_remaining loop,
        │             line_runtime.py:488 accumulation loop)
        ▼
_advance_operation(pos, wip_id, required)        (required = config value, line_runtime.py:582)
```

---

## 2. Weaknesses found

1. **Triple duration truth.** Three copies exist:
   - `AssyLineConfig.station_durations` (config-authoritative)
   - `StationContract.work_duration_s` (copied once at runtime construction)
   - `OperationExecution.work_duration_s` (copied at op creation)
2. **Runtime reads config, not the frozen op duration.** `execute_dwell()` computes
   `max_remaining` and per-station `required` from `self.config.station_durations` in two
   places (`line_runtime.py:465`, `:488`). `OperationExecution.work_duration_s` is
   write-only — serialized into the schema but never read back for gating.
3. **`simulation_time_multiplier` is dead config.** Loaded (`line_runtime.py:197`) into
   `AssyLineConfig.simulation_time_multiplier` but never applied anywhere.
   `presentation_speed` (controller) is correctly UI-only and must stay separate.
4. **`actual_dwell` is not persisted.** Computed locally and only emitted inside trace
   detail strings (`DWELL_READY actual=…`, `DWELL_EXTENDED …`).
   `ConveyorLine.begin_dwell()/begin_operating()/_current_dwell_time_s` exist but are
   never called by `execute_dwell()` (dead code).
5. **No bottleneck metrics** on the snapshot (`demo_snapshot.py` exposes only
   `nominal_dwell_s`, `simulation_time_s`, `dwell_number`, `line_state`).

---

## 3. Architecture questions

### Q1 — Single source of duration truth

- **Authoritative at config load:** `AssyLineConfig.station_durations`.
- **Copied to:** `StationContract.work_duration_s` via `build_default_assy_contracts(...)`
  in `AssyLineRuntime.__post_init__` (`line_runtime.py:337-340`); then to
  `OperationExecution.work_duration_s` in `OperationRegistry.start()`.
- **Runtime actually reads:** `self.config.station_durations` only — in `execute_dwell()`
  twice and in `_execute_station()` (`line_runtime.py:886`).
- **Does `execute_dwell()` read config after op creation?** Yes — re-reads config every
  dwell, ignoring the op's frozen duration.
- **Dual-truth problem exists.** Verdict: real dual-truth — the op carries a duration
  that is never authoritative. This is the Q3 blocker.

### Q2 — Best injection point for AUTO sampling

**Recommendation: a dedicated `TimingResolver`, invoked at the single op-creation site**
(`_advance_operation`, `line_runtime.py:583`).

- Keep `OperationRegistry.start()` minimal and freeze the resolved duration immediately
  after creation in `_advance_operation`, **or** extend `start()` to accept an explicit
  `effective_duration_s` and `timing` payload. Both satisfy the invariant; the latter
  keeps "freeze at creation" atomic.
- **Required invariant** (must be enforced in tests):

```text
same OperationExecution → sample exactly once → freeze → every later STEP uses same sample
```

- `MANUAL` / `ASSISTED` keep the fixed `contract.work_duration_s` (no profile path).
  `AUTO` alone consults the profile. No profile → fall back to current config duration.

### Q3 — Dwell calculation compatibility (BLOCKER)

- `max_remaining` uses **config duration**, not the active `OperationExecution.work_duration_s`
  (`line_runtime.py:465`). A sampled op duration would be **ignored** by dwell.
  **This is a confirmed blocker.**
- **Minimum correction:** `execute_dwell()` must compute `required` from the frozen op
  duration for any position with an active operation, falling back to config for
  unstarted positions. Add `_effective_duration(pos, wip_id)` returning
  `op.work_duration_s` if an active op exists, else `config.station_durations[pos]`.
  Use it in both the `max_remaining` loop and the accumulation loop.

### Q4 — Retry / reinspect timing (AP06 / AP08)

- **Same OperationExecution reused:** on FAIL/NG (non-terminal),
  `submit_operation_command` calls `_reset_quality_observation(op)` and transitions the
  **same** `op` to `AWAITING_DECISION` (`line_runtime.py:725-730`). No new
  `execution_id`. `attempt_number` comes from quality history, not a new op.
- **Elapsed reset:** `_station_elapsed[station] = 0.0` on failure.
- **Does retry re-enter WORKING? No.** It jumps straight to `AWAITING_DECISION`. On the
  next dwell, `_advance_operation` sees state `AWAITING_DECISION` (not `READY`/`WORKING`)
  and auto-submits the decision **without the `work_done` duration gate**.
- **Implication for AUTO-TIME:** retry/reinspect does not re-sample and does not re-run
  the WORKING duration gate. Safest P1: timing profiles apply only to the initial
  WORKING phase; retries keep today's "one dwell to re-observe + decide" semantics and
  do **not** consume a fresh duration sample (preserves sample-once).

### Q5 — AP11 timing

- AP11 contract: `work_duration_s=30`, `normal_action=CONFIRM` (final QC),
  `required_action=RELEASE`.
- Runtime behavior (AUTO): dwell N completes final QC
  (`WORKING → AWAITING_DECISION → CONFIRM → PASS → AWAITING_COMPLETION`); dwell N+1
  executes RELEASE. `work_duration_s` gates **only the final-QC step**; **RELEASE has no
  separate time** — it consumes one full subsequent dwell.
- **Recommendation (safest P1):** `AutoTimingProfile` for AP11 covers final QC only.
  Do **not** add a new RELEASE timing stage. RELEASE stays a disposition step with no
  dedicated duration.

### Q6 — Timing model location

Place in a **new module** `src/virtual_factory/assembly/auto_timing.py`:

| Type | Home |
|---|---|
| `DurationPolicyType` (enum: `FIXED`, `NORMAL`) | `auto_timing.py` |
| `DurationPolicy` (dataclass) | `auto_timing.py` |
| `SubActionTiming` (dataclass) | `auto_timing.py` |
| `AutoTimingProfile` (dataclass) | `auto_timing.py` |
| `TimingSample` (frozen dataclass: effective duration + sub-action samples) | `auto_timing.py` |
| `TimingResolver` (profile + policy + behavior + RNG → `TimingSample`) | `auto_timing.py` |

Principles: stochastic/config logic lives **outside** `operation_execution.py`; no
AP-specific branches in the generic timing engine; `OperationExecution` gains only a
frozen `timing` field (existing `work_duration_s` repurposed as the frozen effective
duration). Config loading for profiles added in `load_assy_config_from_yaml` (additive).

### Q7 — Configuration design (backward compatible)

- `load_assy_config_from_yaml` uses `data.get(...)` everywhere, so **additive top-level
  keys are already safe**.
- Add:

```yaml
simulation:
  time_multiplier: 1.0        # existing (currently unused — flag for SA)
  timing_behavior: DETERMINISTIC
  random_seed: 42

auto_timing_profiles:
  AP05:
    profile_id: AP05_AUTO_V1
    sub_actions:
      - id: positioning
        duration: { type: fixed, seconds: 10 }
      - id: assembly
        duration: { type: normal, mean_s: 75, stddev_s: 8, min_s: 55, max_s: 105 }
```

- Semantics: no profile → AUTO falls back to current fixed duration;
  `DETERMINISTIC` → `NORMAL` uses `mean_s`, no draw; `VARIABLE` → seeded bounded
  `NORMAL` sample; all TIPA values explicitly `DEMO_SYNTHETIC`.

---

## 4. Randomness / reproducibility audit

- **Assembly runtime has no RNG today** (zero `random` usage under
  `src/virtual_factory/assembly/`).
- **Existing seeded pattern** in the discrete engine: `random.Random(run_context.random_seed)`
  (`discrete/engine.py:91`), seed default `42`, validated non-negative non-bool
  (`discrete/run_context.py:39,80-89`). **Reuse this pattern; do not reinvent.**
- Other modules use **global `random`** (`equipment/boundary.py`, `faults/fault_models.py`,
  `instrumentation/base_sensor.py`, `maintenance/event_generator.py`,
  `sensor_quality/quality_model.py`) — not seeded; do not follow that pattern.
- **RNG ownership:** per-`AssyLineRuntime` `random.Random`, seeded from a **derived
  per-sub-line seed** `random_seed + sub_line_index` (deterministic, uncoupled streams).
  The six contexts are independent runtimes created in
  `AssyDemoComposition.initialize()` (`demo_composition.py:225-262`). Derived streams
  avoid cross-sub-line coupling and avoid global `random`.
- **Reset behavior:** `AssyLineRuntime.reset()` and re-initialization must re-seed the
  RNG to reproduce the same run.
- **Invariant:** same config + same seed + same operation creation order = same sampled
  durations.

---

## 5. Snapshot / schema impact

- `OperationExecution.to_dict()` already emits `work_duration_s`, `started_at_sim_s`,
  `completed_at_sim_s` and validates against `operation-execution.schema.json`
  (`additionalProperties: false`).
- **Minimal additive field:** a nested `timing` object on `OperationExecution` (and in
  `to_dict` + schema + `ActiveOperationView`):

```json
"timing": {
  "profile_id": "AP05_AUTO_V1",
  "timing_behavior": "DETERMINISTIC",
  "nominal_duration_s": 90.0,
  "effective_duration_s": 87.3,
  "sub_actions": [
    {"id": "positioning", "policy": "FIXED", "seconds": 10.0},
    {"id": "assembly", "policy": "NORMAL", "sampled_s": 77.3,
     "mean_s": 75.0, "stddev_s": 8.0, "min_s": 55.0, "max_s": 105.0}
  ]
}
```

- Schema change is additive (new optional `timing` property; scoped
  `additionalProperties`). `test_ops02_schema_contract.py` must gain positive/negative
  cases.
- `ActiveOperationView` currently drops `work_duration_s`; add `work_duration_s` and
  `timing` to the detached projection. No large UI panel.

---

## 6. Bottleneck / dwell metrics audit

Current snapshot has only `nominal_dwell_s`, `simulation_time_s`, `dwell_number`,
`line_state`. Add to `AssyDemoSnapshot` (and `to_dict`):

- `actual_dwell_s` — last executed dwell's actual time (must be stored by
  `execute_dwell`, currently discarded).
- `dwell_overrun_s` — `max(0, actual_dwell_s − nominal_dwell_s)`.
- `bottleneck_station_id` — station whose effective remaining time drove `actual_dwell`
  above nominal (else `""`).
- `bottleneck_duration_s` — that station's effective duration (else `0.0`).

Definitions:

```text
station_effective_time      = Σ sampled sub-actions (frozen on the op)
line effective dwell        = max(nominal_dwell, slowest unresolved station's
                               effective remaining time)
dwell_overrun_s             = actual_dwell_s − nominal_dwell_s   (≥ 0)
```

**Invariant:** do **not** sum all AP durations to compute line takt.

---

## 7. Deterministic vs variable timing

Recommend a **global simulation switch** (`simulation.timing_behavior`), not per-profile:

- `DETERMINISTIC` (default acceptance): `FIXED` → fixed; `NORMAL` → `mean_s`.
- `VARIABLE`: `FIXED` → fixed; `NORMAL` → seeded bounded sample (clamp to `[min_s, max_s]`).

Matches the prompt's example, keeps the resolution path single-branch, and makes
regression scenarios D/E trivial. Per-profile override can be additive later.

---

## 8. Future implementation acceptance scenarios

| # | Scenario | Expected |
|---|---|---|
| A | all stations below takt (nominal 120, effective <120) | `actual_dwell=120`, no overrun |
| B | AP05 bottleneck (135) | `actual_dwell=135`, `overrun=15`, bottleneck=AP05 |
| C | automation improvement (AP05 135→65) | new dwell, new bottleneck verified |
| D | `NORMAL(90)` under DETERMINISTIC | always 90 |
| E | seeded VARIABLE (seed 42 vs 43) | 42 reproducible; 43 different |
| F | MANUAL/ASSISTED regression | fixed current duration retained |
| G | semantic regression | no bypass of checklist, AP04 JOIN, AP06 observe-before-result, AP08 decision, AP11 QC-before-RELEASE, HOLD |

Existing suites to extend/keep green: `test_assy_line.py` (A03 overrun),
`test_ops02_operation_execution.py`, `test_ops02_schema_contract.py`,
`test_auto_equiv_01.py`, `test_manual_e2e_01.py`, `test_ops04_c01.py`,
`test_demo_composition.py`, `test_quality.py`.

---

## 9. Risk assessment

| # | Risk | Class | Notes |
|---|---|---|---|
| 1 | Duration double source | **HIGH** | Confirmed; requires dwell to read frozen op duration |
| 2 | Dwell ignoring sampled op duration | **HIGH** | Confirmed blocker (Q3) |
| 3 | Retry/reinspect timing semantics | **MEDIUM** | Retry reuses same op, skips WORKING gate; document + test |
| 4 | Random reproducibility | **LOW** | Reuse `random.Random(seed)` pattern from discrete engine |
| 5 | Six-sub-line RNG coupling | **MEDIUM** | Use derived per-sub-line seeds |
| 6 | Reset reproducibility | **MEDIUM** | Must re-seed on reset/re-initialize |
| 7 | Schema compatibility | **MEDIUM** | Additive optional `timing`; update schema tests |
| 8 | AUTO-EQUIV regression | **HIGH** | AUTO-EQUIV excludes timing today; keep lifecycle identical |
| 9 | MANUAL-E2E regression | **HIGH** | MANUAL/ASSISTED path untouched |
| 10 | Presentation speed confusion | **LOW** | Keep `presentation_speed` UI-only; `simulation_time_multiplier` dead config flagged, not conflated |
| 11 | Performance impact | **LOW** | Sampling once per op; negligible |
| 12 | Accidental MES scope creep | **MEDIUM** | No MES, no wall-clock, no `sleep()`; STOP conditions enforce |

---

## 10. PM implementation plan (not started — for SA authorization)

- **`AUTO-TIME-01A` — timing domain + config.** New `auto_timing.py` (types + resolver);
  additive YAML loader; `DEMO_SYNTHETIC` values. Files:
  `src/virtual_factory/assembly/auto_timing.py`, `line_runtime.py` (loader only),
  `configs/plants/tipa_assy_demo.yaml`. Tests: unit tests for
  FIXED/NORMAL/DETERMINISTIC/VARIABLE + fallback. **STOP:** profile parsing failure must
  fail closed.
- **`AUTO-TIME-01B` — runtime resolution + dwell semantics.** Freeze resolved duration at
  op creation (`_advance_operation`); make `execute_dwell()` read frozen effective
  duration; re-seed RNG on reset. Files: `line_runtime.py`, `operation_execution.py`
  (optional `timing` field). Tests: scenarios A–G, retry no-resample, reset
  reproducibility. **STOP:** if dwell cannot read frozen duration, do not proceed.
- **`AUTO-TIME-01C` — snapshot + bottleneck metrics.** `actual_dwell_s`,
  `dwell_overrun_s`, `bottleneck_station_id`, `bottleneck_duration_s`; `timing` on
  op/schema/view. Files: `demo_snapshot.py`, `operation_execution.py`, schema +
  `test_ops02_schema_contract.py`. **STOP:** any schema regression.
- **`AUTO-TIME-01D` — tests/evidence.** Full gate: `test_assy_line.py`,
  `test_auto_equiv_01.py`, `test_manual_e2e_01.py` regressions + new AUTO-TIME tests;
  harness gate report. **STOP:** AUTO-EQUIV or MANUAL-E2E deviation.

---

## 11. Final evidence (read-only gate)

- Current timing path traced (YAML → config → contract → op → dwell): documented above.
- Weaknesses: dual-truth + dwell-ignores-op-duration (blocker), dead
  `simulation_time_multiplier`, unpersisted `actual_dwell`, no bottleneck metrics.
- Retry/reinspect: same op, no WORKING re-entry, no re-sample (recommended to preserve).
- Recommended YAML schema + classes/files: documented above.
- Test plan + risk assessment: documented above.

No production code, schema, config-behavior, or timing changes were made.

---

`AUTO-TIME-00 — READY FOR SA REVIEW`
