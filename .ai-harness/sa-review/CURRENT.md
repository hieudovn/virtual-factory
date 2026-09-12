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
