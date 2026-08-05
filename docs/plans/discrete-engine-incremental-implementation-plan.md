# Deliverable C — Incremental Implementation Plan

> **Date:** 2026-08-05  
> **Author:** PM (AI Coding Agent)

---

## 1. Planning Principles

1. **Preserve continuous behavior at every stage.** Every slice ends with all 185 tests passing.
2. **No big-bang package moves.** Introduce abstractions incrementally.
3. **Regression tests before structural changes.** Add contract tests before refactoring.
4. **Contracts before TIPA logic.** Engine boundary and schema before any assembly workflow.
5. **TIPA is configuration, not engine logic.** No TIPA-specific class, method or constant in engine code.
6. **Small, reversible slices.** Each slice can be reverted independently.
7. **Explicit stop/go gates.** SA approval required before proceeding past each gate.

---

## 2. Dependency Graph

```
Slice 0 (Baseline)
    │
Slice 1 (Engine Boundary)
    │
    ├── Slice 2 (Discrete Kernel)
    │       │
    │       └── Slice 3 (Manufacturing Semantics)
    │               │
    │               └── Slice 4 (TIPA Demo Config)
    │
    └── (Slice 5: API/UI/MES — planning only, no implementation)
```

---

## 3. Implementation Slices

### Slice 0 — Baseline Protection ✅ (COMPLETED by this assessment)

**Purpose:** Establish facts before any code changes.

**Actions:**
- [x] Capture commit SHA, branch, test results
- [x] Run full test suite (185 passed)
- [x] Document current architecture
- [x] Identify coupling points
- [x] Create assessment documents

**Gate:** SA reviews Deliverables A/B/C/D. Issues Prompt 002 for Slice 1.

---

### Slice 1 — Engine Boundary (S)

**Purpose:** Introduce engine abstraction without changing behavior.

**Files likely to change:**
| File | Change |
|------|--------|
| `core/simulation_engine.py` | Rename `SimulationEngine` → `ContinuousSimulationEngine`. Extract `_process_physics()` method. |
| `core/engine_base.py` (NEW) | `BaseSimulationEngine` with `step()`, `initialize()`, `snapshot()`, `stop()` contracts. |
| `core/engine_factory.py` (NEW) | `create_engine(config) → BaseSimulationEngine` — reads `model_type`. |
| `main.py` | Replace `SimulationEngine(...)` with `create_engine(config)`. |
| `ui/api.py` | Replace `SimulationEngine(...)` in `RuntimeService` with `create_engine(config)`. |
| `ui/runtime_service.py` | Make engine reference generic (`BaseSimulationEngine`). |
| `core/schema.py` | Add `model_type: str = "continuous_process"` to `PlantMetadata`. No schema changes yet. |
| `tests/` (NEW) | `test_engine_contract.py` — tests that both engines satisfy the contract. |

**What this slice does NOT do:**
- No discrete engine logic
- No schema restructuring
- No package moves
- No new dependencies

**Acceptance criteria:**
- All 185 existing tests pass
- `ContinuousSimulationEngine` is a drop-in replacement for old `SimulationEngine`
- `create_engine(continuous_config)` returns `ContinuousSimulationEngine`
- `test_engine_contract.py` validates the contract

**Rollback:** Rename back to `SimulationEngine`, delete new files. Zero data migration.

**Gate:** SA approves Slice 1 result. Prompt 003 issued for Slice 2.

---

### Slice 2 — Discrete Kernel (M)

**Purpose:** Build the minimum discrete-event simulation core.

**New files:**
| File | Content |
|------|---------|
| `core/discrete_engine.py` | `DiscreteSimulationEngine(BaseSimulationEngine)` — event-driven step() |
| `core/discrete_scheduler.py` | `FutureEventScheduler` — heapq-based, `schedule(t, callback)`, `run_until(t)` |
| `core/discrete_entity.py` | `Entity`, `EntityType`, `EntityAttribute` |
| `core/discrete_source.py` | `Source` — generates entities by arrival schedule |
| `core/discrete_queue.py` | `Queue` / `Buffer` — bounded FIFO with WIP tracking |
| `core/discrete_processor.py` | `Processor` — seizes entity, delays, releases |
| `core/discrete_sink.py` | `Sink` — absorbs completed entities |
| `core/discrete_state.py` | `PartState`, `QueueSnapshot`, `ResourceSnapshot` — state structures |
| `core/schema.py` | `DiscreteManufacturingConfig(SimulationModelConfig)` — schema for discrete config |
| `core/time_manager.py` | Add `advance_to(target_s)` method (backward-compatible) |
| `configs/model_types/discrete/` (NEW) | Model-type YAMLs for discrete components |

