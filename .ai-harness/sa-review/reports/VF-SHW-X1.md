# VF-SHW-X1 — Whole-Plant Process Graph + Scope / Fidelity / Control Contracts

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `SHW_WHOLE_PLANT_CONTRACTS_FROZEN`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X1 (Issue #91, authoritative SA task contract) |
| Gate type | **CONTRACT-LAYER gate** — frozen design materialized as machine-readable contracts; **no runtime, no session, no controller, no engine, no rich UI, no PIM write** |
| Branch | `feature/vf-shw-x1` |
| Required base / branch point | `c9d64a5` (X0 CLOSED, `SHW_WHOLE_PLANT_DESIGN_FROZEN`) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`) |
| Task contract | `.ai-harness/tasks/VF-SHW-X1.json` |
| Harness preflight | PASSED (`checks_preflight`) |
| Implementation head | `0f10dc0` (contract layer) · `7130724` (task-contract test-path fix) |
| Baseline / full suite | **overall PASS, `failed_groups []`, 44/44 groups** at `7130724`; `full_suite` **2704 passed** (base 2669 + 35 new) |

**Frozen truth labels (apply to every artefact in this report):**
`site_truth=false` · `simulation_truth=synthetic_reference` · `vf_runtime_authorization=NOT_AUTHORIZED` ·
`site_authorized_execution=NOT_AUTHORIZED` · `whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED` ·
**no PLC/DCS vendor emulation, no site calibration claimed**

**Frozen architecture (unchanged, not reinterpreted):**
`SH-WTP Workspace → ONE RuntimeSession → RunLifecycleService → ShwtpExecutionBridge → whole-plant composition/coordinator → Area/Process participants → Key Asset models/controllers → runtime truth → projections/UI`.
This gate adds a **contract layer** next to that chain; it does not enter it (§8).

---

## 0. Method & repo-first sources

| Source | What it establishes |
| --- | --- |
| `configs/vnext/shwtp/shwtp_readiness_scope.json`, `shwtp_expansion_readiness.json` | the PIM-derived accepted inventory: canonical ids, evidence status, gaps, fidelity ceilings, `stays_reference_only_in_g11` |
| `src/virtual_factory/shwtp/structural.py` | `PLANT-SHW` + 28-scope containment (`_CONTAINMENT_BY_CANONICAL`), executable candidates, authority constants |
| `src/virtual_factory/shwtp/connectivity.py` | `REL-SHW-F01..F07` with evidence status (F01/F04/F05 DocumentConfirmed; F02/F03/F06/F07 PatternInferred) |
| `src/virtual_factory/shwtp/overlay.py` | G18 `ASSUME-SHW-T108-DIST-P108` v1 + `vf_scenario_assumption` / `assumed/synthetic` / `reversible=True` vocabulary |
| `src/virtual_factory/shwtp/expansion.py` | G21 5-scope runnable slice + `PLANT_SLICE_SCOPES` |
| `.ai-harness/sa-review/reports/VF-SHW-X0.md` + `evidence/VF-SHW-X0/**` | the frozen whole-plant design (topology matrix E1..E15, Deep Scope A/B, C0/C1/C2 matrix, loop contracts, X1..X7 sequence) |

Machine-generated companions: `evidence/VF-SHW-X1/01-graph-signature.json` (`WHOLE_PLANT_GRAPH_DETERMINISTIC`),
`02-validation-matrix.json` (`ALL_X1_VALIDATIONS_PASS`), `03-no-construction-proof.json`
(`NO_RUNTIME_CONSTRUCTION_ADDED`), `04-x2-admission-summary.json` (`X2_ADMISSION_FROZEN`),
all produced by `evidence/VF-SHW-X1/generate_evidence.py`.

---

## 1. Deliverable 1 — whole-plant operational process graph contract

`configs/vnext/shwtp/shwtp_whole_plant_graph_v1.json` (schema `vf.vnext.x1.shwtp.whole_plant_graph.v1`).

| Metric | Value |
| --- | --- |
| Nodes | **19** (all VF-local `vf-shw-node-*`; 16 carry an existing PIM canonical id, 3 are VF-local boundary/aggregate nodes) |
| Edges | **25** — `pim_known` **3**, `vf_scenario_assumption` **18**, `reference_only` **4** |
| Assumption registry | **18** entries = exactly the assumption ids used by assumed edges |
| Scope contracts | **17** (16 X2-admitted + the excluded `vf-shw-node-t107`), plus 2 reference-only scope declarations |
| Control contracts | **19** |
| Graph signature (sha256) | `55f49ca475492eaa4ea7c01358127f7698df6770ad1a83675b44eb6d1288b21` |
| Determinism | reload-identical signature; declaration-order independent (proved in tests) |

Covered operational path (every node has a `process_role`): `intake_pumping` → `storage` (RAW-SOURCE → RAW-INTAKE → T100) →
LINE1 `flocculation`/`rapid_mix_dosing_point`/`pac_contact`/`aeration_contact`/`clarification`/`filtration`/`disinfection`/`clean_water_storage`
(T101..T106, T107, T108) → `distribution` (DIST-P108) → `boundary_sink` (network demand);
side streams `chemical_dosing` (CHEM-DOSING → T102/T103), `sludge_sink` (T105/CLARIFIER → SLUDGE-T201),
`wash_water_recovery` (T106 backwash → WASH-T110 → T106); `parallel_line_aggregate` (LINE2 as ONE shallow aggregate over
`UNIT-SHW-L2-T101/T105/T106/T108` internals — reference-only, no invented canonical id);
`electrical_reference` / `automation_reference` (ELEC-MCC, AUTO-PLC) as **reference_only**.

---

## 2. Deliverable 2 — identity & namespace policy (no new PIM id)

* Every PIM-shaped token appearing anywhere in the four contract files is validated against the **accepted PIM-derived
  identity set** (`accepted_canonical_ids()`: readiness inventory ∪ structural containment ∪ selected PIM relations ∪ `PLANT-SHW`).
  Unknown ids fail the load (`ShwtpContractError`).
* VF-local identities are only `vf-shw-node-*`, `vf-shw-edge-*`, `vf-shw-ctrl-*` (prefix `vf-shw-`); a VF-local id may never be
  PIM-shaped, and vice versa.
* No partial/wildcard PIM token is allowed to appear (e.g. a bare `UNIT-SHW-L2-…` prefix is not an id and would fail validation).
* **Zero new PIM canonical ids** were introduced; the graph reuses `UNIT-SHW-*`/`AREA-SHW-*`/`REL-SHW-*` ids only.
* If a needed semantic identity truly had to exist in PIM, the gate had to STOP for SA/PIM SA — that condition did not occur
  (see §11 stop-condition assessment).

---

## 3. Deliverable 3 — assumed vs known topology (per-edge provenance)

| Category | Count | Provenance rule enforced by the validator |
| --- | --- | --- |
| `pim_known` | 3 | must cite `pim_relation_id`, evidence status `DocumentConfirmed`, **no** assumption block |
| `vf_scenario_assumption` | 18 | must carry `assumption.source_kind = vf_scenario_assumption`, `status = assumed/synthetic`, `reversible = true`, `rationale`, `assumption_id = ASSUME-SHW-*` |
| `reference_only` | 4 | support links (electrical/automation, LINE2 internals); `x2_eligible = false`; `flow = reference` |

* No logical edge identity (`source → target : flow`) appears twice: an edge is **never simultaneously PIM-known and VF-assumed**
  (enforced in the validator and probed negatively in the tests with a conflicting-edge fixture).
* X2-eligible assumed edges **15** (used) / excluded **3** (`vf-shw-edge-t106-t107`, `vf-shw-edge-t107-t108`, `vf-shw-edge-chem-t107`);
  the 3 excluded ones are exactly the T107 in-line path, whose in-line position is **not PIM-established** (X0 Q1).
* `pim_known` X2 edges used: `REL-SHW-F01` (T106 → T108 direct, DocumentConfirmed) and both `REL-SHW-F04` bindings.

---

## 4. Deliverable 4 — scope / fidelity process contracts

`configs/vnext/shwtp/shwtp_process_contracts_v1.json`: **16 X2-admitted scope contracts** + 2 reference-only scope declarations
(`vf-shw-node-elec-mcc`, `vf-shw-node-auto-plc`) + the excluded `vf-shw-node-t107`.

Every admitted contract declares the complete frozen field set: `inputs`, `outputs`, `state`, `parameters` (each with `unit` and a
`synthetic_reference*` provenance), `constraints`, `conservation`, `update_rule_family`, `init_reset`, `invalid_state`
(**`fail_closed = true`**), `pim_ceiling`/`evidence_status`, `proposed_vf_fidelity`, `site_truth = false`.

| Scope | Fidelity | Update-rule family | Conservation |
| --- | --- | --- | --- |
| `vf-shw-node-raw-source` / `-network-demand` | synthetic_reference | boundary_condition_v1 | boundary |
| `vf-shw-node-raw-intake` | first_order | pump_flow_algebraic_v1 | flow |
| `vf-shw-node-t100` | first_order | volume_balance_first_order_v1 | volume_balance |
| `vf-shw-node-t101` / `-t104` | logical_only | residence_accumulator_v1 | volume_balance |
| `vf-shw-node-t102` / `-t103` | logical_only / synthetic_reference | dose_ratio_proxy_v1 | dose |
| `vf-shw-node-t105` | synthetic_reference | settling_proxy_v1 | volume_balance |
| `vf-shw-node-t106` | first_order | filter_loading_first_order_v1 | volume_balance |
| `vf-shw-node-t108` | first_order | volume_balance_first_order_v1 | volume_balance |
| `vf-shw-node-wash-t110` | logical_only | recovery_balance_v1 | volume_balance |
| `vf-shw-node-chem-dosing` | logical_only | ratio_dosing_v1 | dose |
| `vf-shw-node-sludge-t201` | logical_only | duty_cycle_rule_v1 | volume_balance |
| `vf-shw-node-dist-p108` | synthetic_reference | pump_curve_algebraic_v1 | flow |
| `vf-shw-node-line2-aggregate` | logical_only | aggregate_split_v1 | split |
| `vf-shw-node-t107` (**excluded**) | synthetic_reference | dose_ratio_proxy_v1 | — |

Nothing here claims site fidelity: fidelity is the *proposed VF* class, capped by the PIM ceiling and explicitly labelled
`synthetic_reference` / `logical_only` / `first_order` (never "vendor-equivalent" or "calibrated").

---

## 5. Deliverable 5 — control contracts (C0 / C1 / C2)

`configs/vnext/shwtp/shwtp_control_contracts_v1.json` — **19 controls**.

| Class | Count | Status in X2 |
| --- | --- | --- |
| C0 | 4 | 2 boundary conditions active in X2 (`raw-source-boundary`, `network-demand-boundary`, type `none` = no controller); 2 reference-only (`elec-mcc`, `auto-plc`, inactive, `implementation_gate = n/a`) |
| C1 | 10 | **9 active in X2** (`implementation_gate = X2`); 1 deferred (`chlorine-residual`, T107, gate X3) |
| C2 | 5 | **all deferred and INACTIVE** (`t108-level-pi`, `dist-pressure-pi`, `f106-inlet-flow-pi` → X3; `raw-flow-pi`, `t100-level-pi` → X4) |

**X2-active C1 controls (the only controllers X2 may implement):** `raw-pump-duty`, `t100-permissive`, `t101-residence`,
`dose-ratio`, `sludge-duty`, `backwash-sequence`, `t108-permissive`, `sludge-sink-duty`, `line2-split`.

Every active C1 contract carries the full field set: `pv`, `sp`, `mv`, units, input/output signals, output limits, `auto_manual`,
`permissives`, `interlocks`, `alarms`, `timers`, deadband, rate limit, `reset_init`, `anti_windup`, `synthetic_tuning_status`,
`provenance`, `evidence_status`.
Every C2 contract additionally carries `pv`/`sp`/`mv`, output limits, bumpless `auto_manual`, permissives/interlocks/alarms,
scan time, rate limit, integrator `reset_init` and a **named anti-windup method** (`conditional_integration + clamping`,
`clamping_with_back_calculation`) — implemented **nowhere** (deferred).
No C2 control is active in X2; no vendor/PLC equivalence is claimed by any contract.

---

## 6. Deliverable 6 — Deep Scope A / Deep Scope B key-asset boundaries (frozen)

* **Deep Scope A — LINE1 downstream (T106/T107/T108-centred):** filtration (`T106`, first_order, DP/backwash sequence),
  **T107 in-line disinfection as an explicit VF assumption** (`ASSUME-SHW-*`, reversible, `x2_eligible = false`, excluded from X2,
  gate X3), clean-water storage (`T108`, first_order), wash-water recovery (`WASH-T110`, logical_only), distribution
  (`DIST-P108`, synthetic_reference, with the pre-existing G18 `ASSUME-SHW-T108-DIST-P108` v1 assumption reused — not redefined).
* **Deep Scope B — RAW WATER + T100:** raw source boundary, intake pumping (rule-based duty/standby), storage
  (`T100`, first_order volume balance, permissive rule).
* Both deep scopes reference only existing Key Asset identity; VF-local synthetic ids stay in the `vf-shw-` namespace.

---

## 7. Deliverable 7 — the authoritative X2 admission manifest

`configs/vnext/shwtp/shwtp_x2_admission_manifest_v1.json` (schema `vf.vnext.x1.shwtp.x2_admission_manifest.v1`) is the
**authorization boundary for X2**:

* **16 executable scopes** (the only scopes X2 may model): raw-source, raw-intake, t100, t101, t102, t103, t104, t105, t106, t108,
  wash-t110, dist-p108, network-demand, chem-dosing, sludge-t201, line2-aggregate.
* **3 reference / container-only scopes**: `elec-mcc`, `auto-plc` (reference-only), `t107` (**EXCLUDED**).
* **9 active C1 controls**, **6 deferral entries** (5 C2 loops + the C1 chlorine controller) with gate X3/X4.
* **Assumed edges used 15 / excluded 3**; **PIM-known edges used 3**.
* **14 frozen invariants** including: `ONE canonical SH-WTP RuntimeSession` for the whole plant; no independent Area/Process
  session or run authority; no C2 loop active; no C3/APC; `site_truth=false`; `simulation_truth=synthetic_reference`;
  no new PIM canonical id; assumed edges never presented as PIM truth; T107/T109 and PROC-SHW-* excluded.
* **Not-authorized list** (explicit): whole-plant runtime execution; PI/PID dynamic implementation; rich SH-WTP UI; gateway/OPC/MQTT/Kafka;
  PIM write / semantic change (escalate to PIM SA); any second workspace/session/run authority; site-faithful or calibrated claims.

Consistency is machine-checked: executable ∩ reference-only = ∅; every executable scope owns exactly one X2-admitted contract;
admission C1 list == the X2-active C1 contract set; every X2-eligible assumed edge is listed as used and every excluded one as excluded.

---

## 8. Deliverable 8 — no-construction proof (`NO_RUNTIME_CONSTRUCTION_ADDED`)

| Probe | Result |
| --- | --- |
| Instrumented constructors during contract load (`RunLifecycleService`, `RuntimeSession`, `ShwtpExecutionBridge`, `T108TankRuntime`, `T106LogicalRuntime`, `SimulationEngine`, `DiscreteSimulationEngine`) | **0 calls** |
| Static token scan of `contracts.py` (docstring-stripped) for `RunLifecycleService` / `ExecutionBridge` / `RuntimeService` / `SimulationEngine` / `RunRecord` / `def advance` / `def step` | **0 hits** |
| Forbidden imports (`runcontrol`, `composition`, `discrete`, `ui`) | **0 hits** |
| Execution-surface attributes on the contract module (`advance`/`step`/`start`/`run`/`reset_session`) | **absent** |
| Existing SH-WTP modules | untouched: `SHWTP_RUNTIME_AUTHORIZATION = NOT_AUTHORIZED`, `SHWTP_SITE_AUTHORIZED_EXECUTION = NOT_AUTHORIZED`, containment ids ⊆ accepted inventory (no structural change) |

`contracts.py` is a **read-only loader/validator** that reads JSON, cross-checks identity/provenance and raises `ShwtpContractError`
on any violation. It creates no runtime, session, bridge, engine, controller, workspace or registry entry.

---

## 9. The ten X1 validations (machine-derived: `ALL_X1_VALIDATIONS_PASS`)

| # | Validation | Artefact |
| --- | --- | --- |
| V1 | graph deterministic + schema valid | `01-graph-signature.json` |
| V2 | no new canonical PIM id (4 contract files + cross-check vs accepted inventory) | `02-validation-matrix.json` |
| V3 | VF-local namespace only (`vf-shw-*`, never PIM-shaped) | `02` |
| V4 | assumption provenance complete (source_kind/status/reversible/rationale/registry) | `02` |
| V5 | no dual-category edge identity (PIM-known vs VF-assumed) | `02` |
| V6 | complete process contract per X2 scope incl. fail-closed invalid state | `02` |
| V7 | C1 complete + C2 deferred/inactive with anti-windup | `02` |
| V8 | admission internally consistent + contract-covered | `02` |
| V9 | invariants + authority frozen across all four artefacts | `02` |
| V10 | zero runtime/session/controller/engine construction | `03-no-construction-proof.json` |

---

## 10. Acceptance criteria → evidence

| ID | Requirement | Where proved |
| --- | --- | --- |
| X1-1 | deterministic schema-valid whole-plant graph with per-edge categories | §1, `01`, tests `TestGraphContract` |
| X1-2 | every referenced PIM id pre-existing; no invented id; `vf-shw-` namespace | §2, tests `TestIdentityAndNamespace` (incl. negative invented-id fixture) |
| X1-3 | assumption provenance on every assumed edge; no dual identity | §3, tests `TestAssumptionProvenance` (incl. conflicting-edge and missing-provenance fixtures) |
| X1-4 | complete process/fidelity contract per X2 scope | §4, tests `TestProcessContracts` |
| X1-5 | complete C1 contracts; C2 deferred + inactive | §5, tests `TestControlContracts` |
| X1-6 | complete, internally consistent X2 admission manifest | §7, tests `TestX2Admission` |
| X1-7 | zero runtime/session/controller/engine construction | §8, tests `TestNoRuntimeConstruction` |
| X1-8 | baseline + full suite green | §12 |

---

## 11. Stop-condition assessment (no STOP triggered)

| Stop condition in the contract | Assessment |
| --- | --- |
| A node/relationship needs new/changed PIM semantics | **Not triggered** — T107 stays VF-assumed and excluded; LINE2 is an aggregate over existing ids; all ids pre-exist |
| X0 deep-scope boundaries internally inconsistent | **Not triggered** — Deep Scope A/B materialized consistently; the only unresolved item (T107 in-line position) remains explicitly flagged and excluded |
| A control contract requires choosing between materially different product behaviours not frozen in X0 | **Not triggered** — C1 set, C2 deferral and gates follow the X0 control matrix |
| X2 admission needs implemented runtime to define the contract | **Not triggered** — admission is fully derivable from the frozen design |
| The canonical SH-WTP architecture would have to change | **Not triggered** — contract layer sits outside the runtime chain; nothing was registered or constructed |

No PIM escalation was necessary. No runtime discovery was used.

---

## 12. Regression & suite (machine-derived, at `7130724`)

| Check | Result |
| --- | --- |
| Harness preflight | **PASSED** |
| Canonical baseline | **overall PASS**, `failed_groups: []`, **44/44 groups** (43 accepted + new `x1_whole_plant_contracts`) |
| New baseline group | `x1_whole_plant_contracts` — `tests/test_vnext_x1_whole_plant_contracts.py`: **35 passed** |
| Full suite | **2704 passed** (base 2669 + 35) |
| `checks_changed_files` | PASSED — 13 changed files, all within the contract allowlist |
| Static/lint/type | unchanged: repo configures none (truthfully reported by the baseline) |

### In-gate correction (disclosed)

`checks_changed_files` initially FAILED: the X1 contract listed the required new test module
`tests/test_vnext_x1_whole_plant_contracts.py` in `allowed_paths` **and** the whole directory `tests/` in `forbidden_paths`,
and the verifier applies forbidden entries unconditionally. Fixed in `7130724` by removing the whole-directory `tests/` entry
(recording the rationale in `forbidden_paths_note`); test protection remains at file granularity — `allowed_paths` permits exactly
one test module, so any other changed test path fails the allowlist. No pre-existing test module changed; no scope, behaviour or
acceptance criterion changed.

---

## 13. Files delivered

| Path | Change |
| --- | --- |
| `.ai-harness/tasks/VF-SHW-X1.json` | new task contract (+ test-path correction) |
| `configs/vnext/shwtp/shwtp_whole_plant_graph_v1.json` | new |
| `configs/vnext/shwtp/shwtp_process_contracts_v1.json` | new |
| `configs/vnext/shwtp/shwtp_control_contracts_v1.json` | new |
| `configs/vnext/shwtp/shwtp_x2_admission_manifest_v1.json` | new |
| `src/virtual_factory/shwtp/contracts.py` | new (loader/validator, constructs nothing) |
| `tests/test_vnext_x1_whole_plant_contracts.py` | new (35 tests) |
| `.ai-harness/sa-review/evidence/VF-SHW-X1/{generate_evidence.py,01..04}` | new |
| `.ai-harness/regression/vnext_baseline_manifest.json` | +`x1_whole_plant_contracts` group; gate context → X1 contract / base `c9d64a5` |
| `.ai-harness/sa-review/CURRENT.md`, `reports/VF-SHW-X1.md` | new gate entry / this report |

`src/virtual_factory/**` (other than `shwtp/contracts.py`), `tests/**` (other than the new module), `configs/**` (other than the four
new contract files), `docs/`, `deploy/`, `examples/`, `simulators/` — **untouched**. No PIM write. No ASSY change. No merge.

---

## 14. Explicit non-objectives honoured

No whole-plant runtime execution · no runnable whole-plant model · no PI/PID dynamic implementation · no rich SH-WTP UI ·
no `RuntimeSession`/`RunLifecycleService` redesign or second run authority · no independent Area sessions · no modification of
existing SH-WTP runtime behaviour · no gateway/OPC/MQTT/Kafka · no PIM write or semantic change · no new PIM canonical id ·
no site-faithful claim · no ASSY change · no X2 implementation start · no rebase onto stale main · no merge.

**Authority remains unchanged:** `vf_runtime_authorization = NOT_AUTHORIZED`,
`site_authorized_execution = NOT_AUTHORIZED`, `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`,
`site_truth = false`, `simulation_truth = synthetic_reference`.

---

**VF-SHW-X1 — READY FOR SA REVIEW · `SHW_WHOLE_PLANT_CONTRACTS_FROZEN`**

**STOP — X2 must not begin.** Only the SA may authorize X2, and only against this admission manifest.
