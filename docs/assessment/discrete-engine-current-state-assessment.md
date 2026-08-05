# Deliverable A — Current-State Repository Assessment

> **Date:** 2026-08-05  
> **Author:** PM (AI Coding Agent)  
> **Repository:** `https://github.com/hieudovn/virtual-factory`  
> **Commit assessed:** `e9aea90`  
> **Prompt:** `02-prompt-001-pm-codebase-assessment.md`

---

## 1. Executive Summary

Virtual Factory is a **model-driven, graph-based continuous-process simulator** with a strong telemetry pipeline and zero engine abstraction. Adding discrete manufacturing requires:

1. An **engine boundary** (base class/adapter) — none exists today.
2. A **discrete scheduler** — the codebase has only fixed-time-step `TimeManager.advance()`.
3. **Schema extension** — `PlantConfig` is process-oriented but has `ConfigDict(extra="allow")`.
4. **Zero telemetry changes** — the entire `SignalValue` → frame → export → MQTT/OPC UA pipeline is domain-neutral.

The codebase is well-structured for extension. The main risk is `simulation_engine.py` which has hard-coded continuous-process calls (`update_continuous_process`, `MassBalance`, `EnergyBalance`).

---

## 2. Repository and Test Baseline

| Item | Value |
|------|-------|
| **Commit SHA** | `e9aea90` |
| **Branch** | `main` |
| **Python** | 3.11.9 |
| **Tests** | 185 passed, 0 failed, 5.10s |
| **Untracked files** | 2 (`out/xr001-pump-trip.csv`, `out/xr001-pumping-station.csv`) |
| **Modified files** | 0 |
| **Warnings** | PytestCacheWarning (permission) — pre-existing |

**Test breakdown:**
- VF-1 WTP simulator: 13 tests
- VF-2 PIM-native simulator: 154 tests
- Main VF engine + equipment + gateways: 18 tests

**Existing demo smoke tests:**
```bash
python -m virtual_factory validate --config configs/plants/compressor_train_benchmark_01.yaml  # ✅
python -m simulators.vf2.main --package simulators/vf2/examples/sample_pim_package.json --validate-only  # ✅
```

---

## 3. Current Runtime Architecture

```
CLI (main.py) / API (ui/api.py)
        │
        ▼
  SimulationEngine(config, dt, scenario)
        │
    initialize() ──► RuntimeFactory.build_runtime()
        │               ├── ModelRegistry.from_directory()
        │               ├── PlantGraph.from_config()
        │               └── build equipment/sensors/controllers/actuators
        │
    step() loop:
        1. scenario actions  ── ScenarioManager
        2. sensors sample    ── BaseSensor.sample()
        3. controllers exec  ── BaseController.execute()
        4. actuators update  ── BaseActuator.update()
        5. update_continuous_process()  ← HARD-CODED CONTINUOUS
        6. equipment.process_step()
        7. mass/energy balance          ← HARD-CODED CONTINUOUS
        8. sensors re-sample
        9. alarms evaluate
        10. telemetry frame             ← REUSABLE
        11. time advance                ← FIXED-STEP ONLY
```

**Key files:**
- `core/simulation_engine.py` (187 lines) — monolithic step() with hard-coded continuous calls
- `core/schema.py` (300+ lines) — Pydantic v2 PlantConfig, extensible via extra="allow"
- `core/runtime_state.py` (97 lines) — truth + signals + diagnostics; streams field is continuous-only
- `core/runtime_factory.py` (79 lines) — domain-agnostic builder via ModelRegistry
- `core/time_manager.py` (17 lines) — fixed-step only, no event-jump
- `core/model_registry.py` (108 lines) — pure string→class mapping, fully generic
- `scenarios/scenario_manager.py` (80 lines) — 5 neutral actions + 1 valve_stuck (continuous)
- `ui/api.py` — FastAPI, hard-codes SimulationEngine, PID endpoint is continuous-specific
- `main.py` — CLI, hard-codes SimulationEngine, no engine selection

---

## 4. Module Responsibility Map

