# VF-vNEXT-G22 — Scenario / Run / Replay Integration — Evidence

Gate: `VF-vNEXT-G22` · Implementation gate (additive session seam + tests).
Base: `028fdd8aadcee05483b7c5b3bbcf9815a680685f` (G21 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/shwtp/bridge.py` — `ShwtpExecutionBridge`, an
  `ExecutionBridge` over the accepted G21 `ShwtpPlantSlice` (next-boundary /
  advance one window / in-context reset via fresh slice rebuild).
- `src/virtual_factory/shwtp/session.py` — `build_shwtp_session` (SH-WTP slice
  session factory).
- `src/virtual_factory/runcontrol/session.py` — `RuntimeSession`,
  `SessionIdentity`, `build_tipa_session`. A thin, orchestration-only, DOMAIN-
  AGNOSTIC facade over the G7 `RunLifecycleService` (preserves the frozen G7
  boundary: runcontrol never references SH-WTP).
- `tests/test_vnext_g22_session.py` — 15 tests.

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| explicit Workspace/run/scenario identity | `SessionIdentity(workspace_id, run_id, scenario_id, state)` |
| reset vs new attempt vs replay distinct | `reset()` (same run id) / `new_attempt()` (restart) / `replay()` (pin scenario) |
| fresh attempt/replay fresh runtime state | new attempt rebuilds bridge (fresh slice/runtime); no carry-over |
| deterministic replay | identical scenario/config reproduces equivalent trace (run-id-normalized) |
| TIPA + SH-WTP isolated | separate services/bridges/workspaces |
| reuse RunContextV2 + constructors | session delegates to `RunLifecycleService.create_run` (RunContextV2); bridges reuse `TipaAssyFederation` / `build_shwtp_plant_slice` |
| orchestration-only | session owns lifecycle only; domain runtime remains truth owner |
| identity mismatch fail closed | wrong workspace/run/scenario raises |
| SH-WTP overlay/fidelity preserved | overlay `serialize()` + `PLANT_SLICE_SCOPES` equal across replay |

## 3. Preserved / unchanged

TIPA ASSY semantics; T106/T108 equations; G21/G20/G19/G18/G14/G15; reference
connectivity graph; PIM pins. No UI, no gateway routing, no MES/PIM change, no
G4 redesign, no T110/Line2 physics.

## 4. Test evidence

- `tests/test_vnext_g22_session.py` — 15 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G22.md`).
