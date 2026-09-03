# VF-ARCH-06 · Evidence 03 — Decision C: Continuous runtime mapping

## 1. Decision statement

**Current continuous seams map to executable scopes WITHOUT inventing a single
workspace engine. The shared core owns execution/composition framework;
SH-WTP-specific physics/process logic remains a domain model, not a core
responsibility.**

## 2. Shared-core vs domain split

| Concern | Owner | Current seam |
|---|---|---|
| Time / step / engine skeleton | shared core | `core/simulation_engine.py` (plant-agnostic) |
| Plant graph / model assembly | shared core | `core/runtime_factory.py`, `core/model_registry.py`, `core/schema.py` |
| Generic continuous dynamics (pump/valve/pipe/tank) | shared core | `equipment/process_dynamics.py` |
| Generic continuous domain models | shared core | `equipment/{compressor,compressor_train,boundary}.py` |
| Balance / medium / stream | shared core | `balance/*` |
| Control (PID) | shared core | `control/pid_controller.py` |
| Operating-state machine | shared core | `operating_states/state_machine.py` |
| Telemetry / observation | shared core | `telemetry/*`, `observation/*` |
| **Water-treatment physics/process logic** | **SH-WTP domain model (future)** | **NOT in `src/` today** |

## 3. What belongs where

- **Shared execution framework** (reusable across workspaces): engine kind
  dispatch (`engine_factory` — currently only `continuous_process`), runtime
  assembly, time manager, scenario manager, telemetry/observation/balance/control
  primitives.
- **SH-WTP-specific domain model** (future): water-treatment stage semantics
  (clarification, filtration, disinfection, energy, KPI) — these are domain
  physics that would plug INTO the shared framework, exactly like the compressor
  train plugs in today. They are NOT new platform architecture.

## 4. Mapping to executable scopes

- An executable SH WTP process-area scope = one runtime boundary hosting one
  `SimulationEngine` (or future equivalent) whose models are SH-WTP domain
  models, assembled from `configs/workspaces/shw-wtp/` (PH00 B9).
- `runtime.engine: continuous_process` (B3) is the discriminator; there is no
  "shw-wtp engine kind" and no one-engine-per-workspace assumption.
- Hybrid is allowed (ARCH-01): different child scopes may use different
  execution mechanisms; engine selection sits at scope/runtime-composition level.

## 5. Evidence that this already works

- `engine_factory.resolve_engine_kind` dispatches on config → `continuous_process`
  (tested by `test_engine_boundary.py`).
- Continuous MVP (`continuous_mvp_01.yaml`) + `process_dynamics` + balance + PID
  + operating states are all proven by the tests in evidence 01 §5.
- The compressor train is the precedent for "domain model inside shared engine".

## 6. Conclusion

SH WTP requires a **domain model** (future) + **already-existing shared
framework** — no new platform architecture decision. The only missing pieces are
the frozen implementation gates (Workspace/Scope foundation, coordinator,
provenance-v2, semantic binding) — all already planned in evidence 08.

**Decision C is explicit.**
