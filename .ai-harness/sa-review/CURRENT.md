# SA REVIEW INBOX

Task: VF-vNEXT-R5
Status: READY FOR SA REVIEW (Single Simulation System Consolidation + Shared VF Shell)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R4 head 989deac2fe189e7e66c89d2c33218004e2b7d08c; Issue #84 + SA decision comment 5644148465

Gate type:
IMPLEMENTATION gate executed under the SA decision that the MVP-01 Continuous surface is
EXPERIMENTAL and NOT a required capability: every competing legacy simulation authority is
de-authorized fail-closed, the attempt-binding defect is fixed, the firewall is proven, and the
bounded shared-shell convergence I1/I3/I4/I5/I6 is delivered. Continuous is NOT canonicalized,
NO third workspace is registered, SH-WTP is NOT expanded (I2 not done), no gateway/PIM/MES work,
no merge.

Base (technical branch point): 989deac2fe189e7e66c89d2c33218004e2b7d08c
Branch: feature/vf-vnext-r5
Harness preflight: PASSED
Verdict: VF_SINGLE_SIMULATION_SYSTEM_CONSOLIDATED

Delivered:
- R5a-1 attempt binding: RunLifecycleService gained an attempt-context-aware bridge seam
  (bridge_factory_ctx); build_tipa_scenario_run_factory no longer has a mutable holder["profile"]
  (profile resolved from the attempt's own immutable RunContextV2 with an immutable per-scenario
  memo) and its zero-arg factory fails closed. A -> B -> replay/new_attempt each use their own
  profile; the R5-audit contamination (replay of tipa-default built tipa-failed-final) is gone.
- Continuous de-authorized: no eager RuntimeService in create_app (import removed), 17 stateful
  dashboard routes are fail-closed 410 aliases with zero runtime construction, no continuous
  workspace registered (registry = TIPA + shwtp). Kernel/library code retained, no active authority.
