# VF-SHW-X2 — Whole-Plant Shallow Runnable Model + C1 Functional Control

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `SHW_WHOLE_PLANT_SHALLOW_RUNTIME_READY`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X2 (Issue #94, authoritative SA task contract) |
| Gate type | **IMPLEMENTATION** — additive next to the frozen X1 contracts; no PI/PID, no T107, no rich UI, no second session authority, no PIM change, no merge |
| Branch | `feature/vf-shw-x2` |
| Required base / technical base | `eba4c58` (X1 + X1-C01 accepted) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`, untouched) |
| Task contract | `.ai-harness/tasks/VF-SHW-X2.json` |
| Harness preflight | PASSED |
| Implementation head | `de268e5` |
| Canonical baseline at `de268e5` | **overall PASS, `failed_groups []`, 45/45 groups** (`checks_changed_files` PASSED, 15 files) |
| New baseline group | `x2_whole_plant_runtime` — **42 passed** |
| Full suite | **2757 passed** (X1-C01 head 2715 + 42) |
| Evidence verdicts | `ONE_CANONICAL_SHWTP_SESSION_AUTHORITY` · `ALL_16_ADMITTED_SCOPES_EXECUTE_ONLY` · `NINE_C1_ACTIVE_ZERO_C2_EVALUATION` · `EVERY_X2_INPUT_RESOLVED_AT_RUNTIME` · `PHYSICAL_ORACLES_SATISFIED` · `RUNTIME_PROVENANCE_VISIBLE` |

**Frozen truth labels:** `site_truth=false` · `simulation_truth=synthetic_reference` ·
`vf_runtime_authorization=NOT_AUTHORIZED` · `site_authorized_execution=NOT_AUTHORIZED`.
`NOT_AUTHORIZED` means **no site-authorized/site-faithful claim**; the synthetic demo runtime is explicitly allowed
to execute (Issue #94).

> **CORRECTION (VF-SHW-X2-C01).** An earlier revision of this report stated
> `whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED`. That conflated **implementation state** with
> **authorization state** and was wrong: the X2 shallow runtime **is implemented** as a synthetic reference
> (`whole_plant_runtime=IMPLEMENTED_SYNTHETIC_REFERENCE`) while it is **not authorized** for site execution
> (`whole_plant_runtime_authorization=NOT_AUTHORIZED`). The two states are now reported separately and are
> asserted separately on every runtime projection (see `evidence/VF-SHW-X2/07-authority-labels.json`).
> Sections 7 and §11 of this report that describe the *default model* are superseded by
> `reports/VF-SHW-X2-C01.md`.

---

## 1. What was implemented

| Module | Role |
| --- | --- |
| `src/virtual_factory/shwtp/whole_plant.py` | the X2 whole-plant model: 16 admitted scopes as composition participants, the frozen topology as composition bindings, per-scope contract update families, provenance/balance/monitor projections |
| `src/virtual_factory/shwtp/x2_controls.py` | the 9 frozen X2-active C1 controllers (deterministic rule/sequence logic, no PID) |
| `src/virtual_factory/shwtp/bridge.py` | the canonical `ShwtpExecutionBridge` now drives either the accepted G21 slice or the X2 whole plant |
| `src/virtual_factory/shwtp/session.py` | explicit model selector + `build_shwtp_whole_plant_session()`; ONE `RuntimeSession`/`RunLifecycleService`/run identity per session |
| `src/virtual_factory/shwtp/__init__.py` | X2 exports |
| `tests/test_vnext_x2_whole_plant_runtime.py` | 42 tests covering the 18 Issue #94 oracles |

Execution model: each window (60 s synthetic step) the C1 layer evaluates **from the previously committed
state**, each participant then advances and stages transfers from its **committed** state, the G4 `Coordinator`
validates and commits, and the model records the transfer ledger + balance. That is the accepted
`explicit_lagged` coupling: **no same-window feed-through** (proved).

Topology: 21 composition bindings = the **18 frozen X2 flow edges** (3 PIM-known + 15 assumed) + **3
contract-declared process input relations** (`l1_demand` T101→T100, `l2_split_fraction` LINE2→T100,
`plant_flow` T100→CHEM). No topology was added beyond the frozen graph + those declared inputs; all 4
reference-only edges are non-material and produce no transfer; the 3 excluded T107 edges never appear.

---

## 2. Scope admission (oracles 2, 3)

* Participants = exactly the admission manifest's 16 executable scopes; `monitor_rows()` returns 16 rows.
* Excluded forever: `vf-shw-node-t107`, `vf-shw-node-elec-mcc`, `vf-shw-node-auto-plc` (no participant, no port,
  no binding) and the LINE2 internals (ONE shallow aggregate over `UNIT-SHW-L2-T10x` reference-only ids).
* Every participant is registered in the G1 workspace as executable-capable; container-only scopes are never registered.

## 3. C1 control and the C2 prohibition (oracles 4, 5, 17, 18)

The nine frozen C1 controllers evaluate in a deterministic order; each emits **only** its contract-declared
`output_signals`, reads its frozen timers/deadbands/thresholds from the control contract (descriptive strings such as
`"start 80 kPa / stop 60 kPa"` are parsed, never re-declared), and records labelled synthetic alarms.

| Frozen X1-C01 actuator behaviour | Runtime |
| --- | --- |
| RAW-INTAKE duty/standby speed | `pump_speed_cmd` ∈ {75.0, 0.0} (read from the contract) |
| T106 inlet valve | `inlet_valve_pos` ∈ {100.0, 0.0} (OPEN/CLOSED by the backwash sequence) |
| T108 transfer pump | `transfer_pump_speed_cmd` ∈ {70.0, 0.0} |
| DIST-P108 high-service pump | deterministic X2 fallback = 80.0 % (`x2_fallback_default`) |
| T100 low/low-low | `outlet_enable=false` (downstream withdrawal inhibited), `intake_enable=true` (upstream refill permitted) |
| T100 high/high-high | `intake_enable=false` (upstream intake inhibited), `outlet_enable=true` |
| T108 low / high-high | `transfer_enable=false` / `inflow_enable=false` respectively |

* **Zero C2 evaluation**: the controller set contains only the 9 C1 contracts; every C2 contract stays
  `active_in_x2=false` with its `x2_status`; the C1 layer source contains no PID vocabulary
  (`integral`/`derivative`/`anti_windup`/gain assignments) and no scan loop (static check + evidence).
* The five deferred C2 loops remain deferred (f106-inlet-flow-pi → X3, t108-level-pi → X3, dist-pressure-pi → X3,
  raw-flow-pi → X4, t100-level-pi → X4).

## 4. Runtime I/O resolution (oracle 6)

`model.input_wiring()` resolves **every** contract input of every admitted scope to a runtime producer class:
`process_node` (coordinated transfer / payload-carried signal), `x2_active_controller` (C1 command),
`scenario` (deterministic synthetic parameter) or `x2_fallback_default` (the single DIST-P108 fallback declared in
the X1 contract). **Zero inputs resolve to `unresolved`** and no C2 loop ever produces an X2 input.

## 5. Physical behaviour (oracles 7–12)

| Property | Result (after 120 windows / 2 h synthetic) |
| --- | --- |
| Per-scope storage balance `ΔV = ∫(in−out)` | residual **exactly 0.0** for every storage scope |
| Plant water balance | `plant_in 66.94 m³`, `plant_out 99.05 m³`, `stored_delta −37.52 m³`, `transit_inventory 8.14 m³`, closure **−2.74 m³ ≤ declared bound** (lag-aware) → `bounded: true` |
| Non-negativity / finiteness | 0 negative or non-finite values across all scopes × 120 windows |
| Bounds | tank volumes ≤ capacity, levels ≥ 0, pump speeds ≤ 100 %, `demand_met_fraction ≤ 1` |
| Turbidity chain | raw 12 NTU → settled 1.47 NTU → filtered 1.47 NTU; `filtered ≤ settled` on the matched explicit_lagged basis |
| Filter DP | non-decreasing between backwashes; 3 backwash cycles observed in 200 windows, each resetting DP to its frozen initial value; wash water produced (5 m³/h) and returned to T106 |
| Sludge path | T105 withdrawal → SLUDGE-T201 → processed flow operate; tank stays within capacity |
| Same-window feed-through | none (window-1 downstream emission is zero while window-1 production is only committed for window 2) |
| Determinism | two independent builds produce the **identical** 20-window trajectory digest (`297f98e0…`); reset reproduces the identical trajectory |

## 6. Provenance and truth labels (oracles 15, 16)

Every runtime transfer payload carries the graph-edge provenance: `edge_category`, `pim_relation_id` for the 3
PIM-known edges, `assumption_id` + `reversible` for the 15 assumed edges, `evidence_status`, `fidelity_class`,
`site_truth=false`, `simulation_truth=synthetic_reference`. All 3 PIM-known and all 15 assumed edges appear in the
runtime ledger of a window; the 3 excluded edges never appear; the 3 contract-declared input relations are labelled
`contract_declared_input`. No assumed edge is ever presented as PIM-known; no PIM id is invented.

## 7. Canonical session integration (oracle 1) — superseded by VF-SHW-X2-C01

> **SUPERSEDED.** The SA correction (Issue #94 comment `5645215200`) required the whole-plant model to become the
> **canonical default** of the `shwtp` session/runtime path, with `g21_slice` retained only as an explicit
> compatibility selector. See `reports/VF-SHW-X2-C01.md` for the accepted arrangement. The text below records the
> pre-correction state only.

`build_shwtp_whole_plant_session()` returns **ONE** `RuntimeSession` (one `RunLifecycleService`, one run identity,
one bridge) whose canonical `ShwtpExecutionBridge` drives the whole-plant model; `session.advance()` drives real
windows through that seam. `build_shwtp_session()` keeps its accepted default (`g21_slice`) and accepts an explicit
`model="whole_plant_x2"` selector.

**Interpretation (recorded, conservative):** Issue #94 requires both "upgrade the existing canonical runtime path"
and "existing G21/G22 accepted behaviour must not regress". Switching the *default* model would have changed the
accepted G21/G22/G23/G24/G25 and workspace-shell projections (which the Issue also requires to stay green and whose
rich SH-WTP UI is explicitly deferred to X5/X6). X2 therefore adds the whole-plant model **behind the same canonical
seam** with an explicit selector, keeps the accepted slice default byte-for-byte behaviour-preserving, and proves the
whole-plant session is a single-run-authority session. No parallel simulator, session, clock or run id exists.

Two further parameterizations were chosen (documented, no semantic change):
1. the frozen T106 permissive `"wash-water tank level sufficient"` is interpreted as **wash-water recovery capacity
   available** (the recovery tank starts empty because wash water is produced *by* a backwash — the literal reading
   would make the first backwash impossible);
2. the frozen T101/T104 `residence_accumulator_v1` interlock inhibits the **scope outlet**, and the residence index
   is the true V/Q residence time of the accumulating basin (the literal "index as a stopwatch" reading deadlocks:
   no flow → no index → no outlet → no flow);
3. the plant-level boundary **IN** is the flow the intake actually pumps (raw-source availability that is not
   pumped stays outside the plant), which is what makes the closure identity meaningful.

## 8. Acceptance criteria

| ID | Requirement | Result |
| --- | --- | --- |
| X2-1 | one canonical session/bridge/run authority | PASS (`01-session-authority.json`) |
| X2-2 | 16 admitted scopes execute; excluded never execute | PASS (`02-scope-execution.json`) |
| X2-3 | 9 C1 active; zero C2 evaluation | PASS (`03-c1-controls.json`) |
| X2-4 | every X2 input resolves at runtime, no hidden fallback | PASS (`04-io-resolution.json`) |
| X2-5 | balance exact/bounded; no negative values; bounds respected | PASS (`05-physical-oracles.json`) |
| X2-6 | deterministic trajectory/reset; explicit_lagged | PASS (`05`) |
| X2-7 | turbidity relation; DP monotone + backwash reset | PASS (`05`) |
| X2-8 | assumed-edge provenance visible; synthetic truth labels | PASS (`06-provenance-ledger.json`) |
| X2-9 | X1-C01 actuator behaviour preserved exactly | PASS (`03`, tests) |
| X2-10 | R1–R5 / UX01 / X0 / X1 regression + full suite green | PASS (§9) |

## 9. Regression (machine-derived at `de268e5`)

| Check | Result |
| --- | --- |
| Harness preflight | PASSED |
| Canonical baseline | **overall PASS**, `failed_groups: []`, **45/45 groups** |
| `x2_whole_plant_runtime` | **42 passed** |
| `x1_whole_plant_contracts` | 46 passed (unchanged) |
| Full suite | **2757 passed** (2715 + 42) |
| `checks_changed_files` | PASSED (15 files, all inside the X2 allowlist) |
| Accepted G13/G13B/G14/G15/G21/G22/G23/G24/G25 | unchanged and green (verified directly before the gate run) |

## 10. Change surface

New: `whole_plant.py`, `x2_controls.py`, `tests/test_vnext_x2_whole_plant_runtime.py`,
`evidence/VF-SHW-X2/{generate_evidence.py,01..06}`.
Modified: `bridge.py`, `session.py`, `__init__.py`, task contract, baseline manifest, `CURRENT.md`, this report.
**Untouched:** every X1 contract/config (`configs/**` is in the contract's `forbidden_paths`), `contracts.py`, all
accepted SH-WTP runtime modules, `runcontrol`, `composition`, ASSY, UI, PIM.

---

**VF-SHW-X2 — READY FOR SA REVIEW · `SHW_WHOLE_PLANT_SHALLOW_RUNTIME_READY`**

**STOP — X3/X4/X5 must not begin.** Merge requires explicit SA authorization for the exact PR head SHA.
