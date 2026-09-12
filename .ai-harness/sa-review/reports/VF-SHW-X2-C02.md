# VF-SHW-X2-C02 — Runtime Identity, WASH Return, Water Ledger, Level-Inhibit Routing (correction)

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `X2_RUNTIME_IDENTITY_AND_WATER_ACCOUNTING_CORRECTED`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X2-C02 (correction of Issue #94, SA comment `5645344049`) |
| Gate type | **CORRECTION** — four residual X2 defects inside the C01 branch; no frozen config/contract change, no new topology/scope/controller, no C2/PI/PID, no T107, no rich UI, no PIM/ASSY, no X3/X4/X5, no merge |
| Branch / PR | `feature/vf-shw-x2-c01` · PR **#96** (Issue #94 stays OPEN) |
| Required base | `aae34825a58b1017127d4eecfb42ec811cf2c5a7` (`aae3482`, C01 head) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`, untouched) |
| Task contract | `.ai-harness/tasks/VF-SHW-X2-C02.json` |
| Harness preflight | PASSED |
| `x2_whole_plant_runtime` group | **75 passed** (was 50; +25 C02 tests) |
| Evidence verdicts | 01…07 unchanged + **`RUNTIME_IDENTITY_BOUND_TO_THE_ACTIVE_ATTEMPT`**, **`COMMITTED_PROCESS_INPUT_CONSUMED_AT_THE_CORRECT_LAG`**, **`PLANT_WATER_CONSERVED_ON_WATER_ONLY`**, **`LEVEL_INHIBIT_ROUTED_TO_THE_UPSTREAM_PATH`** |

---

## 0. SA findings addressed

| Finding | SA text (Issue #94 comment `5645344049`) | Status |
| --- | --- | --- |
| **C02-1** | Participant run identity is fixed; transfers do not carry the session's run id — bind the model/participants/transfers to the active attempt context and prove identity, reset, restart/replay | **CLOSED** (§1) |
| **C02-2** | WASH return is discarded before consumption (`_commit` wrote it into the transient command dict that `prepare_window` replaces) | **CLOSED** (§2) |
| **C02-3** | The conservation oracle counts information as water and hides a real deficit behind a 5 % allowance (`closure=-2.7398 m3`, `bounded=true`) | **CLOSED** (§3) |
| **C02-4** | T108 high level deletes already-received inflow instead of inhibiting the upstream T106 actuator; T100 path to audit | **CLOSED** (§4) |
| Docstring | Correct the stale session module docstring claiming G21 is the default | **CLOSED** (§1.1) |
| Regression | Focused X2, canonical baseline, full suite; evidence regenerated; exact pushed head reported | **DONE** (§5) |

---

## 1. C02-1 — the runtime identity is the ACTIVE attempt's identity

### 1.1 What changed

`src/virtual_factory/shwtp/session.py`

- The model is built **per attempt from that attempt's immutable run context** through the existing
  `RunLifecycleService` `bridge_factory_ctx` seam (the seam TIPA already uses). There is **no new lifecycle
  authority and no second run-id minter**:

  ```python
  def bridge_factory_ctx(context):
      run_id = context.run_id            # the attempt's own identity
      return ShwtpExecutionBridge(lambda: build_model(run_id))
  ```

- `_resolve_model` now returns `build_for_run(run_id)`, so a **fixed** model run id can no longer leak in.
- Fail closed: the zero-arg `bridge_factory` (`_require_attempt_bound_bridge`) and an explicit `run_id=…`
  kwarg to the session factory both raise `SessionError`.
- The stale module docstring (which claimed `g21_slice` was the default) is corrected to the C01 reality:
  `whole_plant_x2` is the canonical default, `g21_slice` is an explicit compatibility selector.

`src/virtual_factory/shwtp/whole_plant.py`

- `WholePlantX2Runtime.run_id` is the attempt identity; `runtime_truth()` exposes
  `run_id` + `run_id_source="attempt_context"`.
- Every **detached ledger row** now carries `run_id` (inspection) next to `transfer_kind` and `boundary`.

### 1.2 Evidence (`08-lifecycle-identity.json`)

| Proof | Result |
| --- | --- |
| attempt run id / model run id | `shwtp-0001` / `shwtp-0001` |
| participant + transfer run ids | all `shwtp-0001`; window ids prefixed with the attempt id |
| `runtime_truth()` | `run_id=shwtp-0001`, `run_id_source=attempt_context` |
| RESET | identity preserved, transfers still `shwtp-0001` |
| `new_attempt()` → advance | `shwtp-0002`, all transfers `shwtp-0002`, `old_identity_leaked=False` |
| `replay()` → advance | `shwtp-0003`, all transfers `shwtp-0003`, `old_identity_leaked=False` |
| zero-arg factory / ambient `run_id` | `FAILED_CLOSED` / `FAILED_CLOSED` |

→ **`RUNTIME_IDENTITY_BOUND_TO_THE_ACTIVE_ATTEMPT`**

---

## 2. C02-2 — the committed WASH return is consumed at the correct lag

`ScopeParticipant` now separates **committed process input** (`self._process_input`, written by `_commit`,
survives `prepare_window`) from **transient controller commands** (`self._commands`, replaced every
`prepare_window`). `_consume_process_input/_consume_process_flow` **pop** the value, so it is consumed exactly
once by the next step (the correct `explicit_lagged` lag). The same rail now carries T100's committed
`line1_demand_m3h` / `line2_split_fraction` (the class-wide instance of the defect).

`FilterParticipant` stores the delivered `wash_in` flow as committed input and consumes it in the volume
balance; `monitor_values()` exposes `wash_return_m3h`.

**Evidence (`09-committed-process-input.json`)** — forced early backwash (`t106_dp_initial_kpa=78`):

| Proof | Result |
| --- | --- |
| positive-return windows (consumed vs delivered-previous) | 2 windows, `lag_mismatches = []` |
| WASH water received / returned | `0.125 m3` / `0.0833 m3` |
| return never exceeds what was received | `true` |
| before the fix | the return was written into the transient command dict and destroyed by the next `prepare_window` → T106 always consumed 0 |

→ **`COMMITTED_PROCESS_INPUT_CONSUMED_AT_THE_CORRECT_LAG`**

---

## 3. C02-3 — conservation is a ledger-based water balance

### 3.1 Control volume and classification

Control volume = **pumped-intake discharge → network/sludge discharge**. Every transfer row is classified:

| kind | rows (last window) | water |
| --- | --- | --- |
| `physical_water` | 17 | counts (in-transit unless it is the boundary discharge) |
| `information` | 3 | **0 m3** — a `60 m3/h` information signal is a signal, not water |
| `source_availability_outside_boundary` | 1 | **0 m3** — whats the intake does not pump never enters the plant |

### 3.2 The ledger (120 windows, default scenario)

| Term | Value |
| --- | --- |
| `plant_in_m3` (intake discharge) | 66.9375 |
| `plant_out_m3` (network + sludge) | 99.051733 |
| `stored_delta_m3` | −37.391667 |
| `transit_inventory_m3` (physical, inside the volume) | 5.134633 |
| `process_loss_m3` (declared LINE2 loss, explicit) | 0.1428 |
| `overflow_m3` / `shortfall_m3` (explicit clamps) | 0.0 / 0.0 |
| **`residual_m3`** | **−1e-12** |
| `tolerance_m3` (documented float rounding) | 2.04e-07 |
| `conserved` | **true** |
| information inventory (excluded from the balance) | 171.9372 |
| unpumped source availability (outside the volume) | 90.0 |

The **previous** oracle summed flow on *all* received transfers (including information signals) and accepted
`5 % of the input + 0.05` — reported `closure = −2.7398 m3` with `bounded = true`. The deficit that hid there
was ≈ **0.55 m3 of water** (the C02-2/C02-4 losses), i.e. far above float rounding; the new oracle closes to
`1e-12` with a `2e-7` tolerance, and every modelled loss is an explicit, alarmed term (no silent clamping).

### 3.3 Scenario matrix (`10-water-ledger.json`)

| Scenario | Windows | residual | conserved |
| --- | --- | --- | --- |
| startup | 1 | 1e-12 | true |
| stopped / zero inflow | 30 | 1e-12 | true |
| backwash + recovery | 30 | 1e-12 | true |
| LINE2 active (split 0.5) | 30 | 1e-12 | true |
| T108 high-level inhibit | 40 | 1.4e-11 | true |
| capacity overflow (T106) | 30 | 1e-12 | true |
| empty tanks | 30 | 0.0 | true |

→ **`PLANT_WATER_CONSERVED_ON_WATER_ONLY`**

---

## 4. C02-4 — the level permissive inhibits the declared UPSTREAM path

### 4.1 Routing (no unfrozen decision)

The frozen `vf-shw-ctrl-t108-permissive` contract names `inflow_enable` as an output owned by T108 whose
`actuator_ownership.upstream_actuator` is the **T106 filtered-water inflow path**, and
`level_action_policy` for `level >= LAHH` is `inhibit_upstream_intake`. The implementation now matches that:

| Scope | Before | After |
| --- | --- | --- |
| T108 (receiver) | `inflow = self._inflow_m3h if inflow_enable else 0.0` → **deleted committed water** | always integrates the received inflow; `inflow_permitted` is a reporting/alarm flag |
| T106 (filter) | kept forwarding into the closed path | `filtered_flow = 0` while inhibited (`filtered_path_inhibited`), still consumes its committed inflow + wash return |
| T105 (clarifier) | pushed water into a closed path | **holds** its water (`outflow_held_by_downstream_inhibit`) — no accumulation, no loss |
| T100 (audit) | `intake = self._inflow_m3h if permit else 0.0` → **deleted committed intake** | always integrates; the upstream `intake_enable` (t100-permissive) stops the **raw-intake pump** at the source |
| raw-intake | already honoured `intake_enable` | unchanged (the declared upstream actuator) |

**Command priority (recorded):** the backwash sequence keeps **exclusive ownership of `inlet_valve_pos`**; the
level inhibit closes the *path* (upstream does not emit, filter does not forward) and never writes a second
owner's actuator signal. During `BACKWASH`/`SETTLE` the sequence already stops filtered production, so both
agree.

### 4.2 Evidence (`11-level-inhibit.json`)

| Proof | Result |
| --- | --- |
| T108 high-level inhibit window | 18 (`inflow_enable=False`, alarm `inhibit_upstream_intake`) |
| T106 filtered path | inhibited, `filtered_flow_m3h = 0` |
| T105 | holds its water |
| windows integrating a committed inflow **while inhibited** | 1 (the transition window — exactly the water the pre-C02 code deleted) |
| T108 balance across the transition | `volume_in` delta == delivered inflow; volume delta == (delivered − withdrawal)·dt; `balance_mismatches = []` |
| T100 audit | inhibit at window 26; `intake_enable=False`; pump `0 m3/h`; 4 windows integrated intake while inhibited |
| overflow (T100 capacity 70 m3) | **3.075 m3 explicitly accounted** (alarm + ledger term, not a silent clamp) |

→ **`LEVEL_INHIBIT_ROUTED_TO_THE_UPSTREAM_PATH`**

---

## 5. Regression and change surface

| Check | Result |
| --- | --- |
| Harness preflight | PASSED |
| Focused modules (X2 + G22/G23/G24/G25 + X1) | **212 passed** |
| Full suite | **2790 passed** (2765 → 2790, +25 C02 tests) |
| `x2_whole_plant_runtime` group | **75 passed** (was 50) |
| Canonical baseline | recorded at the pushed head (§6) |
| `checks_changed_files` | PASSED |

Changed: `src/virtual_factory/shwtp/{whole_plant.py, session.py}`,
`tests/test_vnext_x2_whole_plant_runtime.py`, `.ai-harness/regression/vnext_baseline_manifest.json`,
`.ai-harness/sa-review/{CURRENT.md, reports/VF-SHW-X2-C02.md, evidence/VF-SHW-X2/generate_evidence.py}` and the
regenerated/new evidence artefacts, `.ai-harness/tasks/VF-SHW-X2-C02.json`.

**Untouched:** `configs/**` (all frozen X1 contracts/configs), `contracts.py`, `x2_controls.py`,
`structural.py`, `connectivity.py`, `expansion.py`, `runcontrol/**`, `composition/**`, `src/virtual_factory/ui/**`,
ASSY, PIM, `docs/`, `deploy/`, `examples/`, `simulators/`.

---

**VF-SHW-X2-C02 — READY FOR SA REVIEW · `X2_RUNTIME_IDENTITY_AND_WATER_ACCOUNTING_CORRECTED`**

**STOP — X3/X4/X5 must not begin. Issue #94 stays OPEN. Merge requires explicit SA authorization for the exact PR head SHA.**
