# SA REVIEW INBOX

Task: VF-vNEXT-R5
Status: BLOCKED FOR SA (Single Simulation System Consolidation + Shared VF Shell)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R4 head 989deac2fe189e7e66c89d2c33218004e2b7d08c; Issue #84 (R5 consolidation + shared shell)

Gate type:
IMPLEMENTATION gate executed as AUDIT-LEVEL gate. The repository-wide construction-site
audit, the canonical product-path construction proof and the attempt-binding probe were
completed; two competing runtime authorities were measured to be unreachable-to-consolidate
inside a bounded correction, which is an explicit R5 STOP condition. NO src/ or tests/ file
was modified (changed files: .ai-harness/** only). No SH-WTP expansion, no gateway/protocol
work, no PIM/MES change, no merge.

Base (technical branch point): 989deac2fe189e7e66c89d2c33218004e2b7d08c
Branch: feature/vf-vnext-r5
Harness preflight: PASSED
Verdict: BLOCKED FOR SA

Blocking findings (measured):
- Blocker 1 ROOT_DASHBOARD_RUNTIME_SERVICE (ui/api.py:29, eager at create_app): 19 active
  product routes (/, /step, /run-steps, /start, /stop, /reset, /status, /telemetry/*,
  /alarms, /ws/telemetry, /api/plant-graph, /api/model-types, /api/fault, /api/opcua/status,
  /api/ai/*, /api/config/*, /api/ui/*) own simulation state with NO canonical equivalent:
  the canonical registry exposes only TIPA + shwtp (continuous_workspace_registered=false).
  De-authorizing it loses the whole MVP-01 continuous interactive surface; consolidating it
  requires registering a third user-selectable workspace (product-surface decision).
- Blocker 2 LEGACY_G7_RUN_CONTROL_SERVICE (ui/api.py:813 TIPA, :846 continuous, :829 second
  per-attempt RuntimeService): 11 /vnext/runs* routes behind one shared helper. The TIPA
  discriminator is a DUPLICATE authority over an UNPREPARED federation (initialize() with no
  run profile) - de-authorizable; the continuous discriminator is the only continuous
  run/replay surface - blocked by Blocker 1.
- Finding D (R5 attempt-binding requirement currently VIOLATED): build_tipa_scenario_run_factory
  binds attempts to a single mutable holder['profile'] read by the zero-arg bridge factory.
  Measured contamination: after running tipa-default (A) and tipa-failed-final (B), A.replay()
  builds its federation with profile tipa-assy-failed_final while the canonical context stays
  tipa-assy-happy_path (violations: 1, ATTEMPT_BINDING_UNBOUND).
- De-authorizable without capability loss (recommended unblocked subset, report section 4):
  /demo-assy-mes/* legacy DemoController (9 routes), the G7 TIPA discriminator, attempt-binding
  fix (R5a-1), bounded shell convergence I1/I3/I4/I5/I6, single-system firewall test module.

Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R5/ (generate_evidence.py + 01 architecture
inventory: 21 production construction sites 4-way classified + 67-route authority map;
02 product-path construction proof: canonical path = 2 RuntimeSessions (TIPA 1, shwtp 1),
1 TipaAssyFederation, 0 DemoController, 0 RuntimeService; 03 blocker analysis + options).
Report: reports/VF-vNEXT-R5.md. SA decision requested: report section 5 (3 options;
OPTION 1 register the continuous workspace is recommended).

Regression: no executable source changed. R5-head canonical baseline (42 groups,
gate.task_contract=VF-vNEXT-R5, changed_files_base=989deac) recorded below.

Previous gate (R4, head 989deac) - closed:
- AP05 jam/recover owned by AssyExecutionBridge (canonical raised/resolved clocks +
  120 s downtime, raised-window-sequence recovery gate, jammed lines frozen like holds,
  cleared by capability-scoped reset). One line faults, five continue; Frame A and
  Frame B show the same fault truth; the MES projection READS the canonical fault read
  model (no projection-owned fault state; legacy path unchanged when unbound).
- run-to-terminal = bounded canonical orchestration (canonical session.advance only,
  1..200 window guard, deterministic terminal condition) with per-sub-line state parity
  to manual stepping.
- OEE/final summary = READ-ONLY idempotent projection over canonical facts with canonical
  run identity and canonical downtime (keyed per run+sub-line); reads never mutate truth.
- Scenario selection = FRESH canonical run: WorkspaceMonitor.new_run +
  build_tipa_scenario_run_factory share ONE run-id authority (fresh run id, previous run
  stopped/historical in run_history); shell/rich/output scenario identity agree; no
  in-place mutation of an active run; unknown scenario fails closed.
- Product path: /assy-demo jam/recover/run-to-terminal/oee/scenario are canonical (no 409
  deferral), all payloads keep legacy_runtime_authority=false; DEFERRED_FEATURES is empty.
- Hygiene: R3 same-runtime assertion strengthened (no `or True`); R2V console
  `404 /vnext/runs/current?workspace=TIPA` fixed client-side on canonical pages
  (legacy route contract unchanged).
- Static bindings: JAM/RECOVER/TERMINAL/OEE controls restored; scenario selectors enabled.

Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R4/01..06 JSON (all PASS) +
07-browser-sanity.md (+ screenshots). Report: reports/VF-vNEXT-R4.md.
Audit (separate): reports/VF-CROSS-WORKSPACE-UI-AUDIT.md — 0 BLOCKER, 0 MAJOR,
3 MINOR (I1-I3), 3 OBSERVATION (I4-I6), all recommended to R5 / SH-WTP gate; nothing
fixed in R4.

Regression: R4 focused 27; full suite 2598 -> 2625 passed; canonical baseline
(42 groups) 42/42 groups PASS at 3df5ed0 (`BASELINE PASSED: all required groups green`,
`failed_groups: []`), including `checks_preflight` PASSED and
`checks_changed_files` PASSED (30 files) and the new `r4_canonical_parity` group
(42 groups total; the R3-C01 head had 41), and re-verified at the final pushed head.; R1/R2/R2V/R3/R3-C01 + observation/MES contract suites green.

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.

---

R5 machine-derived status (this gate):
- Harness preflight: PASSED
- Canonical baseline at R5 head 7c03650: overall PASS, failed_groups [], 42/42 groups
  (incl. r1_production_semantics, r2_same_session_rich_assy, r3_canonical_observation_mes,
  r3c01_reset_generation, r4_canonical_parity, full_suite, checks_compile,
  checks_static_lint_type, checks_changed_files [8 files], checks_preflight)
- Full suite: 2625 passed (unchanged from R4 head; no executable source changed)
- R5 verdict: BLOCKED FOR SA (stop conditions triggered and measured)

NEXT ACTION REQUIRED FROM SA: decide report section 5.
OPTION 1 - register the continuous workspace on the canonical path, rewire the root dashboard,
retire the G7 continuous discriminator (no capability lost; changes the product surface).
OPTION 2 - deprecate the dashboard state routes (capability lost: MVP-01 continuous surface).
OPTION 3 - governance scope amendment for non-workspace legacy surfaces.

STOP - no consolidation code, no SH-WTP expansion, no gateway/protocol work, no merge.
