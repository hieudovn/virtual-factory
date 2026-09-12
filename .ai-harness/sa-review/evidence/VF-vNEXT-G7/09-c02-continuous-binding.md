# VF-vNEXT-G7-C02 · Evidence 09 — Continuous vNext execution binding + workspace isolation

SA review of exact head `bf53d8ef6cf8f15d285dd875c1ac8a316529c49d`
(comment `5557404656`) found G7 incomplete: the continuous runtime was not
actually bridged into the vNext run-control layer (only non-regression was
proven). C02 binds the accepted continuous RuntimeService seam and hardens the
workspace boundary. No continuous-engine rewrite, no invented continuous
hierarchy, no cross-workspace composition, no G8+.

## What changed (additive)
- `runcontrol/continuous_bridge.py` (new): `ContinuousExecutionBridge` +
  `build_continuous_workspace()` (root-only Workspace, zero scopes).
- `runcontrol/__init__.py`: exports the continuous bridge + root workspace
  builder.
- `ui/api.py`: `_get_run_control_service(workspace)` is now a per-workspace
  registry (`TIPA` | `continuous`); every `/vnext/runs*` endpoint accepts an
  additive `?workspace=` query param (default `TIPA`, following the existing
  G6 `?workspace=` convention); unknown workspace → 404; cross-workspace run_id
  → 404; foreign target path → 400. Legacy `/step /start /stop /reset`
  endpoints are unchanged (compatibility surfaces, not repointed).
- `ui/static/run_control_context.js`: workspace-aware via
  `data-vf-workspace` (default `TIPA`).
- `ui/static/index.html` + `styles.css`: additive root-only continuous
  run-control mount (hidden until a continuous run exists).

## C02-A — smallest truthful continuous binding (no engine rewrite)
- `natural_next_boundary` = engine time + `dt_s` (the engine's fixed-step scan
  cadence — the only truthful continuous boundary; no invented boundaries).
- `advance` = one `RuntimeService.step_once()` (the accepted runtime seam);
  failures fail closed via `StepResult(status="failed")`, no hidden retry.
- `reset` = `RuntimeService.reset()` (accepted in-context reinitialize to t=0);
  `supports_reset=True`.
- The bridge is constructed over the SAME `RuntimeService` instance the legacy
  dashboard drives — the vNext run-control controls the real continuous
  runtime; no second engine instance is fabricated.

## C02-B — root-only structure (no invented hierarchy)
- `build_continuous_workspace()` returns a Workspace with `workspace_id =
  "continuous"` and `top_level_scopes=()`; `resolve_target` yields
  `target_kind="workspace"` with an EMPTY effective-scope set; any non-root
  path fails closed (`TargetResolutionError`). The plant config `plant_id`
  remains a config/display fact (G6 root-only context unchanged).

## C02-C — independent workspace authorities (no platform-global active run)
- Each workspace key owns its own `RunLifecycleService` (own `_runs`, own
  `_active_run_id`, own `run_id` sequence, own bridge state).
- TIPA and continuous runs can be active simultaneously; mutation is
  scoped per workspace; a TIPA run_id against the continuous authority (and
  vice versa) is an unknown run (404), never cross-mutation.
- Foreign workspace target paths fail closed (400) in both authorities.
- No cross-workspace data exchange / supply-chain semantics.

## C02-D — attempt-bound execution preserved for continuous (C01)
- `ContinuousExecutionBridge.__init__` reinitializes the shared RuntimeService
  to its accepted initial baseline (t=0), so every NEW attempt (restart/replay/
  create-after-terminal) starts fresh — it does not continue the prior
  attempt's time/WIP. The `RunRecord.bridge` stays attempt-local (C01).
- `reset` keeps the same run_id + same attempt (same RuntimeService object);
  it is never turned into restart/replay.
- replay without a pinned scenario is explicit-unavailable (never fabricated).

## Mandatory adversarial tests (10 new; total run-control 37 → 47)
1. continuous natural boundary = one dt; step advances exactly one tick.
2. continuous reset is in-context (t back to 0).
3. continuous workspace is root-only: zero scopes, workspace target empty
   effective set, non-root path fails closed (no fake hierarchy).
4. continuous lifecycle (start/step/pause/step-fails/resume/step/stop) via the
   lifecycle authority; restart starts fresh (t=1 not t=3); source stays
   historical.
5. continuous replay unavailable without pinned scenario.
6. TIPA + continuous active runs coexist (independent authorities).
7. run_id cannot cross-mutate between TIPA and continuous (404).
8. foreign-workspace target fails closed (400); unknown workspace 404.
9. continuous lifecycle via API; legacy engine semantics unchanged (dt=1.0,
   time_s reflects the shared seam).
10. All G7/C01 active-attempt tests remain green.

## Regression (re-run)
run-control 47; UI/API + S04B gating 134; G6 31; G5 26; G4 56; G1 32; G2 36;
G3 328; ASSY oracle 354; continuous/compressor 61; full suite **1953 passed**
(0 failures). Compile PASS.
