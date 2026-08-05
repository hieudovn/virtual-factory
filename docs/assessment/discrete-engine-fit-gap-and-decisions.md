# Deliverable B — Target Fit-Gap and Decision Requests

> **Date:** 2026-08-05  
> **Author:** PM (AI Coding Agent)

---

## 1. Target Architecture Summary

```
┌──────────────────────────────────────────┐
│         Shared Platform                   │
│  Config loading │ Model registry         │
│  Plant graph    │ Runtime state           │
│  Scenario mgr   │ State persistence       │
│  Telemetry pipeline (SignalValue→Export)  │
│  MQTT/OPC UA gateways                    │
│  API/WebSocket/CLI (with engine dispatch) │
└────────────┬──────────────────────────────┘
             │
    ┌────────┴────────┐
    │                  │
┌───▼──────────┐  ┌───▼──────────────────┐
│ Continuous   │  │ Discrete              │
│ Engine       │  │ Engine               │
│              │  │                      │
│ Fixed-step   │  │ Event-driven         │
│ Physics      │  │ Entity/queue/resource│
│ Balance      │  │ Routing/quality      │
│ Sensors/Ctrl │  │ Calendar/failure     │
└──────────────┘  └──────────────────────┘
```

---

## 2. Current-to-Target Gap Matrix

| Gap | Current State | Target State | Effort |
|-----|--------------|-------------|--------|
| Engine abstraction | No base class or interface | `BaseSimulationEngine` with `step()` contract | S |
| Engine selection | Hard-coded `SimulationEngine` | Engine factory via `model_type` | S |
| Process dynamics | Hard-coded in `step()` | Extracted to `ContinuousEngine._process_step()` | S |
| Discrete scheduler | None | Internal future-event calendar | M |
| Schema | Single `PlantConfig` | `SimulationModelConfig` envelope + 2 domain schemas | M |
| Time manager | Fixed-step only | Extended with `advance_to()` + event queue | S |
| Runtime state | `streams` field continuous | Discrete ignores streams; add `parts` dict | XS |
| Scenario actions | `valve_stuck` continuous | Add `entity_inject`, `source_stop`, `station_fail` | S |
| API engine dispatch | Hard-coded `SimulationEngine` | Factory via `model_type` | S |
| CLI engine dispatch | Hard-coded `SimulationEngine` | `--model-type` or auto-detect | S |
| Run identity | None | `RunContext` with id, seed, version | S |
| Deterministic seed | `random.Random()` in some places | Run-scoped seed propagation | S |
| Event trace | Telemetry frames only | Separate event stream + telemetry | M |
| UI discrete workspace | None | Discrete views (line overview, WIP, trace) | L (future) |

---

## 3. Refactor Seams

### Seam 1: `SimulationEngine.step()` method (lines 91-147)

**Current:** Monolithic method with hard-coded continuous calls.  
**Action:** Extract `_process_physics()` method; make it overridable.  
**Risk:** Low — internal refactor, no API change.

### Seam 2: Engine instantiation in `main.py` and `api.py`

**Current:** `SimulationEngine(config, dt_s, scenario)` hard-coded.  
**Action:** Create `engine_factory(config) → BaseEngine` that reads `config.model_type`.  
**Risk:** Low — only changes creation, not behavior.

### Seam 3: `PlantConfig` schema

**Current:** Monolithic Pydantic model with all continuous fields.  
**Action:** Add `model_type` discriminator; create `DiscreteManufacturingConfig`.  
**Risk:** Medium — must not break existing YAML loading. Test all configs in `configs/plants/`.

### Seam 4: `TimeManager` fixed-step

**Current:** Only `advance()` by fixed increment.  
**Action:** Add `advance_to(target_s)`; add optional event queue.  
**Risk:** Low — additive change.

---

## 4. Scheduler Option Comparison

| Criteria | Option 1: Internal FES | Option 2: SimPy + Adapter |
|----------|----------------------|--------------------------|
| **Implementation complexity** | S-M: build event queue, sort by time, process loop | M: learn SimPy API, build adapter layer |
| **Correctness risk** | Low: simple data structure (heapq) | Medium: SimPy's process-based model may leak into domain |
| **Queue/resource capability** | Must build from scratch | Built-in `Resource`, `Store`, `Container` |
| **Determinism** | Full control over seed + ordering | SimPy uses `random` module; needs wrapping |
| **Testability** | High: pure Python, no hidden state | Medium: SimPy environment is stateful |
| **Dependency cost** | Zero | Adds `simpy` to requirements |
| **Long-term maintainability** | Own the code, fix bugs directly | Dependent on SimPy releases |
| **Performance (TIPA scale)** | Fine: 6 streams × 100 entities = trivial | Fine |
| **Hybrid/co-simulation** | Build explicit sync contract | SimPy has no built-in co-simulation |
| **Domain independence** | Full control | Risk of SimPy concepts leaking into domain model |

**PM Recommendation:** **Option 1 — Internal future-event scheduler.**

Rationale:
- TIPA scale (6 parallel streams, ~100 entities) is trivial for a heapq-based scheduler
- Zero dependency cost
- Full determinism control
- No risk of external library concepts leaking into the domain model
- SimPy's `Resource`/`Store` are useful but can be built later if needed; start simple
- The architecture foundation explicitly says SA has not approved SimPy (ADR-CAND-001)

**Decision request for SA:** Approve internal heapq-based scheduler for MVP. SimPy evaluation deferred to post-M2 if resource complexity demands it.

---

## 5. Schema Option Comparison

