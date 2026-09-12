# VF-SHW-X0 — Whole-Plant Simulation & Control Design Freeze

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `SHW_WHOLE_PLANT_DESIGN_FROZEN`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X0 (Issue #89, authoritative SA task contract) |
| Gate type | **DESIGN / AUDIT ONLY** — no source/runtime implementation, no UI implementation, no PIM mutation |
| Branch | `feature/vf-shw-x0` |
| Required base / branch point | `f4dcca5` (UX01 CLOSED, `ASSY_STRUCTURE_UX_CONSISTENT`) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`) |
| Task contract | `.ai-harness/tasks/VF-SHW-X0.json` |
| Harness preflight | PASSED |
| Baseline / full suite | see §14 (design-only: unchanged from the accepted base) |

**Frozen truth labels (apply to every artefact in this report):**
`site_truth=false` · `simulation_truth=synthetic_reference` · `vf_runtime_authorization=NOT_AUTHORIZED` ·
`site_authorized_execution=NOT_AUTHORIZED` · `whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED` ·
**no PLC/DCS vendor emulation, no site calibration claimed**

**Frozen architecture (unchanged, not reinterpreted):**
`SH-WTP Workspace → ONE RuntimeSession → RunLifecycleService → ShwtpExecutionBridge → whole-plant composition/coordinator → Area/Process participants → Key Asset models/controllers → runtime truth → projections/UI`.
No Area/Process may own an independent workspace session or run authority.

---

## 0. Method & repo-first sources

Read-only audit of the accepted base `f4dcca5`. Primary sources (all in-repo):

| Source | What it establishes |
| --- | --- |
| `src/virtual_factory/shwtp/{structural,connectivity,runtime,logical_runtime,projection,federation,evaluation,overlay,expansion,bridge,session}.py` | canonical SH-WTP workspace, 28-scope structural tree, T106/T108 runtimes, F01 projection, 2-participant federation, evaluation rows, G18 overlay, G21 5-scope runnable slice, G22 bridge + session |
| `configs/vnext/shwtp/shwtp_readiness_scope.json` | the PIM-derived inventory: canonical IDs, `pim_canonical_id`, `pim_reference`, `vf_scope_role`, `fidelity_ceiling`, `evidence.status`, `gaps`, `runtime_later`, plus the `pim_authority` / boundary-contract policy and `support` tags |
| `configs/vnext/shwtp/shwtp_expansion_readiness.json`, `shwtp_synthetic_runtime_admission.json`, `shwtp_workstream_independence_review.json` | readiness rationale per unit, admission scope rule (no control/interlock equivalence granted), T108→DIST-P108 `STILL_INSUFFICIENT` finding |
| `simulators/wtp/**` + `docs/wtp-simulator-design.md` + `docs/wtp-simulation-model.md` | the legacy VF-1 standalone WTP simulator: 8 stages, 92 signals (MV 12 / DV 7 / PV 43 / KPI 30), all stage equations, actuator model, scenario set, HTTP API (port 8100) |
| `.ai-harness/sa-review/evidence/SHW-VF-PH00/**`, `SHW-PIM-EXPORT-01/**`, `VF-ARCH-06/**` | inventory/gap/fidelity/disposition evidence used by this freeze |
| `.ai-harness/regression/vnext_baseline_manifest.json` + `tests/test_vnext_g1{0,1,2,21}_*.py` | pinned structural/executable-slice contracts |
| `configs/model_types/{pid_controller,control_valve,valve_actuator,tank,centrifugal_pump}_v1.yaml` | existing reusable model-type contract vocabulary for controllers/actuators/assets |

Machine-generated companions to this report: `evidence/VF-SHW-X0/01-inventory.json`,
`02-topology-matrix.json`, `03-control-matrix.json` (full loop contracts), `04-no-new-pim-id-proof.json`,
`05-no-code-change-proof.json`.

---

## 1. Current SH-WTP asset / process / runtime inventory

Two SH-WTP worlds exist and **do not import each other**:

### 1.1 Legacy standalone simulator (VF-1, reference-only → future deprecation)
| Aspect | Fact |
| --- | --- |
| Location / entry | `simulators/wtp/main.py` (`WtpSimulatorApp`, `main()`); `simulation_loop.py` = **8-stage orchestrator** (`PHASE 0 DVs → PHASE 1 MVs → STAGE 1..8`) |
| Signals | **92**: MV **12**, DV **7**, PV **43**, KPI **30** (`signal_registry.py`) |
| Engines | `actuator_engine`, `disturbance_engine`, `clarification_engine`, `filtration_engine`, `disinfection_engine`, `energy_engine`, `kpi_engine`, `scenario_manager` |
| Plant id / port | `WTP-DEMO-01`; FastAPI `api_server.py` on **8100**; optional OPC UA `opc.tcp://0.0.0.0:4841`; optional push of measurements to PlantOS `POST /api/v1/measurements/ingest` |
| Control model | operator setpoints only + actuator SP→MV with **slew rate + accuracy**; binary on/off where `slew_rate<=0`; **no PI/PID** |
| Authority | **not** a platform workspace; disposition `reference only → future deprecation` (VF-ARCH-06/07) |

### 1.2 Canonical vNext SH-WTP package (the ONE authority today)
| Module | Role |
| --- | --- |
| `structural.py` | `build_shwtp_workspace` — workspace `shwtp`, plant `PLANT-SHW`, **28 scopes** from the frozen G10 plan; `vf_local_id()` maps a PIM canonical id to a VF-local scope id; containment `_CONTAINMENT_BY_CANONICAL` |
| `connectivity.py` | G12B reference graph `REL-SHW-F01..F07`, **inert** (`runtime_effect=none`), oracles for PIM-context coherence |
| `runtime.py` | `T108TankRuntime` — **first_order** tank (`UNIT-SHW-L1-T108`, path `shwtp/line1/l1_t108`) |
| `logical_runtime.py` | `T106LogicalRuntime` — **logical_only** pass-through (`shwtp/line1/l1_t106`) |
| `projection.py` / `federation.py` | G14A T106→T108 projection (2 BoundaryPorts + 1 binding, inert); G14B 2-participant `explicit_lagged` federation |
| `evaluation.py` | per-window evaluation rows incl. `t106_/t108_origin_kind|data_status|fidelity` and `mass_balance_residual_m3` |
| `overlay.py` | G18 T108→DIST-P108 **assumed** topology edge (`source_kind="vf_scenario_assumption"`, reversible) |
| `expansion.py` | G21 runnable **5-scope** plant slice: `shwtp/raw_water/raw_intake`, `shwtp/raw_water/t100`, `shwtp/line1/l1_t106`, `shwtp/line1/l1_t108`, `shwtp/dist_p108` (2 `first_order`, rest `logical_only`; `status` `accepted`/`scenario_assumed`; `inbound_link_assumed` flags) |
| `bridge.py` | `ShwtpExecutionBridge` — **orchestration only; slice runtimes remain the domain-truth owners** |
| `session.py` | `build_shwtp_session(scenario_id="shwtp-g21-slice", workspace_id="shwtp")` → one `RunLifecycleService` + one `RuntimeSession`; registry key `shwtp` in `ui/workspace_monitor.py` |

**Runtime authority today:** exactly one canonical SH-WTP session (registry `shwtp`) over the 5-scope slice; the
generic `runcontrol` package never references SH-WTP; SH-WTP owns its own package.

### 1.3 UI surface today
`_shwtp_view_extra()` returns `runtime: "SH-WTP G21 plant slice"`, `structure`, `values`, `site_truth: False`,
`assumed_topology`, **`ui_page: None`** (pinned by `tests/test_vnext_g24_workspace_ui.py`). No SH-WTP static
asset exists. Accepted audit wording: *"SH-WTP has no dedicated UI page: selecting `shwtp` shows the generic
monitor table"* (I2, MINOR, owner = SH-WTP expansion gate).

---

## 2. Whole-plant Area → Process → current unit mapping

Source: `configs/vnext/shwtp/shwtp_readiness_scope.json` inventory + `structural.py::_CONTAINMENT_BY_CANONICAL`
+ `connectivity.py` relations. **Nothing below is invented** — every canonical ID already exists in the repo
(proof: `04-no-new-pim-id-proof.json`).

| Area (canonical) | Unit (canonical) | Process role (evidence) | Runtime today | Containment | Relation evidence |
| --- | --- | --- | --- | --- | --- |
| `AREA-SHW-RAW-WATER` | `UNIT-SHW-RAW-INTAKE` | raw-water intake / raw pumping | none | explicit | `REL-SHW-F04` aggregate `RAW→T100` (DocumentConfirmed) |
| `AREA-SHW-RAW-WATER` | `UNIT-SHW-T100` | receiving / raw storage junction | none | explicit | `REL-SHW-F04` `T100→L1` aggregate (DocumentConfirmed) |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T101` | aeration | none | explicit | unit-level relation **not established** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T102` | PAC contact | none | explicit | `REL-SHW-F07` chemical input side (PatternInferred) |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T103` | rapid mix / coagulant dosing point | none | explicit | unit-level relation **not established** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T104` | flocculation | none | explicit | unit-level relation **not established** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T105` | lamella clarification / sedimentation | none | explicit | `T105→T106` adjacency **VF-inferred** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T106` | OSF filtration | `T106LogicalRuntime` (logical_only) | explicit | **`REL-SHW-F01` T106→T108 (DocumentConfirmed)** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T107` | disinfection / chlorine contact | none | explicit | in-line position vs F01 **PIM-ambiguous** |
| `AREA-SHW-LINE1` | `UNIT-SHW-L1-T108` | clean-water storage tank | `T108TankRuntime` (first_order) | explicit | **`REL-SHW-F01` target (DocumentConfirmed)** |
| `AREA-SHW-LINE1` | `UNIT-SHW-WASH-T110` | wash-water recovery | none | explicit | return destination **VF-inferred** (PIM confirmation required before first-order use) |
| `AREA-SHW-LINE2` | `UNIT-SHW-L2-T101/T105/T106/T108` | LINE2 equivalents | none | explicit | **PatternInferred**, low confidence |
| `AREA-SHW-CHEMICAL` | `UNIT-SHW-CHEM-DOSING` | chemical dosing | none | explicit | `REL-SHW-F07` PatternInferred; procedure truth gap `GAP-SHW-009` |
| `AREA-SHW-SLUDGE` | `UNIT-SHW-SLUDGE-T201` | sludge treatment sink | none | explicit | `REL-SHW-F06` PatternInferred |
| `AREA-SHW-ELECTRICAL` | `UNIT-SHW-ELEC-MCC` | MCC / VSD reference | none | explicit | IndustryExpected; `GAP-SHW-005` |
| `AREA-SHW-AUTOMATION` | `UNIT-SHW-AUTO-PLC` | PLC / SCADA reference | none | explicit | IndustryExpected; **control truth unavailable `GAP-SHW-002`** |
| (plant level) | `UNIT-SHW-DIST-P108` | distribution pumping / outlet manifold | none | plant root | `REL-SHW-F05` aggregate `L1→DIST` (DocumentConfirmed); exact unit-level edge **not established** |

**Operational process view used by this freeze** (water path, in flow order — VF operational reading, not a
site claim):

`RAW-WATER intake (RAW-INTAKE → T100)` → `LINE1: T101 aeration → T102 PAC contact → T103 rapid mix →
T104 flocculation → T105 clarification` → `LINE1: T106 filtration → T107 disinfection → T108 clean water` →
`DIST-P108 distribution`; side streams `CHEMICAL dosing → T102/T103/T107`, `SLUDGE T201 ← T105`,
`WASH-T110 ← T106 backwash`; reference-only areas `ELECTRICAL`, `AUTOMATION`; parallel `LINE2` (shallow).

---

## 3. Known / assumed / unknown topology matrix

Status vocabulary reused from the repo (no new vocabulary): `DocumentConfirmed | PatternInferred |
IndustryExpected` (PIM evidence), plus VF's own mechanism `source_kind="vf_scenario_assumption"` for
VF-assumed edges (reversible, fail-closed, never claimable as DocumentConfirmed).

| # | Edge | Status today | Evidence | X0 disposition |
| --- | --- | --- | --- | --- |
| E1 | `T106 → T108` | **known / DocumentConfirmed** | `REL-SHW-F01`; G14A projection; G14B federation | keep as the backbone of Deep Scope A; no assumption needed |
| E2 | `RAW-INTAKE → T100` | **known (aggregate)** | `REL-SHW-F04` | used as-is; unit-level detail remains VF-modelled hydraulics |
| E3 | `T100 → LINE1` | **known (aggregate)** | `REL-SHW-F04` | entry edge of the LINE1 chain |
| E4 | `LINE1 → DIST-P108` | **known (aggregate)** | `REL-SHW-F05` | used as the distribution boundary |
| E5 | `T108 → DIST-P108` (unit level) | **unknown / STILL_INSUFFICIENT** | `shwtp_workstream_independence_review.json`; `overlay.py` | modelled as **VF-assumed** edge with explicit label; PIM escalation not required for a *synthetic* upstream→outlet abstraction, but the assumption must stay visible |
| E6 | `T101 → T102 → T103 → T104 → T105` internal LINE1 order | **unknown at unit level** (units are DocumentConfirmed, their serial order is not) | inventory `note` fields; no unit-level relations | modelled as **VF-assumed serial process chain** (engineering-plausible reading of a conventional water-treatment line); labellable and reversible |
| E7 | `T105 → T106` | **inferred (VF)** | readiness rationale only | VF-assumed adjacency; feeds Deep Scope A boundary |
| E8 | `T106 → T107 → T108` vs `T106 → T108` direct | **PIM-ambiguous** (disinfection in-line position unproven) | F01 target is T108 | default: T107 modelled **in-line** between T106 and T108 (VF-assumed); alternative (T107 parallel/off-path) recorded as SA awareness item Q1 |
| E9 | `T106 → WASH-T110` backwash + return destination | **unknown return destination** | `shwtp_synthetic_runtime_admission.json` (T110 rationale) | VF-assumed wash-water return to RAW-WATER/T100 (recovery); explicitly scenario-labelled |
| E10 | `CHEM-DOSING → T102/T103/T107` | **PatternInferred** | `REL-SHW-F07` | kept as VF-assumed dosing points; dosing *procedure/step* truth gap `GAP-SHW-009` stays open |
| E11 | `T105 → SLUDGE-T201` | **PatternInferred** | `REL-SHW-F06` | shallow C1 withdrawal; no sludge-quality claim |
| E12 | LINE2 internal chain | **PatternInferred (low)** | inventory | modelled **shallow/aggregate** (single "LINE2 process block"); no deep claim |
| E13 | ELECTRICAL / AUTOMATION internals | **IndustryExpected, reference-only** | inventory (`GAP-SHW-002`, `-005`) | represented as reference areas + electrical proxy values only; never as control truth |
| E14 | Raw-water **external** source (river/reservoir boundary) | **unknown / out of scope** | no PIM data | C0 source boundary with synthetic disturbance/scenario inputs |
| E15 | Plant-level KPI/quality chain | **unknown** | `GAP-SHW-004` (lab history) | synthetic/reference proxies only; no compliance claim (see §9 failure/quality handling) |

**Unknown-set summary (all remain explicitly unknown at freeze):** PLC/SCADA tag export (`GAP-SHW-001`),
PLC code & interlock matrix (`GAP-SHW-002`), hydraulic parameters (`GAP-SHW-003`), raw-water/lab quality
history (`GAP-SHW-004`), electrical mapping (`GAP-SHW-005`), chemical procedure step (`GAP-SHW-009`),
VF readiness params (`GAP-SHW-010`), calibration (`GAP-SHW-012`).

---

## 4. Fidelity matrix — PIM-supported ceiling vs proposed VF synthetic/reference fidelity

Two separate concepts, never conflated (per the contract). **VF fidelity may never exceed the PIM evidence
ceiling in the claim it makes; VF may still build a richer *synthetic* model as long as it is labelled as
such and never presented as site truth.**

| Scope | PIM evidence ceiling (claim ceiling) | Proposed VF synthetic/reference fidelity | Justification | Resulting label |
| --- | --- | --- | --- | --- |
| `PLANT-SHW` / Areas | structural + aggregate relations only | process graph (VF operational reading) | plan a coherent operational view without inventing canonical IDs | `synthetic_reference` + `site_truth=false` |
| `UNIT-SHW-RAW-INTAKE` | unit DocumentConfirmed, no dynamics | **first_order** pump/flow abstraction (C2 loop) | pumping dynamics are plausibly representable | `synthetic_reference` → `first_order` (VF) |
| `UNIT-SHW-T100` | unit DocumentConfirmed, no volume/hydraulics | **first_order** tank volume balance | storage/residence is plausibly representable; `GAP-SHW-003` blocks "real" hydraulics | `synthetic_reference` → `first_order` (VF) |
| `UNIT-SHW-L1-T101` | unit DocumentConfirmed | `logical_only` residence/quality proxy | no data; keeps the chain physically causal | `logical_only` |
| `UNIT-SHW-L1-T102/T103/T104` | units DocumentConfirmed | `logical_only` / `synthetic_reference` dose–turbidity proxies | `GAP-SHW-009` blocks procedure truth | `synthetic_reference` (labelled) |
| `UNIT-SHW-L1-T105` | unit DocumentConfirmed | `synthetic_reference` settling proxy | plausible first-order settling without calibrated coefficients | `synthetic_reference` |
| `UNIT-SHW-L1-T106` | unit DocumentConfirmed; **logical_only today** | **`synthetic_reference` → `first_order` filter train** (loading/DP/backwash) | the filtration physics that matters (head loss growth, breakthrough) can be represented plausibly as a VF hypothesis | `synthetic_reference`/`first_order` (VF), explicitly not site-calibrated |
| `UNIT-SHW-L1-T107` | unit DocumentConfirmed; in-line position ambiguous | `synthetic_reference` chlorine demand/residual + CT proxy | disinfection reasoning is standard and testable for plausibility | `synthetic_reference` (edge VF-assumed) |
| `UNIT-SHW-L1-T108` | unit DocumentConfirmed; **first_order runtime exists** | **keep `first_order`** (volume balance) and extend with C2 level control | already accepted in G13/G21/G22 | `first_order` (existing) |
| `UNIT-SHW-WASH-T110` | unit DocumentConfirmed; return unknown | `logical_only` recovery/return routing | must stay reversible until PIM confirms the destination | `logical_only` (VF-assumed edge) |
| `UNIT-SHW-L2-*` | PatternInferred | **aggregate shallow block** (`logical_only`) | low confidence; do not over-claim a second full line | `logical_only` |
| `UNIT-SHW-CHEM-DOSING` | PatternInferred; `GAP-SHW-009` | `logical_only` ratio control | plausibility only | `logical_only` |
| `UNIT-SHW-SLUDGE-T201` | PatternInferred | `logical_only` duty cycle | sink/side-stream plausibility | `logical_only` |
| `UNIT-SHW-ELEC-MCC` | IndustryExpected, reference | `reference_only` (proxy values at most) | no mapping available | `reference_only` |
| `UNIT-SHW-AUTO-PLC` | IndustryExpected, **control truth unavailable** | `reference_only`; **all control is VF synthetic** | must never imply site logic | `reference_only` + control `synthetic_reference` |
| `UNIT-SHW-DIST-P108` | aggregate DocumentConfirmed; unit level not established | `synthetic_reference` pump/outlet abstraction | boundary plausibility | `synthetic_reference` |

**Fidelity rules frozen:** (a) no `SourceMapped`/`SiteVerified` claim exists in the model and none may be
made; (b) every VF-introduced asset/loop carries `provenance=simulation`, `simulation_truth=synthetic_reference`,
`site_truth=false`; (c) PIM canonical IDs are **read-only references**; (d) newly introduced runtime objects
without PIM authority use **VF-local runtime identity only** (never a PIM-shaped id — see §6).

---

## 5. Deep scopes — frozen selection and rationale

### Deep Scope A — LINE1 downstream treatment: filtration → clean water (`T106 → T108` centered)
**Frozen as the primary deep scope.** Rationale (all repo-backed):
- `REL-SHW-F01` `T106 → T108` is **PIM DocumentConfirmed** — the only deep process edge with that status.
- Existing VF runtime value to build on: `T106LogicalRuntime` (logical_only), `T108TankRuntime` (first_order),
  G14A projection, G14B `explicit_lagged` federation, G15 evaluation rows with `mass_balance_residual_m3`
  (an existing plausibility oracle), G21 slice membership, G22 bridge + session.
- The region contains the two most legible treatment dynamics for a demo/what-if model: **filter loading +
  backwash** and **storage/level + transfer pumping**.
**Proposed boundary (frozen):** `T105 → T106` (VF-assumed inlet edge, E7) … `T106 → T107 → T108` (E8 VF
in-line default) … `T108 → DIST-P108` (E5 VF-assumed outlet edge), plus `WASH-T110` as the backwash receiver
(E9, recoverable return). Boundary edges are labelled VF-assumed and reversible.

### Deep Scope B — RAW WATER intake / receiving / pumping (`RAW-INTAKE` + `T100` centered)
**Frozen as the secondary deep scope.** Rationale:
- Hydraulic storage and pumping dynamics can be represented **plausibly with simple first-order/algebraic
  models** without site hydraulic parameters (`GAP-SHW-003` stays open, and that is acceptable).
- Both units are `DocumentConfirmed` structurally and are already in the G21 executable slice
  (`shwtp/raw_water/raw_intake`, `shwtp/raw_water/t100`), so the canonical paths already exist.
- It exercises `REL-SHW-F04` (aggregate, DocumentConfirmed) as the upstream boundary.
**Proposed boundary (frozen):** external raw-water **source at C0** → intake train (screens/pumps, C1+C2) →
`T100` storage (C2 level) → LINE1 feed edge (aggregate F04) ; screens/pump duty-standby modelled as
functional C1 sequences.

**Why not LINE2 or CHEMICAL/SLUDGE as deep scopes (frozen decision):** their connectivity is
`PatternInferred` (low confidence) and their truth gaps are wider (`GAP-SHW-009` for chemical procedure,
`F06` inferred for sludge) — they stay **shallow/aggregate** (C0/C1), which satisfies "physically/operationally
reasonable" without over-claiming.

---

## 6. Proposed Key Assets per deep scope

Rules: **Key Asset = asset-level (not sub-asset) runtime object.** A Key Asset that maps to an existing
canonical unit keeps that **read-only PIM reference**; a Key Asset with no PIM authority gets a **VF-local
runtime identity** (`vf-shw-…`, derived with the existing `vf_local_id()` convention for scopes and a VF-local
id for runtime objects) and is labelled `scenario/reference object — not a PIM canonical asset`.
**No new canonical PIM ID is introduced anywhere.**

### 6.1 Deep Scope A (T106 → T108 centered)
| # | Proposed Key Asset | Class / abstraction | PIM authority | Key states / outputs | Fidelity |
| --- | --- | --- | --- | --- | --- |
| A1 | `UNIT-SHW-L1-T106` **filter train** | filter/train abstraction (multi-media bed) | **yes** (read-only canonical reference) | inlet flow, DP/head loss, loading, effluent turbidity proxy, time-since-backwash, backwash state | `synthetic_reference` → `first_order` |
| A2 | `UNIT-SHW-L1-T108` **clean-water tank** | tank/basin (volume balance) | **yes** | level, volume, in/out flow, residence proxy | `first_order` (existing runtime preserved) |
| A3 | `vf-shw-l1-filter-inlet-valve-01` **filter inlet control valve** | inlet control valve | no → VF-local synthetic | position %, commanded SP, fail direction (VF assumption) | `synthetic_reference` |
| A4 | `vf-shw-l1-transfer-pump-01` (+ duty/standby twin) | transfer/distribution pump or VFD pump abstraction | no → VF-local synthetic | speed %, flow, discharge pressure proxy, run state, motor current proxy | `synthetic_reference` |
| A5 | `UNIT-SHW-L1-T107` **disinfection contact** | contact basin / chemical contact | **yes** | residual proxy, CT proxy, contact time, dose command | `synthetic_reference` |
| A6 | `UNIT-SHW-WASH-T110` **wash-water recovery** | receiver tank + return routing | **yes** (return = VF-assumed) | level, backwash inflow, return flow | `logical_only` |
| A7 | `UNIT-SHW-DIST-P108` **outlet/distribution boundary** | pump curve + manifold abstraction | **yes** (unit-level edge VF-assumed) | discharge pressure, outlet flow, pump speed | `synthetic_reference` |
| A8 | Instruments (`T106-TURB-01`, `T106-DP-01`, `T108-LT-01`, `T108-FT-01`, `T107-CL-01`) | **signals, not sub-assets** | no → VF-local signal ids | measured-value signals consumed by loops/UI | `synthetic_reference` |

### 6.2 Deep Scope B (RAW WATER intake / T100 centered)
| # | Proposed Key Asset | Class / abstraction | PIM authority | Key states / outputs | Fidelity |
| --- | --- | --- | --- | --- | --- |
| B1 | `UNIT-SHW-RAW-INTAKE` **intake train** | intake structure + screen + raw pumps | **yes** | screen differential, pump run/stop, total intake flow | `synthetic_reference` |
| B2 | `UNIT-SHW-T100` **receiving tank** | tank/basin (volume balance) | **yes** | level, volume, inflow/outflow | `first_order` |
| B3 | `vf-shw-raw-pump-01/-02` **raw-water pump pair** (duty + standby) | centrifugal pump + VFD | no → VF-local synthetic | speed %, flow, head/pressure proxy, run hours, fault state | `synthetic_reference` |
| B4 | `vf-shw-raw-inlet-valve-01` **intake inlet valve** | inlet control valve | no → VF-local synthetic | position %, fail direction (VF assumption) | `synthetic_reference` |
| B5 | `vf-shw-raw-screen-scraper-01` **screen scraper** | binary actuator | no → VF-local synthetic | run/stop, differential contribution | `synthetic_reference` |
| B6 | Instruments (`T100-LT-01`, `RAW-FT-01`, `RAW-PT-01`, `RAW-TURB-01`) | **signals, not sub-assets** | no → VF-local signal ids | level/flow/pressure/turbidity proxies | `synthetic_reference` |

**Explicitly out of scope at X0:** sub-asset internals (individual filter laterals, valve internals, motor
windings), vendor/device emulation, and any canonical-ID proposal.

---

## 7. Whole-plant C0/C1/C2 control matrix

Full machine-readable matrix + per-loop contracts: `evidence/VF-SHW-X0/03-control-matrix.json`.
Levels (as frozen by the contract): **C0** = no active controller, source/sink/reference only; **C1** =
functional control (on/off, setpoint logic, permissives/interlocks, duty/standby, timers, rule/proportional);
**C2** = dynamic PI/PID for selected important loops inside the deep scopes.

| Scope | Level | Loops | One-line rationale |
| --- | --- | --- | --- |
| `UNIT-SHW-RAW-INTAKE` | **C2** + C1 | B-L1 (via T100 level), B-L3 (duty/standby + screen) | intake pumping is a core deep-scope dynamic |
| `UNIT-SHW-T100` | **C2** | B-L1 level, B-L2 flow | storage + feed control is plausibly modelled |
| `UNIT-SHW-L1-T101` | C1 | P-L1 residence | keep the chain causal without over-modelling |
| `UNIT-SHW-L1-T102/T103` | C1 | P-L2 dose ratio (+optional trim) | chemical truth gap → plausibility only |
| `UNIT-SHW-L1-T104` | C1 | — (pass-through + floc time proxy) | low information content |
| `UNIT-SHW-L1-T105` | C1 | P-L3 sludge withdrawal | side-stream plausibility |
| `UNIT-SHW-L1-T106` | **C2** + C1 sequence | A-L2 inlet flow; A-L3 backwash sequence | filtration loading/backwash is the deep-scope physics |
| `UNIT-SHW-L1-T107` | C1 (C2 optional) | P-L4 residual/CT | compliance proxy; upgrade optional (Q3) |
| `UNIT-SHW-L1-T108` | **C2** | A-L1 level (transfer pump) | existing first_order tank + a real level loop |
| `UNIT-SHW-WASH-T110` | C1 | A-L3 duty | recovery routing stays rule-based |
| `UNIT-SHW-L2-*` | C1 (aggregate) | — | low-confidence topology → shallow |
| `UNIT-SHW-CHEM-DOSING` | C1 | P-L2, P-L4 | ratio control only |
| `UNIT-SHW-SLUDGE-T201` | C1 | P-L5 | duty cycle |
| `UNIT-SHW-ELEC-MCC` | **C0** | — | reference only (`GAP-SHW-005`) |
| `UNIT-SHW-AUTO-PLC` | **C0** | — | **control truth unavailable (`GAP-SHW-002`)** — never site logic |
| `UNIT-SHW-DIST-P108` | C1 (C2 for A-L4) | A-L4 pressure/flow | boundary loop, VF-assumed edge |
| External raw-water source / final distribution network | **C0** | — | pure source/sink boundaries |

---

## 8. Proposed PI/PID loops

12 loop contracts are frozen in `03-control-matrix.json`; each carries the contract minimum:
**PV, SP, MV, controller type, gains, scan time, output limits/saturation, anti-windup, deadband/rate limit,
AUTO/MANUAL with bumpless transfer, init/reset semantics, permissives, interlocks, alarm thresholds,
synthetic-tuning status.** Summary:

| Loop | Scope (deep scope) | Type | PV → MV | Level | Key constraints |
| --- | --- | --- | --- | --- | --- |
| **B-L1** | T100 (B) | PI | level [m] → raw pump speed [%] | C2 | [0,100] %, ramp ≤5 %/s, LALL stop / LAHH stop, deadband 0.02 m |
| **B-L2** | T100 (B) | PI | intake flow [m³/h] → pump VFD / inlet valve [%] | C2 | curve-limited, conditional integration, dry-run + high-pressure interlocks |
| **B-L3** | RAW-INTAKE (B) | rule | run state / screen DP → pump start-stop, scraper | C1 | min run/rest timers, alternation, hysteresis |
| **A-L1** | T108 (A) | PI | level [m] → transfer pump speed [%] | C2 | pump min/max, LALL stop / LAHH inhibit, deadband 0.02 m |
| **A-L2** | T106 (A) | PI | filter inlet flow [m³/h] → inlet valve [%] | C2 | 0–100 % stroke ≤10 %/s, DP high-high interlock, fail direction = VF assumption |
| **A-L3** | T106 + WASH-T110 (A) | rule sequence | DP/turbidity/time → backwash pump + valves | C1 | step timers, one-train-at-a-time, wash-water level permissive |
| **A-L4** | T108 → DIST-P108 (A) | PI | discharge pressure [bar] → HSP speed [%] | C2 | curve-limited, 0.05 bar deadband, overpressure trip, T108 LALL stop |
| **P-L1** | T101 | rule | level/residence → valves | C1 | level band hysteresis |
| **P-L2** | CHEM → T102/T103 | ratio (+trim) | flow → dose stroke [%] | C1 | dose clamps, tank low-low stop, overdose guard |
| **P-L3** | T105 → SLUDGE-T201 | rule | blanket/timer → sludge pump | C1 | min rest, high-pressure stop |
| **P-L4** | T107 | proportional | residual/CT → chlorine dose [%] | C1 | residual band + CT minimum alarms (not trips) |
| **P-L5** | SLUDGE-T201 | rule | level band → transfer pump | C1 | min run/rest |

**Control truth boundary (frozen):** all gains/timings are **`synthetic_reference`** engineering defaults;
the design explicitly does **not** claim vendor/PLC-equivalent tuning, does not emulate a PLC/DCS scan model,
and keeps a future mapping seam (process tag ↔ VF-local controller id ↔ PV/SP/MV ↔ provenance) so real
P&ID/PLC/DCS evidence can be bound later without redesign.

---

## 9. Whole-plant process / state-variable contract

Generic contract (frozen; **every** scope must instantiate it, shallow scopes included):

```yaml
scope: <canonical unit id | VF-local synthetic id>
vf_path: <canonical path (shwtp/...)>          # existing structural path or X1-proposed path
inputs:      [{name, unit, source_scope, signal_id}]
outputs:     [{name, unit, sink_scope, signal_id}]
state:       [{name, unit, initial, bounds}]
parameters:  [{name, unit, value, provenance: synthetic_reference, assumption_id}]
constraints: [{name, min, max, kind: physical|operational|safety(VF)}]
update:      <equation | state transition | rule>   # explicit, deterministic
fidelity:    logical_only | synthetic_reference | first_order   # existing vocabulary only
provenance:  {origin_kind: simulation, data_status: SYNTHETIC|SIMULATED_GROUND_TRUTH,
              simulation_truth: synthetic_reference, site_truth: false}
assumptions: [{assumption_id, statement, reversible: true, evidence_status}]
failure:     {invalid_state_action, saturated_output_behavior, alarm, freeze_or_degrade}
control:     {level: C0|C1|C2, loops: [ids], permissives: [], interlocks: []}
```

Per-scope instantiation (frozen summary; full equations land in X1's process-contract artefacts, not in X0):

| Scope | Inputs → Outputs | Primary state | Update (frozen intent) | Fidelity |
| --- | --- | --- | --- | --- |
| RAW-INTAKE | source flow/quality, pump speed → intake flow, screen DP | pump speed, screen DP, run hours | algebraic pump/flow relation + screen DP first-order build-up; duty rules | `synthetic_reference` |
| T100 | intake flow, outlet demand → tank outflow, level | level, volume | **volume balance**: `dV/dt = Qin − Qout`; level = V/A (existing tank pattern) | `first_order` |
| T101 | inlet flow, level → outlet flow, residence | level, contact time | level band + residence accumulator; quality proxy unchanged through contact | `logical_only` |
| T102/T103 | flow, dose command → dose applied, turbidity proxy | dose ratio, mixing index | ratio dosing + first-order proxy response (bounded, monotone) | `synthetic_reference` |
| T104 | flow, mixing → floc time index | floc index | residence-time accumulator | `logical_only` |
| T105 | flow, floc index → settled turbidity, sludge volume | blanket proxy, sludge volume | settling proxy + sludge accumulation; withdrawal removes volume | `synthetic_reference` |
| T106 | inlet flow, turbidity, backwash state → filtered flow, effluent turbidity, DP | DP, loading, time-since-backwash, backwash step | **DP growth** first-order; efficiency from loading; backwash resets DP with bounded water use | `synthetic_reference` → `first_order` |
| T107 | filtered flow, chlorine dose → residual, CT | residual, contact time | demand (ammonia/organic) → residual; `CT = residual × contact_time` | `synthetic_reference` |
| T108 | inflow, transfer pump speed, demand → outflow, level | level, volume | **volume balance** (existing first_order tank preserved) | `first_order` |
| WASH-T110 | backwash inflow, return flow → level | level | volume balance with bounded return | `logical_only` |
| DIST-P108 | pump speed, network demand proxy → pressure, outlet flow | speed, pressure | pump curve + manifold loss (algebraic) | `synthetic_reference` |
| L2 aggregate | L1 surplus → L2 throughput proxy | aggregate throughput | single shallow block (no internal chain claim) | `logical_only` |
| CHEM-DOSING | demand signals → dose commands, tank level | tank level, dose ratio | ratio + tank drawdown | `logical_only` |
| SLUDGE-T201 | sludge inflow → treated outflow proxy, level | level | duty-cycle drawdown | `logical_only` |
| ELEC-MCC / AUTO-PLC | — | reference values only | no state ownership (reference blocks) | `reference_only` |

**Engineering-reasonableness rules frozen for ALL scopes** (including shallow): mass/volume balance where
storage exists; bounded outputs (no negative flow/volume, clamps at limits); plausible residence/storage
behaviour; causal monotonicity (effect follows cause in time); deterministic reduction on reset; and explicit
invalid-state behaviour (saturate + alarm + labelled degradation, never silent nonsense).

---

## 10. Frame A / Frame B UI information architecture (SH-WTP)

Same **product principles** as ASSY (canonical identity, one session, projection/command only, explicit
fidelity/provenance, no on-load reset/advance, presentation-only selection), **not** the ASSY layout.

### Frame A — Whole-Plant Process Overview (SH-WTP)
- **Layout:** Areas/Processes arranged by **water/process flow** (RAW-WATER → LINE1 → DIST, with CHEMICAL,
  SLUDGE, WASH as side streams; ELECTRICAL/AUTOMATION as reference chips; LINE2 as a parallel shallow block).
- **Animated main flow** in the process direction, with per-block state colour (running/steady/alarm/fault/off).
- **Per-block readouts:** flow, level/storage, selected water-quality proxies (turbidity, residual), state,
  alarm presence, control mode (AUTO/MANUAL) where relevant.
- **Fidelity/provenance indicators:** per-block badge (`first_order`, `synthetic_reference`, `logical_only`,
  `reference_only`), an explicit `site_truth=false` banner and an `assumed_topology` marker for VF-assumed
  edges (T105→T106, T107 in-line, T108→DIST-P108, WASH return).
- **Drill-down:** click a block → Frame B (deep scopes A/B fully detailed; shallow blocks show their contract
  card).
- **Runtime identity:** the SAME canonical SH-WTP `RuntimeSession` (`workspace_id=shwtp`, one `run_id`) with
  `selection_is_presentation_only` semantics (R4/R5 pattern) — no independent simulator, no second session.
- **Run controls:** the canonical STEP/RESET/STOP/NEW ATTEMPT/REPLAY seam only (as in the workspace shell).

### Frame B — Process / Area Detail (deep scopes)
- **Key Assets** of the selected deep scope laid out on a process flow (assets + major pipes/flows).
- **Loop panels:** PV / SP / MV, AUTO/MANUAL (bumpless), output saturation indicator, permissive/interlock and
  alarm state for the loops of that scope (A1–A4/B1–B4).
- **Asset detail:** tank level/storage, valve position, pump speed/run state, filter DP + backwash state.
- **Compact trends/history** per selected signal (bounded window; read-only projection).
- **Scenario/disturbance impact** view (what-if deltas vs the labelled baseline), always labelled
  `synthetic_reference`.
- **Same identity + no separate runtime** (Frame B never constructs a session; it projects the canonical one).

**UI architecture rules frozen:** the UI is a **projection/controller over the one canonical runtime**;
`ui_page` becomes `/shwtp-demo` (or equivalent single canonical page) in X5 — *not implemented in X0*; the
existing monitor-only shell view remains valid until X5 lands.

---

## 11. Implementation gate sequence X1..X7 — validated and refined

| Gate | Scope | Depends on | Exit criteria (frozen) |
| --- | --- | --- | --- |
| **X1** | Whole-plant process graph + scope/fidelity/control contracts (no rich UI, no new dynamics) | X0 (this freeze) | every scope instantiated against §9 contract; VF-assumed edges registered through the existing `vf_scenario_assumption` mechanism; fidelity/labels per §4; **PIM escalation checkpoint**: confirm no PIM change is required, else STOP |
| **X2** | Whole-plant **shallow runnable** model with **C1** functional control, ONE `RuntimeSession` | X1 | plant runs end-to-end on the canonical session; conservation/bounds/monotonicity plausibility checks green; no new authority; no second session |
| **X3** | **Deep Scope A** (LINE1 T106/T108) Key Assets + **C2 PI/PID** loops | X2 (+X1 contracts) | A-L1/A-L2/A-L4 dynamic loops + A-L3 sequence; saturation/anti-windup/mode-transfer tests; filter DP/backwash plausibility; T108 first_order semantics preserved |
| **X4** | **Deep Scope B** (RAW WATER/T100) Key Assets + pump/tank control | X2 (+X1 contracts) | B-L1/B-L2 dynamic loops + B-L3 duty/standby + screen management; storage/pump plausibility tests |
| **X5** | SH-WTP rich UI **Frame A** (whole-plant process view) bound to the canonical session | X2 (**static layout skeleton may be prepared in X1 as design**) | Frame A renders the plant graph with flow animation, fidelity/provenance badges, drill-down entry; identity from the canonical session; presentation-only selection proven |
| **X6** | **Frame B** deep-area views, controller panels, trends/alarms/scenario visualization | X3 + X4 + X5 | loop panels (PV/SP/MV/mode), asset detail, trends, scenario impact; no separate runtime constructed |
| **X7** | Integrated scenarios, regression, plausibility evaluation, end-to-end browser validation | X3 + X4 + X5 + X6 | scenario matrix green; evaluation oracles (incl. mass-balance) green; baseline/full suite green; browser validation clean; report to SA |

**Refinements made in X0 (validation, not reinterpretation):**
1. **X3 and X4 are independent of each other** once X2 lands → they can run in either order or in parallel.
2. **X5 depends on X2, not on X3/X4**: Frame A is a whole-plant projection; its *layout skeleton* can be
   designed inside X1 and implemented right after X2, in parallel with X3/X4. This shortens the critical path.
3. **X6 strictly depends on X3+X4+X5** (it visualises deep-scope detail and reuses Frame A navigation).
4. **X1 must carry the PIM escalation checkpoint** (read-only assessment; any required PIM semantic/code change
   stops the series and is escalated — see §12).
5. **X7 gates on plausibility oracles, not only tests** (the repo already has the mass-balance oracle from G15;
   extend it to the new scopes).
6. No gate may introduce a second workspace/session authority, and none may claim site truth.

---

## 12. STOP decisions / questions for SA

**Assessment: no architecture or product decision remains that blocks X1** — the frozen architecture, the
fidelity/label policy, the deep-scope selection and the gate sequence are all resolvable with documented
VF-assumed defaults, which the contract explicitly authorizes. **No PIM semantic or code change is required by
this design** (all canonical IDs are pre-existing; VF-assumed connectivity uses the existing reversible
`vf_scenario_assumption` mechanism). Therefore the gate is **READY**, not BLOCKED.

Recorded items for SA awareness (each has a frozen default; SA may override at review):

| # | Question | Frozen default (unless SA says otherwise) |
| --- | --- | --- |
| **Q1** | Disinfection (`T107`) position: strictly in-line between T106 and T108 (VF-assumed) or parallel/off-path? | **in-line** (physically conventional), edge labelled VF-assumed |
| **Q2** | Deep Scope A boundary: include `T105` (clarification) and `WASH-T110` (backwash recovery)? | **include** both (needed for a coherent filtration boundary); their edges stay VF-assumed |
| **Q3** | Should `T107` residual control and `CHEM-DOSING` dose trim be upgraded to C2 in X3/X4? | **stay C1** in X2; C2 upgrade deferred (chemical truth gap `GAP-SHW-009`) |
| **Q4** | LINE2: single aggregate shallow block vs four shallow units? | **single aggregate block** (PatternInferred, low confidence) |
| **Q5** | Electrical/automation reference areas: visible chips only, or proxy values? | **chips + optional proxy values**, never control truth (`GAP-SHW-002`) |

**PIM escalation rule (frozen):** if any later gate needs a PIM semantic/code change (e.g. to confirm the
unit-level `T108 → DIST-P108` relation, the `WASH-T110` return destination, or any interlock/control truth),
that gate must **STOP and escalate to PIM SA**; this gate performed **read-only** PIM review only and made no
PIM change.

---

## 13. Compliance with the gate constraints (MUST NOT)

| Constraint | Compliance |
| --- | --- |
| No source/runtime implementation | none: changed files are `.ai-harness/**` only (`05-no-code-change-proof.json`) |
| No UI implementation | none: §10 is information architecture only |
| No PIM write | none: read-only PIM review; no PIM repo change |
| No new canonical PIM IDs | proven: every canonical ID in this report and in the evidence already exists in the repo (`04-no-new-pim-id-proof.json`) |
| No site-faithful claims | every artefact carries `site_truth=false` + `synthetic_reference`; fidelity claims capped at the PIM evidence ceiling (§4) |
| No PLC/DCS vendor emulation | explicitly excluded; control is VF synthetic with a future mapping seam |
| No new RuntimeSession authority | architecture unchanged: ONE canonical SH-WTP session; Areas/Processes own no authority |
| No gateway/protocol work | none |
| No ASSY change | none |
| No X1 start | none; STOP after X0 |

---

## 14. Evidence & machine-derived status

| Artefact | Verdict |
| --- | --- |
| `01-inventory.json` | repo-derived inventory: areas/units/roles/fidelity ceilings/evidence statuses/gaps + G21 slice + registry + runtime classes |
| `02-topology-matrix.json` | known / assumed / unknown edge matrix (E1–E15) with evidence status per edge |
| `03-control-matrix.json` | C0/C1/C2 matrix per scope + 12 loop contracts + plant-wide control rules + control-truth boundary |
| `04-no-new-pim-id-proof.json` | every canonical ID used by the design exists in the repo (no invented PIM ID); VF-local ids use a distinct non-PIM prefix |
| `05-no-code-change-proof.json` | design-only proof: no `src/`, `tests/`, `configs/`, `docs/`, `scripts/`, `simulators/` change |
| Baseline / full suite | unchanged from the accepted base `f4dcca5` (design-only gate): baseline **43/43 groups PASS**, full suite **2669 passed** |

**Authority (restated):** `site_truth=false`; `simulation_truth=synthetic_reference`;
`vf_runtime_authorization=NOT_AUTHORIZED`; `site_authorized_execution=NOT_AUTHORIZED`;
`whole_plant_runtime=NOT_AUTHORIZED / NOT_IMPLEMENTED`.

**STOP — this gate is design-only. X1 (or any other implementation) must not begin.**
