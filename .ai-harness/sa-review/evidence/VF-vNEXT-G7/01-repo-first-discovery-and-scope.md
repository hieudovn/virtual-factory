# VF-vNEXT-G7 · Evidence 01 — Repo-first discovery + scope

## Authorization
GitHub Issue #52 (`VF-vNEXT-G7 — Hierarchical Scenario / Run Control`). Required
base `a10f581ca2e7a8b8b39c605fc54339ae88386922` (accepted G6-C01 head). Branch
`feature/vf-vnext-g7`. Model Pro.

## Repo-first facts (reused, unchanged)
- G2 `RunContextV2` (provenance/context.py) is an immutable, mechanism-neutral
  run-identity/provenance-input record (`workspace_id`, `run_id`, optional
  `scope_path`, `scenario_id`, `model_id`, `profile`, `random_seed`,
  `source_run_id`); it does NOT implement reset/replay orchestration.
- G4 `Coordinator.run_window(window_id, target_time_s)` advances registered
  executable participants through one exact boundary; fail-closed, no rollback,
  no domain scheduling.
- G5 `TipaAssyFederation` + `AssySubLineAdapter` host six ASSY sub-lines over G1
  scopes; advancement only at exact natural dwell boundaries (nominal dwell 120s,
  index 0); arbitrary/fractional boundaries fail closed.
- G6 provides path-qualified hierarchy/context primitives and authoritative ASSY
  sub-line selection via existing `POST /assy-demo/select`.
- Existing continuous and ASSY control APIs/UI remain legacy/domain-specific;
  G7 adds a generic orchestration seam without repointing them.

## Scope decisions (conservative; recorded)
- New additive package `src/virtual_factory/runcontrol/` (targets, lifecycle,
  assy_bridge) + read-only/minimal run-control endpoints under `/vnext/runs/*`
  in `ui/api.py` + additive `run_control_context.js` + a hidden mount in
  `assy_demo.html` + additive CSS. No existing runtime/engine rewritten; no
  legacy endpoint repointed; no new synchronization policy; no G8+.
- The run lifecycle authority is singular and platform-level; execution is
  delegated to `AssyExecutionBridge` (G5 + G4 seams). Domain runtimes remain
  authoritative.
- Continuous is NOT bridged into the new lifecycle (it has no authoritative
  multi-level G1 hierarchy); its existing runtime behavior is preserved and
  regressed (test + continuous baseline).
- Reset is capability-scoped (bridge declares `supports_reset`; only
  `AssyLineRuntime.reset()` in-context). Replay pins prior accepted inputs and
  is exposed as unavailable when the scenario authority is missing.