**Existing files changed:**
| File | Change |
|------|--------|
| `core/runtime_state.py` | Add `parts: dict[str, PartState]`, `queue_states`, `resource_states` (optional fields) |
| `core/engine_factory.py` | Add `"discrete_manufacturing"` → `DiscreteSimulationEngine` |
| `scenarios/scenario_manager.py` | Add `entity_inject` action type |

**Acceptance criteria:**
- `DiscreteSimulationEngine` satisfies engine contract
- Scheduler processes events in correct time order
- Source→Queue→Processor→Sink flow works with 1 entity
- Deterministic: same seed → same event trace
- All 185 continuous tests still pass
- New discrete tests: scheduler (5), entity (3), source (3), queue (3), processor (3), engine (3) = ~20 tests

**Gate:** SA approves Slice 2 result. Prompt 004 issued for Slice 3.

---

### Slice 3 — Manufacturing Semantics (M)

**Purpose:** Add routing, quality, hold/rework, and manufacturing KPIs.

**New files:**
| File | Content |
|------|---------|
| `core/discrete_router.py` | `Router` — conditional branching by entity attribute |
| `core/discrete_quality.py` | `QualityGate`, `TestProfile`, `MeasurementResult`, `AcceptanceRule` |
| `core/discrete_hold_rework.py` | `HoldArea`, `ReworkRoute` — entity hold/rework/scrap flow |
| `core/discrete_resource.py` | `Resource`, `ResourcePool` — seize/release with capacity |
| `core/discrete_calendar.py` | `ShiftCalendar` — availability windows |
| `core/discrete_kpi.py` | Throughput, cycle time, WIP, utilization, yield calculations |
| `core/discrete_event.py` | `SimulationEvent` dataclass — canonical event envelope |
| `core/discrete_event_trace.py` | `EventTrace` — append-only event log |

**Acceptance criteria:**
- Router splits entities by attribute
- Quality gate passes/fails based on measurement + acceptance rule
- Hold area stores entity; rework route sends it back
- Resource pool limits concurrent processing
- KPIs are derivable from event trace
- All previous tests pass

**Gate:** SA approves Slice 3 result. Prompt 005 for Slice 4.

---

### Slice 4 — TIPA Demo Configuration (S)

**Purpose:** Configure the TIPA assembly line as a discrete manufacturing model.

**New files:**
| File | Content |
|------|---------|
| `configs/plants/tipa_assembly_v1.yaml` | TIPA discrete config — 2 sources, 6 process streams |
| `configs/scenarios/tipa_baseline.yaml` | Baseline scenario |
| `configs/scenarios/tipa_source_shortage.yaml` | Source shortage scenario |
| `configs/scenarios/tipa_station_failure.yaml` | Station failure scenario |
| `configs/model_types/discrete/assembly_station_v1.yaml` | Assembly station model type |
| `configs/model_types/discrete/quality_gate_v1.yaml` | Quality gate model type |

**Config structure:**
```yaml
model_type: discrete_manufacturing
model_version: "0.1.0"
plant:
  id: TIPA-ASSEMBLY
  name: TIPA Final Assembly Line
entity_types:
  - id: SSO2
    attributes: [source_method, product_family]
sources:
  - id: HYDRAULIC_SOURCE
    entity_type: SSO2
    arrival_interval_s: 120
    attributes: {source_method: hydraulic}
  - id: HEATING_SOURCE
    entity_type: SSO2
    arrival_interval_s: 180
    attributes: {source_method: heating}
stations:
  - id: SSO2_BUFFER
    type: buffer
    capacity: 20
  - id: AP01 ... AP06
    type: assembly_station
    processing_time_s: {value: 600, status: assumed}
routes:
  - from: HYDRAULIC_SOURCE
    to: SSO2_BUFFER
  - from: HEATING_SOURCE
    to: SSO2_BUFFER
  - from: SSO2_BUFFER
    to: AP01 ... AP06 (round-robin)
```

**Acceptance criteria:**
- Config loads and validates
- 60 simulated minutes produce entities through the line
- Source shortage scenario reduces throughput
- Station failure scenario routes around failed station
- No TIPA-specific code in engine

**Gate:** SA approves Slice 4. Demo ready.

---

### Slice 5 — API/UI and MES Integration (Planning Only)

**Not implemented in this plan.** Scope for future prompt.

**Planning notes:**
- API: add `/api/workspaces`, `/api/runs`, `/api/events`
- UI: line overview, WIP dashboard, entity trace
- MES: canonical event adapter, environment isolation
- PlantOS: replay/telemetry integration

---

## 4. File/Module Impact by Slice

