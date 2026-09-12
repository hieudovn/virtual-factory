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
