# VF-SHW-X2-C01 — Canonical Whole-Plant Default + Authority Labels + Test Rigour (correction)

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `X2_CANONICAL_WHOLE_PLANT_DEFAULT_WITH_LABELS`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X2-C01 (correction of Issue #94, SA comment `5645215200`) |
| Gate type | **CORRECTION** — implementation-surface correction inside the pushed X2 work; no frozen config/contract change, no scope/topology/control/fidelity expansion, no C2/PI/PID, no T107, no rich UI, no PIM/ASSY, no X3/X4/X5, no merge |
| Branch | `feature/vf-shw-x2-c01` |
| Previous head / technical base | `2492329c8e07e54f81eb73e8ce9626c65927929d` (`2492329`, X2 `SHW_WHOLE_PLANT_SHALLOW_RUNTIME_READY`, NOT_COMPLETE) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`, untouched) |
| Task contract | `.ai-harness/tasks/VF-SHW-X2-C01.json` |
| Harness preflight | PASSED |
| Implementation head | `134cedb` |
| Canonical baseline at `134cedb` | **overall PASS, `failed_groups []`, 45/45 groups** · `checks_changed_files` PASSED (19 files) |
| `x2_whole_plant_runtime` group | **50 passed** (was 42, +8 X2-C01 tests) |
| `x1_whole_plant_contracts` group | 46 passed (unchanged) |
| Full suite | **2765 passed** (X2 head 2757 + 8) |
| Evidence verdicts | `ONE_CANONICAL_SHWTP_SESSION_AUTHORITY` · `ALL_16_ADMITTED_SCOPES_EXECUTE_ONLY` · `NINE_C1_ACTIVE_ZERO_C2_EVALUATION` · `EVERY_X2_INPUT_RESOLVED_AT_RUNTIME` · `PHYSICAL_ORACLES_SATISFIED` · `RUNTIME_PROVENANCE_VISIBLE` · **`FOUR_AUTHORITY_LABELS_ON_ALL_OUTPUTS`** (new, `07-authority-labels.json`) |

**Authority labels (now asserted, not just documented):** `site_truth=false` · `simulation_truth=synthetic_reference` ·
`vf_runtime_authorization=NOT_AUTHORIZED` · `site_authorized_execution=NOT_AUTHORIZED`.
**Implementation state is reported separately from authorization state:** `whole_plant_runtime=IMPLEMENTED_SYNTHETIC_REFERENCE` ·
`whole_plant_runtime_authorization=NOT_AUTHORIZED`. `NOT_AUTHORIZED` means **no site-authorized/site-faithful claim**;
the synthetic reference runtime is explicitly allowed to execute (Issue #94).

---

## 0. SA findings addressed

| Finding | SA text (Issue #94 comment `5645215200`) | Status |
| --- | --- | --- |
| **A** | `whole_plant_x2` must become the canonical default of the Workspace `shwtp`; the G21 slice must be kept only as an **explicit compatibility selector** | **CLOSED** (§1) |
| **B** | Add and verify all four labels on runtime outputs: `site_truth=false`, `simulation_truth=synthetic_reference`, `vf_runtime_authorization=NOT_AUTHORIZED`, `site_authorized_execution=NOT_AUTHORIZED` | **CLOSED** (§2, and closed class-wide) |
| **C** | Replace weak or tautological tests, including contract-signature checks, DP monotonicity and conditional assertions that do not directly prove the invariant | **CLOSED** (§3) |
| Report | Correct the report contradiction (`whole_plant_runtime` reported as `NOT_AUTHORIZED / NOT_IMPLEMENTED` while the runtime **is** implemented) | **CLOSED** (§2.3, `reports/VF-SHW-X2.md`) |
| Regression | Focused X2 + canonical baseline + full suite green; evidence/report regenerated; new pushed head pinned | **DONE** (§4) |

---

## 1. Finding A — `whole_plant_x2` is the canonical default; `g21_slice` is an explicit compatibility selector

### 1.1 The canonical path

`src/virtual_factory/shwtp/session.py`

| Name | Value / role |
| --- | --- |
| `SHWTP_MODEL_WHOLE_PLANT_X2` | `"whole_plant_x2"` |
| `SHWTP_MODEL_G21_SLICE` | `"g21_slice"` |
| `SHWTP_DEFAULT_MODEL` | **`SHWTP_MODEL_WHOLE_PLANT_X2`** (canonical default) |
| `X2_SESSION_SCENARIO_ID` | `"shwtp-x2-whole-plant"` (default scenario) |
| `build_shwtp_session(...)` | canonical constructor; default `model=SHWTP_DEFAULT_MODEL`, `scenario_id=X2_SESSION_SCENARIO_ID`, `workspace_id="shwtp"` |
| `build_shwtp_g21_slice_session(...)` | **compatibility factory** — the only supported way to obtain the accepted G21 slice |

`src/virtual_factory/ui/workspace_monitor.py` registers the canonical default in
`_shwtp_session_factory()`; the registry description is
`"SH-WTP canonical whole-plant runtime (X2: 16 scopes, 9 C1 controls)"`. **No second registry, session,
runtime, clock, run identity or UI authority was created** — the same `RuntimeSession` /
`RunLifecycleService` / `ShwtpExecutionBridge` seam carries the whole plant.

`src/virtual_factory/shwtp/bridge.py` is model-agnostic (`ShwtpExecutionBridge(model_builder)`, `model` property,
`slice` retained as a backward-compatible alias); an explicit `model_driven_windows` discriminator keeps the
accepted G21 slice on the generic `prepare_window` + `coordinator.run_window` path while the X2 model uses its
own `run_window`. The landed boundary is validated on every `advance`.

### 1.2 Evidence (machine-derived)

`01-session-authority.json` (regenerated): `canonical_default_model="whole_plant_x2"`,
`accepted_compatibility_model="g21_slice"`, `default_session_model_is_whole_plant=true`,
`session_class="RuntimeSession"`, `workspace_id="shwtp"`, `run_id="shwtp-0001"`,
`scenario_id="shwtp-x2-whole-plant"`, `bridge_class="ShwtpExecutionBridge"`, `bridge_is_canonical=true`,
`bridge_model_class="WholePlantX2Runtime"`, `participant_count=16`, `admitted_scope_count=16`,
`window_index_after_one_step=1`, `coupling_policy="explicit_lagged"` →
**`ONE_CANONICAL_SHWTP_SESSION_AUTHORITY`**.

### 1.3 The G21 compatibility path is still green (not merely "still compiling")

`build_shwtp_g21_slice_session()` builds the accepted 5-scope slice through the same canonical bridge
(`model_driven_windows=False`, generic `prepare_window` path). The accepted G22/G23/G24/G25 modules that
pinned the slice are migrated to the explicit compatibility factory and stay green — the slice is now reachable
**only** through that explicit selector/factory, as required.

### 1.4 Migration of accepted assertions (bounded surface)

| Module | Change |
| --- | --- |
| `tests/test_vnext_g22_session.py` | all slice-internal construction moved to `build_shwtp_g21_slice_session()` |
| `tests/test_vnext_g23_registry.py` | canonical scenario id asserted as `shwtp-x2-whole-plant` |
| `tests/test_vnext_g24_workspace_ui.py` | default selection now asserts the 16-scope whole plant (structure rows equal to the canonical scope metadata) **plus** a compatibility-factory proof for the 5-scope slice |
| `tests/test_vnext_g25_acceptance.py` | B1 asserts the canonical whole plant (16 scopes, RAW-INTAKE → DIST-P108 path present); B2/B3 assert `status="synthetic_reference"` and the four view labels |

The SH-WTP view became **model-agnostic** so that both models render through the single canonical seam: the
live branch reads the driving model (label `"SH-WTP X2 whole plant"` when `model_driven_windows`, otherwise
`"SH-WTP G21 plant slice"`) and the no-live-model branch is built from the 16 contract-derived scopes with
`status="synthetic_reference"`, `fidelity_class`, and the assumed topology. No rich UI page is added (X5/X6).

---

## 2. Finding B — the four authority labels are threaded, asserted and fail-closed

### 2.1 Single source of truth

`src/virtual_factory/shwtp/whole_plant.py`

```python
SITE_TRUTH = False
SIMULATION_TRUTH = "synthetic_reference"
VF_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"
SITE_AUTHORIZED_EXECUTION = "NOT_AUTHORIZED"
AUTHORITY_LABELS: Mapping[str, Any] = {...}      # the four labels, one place
def authority_labels() -> dict: ...             # copy
def require_authority_labels(record, *, where)  # fail-closed guard
```

`require_authority_labels()` raises `WholePlantX2Error` when a label is **missing** or has a **wrong value**;
it is the guard used at the emitting sites, so a projection cannot silently lose a label.

### 2.2 Coverage (class-wide, not one record)

| Projection | Labels carried | Guard |
| --- | --- | --- |
| inter-scope transfer payload (`ScopeParticipant._emit`) | yes | `require_authority_labels(payload, where="transfer payload from …")` |
| per-scope monitor values (`monitor_values`) | yes | yes |
| monitor row (`monitor_rows`) | yes (row **and** `row["values"]`) | yes (both) |
| control row (`control_rows`) | yes | — |
| storage balance row + `balance_report()` top level | yes | — |
| `input_wiring()` row | yes | — |
| `provenance_records()` row | yes | — |
| `assumed_topology()` row | yes | — |
| `runtime_truth()` | yes | — |
| `ScopeRuntimeInfo.to_dict()` | yes | — |
| SH-WTP monitor view | yes | asserted in tests |

`07-authority-labels.json` (new, the Finding-B artefact) inventories **137 records + the SH-WTP view** and
reports `labels_missing=[]`, `labels_drifted=[]` → **`FOUR_AUTHORITY_LABELS_ON_ALL_OUTPUTS`**.

### 2.3 Implementation state vs authorization state (contradiction corrected)

`runtime_truth()` now reports the two states separately:

```
whole_plant_runtime              = "IMPLEMENTED_SYNTHETIC_REFERENCE"
whole_plant_runtime_authorization= "NOT_AUTHORIZED"
```

`reports/VF-SHW-X2.md` previously stated `whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED`, which
conflated the two states (the runtime **is** implemented as a synthetic reference). The X2 report header now
carries an explicit **CORRECTION (VF-SHW-X2-C01)** note and §7 is marked **SUPERSEDED**. Historical reports
(R1…X1) are left unchanged: they predate the X2 runtime, so the phrase was accurate when written.

### 2.4 Evidence (machine-derived)

`07-authority-labels.json` includes `implementation_vs_authorization` with both states and the note that they
are reported separately; `expected_labels` are restated so a drift shows up as a diff, not as prose.

---

## 3. Finding C — weak/tautological tests replaced by bite tests

| Was | Now |
| --- | --- |
| contract-signature check that only compared two loads of the same file | deterministic-load assertion **plus** mutation sensitivity of the covered admission surface: graph node `process_role` tamper → different signature; scope `fidelity_class` tamper → different signature; control `implementation_gate` tamper → **rejected fail-closed** (`deferred_modulator annotation`); `active_in_x2=True` on a C2 loop → **rejected** |
| DP monotonicity asserted once at the end (and `... if … else True` style conditionals) | monotonicity asserted **per cycle between resets**, driven through the real state, plus `test_dp_monotonicity_check_bites_on_a_violation` which proves the check fails on a deliberate violation |
| T106/T108 semantics guarded by conditional expressions that could silently degrade to `True` | direct assertions on the actual resolved behaviour |
| input-resolution asserted loosely | strict mapping: `process_node→coordinated_transfer`, `x2_active_controller→c1_control_command`, `x2_fallback_default→declared_x2_fallback`, `scenario→scenario_parameter`, with exactly **1** declared fallback (DIST-P108) and **1** scenario parameter |
| labels documented but unasserted | `TestAuthorityLabels`: labels checked on >100 records, plus bite tests for **each** missing key and for mutated `site_truth` / `vf_runtime_authorization` |
| no canonical-default test | `TestCanonicalDefaultModel`: default session resolves to `WholePlantX2Runtime`, 16 participants, first landed window = 1; the G21 slice is reachable only via the explicit selector/compatibility factory |

New module-level helper `_assert_monotone_between_resets(series, resets)` is used by the monotonicity tests so
the invariant is asserted on every segment rather than once.

---

## 4. Regression (machine-derived)

| Check | Result |
| --- | --- |
| Harness preflight | PASSED (branch `feature/vf-shw-x2-c01`, clean tree, `expected_base_sha` = `origin/main`) |
| Canonical baseline at `134cedb` | **overall PASS**, `failed_groups: []`, **45/45 groups** |
| `x2_whole_plant_runtime` | **50 passed** (was 42) |
| `x1_whole_plant_contracts` | 46 passed (unchanged) |
| `full_suite` | **2765 passed** (2757 + 8) |
| `checks_changed_files` | PASSED (19 files) |
| `checks_compile` / `checks_static_lint_type` | PASSED |
| G13/G13B/G14/G15/G21/G22/G23/G24/G25 | green (G22/G23/G24/G25 migrated to the canonical default + compatibility factory) |

---

## 5. Change surface

Modified: `src/virtual_factory/shwtp/{whole_plant.py, session.py, bridge.py, __init__.py}`,
`src/virtual_factory/ui/workspace_monitor.py`,
`tests/test_vnext_x2_whole_plant_runtime.py`,
`tests/test_vnext_{g22_session,g23_registry,g24_workspace_ui,g25_acceptance}.py`,
`.ai-harness/regression/vnext_baseline_manifest.json`,
`.ai-harness/sa-review/{CURRENT.md, reports/VF-SHW-X2.md, evidence/VF-SHW-X2/generate_evidence.py}`.
Added: `.ai-harness/tasks/VF-SHW-X2-C01.json`,
`.ai-harness/sa-review/evidence/VF-SHW-X2/07-authority-labels.json`, this report.

**Untouched:** `configs/**` (every frozen X1 contract/config, in the contract's `forbidden_paths`),
`src/virtual_factory/shwtp/contracts.py`, `x2_controls.py`, `structural.py`, `connectivity.py`,
`expansion.py`, `runcontrol`, `composition`, `discrete`, `core`, `assembly`, every other UI module, ASSY, PIM,
`docs/`, `deploy/`, `examples/`, `simulators/`.

---

**VF-SHW-X2-C01 — READY FOR SA REVIEW · `X2_CANONICAL_WHOLE_PLANT_DEFAULT_WITH_LABELS`**

**STOP — X3/X4/X5 must not begin. Issue #94 stays OPEN. Merge requires explicit SA authorization for the exact PR head SHA.**
