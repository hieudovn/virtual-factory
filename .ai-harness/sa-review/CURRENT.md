# SA REVIEW INBOX

Task: VF-vNEXT-R4
Status: READY FOR SA REVIEW (ASSY full parity closure on the canonical runtime)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R3-C01 head 75725508d2894f5afaa1ec10134e64a8874e86df; Issue #83 (+ SA amendment comment 5643565581)

Gate type:
IMPLEMENTATION gate — the only authorized implementation gate. ASSY capability/parity
closed ON the ONE canonical TIPA RuntimeSession (no second runtime/session/federation/
controller authority). Includes the authorized cross-workspace UI consistency audit
(review/report only; no UI redesign). R5, SH-WTP expansion and gateway/protocol work are
NOT authorized and NOT started.

Base (technical branch point): 75725508d2894f5afaa1ec10134e64a8874e86df
Branch: feature/vf-vnext-r4
Head: (this implementation commit)
Harness preflight: PASSED
Verdict: ASSY_CANONICAL_PARITY_COMPLETE

Closed in R4:
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
(42 groups) recorded at the pushed head in the SA submission; R1/R2/R2V/R3/R3-C01 + observation/MES contract suites green.

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.
