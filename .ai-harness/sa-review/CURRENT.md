# SA REVIEW INBOX

Task: VF-vNEXT-G7-C01
Status: READY FOR SA REVIEW (Hierarchical Scenario / Run Control — C01 correction)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate after G6)
Prerequisite: Issue #51 accepted as completed; G1–G6 contracts authoritative

Gate type:
Accelerated implementation gate — Hierarchical Scenario / Run Control (G7), per Issue #52

Architecture baseline:
ARCH-01..06 accepted; G1–G6 contracts authoritative
Required base (branch point): a10f581ca2e7a8b8b39c605fc54339ae88386922 (accepted G6-C01 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive package src/virtual_factory/runcontrol/ + ui seam):
- targets.py: resolve_target() — G1 hierarchical target resolution (workspace/
  container -> deterministic descendant executable scopes; executable -> itself;
  unknown/foreign fail closed; container never a participant).
- lifecycle.py: RunState, RunRecord, RunLifecycleService (create/start/pause/
  resume/stop/step/reset/restart/replay) with immutable RunContextV2 per run,
  fail-closed transition guards, fresh run_id + source_run_id lineage for
  restart/replay, replay pins prior inputs and is explicit-unavailable when the
  scenario authority is missing; StepResult + ExecutionBridge protocol.
- C01 (SA comment 5557354313): mutations require the ACTIVE run_id — known
  historical/superseded run_ids fail closed; create_run fails closed while the
  active run is nonterminal (no concurrent mutable attempts); execution state is
  attempt-bound (fresh bridge per attempt); restart/replay require terminal
  sources and start FRESH domain contexts (no continuation of prior time/WIP/
  domain state); reset stays in-context (same run_id + same runtime objects);
  historical records remain readable; no AssyLineRuntime edit.
- assy_bridge.py: AssyExecutionBridge over TipaAssyFederation + G4 Coordinator —
  natural-boundary-only advancement (no fractional dwell/index); capability-
  scoped in-context reset via AssyLineRuntime.reset().
- ui/api.py (additive): /vnext/runs/* endpoints (create/current/get + start/step/
  pause/resume/stop/reset/restart/replay); legacy endpoints untouched.
- ui/static/run_control_context.js + assy_demo.html mount + assy_demo.css:
  additive minimal run-control context (path-qualified target, state, truthful
  time, Run/Pause/Resume/Step/Stop/Reset).

Frozen invariants preserved:
- One platform-level run lifecycle authority; domain runtimes stay authoritative.
- Immutable RunContextV2 per run; workspace_id/run_id/scope_path/scenario_id
  coherent; one scenario authority per run.
- Terminal run attempts never reused under the same run_id; restart/replay
  create fresh run_id with source lineage.
- ASSY steps reuse G4 natural/common boundaries only; no universal timestep; no
  fractional dwell/index.
- pause/resume change orchestration permission only; stop terminal (history
  preserved); reset capability-scoped; replay never fabricated.
- No AssyLineRuntime/continuous-engine rewrite; no legacy endpoint repoint;
  container-only never executable; no G8+/G9/G10.

Failure semantics (evidence 06):
- Step failure -> run `failed` (distinct from completed); no rollback claimed;
  no hidden retry; terminal runs never step under the same run_id.

STOP-condition assessment: none triggered (no new synchronization/timestep
policy; no ASSY fractionalization; continuous not bridged; reset capability-
scoped; replay never fabricated; no terminal run-id reuse; no container
execution; G2/G4 contracts intact; no G8+).

Test / regression results (evidence 07):
- New G7 tests: 37 passed (incl. C01).
- UI/API + S04B gating tests: 134 passed.
- G6 UI hierarchy tests: 31 passed.
- G5 federation tests: 26 passed.
- G4 composition tests: 56 passed.
- G1 workspace: 32 passed.
- G2 provenance: 36 passed.
- G3 Observation/Event/Alarm (+ M5 + alarm_manager): 328 passed.
- Complete ASSY regression oracle: 354 passed.
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1943 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Deferred (NOT implemented): G8 regression-baseline program, G9 semantic binding,
G10 SH-WTP runtime, full replay browser/editor/history subsystem, scenario
editor, universal reset/synchronization policy.

STOP conditions: none triggered.

G8 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G7.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G7/ (8 files: 01 repo-first discovery +
scope; 02 lifecycle model + guards; 03 target resolution; 04 execution bridge;
05 API + UI binding; 06 failure + stop assessment; 07 tests + regression
results; 08 C01 corrections — active-attempt authority + attempt-bound
execution)






