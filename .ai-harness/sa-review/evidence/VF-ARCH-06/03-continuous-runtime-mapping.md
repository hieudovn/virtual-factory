# VF-ARCH-06 · Evidence 03 — Decision C: Continuous runtime mapping

## 1. Decision statement

**An executable Simulation Scope owns an execution/runtime boundary — not
necessarily exactly one engine instance. The current continuous seams are a
shared-core precedent that can be hosted behind that boundary; the shared core
owns the execution/composition framework while SH-WTP-specific physics/process
logic remains a domain model, not a core responsibility.**

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

## 4. Mapping to executable scopes (execution boundary, not engine cardinality)

- An executable SH WTP process-area scope owns an **execution/runtime
  boundary**. The boundary may host/use **one or more execution mechanisms**
  appropriate to the scope contract — continuous dynamics, state-machine /
  procedure, discrete-event behavior, or composed/hybrid mechanisms. It is NOT
  frozen as exactly one `SimulationEngine` instance.
- For the **current continuous shared-core precedent**, `SimulationEngine` /
  `runtime.engine: continuous_process` is the current implementation/profile
  descriptor (PH00 B3/B9), NOT a universal `1 scope = 1 engine` platform
  invariant.
- `runtime.engine` remains the PH00 **compatibility / default / profile
  descriptor** already frozen; it is not reinterpreted here as universal
  runtime cardinality.
- Scope-level execution ownership is valid; **engine cardinality/type is an
  implementation/profile concern** unless explicitly frozen by a later contract.
- SH WTP stays compatible with hybrid scopes/workspaces and ARCH-02
  synchronization/composition semantics. SH-WTP domain models are assembled from
  `configs/workspaces/shw-wtp/` (PH00 B9) and hosted behind the scope execution
  boundary.

## 5. Evidence that this already works

- `engine_factory.resolve_engine_kind` dispatches on config → `continuous_process`
  (tested by `test_engine_boundary.py`).
- Continuous MVP (`continuous_mvp_01.yaml`) + `process_dynamics` + balance + PID
  + operating states are all proven by the tests in evidence 01 §5.
- The compressor train is the precedent for a "domain model hosted on the shared
  continuous framework behind a scope execution boundary".

## 6. Conclusion

SH WTP requires a **domain model** (future) + **already-existing shared
framework** — no new platform architecture decision. The only missing pieces are
the frozen implementation gates (Workspace/Scope foundation, coordinator,
provenance-v2, semantic binding) — all already planned in evidence 08.

**Decision C is explicit.**