- Legacy G7 de-authorized: both discriminators (duplicate unprepared TIPA + continuous) removed;
  13 /vnext/runs* routes return 410; canonical TIPA only via /vnext/workspaces/TIPA/* and /assy-demo/*.
- demo-assy-mes de-authorized: DemoController runtime path removed from routing (9 routes 410);
  the module stays reference/test-only.
- Shared shell I1/I3/I4/I5/I6 implemented; I2 (SH-WTP page) NOT done.
- Firewall: tests/test_vnext_r5_single_system.py proves (static AST + dynamic counters) that no
  active product path constructs RuntimeService / DemoController / duplicate RunLifecycleService /
  standalone engine authority / hidden legacy session cache.

Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R5/ (generate_evidence.py, 01 architecture
inventory, 02 product-path construction proof, 03 de-authorization proof
ALL_LEGACY_AUTHORITIES_DEAUTHORIZED_FAIL_CLOSED, 04 attempt binding ATTEMPT_BINDING_CONTEXT_BOUND,
05 firewall FIREWALL_HELD, 06 shell convergence SHELL_CONVERGENCE_I1_I3_I4_I5_I6_COMPLETE,
07 browser sanity + screenshots). Report: reports/VF-vNEXT-R5.md.

Defect found by the real-server smoke and fixed in-gate: the de-authorization left
`del auto_start` in the ASGI lifespan (UnboundLocalError at uvicorn startup); fixed and covered by
a new lifespan regression test that asserts zero construction with auto_start=True.

Test migrations (legacy HTTP contract -> de-authorized contract): tests/test_api.py,
tests/test_run_control.py, tests/test_ui_hierarchy.py, tests/test_demo_assy_mes_v1.py,
tests/test_vnext_r4_canonical_parity.py. All library/domain coverage retained.

Regression: R5 focused 30 passed; full suite 2625 -> 2660 passed; canonical baseline all required
groups PASSED (incl. the new r5_single_system group) - recorded below; browser sanity clean
(0 console errors; shell NEW RUN created TIPA-0002 tipa-failed-final; the rich /assy-demo page shows
the same session/profile with 6 sub-lines x 12 stations).

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

STOP - awaiting SA review. SH-WTP expansion, gateway/protocol work and merge are NOT authorized.

---

R5 machine-derived status (this gate):
- Harness preflight: PASSED
- Implementation head: e344e9e
- Canonical baseline at e344e9e: overall PASS, failed_groups [], 43/43 groups (incl. the new
  r5_single_system group, r1..r4, full_suite, checks_compile, checks_static_lint_type,
  checks_changed_files, checks_preflight)
- Full suite: 2661 passed (R4 head: 2625)
- R5 focused module: 30 passed
- Verdict: VF_SINGLE_SIMULATION_SYSTEM_CONSOLIDATED

---

R5-C01 correction (SA comment 5644417111) - root canonical entrypoint:
- Previous head: 7558aaa
- Branch: feature/vf-vnext-r5-c01; harness preflight: PASSED
- GET / = canonical entrypoint: 307 redirect to /workspaces; the legacy continuous dashboard is no
  longer served at root; continuous static assets retained reference-only; no continuous workspace
  registered
- create_app docstring de-staled (no "backed by one RuntimeService instance" claim)
- Regression: root entry resolves to the canonical shell and constructs ZERO runtime state
  (create_app / redirect / redirect+shell / shell counters all empty)
- Evidence: evidence/VF-vNEXT-R5/08-root-entry.json -> ROOT_IS_CANONICAL_ENTRYPOINT
- Browser smoke from / -> lands on /workspaces, shell rendered, 0 console errors, SCADA absent
- Full suite: 2663 passed; R5-C01 focused module: 32 passed
- Implementation head: 6b2bc48
- Canonical baseline at 6b2bc48: overall PASS, failed_groups [], 43/43 groups (incl. r5_single_system)
- Verdict: VF-vNEXT-R5-C01 - READY FOR SA REVIEW

---

VF-vNEXT-UX01 - ASSY Structural Context Drawer & Sidebar Cleanup (Issue #87):
- Previous head / required base: 4105e3a
- Branch: feature/vf-vnext-ux01; harness preflight: PASSED
- Delivered: the fixed Structural Context block is gone from the default left sidebar (sidebar keeps
  Line Overview / Legend / Actions); the hierarchy now lives in an on-demand Structure / Model drawer
  opened from the top bar (closed by default, Esc/close button, same visual language); minimum
  hierarchy TIPA -> ASSY Line -> ASSY-SL01..ASSY-SL06; WORKSPACE / CONTAINER / EXECUTABLE are secondary
  badges only.
- Selection is presentation-only: the drawer reuses the ONE existing POST /assy-demo/select seam
  (fail-closed, single call site); measured same run_id, identical step, byte-identical sub-line
  projection, no new session/federation/runtime. Frame A (6 cards) and Frame B (rich 2D) unchanged.
- No runtime/lifecycle/route authority change; no Python source change; no SH-WTP work.
- Evidence: evidence/VF-vNEXT-UX01/ (generate_evidence.py + 01-sidebar-cleanup.json
  STRUCTURAL_CONTEXT_REMOVED_FROM_SIDEBAR, 02-drawer-and-hierarchy.json
  STRUCTURE_DRAWER_WIRED_TO_CANONICAL_CONTEXT, 03-selection-non-mutation.json
  SELECTION_IS_PRESENTATION_ONLY, 04-browser-sanity.md + 5 screenshots).
- Browser: all 8 required items observed; 0 console errors; 0 BLOCKER/MAJOR/MINOR.
- Full suite: 2669 passed (base 2663). R5-C01 baseline carry-over unchanged.
- Implementation head: bf827d6
- Canonical baseline at bf827d6: overall PASS, failed_groups [], 43/43 groups (incl. r5_single_system)
- Verdict: VF-vNEXT-UX01 - READY FOR SA REVIEW; UX verdict ASSY_STRUCTURE_UX_CONSISTENT

---

VF-SHW-X0 - Whole-Plant Simulation & Control Design Freeze (Issue #89): DESIGN / AUDIT ONLY
- Previous head / required base: f4dcca5
- Branch: feature/vf-shw-x0; harness preflight: PASSED
- Report: reports/VF-SHW-X0.md (12 required deliverables: runtime inventory; Area->Process->Unit mapping;
  known/assumed/unknown topology matrix E1..E15; PIM fidelity ceiling vs proposed VF synthetic/reference
  fidelity; Deep Scope A frozen = LINE1 downstream T106->T108-centred filtration/clean-water; Deep Scope B
  frozen = RAW WATER RAW-INTAKE+T100-centred; Key Assets per deep scope with PIM reference vs VF-local
  synthetic identity; whole-plant C0/C1/C2 control matrix; 12 loop contracts with the full PI/PID minimum;
  process/state-variable contract per scope; Frame A/Frame B SH-WTP UI information architecture; refined
  X1..X7 sequence with dependencies; STOP assessment = no blocking decision, no PIM change required).
- Frozen labels: site_truth=false, simulation_truth=synthetic_reference, vf_runtime_authorization=NOT_AUTHORIZED;
  no PLC/DCS vendor emulation; no site-faithful claim; control truth gap GAP-SHW-002 stays open.
- Evidence: evidence/VF-SHW-X0/ (generate_evidence.py + 01-inventory INVENTORY_DERIVED_FROM_REPO,
  02-topology-matrix TOPOLOGY_MATRIX_FROZEN, 03-control-matrix (machine-readable C0/C1/C2 + loop contracts),
  04-no-new-pim-id-proof NO_NEW_PIM_ID_INTRODUCED (47 canonical IDs used, all pre-existing),
  05-no-code-change-proof DESIGN_ONLY_NO_CODE_CHANGE).
- X1..X7 refinements: X3/X4 independent after X2; X5 depends on X2 (not on X3/X4) so Frame A can run in
  parallel; X6 depends on X3+X4+X5; X1 carries the PIM escalation checkpoint; X7 gates on plausibility oracles.
- Design-only: no src/tests/configs/docs/simulators/scripts change; baseline and full suite unchanged from f4dcca5.
- Implementation head: 00e8422
- Canonical baseline at 00e8422: overall PASS, failed_groups [], 43/43 groups (incl. every SH-WTP group
  g10/g11/g12b/g13/g13b/g14a/g14b/g15/g18/g21/g22); full suite 2669 passed (unchanged)
- Verdict: VF-SHW-X0 - READY FOR SA REVIEW; SHW_WHOLE_PLANT_DESIGN_FROZEN
- STOP: X1 (and any other implementation) must NOT begin; SH-WTP expansion is design-frozen only.

---

VF-SHW-X1 - Whole-Plant Process Graph + Scope/Fidelity/Control Contracts (Issue #91): CONTRACT LAYER
- Previous head / required base: c9d64a5 (X0 CLOSED, SHW_WHOLE_PLANT_DESIGN_FROZEN)
- Branch: feature/vf-shw-x1; harness preflight: PASSED
- Report: reports/VF-SHW-X1.md (all 8 acceptance criteria X1-1..X1-8 mapped; 6 stop conditions assessed; none triggered)
- Deliverables (4 new contract artefacts + validator, constructs nothing):
  configs/vnext/shwtp/shwtp_whole_plant_graph_v1.json (19 nodes / 25 edges; pim_known 3,
  vf_scenario_assumption 18, reference_only 4; signature 55f49ca4...; deterministic and declaration-order
  independent), shwtp_process_contracts_v1.json (16 X2-admitted scope contracts with inputs/outputs/state/
  parameters+units/constraints/conservation/update family/init-reset/fail-closed invalid state; 2 reference-only
  scope declarations; T107 excluded), shwtp_control_contracts_v1.json (19 controls: 9 C1 active in X2, 1 C1
  deferred to X3, 5 C2 PI/PID deferred X3/X4 and INACTIVE, 2 C0 boundaries, 2 C0 reference-only),
  shwtp_x2_admission_manifest_v1.json (16 executable scopes, 3 reference/container-only, 15 assumed edges used /
  3 excluded, 3 PIM-known edges used, 14 frozen invariants, not-authorized list).
- Identity: every PIM id referenced is pre-existing (validated against the accepted inventory); no new canonical
  id; VF-local ids confined to the vf-shw- namespace; no partial/wildcard PIM token allowed anywhere.
- Assumptions: every assumed edge carries source_kind=vf_scenario_assumption, status=assumed/synthetic,
  reversible=true, rationale and ASSUME-SHW-* id; registry == used ids; no edge is simultaneously PIM-known and
  VF-assumed (negative fixtures prove the validator rejects both a conflicting edge and missing provenance).
- Deep Scope A (LINE1 T106/T107/T108-centred; T107 stays VF-assumed and OUT of X2) and Deep Scope B (RAW WATER +
  T100) key-asset boundaries materialized as contracts; G18 ASSUME-SHW-T108-DIST-P108 v1 reused, not redefined.
- No construction: instrumented constructors 0 calls (RunLifecycleService / RuntimeSession / ShwtpExecutionBridge /
  T108TankRuntime / T106LogicalRuntime / SimulationEngine / DiscreteSimulationEngine) + static token/import scan
  clean; structural.py/connectivity.py untouched (authority constants NOT_AUTHORIZED).
- Evidence: evidence/VF-SHW-X1/ (generate_evidence.py, 01-graph-signature WHOLE_PLANT_GRAPH_DETERMINISTIC,
  02-validation-matrix ALL_X1_VALIDATIONS_PASS (V1..V10), 03-no-construction-proof NO_RUNTIME_CONSTRUCTION_ADDED,
  04-x2-admission-summary X2_ADMISSION_FROZEN).
- In-gate correction (disclosed): the X1 contract listed the required new test module in allowed_paths AND the whole
  directory tests/ in forbidden_paths; the verifier applies forbidden unconditionally, so checks_changed_files failed.
  Fixed by dropping the tests/ directory entry (rationale recorded in forbidden_paths_note); test protection stays at
  file granularity via the allowlist. No pre-existing test module changed.
- Regression: x1_whole_plant_contracts group 35 passed; full suite 2669 -> 2704 passed.
- Implementation head: 0f10dc0 (contract layer) + 7130724 (test-path fix)
- Canonical baseline at 7130724: overall PASS, failed_groups [], 44/44 groups (incl. the new x1_whole_plant_contracts
  group, R1..R5, all SH-WTP groups, full_suite, checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight)
- Verdict: VF-SHW-X1 - READY FOR SA REVIEW; SHW_WHOLE_PLANT_CONTRACTS_FROZEN
- STOP: X2 must NOT begin. X2 is authorized only by the SA and only against this admission manifest.

---

VF-SHW-X1-C01 - X2-safe actuator ownership + level-action direction (Issue #91 comment 5644974241): CORRECTION
- Previous head / technical base: ec57d7d (X1 contract layer, SHW_WHOLE_PLANT_CONTRACTS_FROZEN); branch feature/vf-shw-x1-c01
- Harness preflight: PASSED; report: reports/VF-SHW-X1-C01.md
- Finding A CLOSED class-wide (4 sites, not 1): raw-intake pump_speed_cmd now produced in X2 by the X2-active C1
  duty/standby controller raw-pump-duty with an explicit deterministic fixed synthetic-reference speed command
  (RUN -> 75 %, STOP -> 0 %, is_feedback_controlled_in_x2 = false); the same class found at T106 inlet_valve_pos
  (C1 backwash sequence, discrete OPEN/CLOSED), T108 transfer_pump_speed_cmd (C1 t108-permissive, fixed speed) and
  DIST-P108 hsp_speed_cmd (explicit declared X2 fallback/default, 80 % synthetic reference). All five C2 PI/PID
  loops stay C2 + inactive + later gate and now carry x2_status + x2_replacement. No C2 activated; X2-active C1
  set still 9; no new control added.
- Finding B CLOSED: vf-shw-ctrl-t100-permissive now declares actuator_ownership (upstream raw-intake intake_enable,
  downstream t101 outlet_enable) and a structured level_action_policy - low/low-low inhibits/reduces DOWNSTREAM
  withdrawal with upstream refill permitted, high/high-high inhibits UPSTREAM intake with downstream withdrawal
  permitted; the contradictory "LALL -> stop intake pump(s)" wording is removed and replaced by an explicit
  no-trip statement. t108-permissive gets the same ownership/policy (low -> dist-p108 transfer_enable, high ->
  t106 inflow_enable) and the deferred t100-level-pi protective wording is aligned. VF synthetic/reference only;
  site_truth=false; no site-truth claim.
- Validation: two new fail-closed validators in contracts.py - _validate_x2_io_resolution (every X2-admitted input
  must resolve to an X2 producer: process node / scenario boundary / X2-active C1 / explicit x2_fallback_default
  with mode+value+rule+provenance; a C2-sourced input without a fallback is rejected; deferred-modulator
  annotations cross-checked) and _validate_level_action_direction (actuator ownership + exactly one direction per
  action + graph-reachability of the target scope + matching actuator signal; a low level tripping the upstream
  intake is rejected). Read-only helpers x2_io_resolution_audit / level_action_audit.
- Evidence: 05-x2-io-resolution.json X2_SAFE_C1_ACTUATOR_BEHAVIOUR_FROZEN (29/29 admitted inputs resolved,
  inputs_requiring_a_c2_output = []); 01..04 regenerated; validation matrix now V1..V12 ALL_X1_VALIDATIONS_PASS.
- Bounded surface: frozen graph UNTOUCHED (19 nodes / 25 edges / same signature); admission gains 2 X1-C01
  invariants (16) and the DIST-P108 control-level label is corrected to X2_fallback_default+C2(X3) (its only loop
  is a deferred C2); raw-flow-pi owning scope corrected to raw-intake; contract-only, no runtime/PID/UI/PIM change.
- Tests: tests/test_vnext_x1_whole_plant_contracts.py 35 -> 46 passed (11 new incl. 4 negative fixtures that prove
  the validators reject a C2 dependency without fallback, a low-level upstream intake trip, a downstream action on
  an upstream scope and an incomplete fallback).
- Regression: canonical baseline at f0f9f30 overall PASS, failed_groups [], 44/44 groups; full suite 2704 -> 2715 passed.
- Implementation head: f0f9f30
- Verdict: VF-SHW-X1-C01 - READY FOR SA REVIEW; X2_SAFE_C1_ACTUATOR_BEHAVIOUR_FROZEN
- STOP: X2 must NOT begin; no merge without explicit SA authorization for the exact PR head SHA.

---

VF-SHW-X2 - Whole-Plant Shallow Runnable Model + C1 Functional Control (Issue #94): IMPLEMENTATION
- Required/technical base: eba4c58 (X1 + X1-C01 accepted). Branch feature/vf-shw-x2; harness preflight PASSED.
- Report: reports/VF-SHW-X2.md; all 10 acceptance criteria X2-1..X2-10 mapped.
- Delivered (additive, contracts untouched): src/virtual_factory/shwtp/whole_plant.py (16 admitted scopes as
  composition participants under explicit_lagged; frozen topology as 21 bindings = 18 graph flow edges + 3
  contract-declared process input relations; per-scope contract update families; monitor/control/balance/
  input-wiring/transfer-ledger/provenance projections), src/virtual_factory/shwtp/x2_controls.py (the nine frozen
  X2-active C1 controllers as deterministic rule/sequence logic reading the frozen actuator command values/timers/
  deadbands from the contracts), bridge.py (canonical bridge drives either the accepted G21 slice or the X2 whole
  plant), session.py (explicit model selector + build_shwtp_whole_plant_session; ONE RuntimeSession per session),
  __init__.py exports, tests/test_vnext_x2_whole_plant_runtime.py (42 tests = the 18 Issue #94 oracles).
- Oracles: ONE_CANONICAL_SHWTP_SESSION_AUTHORITY; ALL_16_ADMITTED_SCOPES_EXECUTE_ONLY (T107/ELEC-MCC/AUTO-PLC/
  LINE2 internals never execute); NINE_C1_ACTIVE_ZERO_C2_EVALUATION (no PID/integrator/derivative/scan loop, five
  C2 loops stay deferred X3/X4); EVERY_X2_INPUT_RESOLVED_AT_RUNTIME (process node / X2-active C1 / scenario /
  the single declared DIST-P108 fallback); PHYSICAL_ORACLES_SATISFIED (per-scope storage residual exactly 0,
  plant closure bounded with the reported transit inventory, 0 negative values over 120 windows, filtered <=
  settled turbidity on the matched lag basis, filter DP non-decreasing with 3 backwash resets and wash-water
  return, no same-window feed-through, identical trajectory digests across independent builds and after reset);
  RUNTIME_PROVENANCE_VISIBLE (3 PIM-known + 15 assumed edges in the runtime ledger with assumption_id/reversible,
  site_truth=false and simulation_truth=synthetic_reference on every payload, excluded edges never used).
- X1-C01 actuator behaviour preserved exactly: RAW-INTAKE 75/0, T106 valve 100/0, T108 70/0, DIST-P108 80 percent
  fallback, T100 low -> downstream withdrawal inhibited while upstream refill permitted, T100 high -> upstream
  intake inhibited, T108 direction correct.
- Interpretation recorded in the report: the accepted G21 slice stays the default model (issue requires the
  accepted G21/G22/G23/G24/G25 behaviour to stay green and defers the rich SH-WTP UI to X5/X6), so the whole
  plant is reachable through the SAME canonical seam via model="whole_plant_x2"; plus three documented
  parameterizations (T106 wash-water permissive as recovery capacity available, T101/T104 residence interlock on
  the scope outlet with a true V/Q residence index, plant boundary IN = actually pumped intake flow).
- Regression: canonical baseline at de268e5 overall PASS, failed_groups [], 45/45 groups (new
  x2_whole_plant_runtime group 42 passed, x1_whole_plant_contracts 46 unchanged, checks_changed_files PASSED);
  full suite 2715 -> 2757 passed.
- Implementation head: de268e5
- Verdict: VF-SHW-X2 - READY FOR SA REVIEW; SHW_WHOLE_PLANT_SHALLOW_RUNTIME_READY
- STOP: X3/X4/X5 must NOT begin; no merge without explicit SA authorization for the exact PR head SHA.

---

VF-SHW-X2-C01 - Canonical whole-plant default + authority labels + test rigour (Issue #94 comment 5645215200): CORRECTION
- Previous head / technical base: 2492329 (X2 SHW_WHOLE_PLANT_SHALLOW_RUNTIME_READY, NOT_COMPLETE); branch feature/vf-shw-x2-c01
- Harness preflight: PASSED; report: reports/VF-SHW-X2-C01.md; Issue #94 stays OPEN.
- Finding A CLOSED (canonical default): whole_plant_x2 is now SHWTP_DEFAULT_MODEL for the normal shwtp session/runtime/
  UI path (scenario shwtp-x2-whole-plant); build_shwtp_session() resolves to the whole plant, the registry description
  is "SH-WTP canonical whole-plant runtime (X2: 16 scopes, 9 C1 controls)" and the SH-WTP view is model-agnostic
  (live model rows + assumed topology, 16 contract-derived scopes as fallback). g21_slice is retained ONLY through the
  explicit selector model="g21_slice" and build_shwtp_g21_slice_session(); its accepted behaviour stays green (same
  canonical RuntimeSession/RunLifecycleService/ShwtpExecutionBridge seam; bridge model_driven_windows discriminator).
  No second registry/session/runtime/clock/run identity/UI authority. Accepted G22/G23/G24/G25 assertions that pinned
  the slice as the default are migrated to the explicit compatibility factory (incl. a compatibility-factory proof and
  the 16-scope canonical structure in the UI view).
- Finding B CLOSED (authority labels): site_truth=false, simulation_truth=synthetic_reference,
  vf_runtime_authorization=NOT_AUTHORIZED, site_authorized_execution=NOT_AUTHORIZED are declared once
  (AUTHORITY_LABELS) and threaded through every applicable projection - transfer payloads, monitor values and monitor
  rows, control rows, balance report top level and every storage row, input wiring, provenance records, assumed
  topology, runtime truth, ScopeRuntimeInfo - with a fail-closed require_authority_labels() guard that raises
  WholePlantX2Error on a missing or mutated label. New artefact 07-authority-labels.json inventories 137 records plus
  the SH-WTP view: labels_missing=[] and labels_drifted=[] -> FOUR_AUTHORITY_LABELS_ON_ALL_OUTPUTS.
- Implementation vs authorization separated: runtime_truth() reports whole_plant_runtime=IMPLEMENTED_SYNTHETIC_REFERENCE
  and whole_plant_runtime_authorization=NOT_AUTHORIZED. The X2 report contradiction (whole_plant_runtime reported as
  NOT_AUTHORIZED / NOT_IMPLEMENTED while the runtime is implemented) is corrected in reports/VF-SHW-X2.md (explicit
  CORRECTION note, section 7 marked SUPERSEDED). Historical reports (R1..X1) are unchanged: they predate the X2
  runtime, so the phrase was accurate then.
- Finding C CLOSED (test rigour): contract-signature test now proves deterministic loading AND mutation sensitivity of
  the covered admission surface (graph process_role tamper -> different signature; scope fidelity_class tamper ->
  different signature; control implementation_gate tamper -> rejected fail-closed on the deferred_modulator
  annotation; active_in_x2=True on a C2 loop -> rejected); DP monotonicity asserted per cycle between resets via
  _assert_monotone_between_resets plus a dedicated bite test; the weak T106/T108 conditional assertions replaced by
  direct semantics assertions; input resolution checked against a strict mapping with exactly 1 declared fallback and
  1 scenario parameter; new TestAuthorityLabels (labels on >100 records + bite tests for each missing key and for
  mutated site_truth/vf_runtime_authorization) and TestCanonicalDefaultModel (default session -> WholePlantX2Runtime,
  16 participants, window 1; G21 only via the explicit selector/factory).
- Evidence: 07-authority-labels.json new; 01/02/04/05/06 regenerated; all verdicts green.
- Regression: canonical baseline at 134cedb overall PASS, failed_groups [], 45/45 groups;
  x2_whole_plant_runtime 42 -> 50 passed; x1_whole_plant_contracts 46 unchanged; checks_changed_files PASSED (19
  files); full suite 2757 -> 2765 passed.
- Implementation head: 134cedb
- Verdict: VF-SHW-X2-C01 - READY FOR SA REVIEW; X2_CANONICAL_WHOLE_PLANT_DEFAULT_WITH_LABELS
- STOP: X3/X4/X5 must NOT begin; no merge without explicit SA authorization for the exact PR head SHA.

---

VF-SHW-X2-C02 - Runtime identity + WASH return + water ledger + level-inhibit routing (Issue #94 comment 5645344049): CORRECTION
- Required base: aae3482 (C01 head). Same branch feature/vf-shw-x2-c01 / PR #96; harness preflight PASSED; report: reports/VF-SHW-X2-C02.md.
- C02-1 CLOSED (runtime identity): the model/participants/transfers are built per attempt from that attempt's own immutable
  run context via the existing RunLifecycleService bridge_factory_ctx seam (the TIPA seam) - no new lifecycle authority and
  no second run-id minter. runtime_truth() reports run_id + run_id_source=attempt_context; every detached ledger row carries
  run_id. Evidence 08-lifecycle-identity.json: attempt shwtp-0001 == model shwtp-0001; RESET preserves the identity;
  new_attempt -> shwtp-0002 and replay -> shwtp-0003 with all transfers re-issued and no old-id leakage; the zero-arg bridge
  factory and an ambient run_id kwarg both FAIL CLOSED (SessionError). Stale session docstring corrected
  (whole_plant_x2 is the canonical default; g21_slice is an explicit compatibility selector).
- C02-2 CLOSED (WASH return): committed process input now lives in its own rail (_process_input, written by _commit,
  surviving prepare_window) and is consumed exactly once by the next step; the transient controller commands (_commands)
  stay separate. FilterParticipant consumes the delivered wash_in flow and exposes wash_return_m3h; T100's committed
  line1_demand_m3h/line2_split_fraction use the same rail. Evidence 09-committed-process-input.json (forced early backwash):
  2 positive-return windows with consumed == delivered-previous and lag_mismatches=[], 0.125 m3 received / 0.0833 m3 returned,
  return never exceeds what was received. Before the fix the return was destroyed by the next prepare_window (consumed 0 forever).
- C02-3 CLOSED (conservation oracle): the control volume is the pumped-intake discharge .. network/sludge discharge; every
  transfer row is classified physical_water / information / source_availability_outside_boundary (the latter two carry 0 m3
  water - the old oracle summed flow on ALL received transfers, so a 60 m3/h information signal became 1 m3 of inventory).
  The balance is ledger-based (IN = intake discharge, OUT = network discharge + sludge outflow, LOSS = declared LINE2 loss,
  water inside = storage delta + physical in-transit) with explicit overflow/shortfall accounting and a documented
  float-rounding tolerance. 120-window residual = -1e-12 (tolerance 2.04e-07, conserved true) vs the previous
  closure=-2.7398 m3 accepted under a 5% allowance (a real ~0.55 m3 water deficit was hidden). Scenario matrix green:
  startup, stopped/zero inflow, backwash/recovery, LINE2 active, T108 high inhibit, capacity overflow, empty tanks.
- C02-4 CLOSED (level inhibit routing): T108 no longer deletes received inflow - it always integrates it, and the frozen
  upstream actuator path is closed instead (T106 filtered_flow=0 + filtered_path_inhibited; T105 holds its water). Command
  priority recorded: the backwash sequence keeps exclusive ownership of inlet_valve_pos; the inhibit closes the path.
  T100 audit: intake never deleted; the t100-permissive stops the raw-intake pump at the source (0 m3/h). Evidence
  11-level-inhibit.json: T108 inhibit at window 18 with 1 accumulated-inflow-integrated window at the transition and
  balance_mismatches=[]; T100 inhibit at window 26 with 4 such windows and 3.075 m3 of capacity overflow EXPLICITLY
  accounted (alarm + ledger term, no silent clamping).
- Tests: tests/test_vnext_x2_whole_plant_runtime.py 50 -> 75 passed (+25 C02 tests incl. bite tests: classification is
  load-bearing, information counted as water would break the ledger, a percentage allowance would hide the deficit,
  deletion would fail the per-window tank balance). Focused modules 212 passed; full suite 2765 -> 2790 passed.
- Verdict: VF-SHW-X2-C02 - READY FOR SA REVIEW; X2_RUNTIME_IDENTITY_AND_WATER_ACCOUNTING_CORRECTED
- STOP: X3/X4/X5 must NOT begin; no merge without explicit SA authorization for the exact PR head SHA.

---

VF-SHW-X2-C03 - Physical conservation vs accounting reconciliation (Issue #94 comment 5645448466): CORRECTION
- Required base: c3e7893 (C02 head). Same branch feature/vf-shw-x2-c01 / PR #96; harness preflight PASSED;
  report: reports/VF-SHW-X2-C03.md.
- SA finding reproduced before the fix with the exact methods: _bound_volume(-1, 10) -> volume 0, shortfall 1.0,
  balance_report residual 0.0 and conserved TRUE, because _shortfall_m3 (water CREATED by the negative clamp) was
  subtracted from the residual. A diagnostic correction term must never certify invented water.
- Requirement 1 CLOSED: the residual no longer contains the created-water compensation term. balance_report now
  separates conserved/physical_valid (no compensation, created water within the rounding tolerance, loss audit ok)
  from accounting_reconciled (the created-water-subtracted view, explicitly labelled "NOT a physical-conservation
  claim"). shortfall_m3/created_water_diagnostic_m3 are read LIVE from the scopes, and created_water_within_rounding
  uses CREATED_WATER_TOLERANCE_M3 = 1e-9.
- Requirement 2 CLOSED: new ScopeParticipant._available_outflow_rate = held/dt + inflow, and every real discharge is
  bounded by it (the T106 backwash wash water now min(requested, available) with the explicit alarm
  wash_water_limited_by_available_volume; T108/T100/T105/T110/T201 verified). No scope emits unavailable water and
  repairs storage with a clamp - the clamp is only a float-noise guard whose output is a diagnostic.
- Requirement 3 CLOSED by tests: the SA counterexample (created water 1.0 m3) now reports conserved=false /
  physical_valid=false / created_water_within_rounding=false; 7 accepted scenarios (default, stopped/zero inflow,
  backwash, DRY-FILTER forced backwash via t106_dp_initial_kpa=85 + t106_initial_volume_m3=0 through the real window
  path, empty T108, tiny LINE2 capacity, overflowing T106) all keep shortfall <= 1e-9 with physical_valid=true; a
  deliberate pre-C03 mutation shows accounting_reconciled=true while conserved=false (the claims are separate); a
  bounded-discharge proof covers 3 extreme scenarios x 20 windows.
- Requirement 4 CLOSED: audit_line2_process_loss() proves the LINE2 loss = declared law (feed x loss_fraction) plus
  the modelled capacity spill max(0, feed x (1-loss) - capacity); the participant computes its delivery FROM the
  declared law and records step_feed/declared_loss/capacity_spill/observed_loss/audit flags; the ledger uses
  declared+spill so an arbitrary dropped delivery cannot be relabelled. Negative mutation check: feed 100 ->
  delivered 50 is valid=false (both checks false) while 100 -> 99 (1 % loss) and the 89 m3 spill case are valid.
- Requirement 5 CLOSED: 05-physical-oracles.json now requires physical_valid + created_water_within_rounding +
  the loss audit (a reconciled residual alone can no longer yield PHYSICAL_ORACLES_SATISFIED), 10-water-ledger.json
  requires physical validity per scenario, and the new 12-physical-validity.json reports
  INVENTED_WATER_FAILS_PHYSICAL_VALIDITY with the counterexample (C02 oracle formula would have said true, the C03
  oracle rejects it), the dry-filter proof and the declared-loss audit with its negative mutation.
- Regression: x2_whole_plant_runtime 75 -> 84 passed; full suite 2790 -> 2799 passed; 12/12 evidence artefacts green.
- Verdict: VF-SHW-X2-C03 - READY FOR SA REVIEW; INVENTED_WATER_FAILS_PHYSICAL_VALIDITY
- STOP: X3/X4/X5 must NOT begin; no merge without explicit SA authorization for the exact PR head SHA.

---

VF-SHW-X3 - Physical bounds + deep scope A two-PI runtime (Issue #98; design freeze Issue #97 + SA comment
5645547152): IMPLEMENTATION
- Required base: 92fbabe7b0023785f86058c6d9d6fce3f9c5c861 (X2-C03 head, PR #96). Branch: feature/vf-shw-x3
  (created from that exact commit, NOT from main); harness preflight PASSED; report: reports/VF-SHW-X3.md.
- ORDERING DISCLOSURE (SA #98 section 1, not backdated): the X3 modules and the bounded whole_plant.py hooks
  were authored BEFORE this task's contract/preflight existed; the contract carries that disclosure and the
  preflight is a post-edit gate check. The carried work was checkpointed as a commit so the harness could gate
  a clean tree; no evidence time was rewritten.
- Full-run conservation (SA section 2, the interval balance was NOT accepted as a substitute): the authoritative
  identity is evaluated from tick zero as
  R(t) = [storage flow delta + created water + in-transit] - cumulative in + cumulative out - declared losses.
  The storage integration gap (state delta - flow delta - created + overflow) is a separate physical claim, so a
  duplicated/missing initialisation stock or a hidden clamp fails even when the flow residual closes;
  created_water is always a failure and can never reconcile; the marked-baseline window residual is
  supplementary only (full_run_authoritative=true). Measured over 2400 ticks: 0 invalid ticks, worst residual
  2.0e-12 m3 (tick 432), created water 0.0 m3. Two REAL defects were found by this work and fixed: a
  pass-through conduit capped its EMISSION by its new inbound water and so destroyed the parcel it still held
  (DIST discharge collapsed 28.7 -> 2.9 m3/h at tick 65), and the DIST loss was mis-converted
  (7.776e8 -> 79266.06 s^2/m^5 = 0.0006 bar/(m3/h)^2 via 1e5 x 3600^2 / (rho g)), which had pinned the DIST
  pump at 0.66 m3/h.
- Reservations (SA section 3): a reservation is a CAPACITY token, never water - m3/s internally, m3/h at the
  processor boundary; acquired when water ENTERS a conduit, released by the forward emission; a series hop is
  never charged twice (the same parcel charges t102-t103 and t103-t104 equally); parallel branches of the same
  header share the trunk in the tick (shared_trunk binding factor, trunk saturated); the queue bound is
  enforced (X3BudgetError); a trip/stop removes the request so the token is released next tick with no hidden
  loss and no deadlock; in-flight slugs are physical inventory and survive stop/reset; a full receiver blocks
  its chain and the water stays upstream; a narrow serial pipe throttles the chain without loss. Queue bound
  max_queued_volume_m3=40 and the no-double-count proof are in evidence 03.
- Two active C2 loops only (T106 inlet flow, T108 level) with the nine reused C1 functions and explicit
  arbitration. Measured: flow error 0.0000 % of SP at the nominal operating point, level error 0.0292 m after
  the declared 1800 s settling horizon (off-nominal band 0.10 m documented); DISTINCT setpoints give distinct
  actuator positions; the backwash at tick 3356 takes the valve (c1_backwash_closes_inlet), the measured flow is
  exactly 0 while pi_output_mv stays visible, the integral is HELD (anti-windup) and the loop recovers; an
  unreachable SP reports saturated=true / output_saturated with the PV below the SP and never claims the SP.
  Pump envelope (0-100 % speed, 3 pumps) is head- and motor-feasible with OFF exactly 0 flow/0 W and total
  energy 11.821 MJ; unmodelled drives are declared unavailable, never fabricated.
- Canonical wiring: whole_plant_x3 is the default model at 1 s windows (SHWTP_DEFAULT_MODEL); whole_plant_x2
  (60 s, ZERO C2) and g21_slice (5 scopes) stay explicitly constructible with their scenario ids; runtime
  identity stays bound to the attempt context; the read-only workspace_monitor projection follows the model's
  own rows + model_label and selecting never advances the tick.
- Tests: 4 new X3 modules 64 passed; accepted-suite migrations in test_vnext_x2_whole_plant_runtime.py (default
  -> X3 + an explicit X2 availability test), test_vnext_g23_registry.py, test_vnext_g24_workspace_ui.py,
  test_vnext_g25_acceptance.py; full suite 2799 -> 2864 passed, 0 failed.
- Evidence: .ai-harness/sa-review/evidence/VF-SHW-X3/ (generate_evidence.py + 01..09) - all seven section
  verdicts PASS, overall SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED; baseline group x3_whole_plant_runtime
  inserted before full_suite with the manifest gate context pointed at this contract/base.
- Verdict: VF-SHW-X3 - READY FOR SA REVIEW; SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED
- Head: implementation commit e3c2846d0a40d786dad8b398039f4eb6d92897a6 (all source/config/tests/contract/
  manifest), evidence+acceptance commit c105ec8b143b9abff04a1bc46ee7d6e1e5b89eb0 (artefacts, the machine-
  checkable x3.* rules and this report; no source change), then the markdown-only docs/status pin commit(s);
  the exact reviewed SHA is the PR #99 head reported to the SA. PR #99 (base main, not merged).
  Machine-derived at the implementation head with a clean tree: canonical baseline overall PASS, 46 groups,
  failed_groups [], x3_whole_plant_runtime PASS (64 passed), x2_whole_plant_runtime PASS (85 passed),
  full_suite PASS (2864 passed), checks_changed_files PASS (FILE VALIDATION PASSED (31 file(s))),
  checks_preflight PASS (PRECHECK PASSED); VF-DM CI run 34701098691 SUCCESS at that head. The contract's
  acceptance criteria X3-1..X3-7 are evaluated by .ai-harness/scripts/evaluate_acceptance.py against the
  x3.* block in evidence 08 (7/7 PASS); the canonical baseline is re-run on the final branch head and that
  machine-derived result is reported in the PR #99 comment.
- STOP: X4/X5 must NOT begin; no merge, no Issue #98 closure without explicit SA authorization for the exact
  PR head SHA.

---

VF-SHW-X3-C01 - Correction of the two blocking SA findings (Issue #98 SA review comment 5646905334): CORRECTION
- Reviewed head / technical base: c3f4b231bb83bbd48f2c8a66f7dda13efd7ef290. Same branch feature/vf-shw-x3 /
  PR #99; no competing implementation gate. Correction contract .ai-harness/tasks/VF-SHW-X3-C01.json was
  created BEFORE the edits and the harness preflight PASSED (PRECHECK PASSED) on the clean tree at the
  contract commit 579f0c2. Report: reports/VF-SHW-X3-C01.md.
- C01-1 CLOSED (the final physical actuator is the controller's tracked actuator). Protective ownership is now
  decided BEFORE the PI scans (trip > C1 backwash/permissive > interlock > PI), the protective status commits
  the ACTUAL value into actuator tracking exactly once, the integral is held from the first protected scan,
  the trip/interlock release preloads from that actual stopped value, every ordinary reopening is slew limited
  (valve 10 pp/s, pump 5 pp/s, protective stopping exempt) and the back-calculation is reconciled with the
  FINAL realized command (commit_actual). Measured (evidence 11-actuator-tracking.json): SA counterexample
  90.00 % -> stop 0.00 % (tracked 0.00 %) -> release step 0.000 pp vs the 10 pp/s limit; all 6 protective
  epilogues (trip/interlock/C1 override x flow/level) hold the integral on the first protected scan and with a
  changed PV, stay inside the slew and take the actuator back; a 5400-tick runtime scan (the real backwash
  episode, 390 ticks under c1_backwash_closes_inlet) has ZERO tracking/slew violations; feasible SP step,
  unreachable-SP saturation with output_saturated and recovery all happen INSIDE one ongoing attempt with the
  controller state retained (control_rows now projects the setpoint in force).
- C01-2 CLOSED (energy from the ACHIEVED pumped throughput). The capacity point is kept for allocation/envelope
  only; a new PumpModel.realized_point() evaluates the committed physical pumped throughput of the tick
  against the frozen pump/system laws, head and motor feasibility are enforced on the realized point, OFF
  (not energized) is separated from energized-zero-flow/insufficient-head, the declared idle-loss rule charges
  only no_load_w when no water moves with NO invented useful hydraulic power, and the runtime exports per-tick
  actual Q/speed/H/Hreq/P/energy (energy_trace). Measured (evidence 10-energy-from-actual-flow.json): total
  4.207016 MJ = idle 0.102650 MJ + pumped 4.104366 MJ (DIST 1.895614, raw 1.150922, T108 1.160480); the
  ledger matches an INDEPENDENT recomputation from the per-tick actual rows per pump (<= 1e-6 J); a
  rated/capacity-flow substitution is detected (up to 1.763154 MJ difference) and cannot pass; 0 infeasible
  realized ticks out of 1200; startup / zero available water / full receiver / narrowed downstream scenarios
  all keep the water identity valid, with the empty plant pumping 0.0 m3 through the downstream chain.
- Regression: water identity 0 invalid ticks, worst residual 2e-12 m3, created water 0.0 m3, integration gap
  -5e-12 m3; level acceptance inside the declared 0.05 m band at the nominal SP (final level error 0.0366 m)
  with the post-backwash release slew limited to 10.0 pp and the flow re-settled by tick 5700.
- Tests at the correction head: tests/test_vnext_x3_physical_bounds.py 30, tests/test_vnext_x3_two_pi_control.py
  26, tests/test_vnext_x3_reservations.py 16, tests/test_vnext_x3_session_wiring.py 12 (84 passed, 0 failed);
  tests/test_vnext_x2_whole_plant_runtime.py 85 passed (no migration needed).
- Evidence: 01..11 all green, overall SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED; the harness acceptance
  evaluation of the C01 contract is 9/9 PASS (X3C01-1, X3C01-2 + the X3-1..X3-7 regression re-assertions).
- Gate: the canonical 46-group baseline (including full_suite) and VF-DM CI are run at the exact pushed head
  of this correction; their machine-derived numbers are recorded in the C01 verification comment on PR #99.
- STOP: X4/X5 must NOT begin; no merge and no Issue #98 closure without the SA's explicit authorization for
  the exact PR head SHA.