| Criteria | Option A: Generalize PlantConfig | Option B: Envelope + Domain Schemas | Option C: Separate Discrete Schema |
|----------|-------------------------------|-------------------------------------|-----------------------------------|
| **BC risk** | High: conditional logic may break validation | Low: existing continuous schema unchanged | Zero: no changes to existing |
| **Code clarity** | Low: mixed concerns in one model | High: clear separation | High: isolation |
| **Shared fields** | Built-in | Via envelope base class | Duplicated |
| **Engine selection** | Need extra field anyway | `model_type` drives it | Separate config type implies engine |
| **Duplication** | None | Minimal (identity/version fields) | Moderate |

**PM Recommendation:** **Option B — Shared envelope with discriminated model_type.**

```python
class SimulationModelConfig(BaseModel):
    model_type: Literal["continuous_process", "discrete_manufacturing"]
    model_version: str
    plant: PlantMetadata

class ContinuousPlantConfig(SimulationModelConfig):
    model_type: Literal["continuous_process"] = "continuous_process"
    medium: MediumConfig  # unchanged from current
    equipment: list[EquipmentConfig]
    # ... all existing fields

class DiscreteManufacturingConfig(SimulationModelConfig):
    model_type: Literal["discrete_manufacturing"] = "discrete_manufacturing"
    entity_types: list[EntityTypeConfig] = []
    stations: list[StationConfig] = []
    routes: list[RouteConfig] = []
    sources: list[SourceConfig] = []
    # ... discrete-specific fields
```

**Rationale:** Clean separation, zero risk to continuous config, explicit type for engine selection. Existing `PlantConfig` becomes `ContinuousPlantConfig` with all current fields preserved.

---

## 6. State/Event-Store Recommendation

| Concern | Recommendation |
|---------|---------------|
| Entity lifecycle | New `RuntimeState.parts: dict[str, PartState]` field |
| Queue state | New `queue_states: dict[str, QueueSnapshot]` field |
| Resource state | New `resource_states: dict[str, ResourceSnapshot]` field |
| Pending event calendar | New `pending_events: list[ScheduledEvent]` field (heapq in engine, exposed via snapshot) |
| Event trace | Separate `EventTrace` store (list of `SimulationEvent`), distinct from telemetry frames |
| WIP | Derived from `parts` dict |
| Hold/rework | `PartState.hold_reason`, `PartState.rework_count` |
| Deterministic replay | `RunContext.seed` + `EventTrace` enables replay |

**Shared:** `RuntimeState.truth`, `RuntimeState.signals`, `RuntimeState.diagnostics` + `RingBufferTelemetryStore`.  
**Discrete-only:** `RuntimeState.parts`, `RuntimeState.queue_states`, `RuntimeState.resource_states`, `EventTrace`.  
**Continuous-only:** `RuntimeState.streams` (unchanged).

---

## 7. Decisions PM Recommends

| ID | Decision | Rationale |
|----|----------|-----------|
| PM-REC-001 | Internal heapq scheduler | Zero dependency, full determinism, sufficient for TIPA scale |
| PM-REC-002 | Schema Option B (envelope + domain schemas) | Clean separation, zero BC risk |
| PM-REC-003 | Wrap `SimulationEngine` as `ContinuousSimulationEngine(BaseEngine)` | Preserves behavior, enables factory |
| PM-REC-004 | Shared `RuntimeState` with discrete-specific fields added | Reuses truth/signals/diagnostics; streams untouched |
| PM-REC-005 | `RunContext` with id, seed, model_type, version | Foundation for determinism and multi-run |
| PM-REC-006 | `EventTrace` separate from telemetry frames | Events describe what happened; telemetry is current state |
| PM-REC-007 | Add `model_type` discriminator to config top-level | Enables engine selection without new CLI flag |

---

## 8. Decisions Requiring SA Approval

| ID | Question | PM Position |
|----|----------|------------|
| ADR-CAND-001 | Internal heapq scheduler or SimPy? | Recommend internal heapq |
| ADR-CAND-002 | `core/` package migration strategy? | Wrap existing; no package moves in Slice 0-1 |
| ADR-CAND-003 | Schema strategy? | Option B — envelope + domain schemas |
| ADR-CAND-004 | Reuse or replace TimeManager? | Extend with `advance_to()` |
| ADR-CAND-005 | Event store: in-memory or separate? | In-memory `EventTrace` first |
| ADR-CAND-006 | --engine CLI flag or auto-detect? | Auto-detect from config `model_type` |
| ADR-CAND-009 | Model inheritance for templates? | Defer to M3+ |
| ADR-CAND-010 | Asset identity vs manufacturing resources? | Defer to M3+ |

---

## 9. Assumptions and Confidence

| Assumption | Confidence |
|-----------|-----------|
| Current tests pass and will be protected | High (verified) |
| Telemetry pipeline is fully reusable | High (verified — zero continuous coupling) |
| Schema extension via extra="allow" is safe | High (verified — Pydantic v2 behavior) |
| Internal heapq scheduler is sufficient for TIPA scale | High (6 streams × O(100) entities) |
| Engine boundary can be introduced without breaking changes | Medium-High (wrapping is safe; API changes need care) |
| Discrete config can coexist with continuous in same PlantGraph | Medium (graph builder needs dispatch) |
| PlantOS/MES integration is deferred | High (per SA architecture doc §13) |

---

## 10. Items Explicitly Deferred

- PlantOS/MES adapter
- OPC UA/MQTT for discrete
- UI discrete workspace
- Hybrid continuous/discrete co-simulation
- External scheduler (SimPy)
- Package extraction into separate service/repository
- TIPA detailed workflow (placeholder only)
- Production deployment
- AI-generated plant configuration