| File | Slice 0 | Slice 1 | Slice 2 | Slice 3 | Slice 4 |
|------|---------|---------|---------|---------|---------|
| `core/simulation_engine.py` | Read | **Modify** | — | — | — |
| `core/engine_base.py` | — | **NEW** | — | — | — |
| `core/engine_factory.py` | — | **NEW** | Modify | — | — |
| `core/discrete_engine.py` | — | — | **NEW** | — | — |
| `core/discrete_scheduler.py` | — | — | **NEW** | — | — |
| `core/discrete_*.py` (10 files) | — | — | **NEW** | **NEW** | — |
| `core/schema.py` | Read | Modify | **NEW models** | — | — |
| `core/runtime_state.py` | Read | — | Modify | — | — |
| `core/time_manager.py` | Read | — | Modify | — | — |
| `scenarios/scenario_manager.py` | Read | — | Modify | — | — |
| `main.py` | Read | Modify | — | — | — |
| `ui/api.py` | Read | Modify | — | — | — |
| `ui/runtime_service.py` | Read | Modify | — | — | — |
| `configs/plants/tipa_*.yaml` | — | — | — | — | **NEW** |
| `configs/model_types/discrete/` | — | — | **NEW** | — | **NEW** |
| `tests/test_engine_contract.py` | — | **NEW** | — | — | — |
| `tests/test_discrete_*.py` (~10 files) | — | — | **NEW** | **NEW** | — |

---

## 5. Test Additions by Slice

| Slice | New Tests | Cumulative |
|-------|-----------|-----------|
| Slice 0 | 0 (baseline only) | 185 |
| Slice 1 | ~5 (engine contract) | ~190 |
| Slice 2 | ~20 (scheduler, entity, source, queue, processor, engine) | ~210 |
| Slice 3 | ~20 (router, quality, hold/rework, resource, calendar, KPI, event) | ~230 |
| Slice 4 | ~5 (config validation, integration smoke) | ~235 |

---

## 6. Acceptance Criteria by Slice

| Slice | Key AC |
|-------|--------|
| 0 | 185 tests pass. Assessment docs produced. |
| 1 | Continuous engine satisfies contract. Factory creates both engine types. 185+ tests pass. |
| 2 | Discrete scheduler processes events in order. Source→Queue→Processor→Sink pipeline works. Deterministic. |
| 3 | Router splits. Quality gate decides. Hold/rework flows. Resource pool limits. KPIs traceable. |
| 4 | TIPA config loads. 60 min simulation produces entities. 2 scenarios demonstrate different behavior. |

---

## 7. Stop/Go Gates

| Gate | Condition | Who |
|------|-----------|-----|
| G0→G1 | SA reviews assessment, approves Slice 1 | SA |
| G1→G2 | Slice 1 tests pass, SA approves | SA |
| G2→G3 | Slice 2 tests pass, SA approves scheduler approach | SA |
| G3→G4 | Slice 3 tests pass, SA approves quality/hold/rework model | SA |
| G4→G5 | Slice 4 demo ready, SA approves TIPA config | SA |

---

## 8. Rollback Strategy

Each slice is independently reversible:
- **Slice 1:** Rename class back, delete 2 new files
- **Slice 2:** Delete `core/discrete_*.py`, remove discrete factory entry, revert schema additions
- **Slice 3:** Delete 8 new files, revert discrete state fields
- **Slice 4:** Delete 6 config files

No data migration required at any slice.

---

## 9. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Engine boundary breaks API/CLI | Low | High | Test factory dispatch in Slice 1 before Slice 2 |
| Schema extension breaks YAML loading | Medium | Medium | Test all existing configs in `configs/plants/` |
| Discrete scheduler has ordering bugs | Medium | Medium | Deterministic seed tests from day 1 |
| TIPA assumptions leak into engine | Medium | High | Code review gate before Slice 4 |
| Scope creep into MES/PlantOS | Medium | Medium | Explicitly out of scope per SA architecture doc |

---

## 10. Suggested Prompt 002 Scope

**Prompt 002 should cover Slice 1 only:**

1. Create `BaseSimulationEngine` contract
2. Rename `SimulationEngine` → `ContinuousSimulationEngine` with `_process_physics()`
3. Create `engine_factory.py` with `model_type` dispatch
4. Update `main.py` and `api.py` to use factory
5. Add `model_type` to `PlantMetadata`
6. Create `test_engine_contract.py`
7. Run full test suite — must be 185+ passing

---

## 11. Estimated Complexity

| Slice | Complexity | Rationale |
|-------|-----------|-----------|
| Slice 1 — Engine Boundary | **S** | Rename + extract method + factory. ~3 files changed, ~5 new tests. |
| Slice 2 — Discrete Kernel | **M** | New scheduler, entity, source/queue/processor/sink. ~8 new files, ~20 tests. |
| Slice 3 — Manufacturing Semantics | **M** | Router, quality, hold/rework, resource, calendar, KPI, event trace. ~8 new files, ~20 tests. |
| Slice 4 — TIPA Demo Config | **S** | Pure configuration. ~6 YAML files, ~5 integration tests. |
| Slice 5 — API/UI/MES | **L** | Deferred. Major API expansion + UI workspaces. |
