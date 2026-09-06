# VF-vNEXT-G7 — Hierarchical Scenario / Run Control

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G7` (GitHub Issue #52) |
| Program | Implementation phase (G7; only authorized implementation gate after G6) |
| Required base (branch) | `a10f581ca2e7a8b8b39c605fc54339ae88386922` (accepted G6-C01 head) |
| Branch | `feature/vf-vnext-g7` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Model | Pro |
| G8+ started | **NO** |

## 1. Objective

Implement the smallest generic vNext run-control layer targeting a G1 Workspace
or executable Scope hierarchy while preserving child runtime/domain authority —
one platform-level run lifecycle authority, immutable `RunContextV2` per run,
deterministic effective executable-scope resolution, an ASSY execution bridge on
the accepted G5/G4 seams (natural boundaries only), additive `/vnext/runs/*`
endpoints, and additive UI binding — with no universal timestep, no fractional
ASSY dwell, no run-id reuse, no fabricated replay, no G8+.

## 2. Implementation (additive)

- `runcontrol/targets.py` — G1 hierarchical target resolution (workspace /
  container / executable → deterministic executable scope set; fail-closed on
  unknown/foreign; container never a participant).
- `runcontrol/lifecycle.py` — `RunState`, `RunRecord`, `RunLifecycleService`
  (create/start/pause/resume/stop/step/reset/restart/replay), `StepResult`,
  `ExecutionBridge` protocol; fail-closed guards; fresh run identity for
  restart/replay with `source_run_id`; replay pins prior accepted inputs and is
  unavailable when the scenario authority is missing.
- `runcontrol/assy_bridge.py` — `AssyExecutionBridge` over `TipaAssyFederation`
  + G4 `Coordinator`; natural-boundary-only advancement; capability-scoped
  in-context reset (`AssyLineRuntime.reset()`).
- `ui/api.py` — additive `/vnext/runs/*` endpoints (create/current/get +
  start/step/pause/resume/stop/reset/restart/replay). Legacy endpoints untouched.
- `ui/static/run_control_context.js` + `assy_demo.html` mount + `assy_demo.css`
  — additive minimal run-control context (path-qualified target, state, truthful
  time, Run/Pause/Resume/Step/Stop/Reset). No layout redesign.

## 3. Failure semantics

Step failure → run `failed` with distinct `last_result`/`failure`; no rollback
claimed; terminal runs never step under the same `run_id`; no hidden retry.

## 4. Test / regression results (evidence 07)

| Suite | Result |
|---|---|
| New G7 tests | **30 passed** |
| UI/API + S04B gating | **134 passed** |
| G6 UI hierarchy | **31 passed** |
| G5 federation | **26 passed** |
| G4 composition | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm) | **328 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1936 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 5. STOP-condition assessment (evidence 06)

None triggered. No new synchronization/timestep policy; no ASSY
fractionalization; continuous not bridged (behavior green); reset
capability-scoped; replay never fabricates; no terminal run-id reuse; no
container execution; G2/G4 contracts intact; no G8+.

## 6. Acceptance (Issue #52 criteria)

| Criterion | Result |
|---|---|
| One platform-level run lifecycle authority over path-qualified targets | PASS |
| Immutable RunContextV2 per run; one scenario authority | PASS |
| Container/workspace targets resolve to real executable descendants | PASS |
| Existing domain runtimes remain authoritative | PASS |
| ASSY uses only legitimate natural coordination boundaries | PASS |
| pause/resume/stop/reset/restart/replay obey frozen identity/history semantics | PASS |
| No new synchronization policy or G8+ scope | PASS |
| Working tree clean and branch/head pushed | PASS (after push) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G7/` — 7 files (01…07).

## 8. Final status

```text
VF-vNEXT-G7 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G8 is NOT started.
