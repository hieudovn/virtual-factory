# VF-SHW-X1-C01 — X2-Safe Actuator Ownership + Level-Action Direction (correction)

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `X2_SAFE_C1_ACTUATOR_BEHAVIOUR_FROZEN`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X1-C01 (correction of Issue #91, SA comment `5644974241`) |
| Gate type | **CONTRACT CORRECTION** — no runtime, no PID dynamics, no UI, no PIM change, no X2 start |
| Branch | `feature/vf-shw-x1-c01` |
| Previous head / technical base | `ec57d7d` (X1 contract layer, `SHW_WHOLE_PLANT_CONTRACTS_FROZEN`) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`, unchanged) |
| Task contract | `.ai-harness/tasks/VF-SHW-X1-C01.json` |
| Harness preflight | PASSED |
| Implementation head | `f0f9f30` |
| Canonical baseline at `f0f9f30` | **overall PASS, `failed_groups []`, 44/44 groups** · `checks_changed_files` PASSED (13 files) |
| New/changed test group | `x1_whole_plant_contracts` — **46 passed** (was 35, +11 X1-C01 tests) |
| Full suite | **2715 passed** (X1 head 2704 + 11) |

**Frozen truth labels unchanged:** `site_truth=false` · `simulation_truth=synthetic_reference` ·
`vf_runtime_authorization=NOT_AUTHORIZED` · `site_authorized_execution=NOT_AUTHORIZED` ·
`whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED` — the corrected logic is VF synthetic/reference only,
never presented as site or PLC logic.

---

## 0. SA findings addressed

| Finding | SA text | Status |
| --- | --- | --- |
| **A** | `vf-shw-node-raw-intake` declares `pump_speed_cmd` from `vf-shw-ctrl-raw-flow-pi`, which the admission manifest marks C2 / gate X4 / `active_in_x2=false` ⇒ X2 would have to invent the actuator behaviour | **CLOSED** (and closed for the whole admitted set, §1) |
| **B** | `vf-shw-ctrl-t100-permissive` says both "level > LALL to run intake" and "LALL -> stop intake pump(s)" — directionally inconsistent with RAW-INTAKE → T100 → downstream | **CLOSED** (§2) |
| Regression | 4 focused proofs + V1–V10 + 44/44 baseline + full suite green | **DONE** (§3, §6) |

---

## 1. Finding A — no X2-admitted process requires a C2 output

### 1.1 Full inventory of the defect class (4 sites, not 1)

Auditing every `inputs[].source` of every X2-admitted scope against the loaded control contracts found the SA's
named site plus **three further instances of the same class**, which the required proof "no admitted X2 process
requires any C2 controller output" would have failed on:

| Admitted scope | Input signal | C2 controller that owned it | X2 producer after this correction |
| --- | --- | --- | --- |
| `vf-shw-node-raw-intake` | `pump_speed_cmd` | `vf-shw-ctrl-raw-flow-pi` (C2, X4) | **C1 `vf-shw-ctrl-raw-pump-duty`** — fixed synthetic-reference speed (RUN → 75 %, STOP → 0 %) |
| `vf-shw-node-t106` | `inlet_valve_pos` | `vf-shw-ctrl-f106-inlet-flow-pi` (C2, X3) | **C1 `vf-shw-ctrl-backwash-sequence`** — discrete OPEN → 100 % / CLOSED → 0 % position |
| `vf-shw-node-t108` | `transfer_pump_speed_cmd` | `vf-shw-ctrl-t108-level-pi` (C2, X3) | **C1 `vf-shw-ctrl-t108-permissive`** — fixed synthetic-reference speed (RUN → 70 %, STOP → 0 %) |
| `vf-shw-node-dist-p108` | `hsp_speed_cmd` | `vf-shw-ctrl-dist-pressure-pi` (C2, X3) | **explicit X2 fallback/default** (no X2-active C1 owns the high-service pump): deterministic synthetic reference speed 80 %, declared on the input with mode/value/rule/provenance |

The three extra sites are disclosed as the same defect class (the SA named one instance; the required proof is
class-wide). The mechanical audit is in `05-x2-io-resolution.json` → `x2_input_resolution` (29 rows over 16
admitted scopes) and `c2_dependency_check` (`inputs_requiring_a_c2_output: []`).

### 1.2 RAW-INTAKE X2-safe behaviour (SA preferred pattern)

* **C1 duty/standby owns RUN/STOP** — `vf-shw-ctrl-raw-pump-duty` (class C1, gate X2, active) keeps ownership of
  `pump_run_cmd`/`scraper_run_cmd` and now also declares the actuator command output `pump_speed_cmd`.
* **Explicit declared X2 command** — `x2_actuator_command`:
  `{"signal": "pump_speed_cmd", "mode": "fixed_speed_synthetic_reference", "value_when_running": 75.0,
  "value_when_stopped": 0.0, "is_feedback_controlled_in_x2": false, "rule": "RUN -> 75.0; STOP -> 0.0",
  "provenance": "synthetic_reference", "deferred_modulator": {"vf-shw-ctrl-raw-flow-pi", "X4"}}`.
* **C2 stays deferred** — `vf-shw-ctrl-raw-flow-pi` remains class C2, gate X4, `active_in_x2=false`, and now carries
  `x2_status` ("inactive in X2; must NOT modulate pump_speed_cmd while X2 runs") plus `x2_replacement`
  (`gate X4`, `x2_producer vf-shw-ctrl-raw-pump-duty`, `mode fixed_speed_synthetic_reference`).
* Same pattern applied to T106 (sequence) and T108 (permissive); DIST-P108 uses the SA-permitted
  "explicit X2 fallback/default" form because no X2-active C1 control owns that pump.
* **No C2 loop was activated and no new X2-active control was added** — the active C1 set is still the frozen 9.

---

## 2. Finding B — T100 (and T108) level-action direction and ownership

`vf-shw-ctrl-t100-permissive` now declares the actuator ownership and a structured, machine-checkable policy:

| Structure | Content |
| --- | --- |
| `actuator_ownership.upstream_actuator` | `vf-shw-node-raw-intake` / `intake_enable` (RAW-INTAKE pump(s); RUN/STOP also requires the C1 duty/standby contract) |
| `actuator_ownership.downstream_actuator` | `vf-shw-node-t101` / `outlet_enable` (T100 outlet → LINE1 + LINE2 feed path) |
| `level_action_policy` low | `level <= LALL` → `inhibit_downstream_withdrawal` on `t101.outlet_enable`, **upstream refill permitted**; `LALL < level <= LAL` → `reduce_downstream_withdrawal` (same actuator) |
| `level_action_policy` high | `LAH <= level < LAHH` and `level >= LAHH` → `inhibit_upstream_intake` on `raw-intake.intake_enable`, **downstream withdrawal permitted** |
| Permissives | upstream refill permitted while `level < LAH` and no upstream fault; downstream withdrawal requires `level > LALL` |
| Interlocks | LAL/LALL inhibit/reduce DOWNSTREAM withdrawal (upstream refill stays permitted); LAH/LAHH inhibit UPSTREAM intake (downstream withdrawal stays permitted); explicit statement that **no low-level trip of the RAW-INTAKE pumps is implied** |
| Removed wording | the contradictory `LALL -> stop intake pump(s)` is gone |

`vf-shw-ctrl-t108-permissive` received the same explicit ownership/policy (low → `dist-p108.transfer_enable`,
high → `t106.inflow_enable`), and the protective wording of the deferred `vf-shw-ctrl-t100-level-pi` was aligned
(`LALL` no longer claims an intake trip; `LAHH` inhibits upstream intake). The X4 modulation strategy of the level
PI is **not** frozen by this correction — only the protective direction is.

No site-truth claim is made anywhere: the corrected entries keep `synthetic_tuning_status = synthetic_reference`,
`synthetic_reference` provenance and `site_truth=false`.

---

## 3. Focused fail-closed validation (V1–V12)

Two new validators run inside the contract load (a violation fails the load):

**`_validate_x2_io_resolution`** — for every input of every X2-admitted scope:
1. a control-sourced input must come from an **X2-active C1 at gate X2**, otherwise it must declare
   `x2_producer_class = x2_fallback_default` **and** an `x2_fallback` block with `mode` ∈ the frozen fallback
   vocabulary, a non-null deterministic `value`, a non-empty `rule` and `synthetic_reference` provenance →
   a **C2-sourced input without a fallback is rejected**;
2. a node-sourced input must reference an existing, X2-eligible graph node;
3. `scenario` is the only non-node/non-control producer allowed; anything else is rejected;
4. a declared `x2_producer_class` must match the resolved class (no annotation drift);
5. `deferred_modulator` annotations must name an existing **C2** control in a later gate, marked inactive, and
   restate the modulated signal.

**`_validate_level_action_direction`** — for any control declaring `level_action_policy`/`actuator_ownership`:
1. both ownership blocks are required, each with `scope`/`signal`/`direction` and a scope that exists in the graph;
2. every action must name **exactly one** direction (`upstream` xor `downstream`);
3. the action's `target_scope` must be **graph-reachable** downstream of (or upstream into) the owning scope using
   the frozen water-flow edges, and `target_signal` must equal the declared actuator signal for that direction;
4. an X2-active C1 control with level alarms **must** declare the policy (this is what makes the old wording illegal);
5. a permissive/interlock text that lets a low level trip the upstream intake is rejected (explicit negations are
   exempt so a "no low-level trip" statement is not mistaken for one).

Read-only helpers `x2_io_resolution_audit()` / `level_action_audit()` expose the derived resolutions for
evidence/tests (no runtime, no side effects).

### Negative fixtures (prove the validators bite)

| Fixture | Expected rejection |
| --- | --- |
| raw-intake `pump_speed_cmd` re-pointed to `vf-shw-ctrl-raw-flow-pi` without a fallback | `… without an explicit X2 fallback/default; X2 must not require a C2 controller output` |
| T100 interlock restored to `LALL -> stop intake pump(s)` | `… lets a low level trip the upstream intake` |
| low-level action re-targeted at the upstream `raw-intake` scope | `… must target a scope reachable downstream` |
| DIST-P108 fallback declared with only `mode` | `… is missing 'value'` |

---

## 4. Deferred C2 loops (all five, unchanged in class/gate/activity)

| Controller | Class | Gate | X2 state | `x2_replacement` |
| --- | --- | --- | --- | --- |
| `raw-flow-pi` | C2 | X4 | inactive | `raw-pump-duty` fixed speed |
| `t100-level-pi` | C2 | X4 | inactive | `raw-pump-duty` fixed speed |
| `f106-inlet-flow-pi` | C2 | X3 | inactive | `backwash-sequence` discrete valve position |
| `t108-level-pi` | C2 | X3 | inactive | `t108-permissive` fixed speed |
| `dist-pressure-pi` | C2 | X3 | inactive | declared X2 fallback default |

Each now carries `x2_status` ("inactive in X2; must NOT modulate <signal> while X2 runs") and a `x2_replacement`
block whose gate equals the controller's own gate and whose signal equals the controller's MV signal. Evidence:
`05-x2-io-resolution.json` → `deferred_c2_annotations`.

---

## 5. Change surface (bounded)

| Artefact | Change |
| --- | --- |
| `configs/vnext/shwtp/shwtp_process_contracts_v1.json` | 4 input entries gain explicit X2 producer resolution/provenance (raw-intake, t106, t108, dist-p108); dist-p108 `control_level` corrected to `X2_fallback_default+C2(X3)` (its only loop is a deferred C2 — the old `C1+C2` label was wrong) |
| `configs/vnext/shwtp/shwtp_control_contracts_v1.json` | X2 actuator commands on the 3 owning C1 controls; T100/T108 actuator ownership + level policy (T100 rewritten); 5 C2 deferral annotations; `raw-flow-pi` owning scope corrected to `raw-intake` (its MV is the intake pump speed) |
| `configs/vnext/shwtp/shwtp_x2_admission_manifest_v1.json` | dist-p108 control-level correction + **2 X1-C01 invariants** (now 16) |
| `src/virtual_factory/shwtp/contracts.py` | 2 new fail-closed validators + 2 read-only audit helpers (constructs nothing) |
| `tests/test_vnext_x1_whole_plant_contracts.py` | +11 tests (ownership, resolution, determinism, direction, 4 negative fixtures); invariant pin 14 → 16 |
| evidence `VF-SHW-X1/{01..04}` + **new `05-x2-io-resolution.json`** | regenerated / added |
| `.ai-harness/tasks/VF-SHW-X1-C01.json`, manifest gate context, report, `CURRENT.md` | gate bookkeeping |

**Explicitly unchanged:** the frozen whole-plant **graph** (still 19 nodes / 25 edges, signature
`55f49ca4…`, untouched — it is in the contract's `forbidden_paths`), the X2-active C1 set (still 9), every C2
class/gate/activity, all SH-WTP runtime modules, `tests/**` other than the X1 module, and PIM.

---

## 6. Acceptance criteria & regression

| ID | Requirement | Result |
| --- | --- | --- |
| X1C01-1 | Every admitted input resolves to an X2 producer; no admitted scope requires a C2 output | PASS — `V11_x2_input_resolution_no_c2_dependency`, 29/29 inputs resolved |
| X1C01-2 | RAW-INTAKE X2-safe C1 behaviour; `raw-flow-pi` inactive/X4 only | PASS — `V12`, §1.2 |
| X1C01-3 | T100 low/high actions identify the correct actuator ownership/direction | PASS — `V12`, §2 |
| X1C01-4 | Defect class closed everywhere; V1–V12 green; 44/44 baseline green; full suite green | PASS — §6 table below |

| Check | Result |
| --- | --- |
| Harness preflight | **PASSED** |
| Canonical baseline at `f0f9f30` | **overall PASS**, `failed_groups: []`, **44/44 groups** |
| `checks_changed_files` | PASSED — 13 files, all inside the correction allowlist |
| `x1_whole_plant_contracts` group | **46 passed** (35 + 11 new) |
| Full suite | **2715 passed** (X1 head 2704 + 11) |
| Evidence verdicts | `WHOLE_PLANT_GRAPH_DETERMINISTIC`, `ALL_X1_VALIDATIONS_PASS` (V1–V12), `NO_RUNTIME_CONSTRUCTION_ADDED`, `X2_ADMISSION_FROZEN`, `X2_SAFE_C1_ACTUATOR_BEHAVIOUR_FROZEN` |
| Stop conditions | none triggered (no graph/PIM change needed, no C2 activation, no invented behaviour) |

---

**VF-SHW-X1-C01 — READY FOR SA REVIEW · `X2_SAFE_C1_ACTUATOR_BEHAVIOUR_FROZEN`**

**STOP — X2 must not begin.** Merge requires explicit SA authorization for the exact PR head SHA.