| Module | Responsibility | Domain |
|--------|---------------|--------|
| `core/schema.py` | Plant + equipment + sensor config | Continuous (extensible) |
| `core/simulation_engine.py` | Orchestration + step loop | Continuous (monolithic) |
| `core/runtime_state.py` | Truth + signals + streams | Mixed (streams=continuous) |
| `core/runtime_factory.py` | Build objects from config + registry | **Neutral** |
| `core/time_manager.py` | Fixed-step time | **Neutral** (too simple) |
| `core/model_registry.py` | YAML→class mapping | **Neutral** |
| `core/plant_graph.py` | Node+edge graph from config | Mostly neutral |
| `core/state_persistence.py` | Last-used config path | **Neutral** |
| `scenarios/scenario_manager.py` | Time-based action injection | Mostly neutral |
| `telemetry/signal_value.py` | Frozen data carrier | **Neutral** |
| `telemetry/telemetry_frame.py` | Frame builder from config+state | **Neutral** |
| `telemetry/ring_buffer.py` | Deque-based store | **Neutral** |
| `telemetry/export.py` | CSV/JSONL export | **Neutral** |
| `telemetry/output_policy.py` | Publish/block gatekeeper | **Neutral** |
| `protocols/mqtt_gateway.py` | MQTT publisher | **Neutral** |
| `protocols/opcua_gateway.py` | OPC UA server | **Neutral** |
| `equipment/base_equipment.py` | Abstract equipment lifecycle | **Neutral** |
| `ui/api.py` | FastAPI server | Mixed (PID endpoint) |
| `main.py` | CLI entry | Mixed (hard-coded engine) |

---

## 5. Continuous-Domain Coupling Map

| Coupling Point | File:Line | Type | Action |
|---------------|-----------|------|--------|
| `update_continuous_process()` import | `simulation_engine.py:12` | Must stay continuous | **Create discrete counterpart** |
| `MassBalance` + `EnergyBalance` | `simulation_engine.py:25-26,129-141` | Must stay continuous | **Extract to continuous-specific method** |
| `_append_equipment_truth()` TRUTH_PARAMS | `simulation_engine.py:190-240` | Must stay continuous | **Move to continuous engine** |
| `MediumConfig` (density, viscosity) | `schema.py:35-41` | Can become shared | **Make optional** |
| `ConnectionConfig.type=physical` | `schema.py:57` | Needs adapter | **Allow "logical"/"routing"** |
| `RuntimeState.streams` + Stream import | `runtime_state.py:20` | Must stay continuous | **Keep as-is; discrete ignores** |
| `valve_stuck` scenario action | `scenario_manager.py:74-79` | Must stay continuous | **No change needed** |
| PID controller endpoint | `api.py` | Can become shared | **Conditional on engine type** |
| SimulationEngine hard-code in main.py | `main.py` | Needs adapter | **Add engine factory** |
| SimulationEngine hard-code in api.py | `api.py:RuntimeService` | Needs adapter | **Add engine factory** |
| Default config path | `main.py`, `state_persistence.py` | Cosmetic | **Derive from config type** |

**Summary:** 2 strong couplings (process dynamics, mass/energy balance), 7 moderate couplings (config, time, engine selection), 0 couplings in the telemetry pipeline.

---

## 6. Reusable Shared-Platform Assessment

| Capability | Current Responsibility | Current Coupling | Reuse | Required Change | BC Risk |
|-----------|----------------------|-----------------|-------|-----------------|---------|
| Config loading | `load_plant_config()` YAML→Pydantic | Schema-specific | ✅ Share | Add discrete schema, dispatch | Low |
| Model registry | String→class via YAML | None | ✅ Share as-is | Add discrete model-type YAMLs | None |
| Plant graph | Node+edge builder | Config section names | ⚠️ Adapt | Dispatch by config type | Low |
| Runtime state | Truth+signals+streams | Stream class import | ✅ Share | Discrete ignores streams | None |
| Time manager | Fixed-step advance | None | ⚠️ Extend | Add `advance_to(t)` / event queue | Low |
| Scenario manager | Timed action injection | valve_stuck action | ✅ Share | Add discrete action types | Low |
| State persistence | Last-used config path | Default path | ✅ Share as-is | None | None |
| Alarm/event mgr | Threshold-based alarms | Signal-based | ✅ Share | Add discrete event types | Low |
| Telemetry store | Ring buffer of frames | SignalValue only | ✅ Share as-is | None | None |
| API | FastAPI endpoints | Engine hard-code | ⚠️ Adapt | Engine factory, remove PID conditional | Medium |
| WebSocket | Telemetry streaming | SignalValue only | ✅ Share as-is | None | None |
| MQTT gateway | SignalValue→MQTT | None | ✅ Share as-is | Topic prefix configurable | None |
| OPC UA gateway | SignalValue→OPC UA | None | ✅ Share as-is | None | None |
| File export | CSV/JSONL | SignalValue fields | ✅ Share as-is | None | None |
| UI shell | Static HTML/JS | API endpoint names | ⚠️ Adapt | Add discrete workspace | Low |
| CLI | argparse subcommands | Engine hard-code | ⚠️ Adapt | Engine factory + --engine flag | Low |
| Docker | Dockerfile + compose | None | ✅ Share | Add discrete service or shared | None |
| Analytics | `analytics/` directory | Continuous metrics | ⚠️ New | Add discrete KPIs | None |

