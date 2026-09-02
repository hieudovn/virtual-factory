# 01 — Current-State Runtime/Composition Evidence Inventory

Repo-first discovery of runtime/composition seams, recorded against the ARCH-01
package baseline (`feature/vf-arch-01` @ `41903e18…`). Distinguishes reusable
runtime seam vs domain-specific behavior vs demo-only orchestration vs legacy.

## 1.1 ASSY composition orchestration (demo seam)

| File | Current behavior | Classification |
|---|---|---|
| `src/virtual_factory/assembly/demo_composition.py` `AssyDemoComposition.step_all()` | Steps each non-excluded `AssyDemoContext` via `step_context()`; `demo_step_number += 1` once per composition step. Policy documented as **COMMON_DEMO_CLOCK**. **No assertion of equal `simulation_time_s`** across contexts. Excluded (faulted) sub-lines are fully frozen (no feed, no step). | **Demo-only orchestration** (not plant synchronization truth). Reusable precedent for "coordinate N independent executable scopes on a common advance". |
| `AssyDemoContext.step_context()` | on-demand RSO2 → `execute_dwell()` → `index_line()` if `READY_TO_INDEX` → `introduce_next_sso2()`. | **Demo orchestration policy** over one runtime. |
| `AssyDemoComposition.reset()` / `initialize()` | Rebuilds all 6 isolated contexts from config. | **Lifecycle seam** (create/reset). |
| `AssyDemoComposition.snapshot()` | Detached snapshot of the selected context. | **Inspection seam**. |

## 1.2 ASSY domain runtime (must not be rewritten)

| File | Current behavior |
|---|---|
| `src/virtual_factory/assembly/line_runtime.py` `AssyLineRuntime` | ONE conveyor lane, stop-and-go indexed; WIP lifecycle; AP01-AP06 stations; genealogy; quality records; auto-timing; operation execution. `global_run_mode` (CompletionMode.AUTO default); `produce_sso2_wip`/`produce_rso2_wip`; `introduce_to_assy`; `execute_dwell`; `index_line`; `reset`; per-WIP `released_at_sim_s`. |

**Accepted semantics:** the runtime owns its domain state; composition must not
reach into it. (Frozen: `AssyLineRuntime` is not rewritten for composition.)

## 1.3 Discrete kernel (reusable domain-neutral runtime seam)

| File | Current behavior |
|---|---|
| `src/virtual_factory/discrete/state.py` | `RunStatus`: CREATED → READY → RUNNING/PAUSED → COMPLETED/STOPPED/FAILED. `DiscreteRunState` (`run_id`, `simulation_time_s`, `processed_events`, `pending_events`, `stop_reason`, `failure_error`, `snapshot_sequence`). |
| `src/virtual_factory/discrete/controller.py` | `DiscreteRunController`: `ExecutionMode` MANUAL/AUTOMATIC/HYBRID; command queue; SafePoint; allowed-actions projection; `ControllerPacingPolicy` (speed_factor, max_events_per_second, snapshot_broadcast_max_hz). No async loop, no domain logic. |
| `src/virtual_factory/discrete/engine.py` | `DiscreteSimulationEngine`: deterministic, synchronous, domain-neutral; `FutureEventScheduler`; max-events safety; no-progress detection; replay metadata. |
| `src/virtual_factory/discrete/run_service.py` | `DiscreteRunService`: one-run façade owning at most one controller → engine; no multi-run, no transport. |
| `src/virtual_factory/discrete/{run_context,scheduler,events,dispatcher}.py` | RunContext, FutureEventScheduler, ScheduledEvent, EventDispatcherProtocol. |

**Reusable seam:** the discrete lifecycle (CREATED→…→FAILED) and run/service
separation are a precedent for the platform run lifecycle.

## 1.4 Continuous kernel (reusable domain-neutral runtime seam)

| File | Current behavior |
|---|---|
| `src/virtual_factory/core/engine_contract.py` | `SimulationEngineProtocol` (structural): `initialized`, `dt_s`, `initialize()`, `step()`. |
| `src/virtual_factory/core/engine_factory.py` | `resolve_engine_kind` (top-level `model_type`; default `continuous_process`), `create_engine`. Single construction seam. |
| `src/virtual_factory/core/simulation_engine.py` | `SimulationEngine`: `dt_s` (default 1.0), `TimeManager`, `ScenarioManager`, `initialize()` builds `RuntimeAssembly`, `step()`. |
| `src/virtual_factory/core/time_manager.py` | `TimeManager`: `current_time_s`, `step_s`, `advance()` — fixed-step tick. |
| `src/virtual_factory/core/runtime_factory.py` | `build_runtime` → `RuntimeAssembly` (graph, state, equipment/sensors/controllers/actuators, alarm manager, output policy, telemetry store). |
| `src/virtual_factory/core/plant_graph.py`, `core/ports.py` | `PlantGraph` (nodes+edges); `Port` (kind physical/measurement/signal/command/publication; direction in/out/inout). |

**Reusable seam:** `SimulationEngineProtocol.initialize/step` + `TimeManager`
fixed-step tick; `Port` typed interface (evidence only — not assumed sufficient
for vNext boundary payloads).

## 1.5 Scenario / reset APIs

| File | Current behavior |
|---|---|
| `src/virtual_factory/scenarios/scenario_manager.py` | `ScenarioManager.apply_due_actions(time)` applies time-scheduled actions to `RuntimeState`/config. |
| `src/virtual_factory/scenarios/scenario_loader.py` | `load_scenario` → `ScenarioConfig`. |

Scenario authority: one scenario config drives actions within a run; no second
scenario engine is introduced here.

## 1.6 Summary — seams vs domain vs demo vs legacy

| Layer | Reusable runtime seam | Domain-specific | Demo-only | Legacy/reference |
|---|---|---|---|---|
| Continuous | `SimulationEngineProtocol`, `TimeManager`, `RuntimeAssembly`, `PlantGraph`, `Port` | equipment/control physics | — | `simulators/wtp` (VF-1) |
| Discrete | `RunStatus` lifecycle, `DiscreteRunController/Service`, scheduler/engine | — | — | `simulators/vf2` (VF-2) |
| ASSY | per-context isolated `AssyLineRuntime` (standalone/federated precedent) | `AssyLineRuntime` line/station/quality semantics | `AssyDemoComposition.step_all` (COMMON_DEMO_CLOCK), feed policy | `tipa.py` single-line topology |
