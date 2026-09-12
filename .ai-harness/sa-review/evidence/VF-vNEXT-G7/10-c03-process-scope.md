# VF-vNEXT-G7-C03 · Evidence 10 — PROCESS executable scope + attempt isolation

SA decision `5557511518` (authorized): choose Option 1. A Workspace is a
plant/site isolation boundary and does NOT own executable runtime semantics;
runtime ownership sits below the Workspace on an executable Simulation Scope.

## Frozen architecture (applied)
- `continuous` Workspace → `PROCESS` Scope (executable); canonical path
  `continuous/PROCESS`.
- `PROCESS` is a bounded generic execution-boundary wrapper around the existing
  single continuous runtime — NOT derived from plant_id/process type/PIM/UI and
  NOT an invented unit/area/equipment/process-section topology.

## What changed (additive; no engine rewrite)
- `runcontrol/continuous_bridge.py`: `build_continuous_workspace()` now builds
  (via the accepted G1 builder) a Workspace with exactly ONE executable child
  Scope `PROCESS`; `process_scope_path()` returns `continuous/PROCESS`.
  `ContinuousExecutionBridge` executes on behalf of the effective executable
  Scope (`participant_id = "continuous/PROCESS"`); the Workspace root is never a
  participant.
- `runcontrol/__init__.py`: exports `PROCESS_SCOPE_ID`, `process_scope_path`.
- `ui/api.py`:
  - continuous `bridge_factory` now constructs a FRESH `RuntimeService` per
    attempt from the same accepted config/runtime construction inputs
    (`config_path`, `scenario_path`, `dt_s`, MQTT/OPC-UA options). The legacy
    dashboard's `RuntimeService` is a separate compatibility surface and is
    never aliased into vNext attempt state.
  - `/api/ui/hierarchy` and `/api/ui/context` now accept `workspace=continuous`
    and project `continuous → PROCESS` through the shared G1 hierarchy
    primitive (additive; `workspace=TIPA` unchanged; unknown workspace still
    404). `/api/ui/context/continuous` root-only minimal context is unchanged.

## C03-A — non-executable Workspace, single executable PROCESS scope
- `resolve_target(continuous)` → `target_kind="workspace"`, effective set
  exactly `("continuous/PROCESS",)`.
- `resolve_target(continuous/PROCESS)` → `target_kind="executable"`, itself.
- Any other continuous path (e.g. `continuous/NOPE`, `continuous/PROCESS/UNIT`)
  fails closed. No additional fake scopes.

## C03-B — path-qualified participant identity
- Run record `effective_scopes == ("continuous/PROCESS",)`;
  `effective_sub_line_ids == ("PROCESS",)` (leaf id for the bridge).
- `StepResult.participants == committed == ("continuous/PROCESS",)` — never the
  Workspace root.

## C03-C — correct attempt isolation
- Every vNext continuous run attempt owns a FRESH `RuntimeService`/engine
  (fresh object + fresh state). Historical and active attempts never share a
  mutable `RuntimeService`.
- restart/replay/new attempt → distinct run_id + fresh runtime object/state;
  the source attempt runtime is never reset/mutated and remains readable
  history.
- reset → same run_id + same runtime object of the ACTIVE attempt, reinitialized
  to the accepted t=0 baseline.
- Legacy continuous `/start /step /stop /reset` remain compatibility surfaces
  (not repointed); the legacy dashboard engine is untouched by vNext continuous
  attempts (its own time stays at its own value).

## C03-D — preserved invariants
- TIPA and continuous keep independent `RunLifecycleService` authorities; both
  may be active concurrently; cross-workspace target/run_id fail closed;
  unknown workspace 404.
- No PIM/semantic binding, no cross-workspace data exchange, no supply-chain
  semantics, no G8+/G9/G10.

## Mandatory tests (run-control 47 → 50)
- Workspace root non-executable with exactly one executable child
  `continuous/PROCESS`; workspace target resolves to exactly
  `continuous/PROCESS`; executable target resolves only itself; extra paths
  fail closed.
- Participant/effective-scope identity is path-qualified `continuous/PROCESS`
  (never Workspace root).
- Attempt isolation: run A advances to nonzero (t=2.0); after terminal,
  restart B gets a FRESH runtime object/state and its first step lands at the
  initial boundary (t=1.0, not 3.0); A's runtime remains unchanged (t=2.0).
- Reset keeps B's run_id and B's runtime object identity (time back to 0).
- TIPA + continuous active runs coexist and remain isolated; cross-workspace
  target/run_id fail closed.
- API: `continuous/PROCESS` target resolves executable; foreign continuous path
  400; `/api/ui/hierarchy?workspace=continuous` shows `continuous → PROCESS`.
- Legacy engine independent: vNext continuous step does not advance the legacy
  dashboard engine; legacy `/step` still works.
- All C01/C02 lifecycle tests remain green.

## Regression (re-run)
run-control 50; UI/API + S04B gating 134; G6 31; G5 26; G4 56; G1 32; G2 36;
G3 328; ASSY oracle 354; continuous/compressor 61; full suite **1956 passed**
(0 failures). Compile PASS.