---

## 7. Schema Assessment

### Option A — Generalize PlantConfig

**Pro:** Single schema, less duplication. **Con:** Risk of breaking continuous validation, complex conditional logic.

### Option B — Shared envelope + domain schemas ✅ RECOMMENDED

```python
class SimulationModelConfig(BaseModel):
    model_type: Literal["continuous_process", "discrete_manufacturing"]
    model_version: str
    plant: PlantMetadata  # shared identity
    # domain-specific fields via discriminated union or optional fields

class ContinuousPlantConfig(SimulationModelConfig):
    model_type: Literal["continuous_process"]
    medium: MediumConfig
    equipment: list[EquipmentConfig]
    connections: list[ConnectionConfig]
    sensors: list[SensorConfig]
    # ...

class DiscreteManufacturingConfig(SimulationModelConfig):
    model_type: Literal["discrete_manufacturing"]
    entity_types: list[EntityTypeConfig]
    stations: list[StationConfig]
    routes: list[RouteConfig]
    sources: list[SourceConfig]
    # ...
```

**Rationale:** Clean separation, no risk to continuous config, explicit type field enables engine selection.

### Option C — Keep continuous intact, separate discrete

**Pro:** Zero risk to existing code. **Con:** Duplication of shared fields (plant identity, versioning).

**Decision:** **Option B** — shared envelope with discriminated model_type. Keeps shared identity/versioning, enables engine selection, isolates domain logic.

---

## 8. API/CLI/UI Assessment

**Current assumptions:**
- Only one engine exists (`SimulationEngine`)
- Only process-industry signal categories
- Only PID controllers
- Only continuous-process plant graph

**Proposed backward-compatible concepts:**
- `model_type` in config drives engine selection (no new CLI flag required)
- Telemetry endpoints work unchanged (they only know `SignalValue`)
- Add `/api/workspaces` endpoint returning engine types
- PID endpoint conditional on engine type
- Discrete UI workspace loads from discrete config

---

## 9. Test and Compatibility Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Engine boundary refactor breaks continuous tests | High | Wrap, don't rewrite. Run full suite after each slice. |
| Schema extension breaks existing YAML loading | Medium | Use Pydantic discriminated unions; test all existing configs |
| TimeManager changes affect continuous step | Low | Subclass or add method; don't change existing behavior |
| API endpoint changes break UI | Medium | Keep existing endpoints; add new ones |

**Existing tests likely to break under refactor:**
- None if using wrapper/adapter pattern (Slice 1)
- Tests that import `SimulationEngine` directly may need import path update if moved (Slice 1)

---

## 10. Security/Operational Risks

| Risk | Finding |
|------|---------|
| Unsafe config loading | Pydantic v2 validates all inputs; YAML is safe-loaded |
| Unbounded event generation | Discrete engine must cap event queue size |
| External event injection | `inject()` method must validate event schema |
| Data isolation | `source_kind: "simulation"` already exists; `environment` field should be added |
| File export safety | Paths are validated via `Path`; CSV appends safely |
| API authorization | No auth currently — future scope |
| MQTT namespace separation | Topic prefix is configurable per engine |

---

## 11. Technical Debt Relevant to This Initiative

| Debt | Impact |
|------|--------|
| No engine abstraction | Must be created before discrete engine |
| Hard-coded continuous calls in step() | Must be extracted |
| Monolithic `PlantConfig` | Needs splitting or envelope |
| `RuntimeService` owns one engine | Must become multi-engine or multi-instance |
| No run identity/versioning | Needed for deterministic replay |
| Global random in some places | Must be scoped to run |

---

## 12. Evidence Appendix

```text
Commit: e9aea90
Branch: main (clean)
Python: 3.11.9
Tests: 185 passed, 0 failed, 5.10s
VF-1 tests: 13/13
VF-2 tests: 154/154
Other tests: 18/18
```
