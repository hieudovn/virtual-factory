# VF-vNEXT-G7 — Hierarchical Scenario / Run Control

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G7` (GitHub Issue #52) + C01 + C02 |
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
  `ExecutionBridge` protocol; fail-closed guards. C01: mutations require the
  active run_id (superseded historical ids fail closed); `create_run` fails
  closed while the active run is nonterminal; execution state is attempt-bound
  (fresh bridge per attempt); restart/replay require terminal sources and start
  fresh domain contexts; reset stays in-context (same run_id + runtime objects).
- `runcontrol/assy_bridge.py` — `AssyExecutionBridge` over `TipaAssyFederation`
  + G4 `Coordinator`; natural-boundary-only advancement; capability-scoped
  in-context reset (`AssyLineRuntime.reset()`).
- `runcontrol/continuous_bridge.py` — `ContinuousExecutionBridge` over the
  accepted continuous `RuntimeService` seam (one `step_once()` per boundary,
  `reset()` in-context) + `build_continuous_workspace()` (root-only, zero
  scopes). No engine rewrite, no invented continuous hierarchy. C02: the
  bridge constructor reinitializes the shared RuntimeService to t=0 so every
  new attempt starts fresh (C01 preserved).
- `ui/api.py` — additive `/vnext/runs/*` endpoints (create/current/get +
  start/step/pause/resume/stop/reset/restart/replay) with an additive
  `?workspace=` discriminator (`TIPA` default | `continuous`); independent
  per-workspace `RunLifecycleService` (no platform-global active run); unknown
  workspace/foreign run_id → 404, foreign target → 400. Legacy endpoints
  untouched (compatibility surfaces, not repointed).
- `ui/static/run_control_context.js` (workspace-aware) + `assy_demo.html`
  mount + `assy_demo.css` + `index.html` mount + `styles.css` — additive
  minimal run-control context (path-qualified target, state, truthful time,
  Run/Pause/Resume/Step/Stop/Reset). No layout redesign.

## 3. Failure semantics

Step failure → run `failed` with distinct `last_result`/`failure`; no rollback
claimed; terminal runs never step under the same `run_id`; no hidden retry.

## 4. Test / regression results (evidence 07)

| Suite | Result |
|---|---|
| New G7 tests | **47 passed** (incl. C01 + C02) |
| UI/API + S04B gating | **134 passed** |
| G6 UI hierarchy | **31 passed** |
| G5 federation | **26 passed** |
| G4 composition | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm) | **328 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1953 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 5. STOP-condition assessment (evidence 06)

None triggered. No new synchronization/timestep policy; no ASSY
fractionalization; continuous is now truthfully bridged over its existing
RuntimeService seam (root-only, no invented hierarchy); reset
capability-scoped; replay never fabricates; no terminal run-id reuse; no
container execution; TIPA/continuous workspace authorities independent (no
platform-global active run, no cross-workspace mutation); G2/G4 contracts
intact; no G8+.

## 6. Acceptance (Issue #52 criteria)

| Criterion | Result |
|---|---|
| One platform-level run lifecycle authority over path-qualified targets | PASS |
| Immutable RunContextV2 per run; one scenario authority | PASS |
| Container/workspace targets resolve to real executable descendants | PASS |
| Existing domain runtimes remain authoritative | PASS |
| ASSY uses only legitimate natural coordination boundaries | PASS |
| Continuous bridged over its existing RuntimeService seam (root-only) | PASS |
| TIPA/continuous independent workspace authorities (no cross-workspace) | PASS |
| pause/resume/stop/reset/restart/replay obey frozen identity/history semantics | PASS |
| No new synchronization policy or G8+ scope | PASS |
| Working tree clean and branch/head pushed | PASS (after push) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G7/` — 9 files (01…09; 08 = C01
corrections: active-attempt authority + attempt-bound execution; 09 = C02
continuous binding + workspace isolation).

## 8. Final status

```text
VF-vNEXT-G7-C02 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G8 is NOT started.
