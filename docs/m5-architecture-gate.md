# M5 — Reality Observation & Integration Foundation
## Architecture Gate — Design & Audit

**Status**: DESIGN/AUDIT ONLY. No M5 production implementation.
**Date**: 2026-08-08
**Prerequisite**: M4 CLOSED at `ec307b9`, 823 tests green.

---

## 1. Current-State Audit

### 1.1 Existing Architecture Layers

```
┌─────────────────────────────────────────────┐
│  External Consumers (IIoT, MES, Analytics)   │
├─────────────────────────────────────────────┤
│  Protocol Gateways (MQTT, Sparkplug, OPC UA) │  ← protocols/
│  WebSocket / REST API                        │  ← ui/ (FastAPI)
├─────────────────────────────────────────────┤
│  Output Policy (industrial vs debug/bench)   │  ← telemetry/output_policy.py
│  Telemetry Frames (SignalValue list)         │  ← telemetry/telemetry_frame.py
├─────────────────────────────────────────────┤
│  Sensors (truth → measured signal)           │  ← instrumentation/
│  Controllers, Actuators                      │  ← control/, actuation/
├─────────────────────────────────────────────┤
│  Continuous Process Runtime                  │  ← core/
│  Discrete Assembly Runtime (M2–M4)           │  ← discrete/, assembly/
├─────────────────────────────────────────────┤
│  Plant Configuration (YAML/JSON)             │  ← configs/
│  Equipment Models                            │  ← equipment/
│  Fault Engine, Maintenance, Analytics        │  ← faults/, maintenance/, analytics/
└─────────────────────────────────────────────┘
```

### 1.2 Stable Invariants (Verified)

| Invariant | Status | Evidence |
|-----------|--------|----------|
| Kernel → Engine → Dispatcher Protocol → HandlerRegistry → domain state | ✅ | `discrete/engine.py`, `discrete/dispatcher.py`, `discrete/handler_registry.py` |
| Controller → Engine | ✅ | `discrete/controller.py` |
| Service → Controller | ✅ | `discrete/run_service.py` |
| Configuration-driven topology/workflow | ✅ | `assembly/definition.py`, `configs/` |
| M4 projection/scene boundaries | ✅ | `assembly/projection.py`, `assembly/scene.py` |
| MES adapter boundary (no runtime exposure) | ✅ | `assembly/mes_adapter.py`, test enforcement |
| Output policy guards internal truth | ✅ | `telemetry/output_policy.py`, `telemetry/telemetry_frame.py` |
| Sensors create industrial reality | ✅ | `instrumentation/`, design-principles.md |
| Gateways publish only policy-allowed signals | ✅ | `protocols/mqtt_gateway.py:72` — rejects `internal_truth` |

### 1.3 Current Observation/Integration Points

| Boundary | What Flows | Direction | Format |
|----------|-----------|-----------|--------|
| `MqttGateway.publish_frame()` | `SignalValue[]` | Out | MQTT JSON per signal |
| `SparkplugBGateway.publish_frame()` | `SignalValue[]` | Out | Sparkplug B NDATA |
| `OpcUaGateway` | `SignalValue[]` | Out | OPC UA nodes |
| FastAPI `/telemetry/latest` | `SignalValue[]` via `build_publishable_frame()` | Out | JSON |
| FastAPI WebSocket `/ws/telemetry` | `SignalValue[]` streaming | Out | JSON frames |
| `telemetry_export` (CSV/JSONL) | `SignalValue[]` | Out | File |
| `MESAdapter.simulation_to_mes()` | `MESEvent[]` | Out | `MESOutput` dataclass |
| `MESAdapter.mes_to_simulation()` | `MESInput` → dict | In | Configuration dict |
| `build_publishable_frame()` | `RuntimeState` → `SignalValue[]` | Internal | `OutputPolicy` filter |

### 1.4 Current Signal Abstraction

```python
@dataclass(frozen=True, slots=True)
class SignalValue:
    name: str
    value: float | int | str | bool | None
    unit: str | None
    category: str          # industrial_signal, controller_signal, actuator_feedback, industrial_event, internal_truth
    timestamp_s: float
    quality: str           # GOOD, BAD, UNCERTAIN
    source: str | None
```

Categories: `industrial_signal`, `controller_signal`, `actuator_feedback`, `industrial_event`, `internal_truth`.

`OutputPolicy` enforces that `internal_truth` is never published in `industrial` mode.

### 1.5 Current Discrete/Assembly Event Model

```
ScheduledEvent
  → HandlerOutcome (success/fail, state_changes, follow_up_events)
  → EventTraceEntry (trace_sequence, event_id, correlation_id, causation_id, ...)
  → AssemblyProjection → EventView (detached, serializable)
  → MESAdapter.simulation_to_mes() → MESEvent
```

Key properties:
- `correlation_id` carries WIP identity across events
- `causation_id` carries event lineage
- `event_id` carries naming convention: `{wip_id}-{flow}-{suffix}`
- `state_changes` tuple carries domain state transitions
- `EventTraceBuffer` (capacity 128) bounds trace memory

### 1.6 Current Identity Model

| Identity Type | Current State |
|--------------|---------------|
| Simulation entity ID | `primitive_id` on `AssemblyPrimitive` |
| WIP identity | `WipId` (e.g., `wip-0001`), carried via `correlation_id` |
| Business serial/lot | **Not yet modeled** |
| External system references | **Not yet modeled** |
| Station/resource ID | `primitive_id` on topology nodes |
| Carrier/pallet ID | **Not yet modeled** |

### 1.7 Current Time Model

| Time Dimension | Current State |
|---------------|---------------|
| Simulation time (`simulation_time_s`) | ✅ Present on `ScheduledEvent`, `EventTraceEntry`, `SignalValue` |
| Wall-clock / emission time | ❌ Not tracked |
| Occurrence time vs emission time | ❌ Not distinguished |

---

## 2. Gap Analysis

### 2.1 Structural Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| No explicit ObservationPoint abstraction | High | Observation logic is embedded in `build_publishable_frame()` and gateways |
| No ObservationEnvelope abstraction | High | Gateways build ad-hoc payloads; no consumer-neutral intermediate |
| No consumer-specific projection framework | High | All consumers (MQTT, API, file) see the same `SignalValue[]` |
| Continuous and discrete observation are separate code paths | Medium | `SignalValue` for continuous; `MESEvent` for discrete; no unified path |
| No trigger/sampling policy beyond "every step" | Medium | Periodic polling is implicit; no event-triggered or on-change sampling |
| No reverse control/context boundary | Medium | `MESAdapter.mes_to_simulation()` is a stub returning a dict |
| Identity decoupling incomplete | Medium | Business serial/lot, external refs, carrier/pallet not modeled |
| No observation identity or idempotency | High | Consumers cannot deduplicate or correlate observations |
| Gateway failure semantics undocumented | Low | Gateways raise exceptions; no explicit isolation contract |

### 2.2 What Works Well (Reuse Candidates)

| Component | Reuse Strategy |
|-----------|---------------|
| `OutputPolicy` | Generalize to cover observation policy, not just signal publish/don't-publish |
| `SignalValue` | Keep as the continuous-domain measurement primitive |
| `EventTraceEntry` | Already has `correlation_id`, `causation_id`, time — near-ready for observation |
| `MESAdapter` | Keep as a compatibility façade; its `simulation_to_mes()` is a concrete projection |
| `MqttGateway` / `SparkplugBGateway` | Reuse as gateway implementations behind a generic `ObservationGateway` protocol |
| `AssemblyProjection` | Keep; consumer projections are separate from this internal projection |
| `build_publishable_frame()` | Generalize to `collect_observations()` |
| `HandlerRegistry` | Already domain-neutral; no changes needed |

---

## 3. Target Architecture

### 3.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    SIMULATION DOMAIN                         │
│                                                              │
│  Continuous Process        Discrete Assembly                 │
│  (core/, equipment/)       (discrete/, assembly/)            │
│         │                        │                           │
│         ▼                        ▼                           │
│  ┌──────────────────────────────────────┐                    │
│  │       OBSERVATION SERVICE            │                    │
│  │  collect_observations(policy)        │                    │
│  │  one reality event → 0..N obs        │                    │
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                    │
│  │       ObservationPoint[]             │                    │
│  │  (what, when, trigger, policy)       │                    │
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                    │
│  │       ObservationEnvelope[]          │                    │
│  │  (identity, time, source, payload)   │  ← consumer-neutral│
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                    │
│  │       ROUTING / SUBSCRIPTION         │  ← NEW             │
│  │  route(envelope) → projection[]      │                    │
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
│        ┌────────┼────────┐                                   │
│        ▼        ▼        ▼                                   │
│  ┌──────────────────────────────────────┐                    │
│  │       PROJECTIONS (per consumer)     │                    │
│  │  MESProjection, IIoTProjection, ...  │                    │
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
├─────────────────┼────────────────────────────────────────────┤
│  GATEWAY LAYER  │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                    │
│  │  ObservationGateway (protocol)       │                    │
│  │  MqttObsGateway, RestObsGateway,     │                    │
│  │  FileObsGateway, InMemoryObsGateway  │                    │
│  └──────────────────────────────────────┘                    │
│                 │                                            │
└─────────────────┼────────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────────────┐
│              EXTERNAL CONSUMERS                              │
│  MES/CDM  │  IIoT Platform  │  Analytics  │  Dashboard       │
└──────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│              REVERSE CONTROL/CONTEXT                         │
│                                                              │
│  External Production Context / Command                       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────┐                    │
│  │  Control Boundary                    │                    │
│  │  validate_context(mes_input)         │                    │
│  │  map_to_simulation_parameters()      │                    │
│  └──────────────┬───────────────────────┘                    │
│                 │                                            │
│                 ▼                                            │
│  SimulationDefinition / RunContext / ScheduledEvent          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Architectural Principles (from SA constitution)

1. VF internal data models **MUST NOT** mirror MES/Odoo data models.
2. Simulation internal state **MUST** remain consumer-neutral.
3. Semantic alignment is required **only** at explicit observation/control boundaries.
4. A reality event may create **zero, one, or multiple** observations.
5. Different consumers may receive **different projections** of the same reality.
6. MQTT/REST/OPC UA/WebSocket/file concerns stay **outside** simulation runtime/domain.
7. Internal truth, solver state, hidden fault state **MUST NOT** leak into industrial/MES outputs.
8. Existing M2–M4 architecture is **stable** and must not be redesigned without proven necessity.
9. Existing gateway/telemetry/output-policy infrastructure **must be reused** or generalized.
10. M5 is **foundation work**, not full TIPA workflow and not production MES integration.

---

## 4. Component Responsibility Table

| Component | Package | Responsibilities | Non-Responsibilities |
|-----------|---------|-----------------|---------------------|
| **ObservationPoint** | `observation/` | Declare **what** reality source to observe, **when** (trigger), **how** (field extractor). Does NOT declare who consumes. | Perform I/O, know about consumers, hold runtime state, declare target projection |
| **ObservationEnvelope** | `observation/` | Carry observation identity (including `idempotency_key`), type, time, source, subject, payload in consumer-neutral form | Know about MQTT/HTTP, serialize to wire format, hold consumer semantics |
| **ObservationService** | `observation/` | Collect envelopes from configured points; apply trigger policy | Dispatch to networks, manage connections, store history, know about consumers |
| **ObservationRouter** | `observation/` | **NEW** — Route envelopes to projection(s) via subscription rules. One envelope → zero/one/multiple projections. | Transform payloads, perform I/O |
| **ObservationPolicy** | `observation/` | Generalize `OutputPolicy`: control what is observable, under what mode. Does NOT decide who consumes — that is the Router's job. | Encode business rules, know about MES |
| **TriggerPolicy** | `observation/` | Define when an observation point fires: event-triggered, periodic, on-change, manual | Schedule wall-clock timers, manage external triggers |
| **MESProjection** | `observation/projections/` | Transform `ObservationEnvelope[]` → `MESOutput` (typed, business-semantic) | Perform I/O, talk to Odoo |
| **IIoTProjection** | `observation/projections/` | Transform `ObservationEnvelope[]` → generic industrial payload (SignalValue-like) | Perform I/O, enforce Sparkplug |
| **ObservationGateway** | `protocols/` | Abstract protocol for delivering projected payloads to external systems | Know about observation semantics, transform payloads |
| **ControlBoundary** | `observation/` | Validate external context, map MESInput → simulation parameters | Execute simulation, know about MES internals |
| **MESAdapter** (existing) | `assembly/` | Compatibility façade; delegate to MESProjection internally | Change its public API without deprecation notice |

---

## 5. Observation Flow

```
REALITY EVENT occurs (e.g., PROCESS_COMPLETE at AP04)
        │
        ▼
ObservationService.check_points(event, runtime_state)
        │
        ├─→ ObservationPoint "ap04-completion" matches? (trigger=event, event_type=PROCESS_COMPLETE)
        │       │
        │       ▼
        │   ObservationEnvelope(
        │       observation_id="obs-00042",
        │       observation_type=EVENT,
        │       run_id="run-1",
        │       simulation_time_s=12.5,
        │       occurrence_time_s=12.5,
        │       emission_time_s=12.5,
        │       source="assembly.processor.AP04",
        │       subject="wip-0001",
        │       context={"station": "AP04", "flow": "base"},
        │       payload={"event_type": "PROCESS_COMPLETE", "result": "committed"},
        │       quality="GOOD",
        │       correlation_id="wip-0001",
        │       causation_id="evt-0041",
        │       schema_version="1.0"
        │   )
        │       │
        │       ▼
        │   MESProjection.project([envelope])
        │       │
        │       ▼
        │   MESOutput → MqttGateway → MES/CDM
        │
        └─→ ObservationPoint "ap04-iiot" matches? (different projection)
                │
                ▼
            IIoTProjection.project([envelope])
                │
                ▼
            SparkplugBGateway → IIoT Platform
```

**Key**: One PROCESS_COMPLETE reality event → two different observations → two different projections → two different consumers.

---

## 6. Reverse Control / Context Flow

```
MESInput arrives (ProductionOrder, MaterialRelease)
        │
        ▼
ControlBoundary.validate(mes_input, simulation_definition)
        │
        ├─ Validate: order exists, source matches, routing compatible
        ├─ Map: order_id → internal model_id
        ├─ Map: source_id → topology source primitive
        ├─ Map: quantity → WIP creation parameters
        │
        ▼
SimulationRunRequest(
    run_id="mes-run-001",
    model_id="generic-demo",
    initial_wips=[{"wip_id": None, "source": "source-1", "flow_id": "base"}],
    quality_plan={},
    scenario_params={}
)
        │
        ▼
DiscreteRunService.create_run(...)
```

**Key**: The ControlBoundary is the **only** place where MES semantics enter the simulation. No MES concepts leak past this boundary.

---

## 7. Proposed Package/Module Structure

```
src/virtual_factory/
├── observation/                    # NEW — M5 foundation
│   ├── __init__.py
│   ├── envelope.py                 # ObservationEnvelope dataclass
│   ├── point.py                    # ObservationPoint, ObservationType, TriggerPolicy
│   ├── policy.py                   # ObservationPolicy (generalizes OutputPolicy)
│   ├── service.py                  # ObservationService (collect, evaluate triggers)
│   ├── router.py                   # ObservationRouter (route envelopes → projections)
│   ├── identity.py                 # Identity strategy, idempotency_key derivation
│   ├── projections/
│   │   ├── __init__.py
│   │   ├── mes_projection.py       # MESProjection (envelope → MESOutput)
│   │   ├── iiot_projection.py      # IIoTProjection (envelope → generic payload)
│   │   └── base.py                 # ProjectionProtocol
│   └── control_boundary.py         # ControlBoundary (MESInput → SimulationRunRequest)
│
├── telemetry/                      # EXISTING — keep, adapt
│   ├── signal_value.py             # Keep SignalValue
│   ├── output_policy.py            # Keep, mark as specialization of ObservationPolicy
│   ├── telemetry_frame.py          # Keep build_publishable_frame(), adapt to use ObservationService
│   └── signal_registry.py          # Keep
│
├── protocols/                      # EXISTING — add ObservationGateway protocol
│   ├── mqtt_gateway.py             # Keep, add ObservationGateway implementation
│   ├── sparkplug_gateway.py        # Keep
│   ├── opcua_gateway.py            # Keep
│   ├── observation_gateway.py      # NEW — ObservationGateway protocol
│   └── file_gateway.py             # NEW — FileObsGateway (JSONL/CSV)
│
├── assembly/                       # EXISTING — no changes
│   ├── projection.py               # Keep (internal projection, not consumer projection)
│   ├── scene.py                    # Keep
│   ├── mes_adapter.py              # Keep as compatibility façade
│   └── ...
│
└── discrete/                       # EXISTING — no changes
    ├── trace.py                    # Keep EventTraceEntry
    ├── events.py                   # Keep ScheduledEvent
    └── ...
```

---

## 8. ObservationPoint Schema Proposal

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

class ObservationType(str, Enum):
    EVENT = "event"            # Discrete domain event (PROCESS_START, QUALITY_CHECK, ...)
    MEASUREMENT = "measurement" # Continuous signal sample (LT102_LEVEL, FT101_FLOW)
    STATE = "state"            # Snapshot of entity state (WIP status, buffer occupancy)
    HUMAN_ENTRY = "human_entry" # Operator input, checklist, manual data

class TriggerKind(str, Enum):
    ON_EVENT = "on_event"           # Fire when matching reality event occurs
    PERIODIC = "periodic"           # Fire every N simulation seconds
    ON_CHANGE = "on_change"         # Fire when observed value changes beyond threshold
    MANUAL = "manual"               # Fire only on external request

@dataclass
class TriggerPolicy:
    kind: TriggerKind
    # ON_EVENT
    event_types: tuple[str, ...] = ()        # e.g., ("PROCESS_COMPLETE",)
    target_ids: tuple[str, ...] = ()         # e.g., ("AP04",)
    # PERIODIC
    interval_s: float = 1.0
    # ON_CHANGE
    change_threshold: float | None = None
    change_field: str | None = None

@dataclass
class FieldPolicy:
    """Controls what fields enter the observation envelope.

    PRIMARY DEFENSE: default-deny with explicit allow-list.
    Only fields named in `extract` are observable.
    `deny` is defense-in-depth — it provides an additional safety
    net for fields that must never appear even if `extract` is misconfigured.
    """
    extract: tuple[str, ...] = ()      # Explicit allow-list — ONLY these fields are extracted
    deny: tuple[str, ...] = ()         # Defense-in-depth deny-list (internal_truth, solver_state, ...)

@dataclass
class ObservationPoint:
    point_id: str
    observation_type: ObservationType
    label: str
    # What reality source
    source_type: str                  # "assembly.event", "continuous.signal", "assembly.wip"
    source_filter: dict[str, Any]     # e.g., {"event_type": "PROCESS_COMPLETE", "target_id": "AP04"}
    # Trigger
    trigger: TriggerPolicy
    # Exposure control — default deny, explicit allow
    fields: FieldPolicy
    # Optional business context mapping
    context_map: dict[str, str] = field(default_factory=dict)
    # Disabled
    enabled: bool = True

    # NOTE: ObservationPoint does NOT declare projections or consumers.
    # Routing to projections is handled by ObservationRouter via subscription rules.
```

**Example — AP04 completion observation point:**

```python
ObservationPoint(
    point_id="ap04-completion",
    observation_type=ObservationType.EVENT,
    label="AP04 Process Complete",
    source_type="assembly.event",
    source_filter={"event_type": "PROCESS_COMPLETE", "target_id": "AP04"},
    trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT, event_types=("PROCESS_COMPLETE",), target_ids=("AP04",)),
    fields=FieldPolicy(
        extract=("event_type", "result", "state_changes", "target_id"),
        deny=("internal_truth", "solver_state", "degradation_truth"),
    ),
)
# NOTE: This point does NOT declare where the envelope goes.
# ObservationRouter decides: MESProjection, IIoTProjection, or both.
```

---

## 9. ObservationEnvelope Schema Proposal

```python
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass
class ObservationEnvelope:
    """Consumer-neutral observation carrier.

    Fields are ordered by importance. Optional context must remain optional.
    """

    # ── Identity ──
    observation_id: str                              # UUID, unique per envelope instance
    idempotency_key: str                             # Deterministic logical identity
                                                     # Derived from: run_id + source_event_id/causation_id
                                                     #              + point_id + schema_version
                                                     # Enables reliable dedup/replay for consumers.
    observation_type: str                            # "event", "measurement", "state", "human_entry"

    # ── Run context ──
    run_id: str                                      # which simulation run
    model_id: str                                    # which plant/model

    # ── Time ──
    simulation_time_s: float                         # Simulation-clock coordinate (float seconds)
    occurred_at: str | None = None                   # Simulated calendar timestamp (ISO 8601)
                                                     # Populated when run has an epoch/reference datetime.
                                                     # Example: "2026-08-08T00:05:30.0Z"
    emitted_at: str                                  # UTC wall-clock timestamp (ISO 8601)
                                                     # When this envelope was actually created.
                                                     # Example: "2026-08-08T14:30:01.234Z"

    # ── Source ──
    source_domain: str                               # "continuous", "assembly"
    source_path: str                                 # e.g., "processor.AP04", "transmitter.LT102"

    # ── Subject ──
    subject_type: str | None = None                  # "wip", "equipment", "signal", "buffer"
    subject_id: str | None = None                    # e.g., "wip-0001", "T102"

    # ── Optional business/production context ──
    context: dict[str, Any] = field(default_factory=dict)
    # Examples: {"station_id": "AP04", "flow_id": "base", "order_id": "MO-001"}

    # ── Payload ──
    payload: dict[str, Any] = field(default_factory=dict)
    # Shape depends on observation_type:
    #   EVENT: {"event_type": "PROCESS_COMPLETE", "result": "committed", "state_changes": [...]}
    #   MEASUREMENT: {"name": "LT102_LEVEL", "value": 1.23, "unit": "m"}
    #   STATE: {"entity_type": "wip", "status": "processing", "location": "AP04"}

    # ── Quality / validity ──
    quality: str = "GOOD"                            # GOOD, UNCERTAIN, BAD
    validity: dict[str, Any] = field(default_factory=dict)

    # ── Correlation / causation ──
    correlation_id: str | None = None                # groups related observations (e.g., same WIP)
    causation_id: str | None = None                  # links to parent reality event

    # ── Schema ──
    schema_version: str = "1.0"

    # ── Factory ──
    @classmethod
    def create(cls, **overrides) -> "ObservationEnvelope":
        defaults = {"observation_id": str(uuid4())}
        defaults.update(overrides)
        return cls(**defaults)
```

**Key design decisions:**

1. **`observation_id`** is a UUID — unique per envelope instance. Does NOT provide idempotency.
2. **`idempotency_key`** is a deterministic logical identity — derived from `run_id + source_event_id + point_id + schema_version`. Enables reliable consumer-side dedup and replay.
3. **`simulation_time_s`** (float) — simulation-clock coordinate. Always present.
4. **`occurred_at`** (ISO 8601 str, optional) — simulated calendar timestamp when the run has an epoch.
5. **`emitted_at`** (ISO 8601 str) — UTC wall-clock when the envelope was created. Never simulation time.
6. **`context`** is a dict — carries optional business/production context without coupling to MES schemas.
7. **`payload`** is a dict — shape depends on `observation_type`; projections interpret it.
8. **`correlation_id`** maps to `EventTraceEntry.correlation_id` for discrete events.
9. **`causation_id`** maps to `EventTraceEntry.causation_id` for event lineage.
10. **No MES/Odoo fields** — business semantics live in `context`, interpreted by projections only.

---

## 10. Identity / Context Strategy

### 10.1 Identity Separation

| Layer | Identity | Example | Where |
|-------|----------|---------|-------|
| Simulation entity | `primitive_id` | `AP04`, `source-1` | `AssemblyPrimitive`, topology |
| WIP identity | `WipId` | `wip-0001` | `WipState.wip_id`, `EventTraceEntry.correlation_id` |
| Observation instance ID | `observation_id` (UUID) | `obs-a1b2c3d4` | `ObservationEnvelope.observation_id` |
| Observation idempotency key | `idempotency_key` (deterministic) | `run-1\|evt-0041\|ap04-completion\|1.0` | `ObservationEnvelope.idempotency_key` |
| Business serial/lot | `context.serial_id` | (future) | `ObservationEnvelope.context` |
| Order reference | `context.order_id` | `MO-001` | `ObservationEnvelope.context` |
| External system ref | `context.external_ref` | (future, Odoo DB ID) | `ObservationEnvelope.context` |
| Station/resource | `context.station_id` | `AP04` | `ObservationEnvelope.context` |
| Carrier/pallet | `context.carrier_id` | (future) | `ObservationEnvelope.context` |

### 10.2 Idempotency

- **`observation_id`** (UUID): Unique per envelope *instance*. Two retries of the same logical observation will have different `observation_id` values. Useful for tracing and audit, but NOT for dedup.
- **`idempotency_key`** (deterministic string): Same logical observation always produces the same key. Derived from:
  ```
  run_id + "|" + source_event_id + "|" + point_id + "|" + schema_version
  ```
  Example: `"tipa-run-1|evt-ap04-0040|ap04-completion|1.0"`
- Consumers use `idempotency_key` for reliable deduplication.
- Replay of the same simulation run with the same seed produces identical `idempotency_key` values.
- `observation_id` remains useful for tracing a specific delivery attempt through the gateway layer.

### 10.3 Context Mapping

`ObservationPoint.context_map` defines how internal fields map to business context:

```python
ObservationPoint(
    point_id="ap04-completion",
    context_map={
        "station_id": "source_filter.target_id",    # maps to "AP04"
        "order_id": "production_order",              # from external context
    },
)
```

The `ControlBoundary` provides production context (order, lot, etc.) at run start, and `ObservationService` merges it into envelopes.

---

## 11. Time Semantics

| Field | Type | Source | Semantics |
|-------|------|--------|-----------|
| `simulation_time_s` | `float` | `RuntimeSnapshot.simulation_time_s` | Simulation-clock coordinate — the "now" inside the simulated plant. Always present. |
| `occurred_at` | `str \| None` (ISO 8601) | Derived from `simulation_time_s` + run epoch | Simulated calendar timestamp. Populated when the run has a reference epoch (e.g., `"2026-08-08T00:00:00Z"`). Example: `"2026-08-08T00:05:30.0Z"`. `None` if no epoch is configured. |
| `emitted_at` | `str` (ISO 8601) | `datetime.utcnow().isoformat()` | UTC wall-clock timestamp when the envelope was actually created. Never simulation time. Example: `"2026-08-08T14:30:01.234Z"`. |
| Wall-clock (gateway internal) | `float` (Unix) | `time.time()` / `time.monotonic()` | Gateway-layer only — used for connection timeout, retry backoff, logging. Distinct from `emitted_at` (which IS in the envelope but as an audit timestamp, not for protocol logic). |

### Key Principle

**No single field serves dual purpose.** `simulation_time_s` is always a float simulation coordinate. `occurred_at` is always an ISO 8601 calendar string. `emitted_at` is always a UTC wall-clock ISO 8601 string. They never conflate.

### Time Scenarios

**Real-time simulation:**
- `simulation_time_s` ≈ wall-clock elapsed
- `emitted_at` ≈ wall-clock time of emission

**Accelerated simulation (e.g., 1 hour sim = 1 second real):**
- `simulation_time_s` advances rapidly (0, 3600, 7200, ...)
- `occurred_at` shows simulated calendar time (e.g., `"2026-08-08T01:00:00Z"`, `"2026-08-08T02:00:00Z"`)
- `emitted_at` shows actual wall-clock time (all within a few seconds of each other)

**Periodic observation:**
- `simulation_time_s` = last sample time in simulation
- `occurred_at` = corresponding calendar time
- `emitted_at` = when the periodic trigger actually fired (wall clock)

**On-change observation:**
- `simulation_time_s` = time of the change in simulation
- `occurred_at` ≈ `simulation_time_s` mapped to calendar
- `emitted_at` ≈ wall clock (near-synchronous)

---

## 12. Trigger / Sampling Policy

```python
class TriggerPolicy:
    kind: TriggerKind

    # ON_EVENT: fires when reality event matches
    event_types: tuple[str, ...]    # "PROCESS_COMPLETE", "QUALITY_CHECK"
    target_ids: tuple[str, ...]     # "AP04", "final-quality"

    # PERIODIC: fires every interval_s seconds of simulation time
    interval_s: float               # e.g., 1.0, 10.0

    # ON_CHANGE: fires when field changes beyond threshold
    change_threshold: float | None
    change_field: str | None        # e.g., "value", "status"

    # MANUAL: fires only on explicit request
    # (no additional fields)
```

### Trigger Evaluation

`ObservationService` evaluates triggers at two points:

1. **Post-event**: After each discrete event dispatch → check `ON_EVENT` points.
2. **Post-step**: After each simulation step/period → check `PERIODIC` and `ON_CHANGE` points.

`MANUAL` points are evaluated only when `ObservationService.collect_manual(point_id)` is called.

### Example Configurations

```yaml
observation_points:
  - id: ap04-every-completion
    trigger: { kind: on_event, event_types: [PROCESS_COMPLETE], target_ids: [AP04] }

  - id: tank-level-periodic
    trigger: { kind: periodic, interval_s: 5.0 }

  - id: level-alarm-on-change
    trigger: { kind: on_change, change_field: value, change_threshold: 0.1 }
```

---

## 13. Projection Responsibilities

### 13.1 Projection Protocol

```python
from typing import Protocol, runtime_checkable
from virtual_factory.observation.envelope import ObservationEnvelope

@runtime_checkable
class ProjectionProtocol(Protocol):
    """Transform ObservationEnvelope[] → consumer-specific output."""

    def project(self, envelopes: list[ObservationEnvelope]) -> Any:
        ...
```

### 13.2 MESProjection

```python
class MESProjection:
    """Transform ObservationEnvelope[] → MESOutput.

    Responsibilities:
    - Map observation_type=EVENT → MESEvent with correct MESEventType
    - Populate wip_id, station_id, disposition, result from payload/context
    - Preserve correlation_id for genealogy
    - Drop non-MES observations (measurements, human_entries unless configured)

    Non-responsibilities:
    - Network I/O
    - Odoo protocol encoding
    - Business validation
    """

    def project(self, envelopes: list[ObservationEnvelope]) -> MESOutput:
        ...
```

### 13.3 IIoTProjection

```python
class IIoTProjection:
    """Transform ObservationEnvelope[] → generic industrial payload.

    Responsibilities:
    - Map observation_type=MEASUREMENT → SignalValue-like dict
    - Map observation_type=EVENT → industrial event/alarm
    - Apply OutputPolicy to filter internal_truth
    - Produce Sparkplug-compatible category mapping

    Non-responsibilities:
    - Network I/O
    - Sparkplug B encoding (that's the gateway's job)
    """

    def project(self, envelopes: list[ObservationEnvelope]) -> list[dict[str, Any]]:
        ...
```

### 13.4 Relationship to AssemblyProjection

`AssemblyProjection` (M4) is an **internal** projection — it exposes assembly runtime state for the Scene and internal diagnostics. It is NOT a consumer projection.

Consumer projections (MESProjection, IIoTProjection) consume `ObservationEnvelope[]`, not `AssemblyProjection`. This keeps the boundaries clean:

```
AssemblyRuntimeState → AssemblyProjection (internal, for Scene)
                     → ObservationService → ObservationEnvelope[] → MESProjection (consumer)
                                                                    → IIoTProjection (consumer)
```

---

## 14. Gateway Reuse / Generalization Plan

### 14.1 ObservationGateway Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObservationGatewayProtocol(Protocol):
    """Deliver projected payloads to external systems.

    Gateway failure must not corrupt simulation state.
    """

    def deliver(self, payload: Any, topic: str | None = None) -> bool:
        """Return True on success, False on non-fatal failure.
        Raise only on fatal, unrecoverable errors.
        """
        ...

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    @property
    def connected(self) -> bool: ...
```

### 14.2 Reuse Matrix

| Existing Component | M5 Adaptation |
|-------------------|---------------|
| `MqttGateway` | Add `ObservationGatewayProtocol` impl; delegate to existing `publish_frame()` |
| `SparkplugBGateway` | Add `ObservationGatewayProtocol` impl; delegate to existing `publish_frame()` |
| `OpcUaGateway` | Add `ObservationGatewayProtocol` impl; delegate to existing node writes |
| FastAPI endpoints | Wrap in `InMemoryObsGateway` for testing; existing REST stays independent |
| WebSocket stream | Wrap in `InMemoryObsGateway`; existing WS stays independent |
| File export (new) | `FileObsGateway` — writes JSONL/CSV, implements `ObservationGatewayProtocol` |

### 14.3 Gateway Composition

Rather than replacing existing gateways, M5 wraps them:

```python
class MqttObsGateway:
    """M5 ObservationGateway wrapping existing MqttGateway."""

    def __init__(self, mqtt: MqttGateway):
        self._mqtt = mqtt

    def deliver(self, payload: Any, topic: str | None = None) -> bool:
        try:
            # Existing MqttGateway logic with error handling
            self._mqtt.publish_frame(payload)
            return True
        except Exception:
            return False  # Non-fatal — simulation continues
```

---

## 15. Gateway Failure Semantics

| Scenario | Behavior |
|----------|----------|
| MQTT broker unreachable at connect | `connect()` raises after retries; simulation may start without MQTT |
| MQTT broker disconnected mid-run | `deliver()` returns `False`; observation is dropped; simulation continues |
| File gateway disk full | `deliver()` returns `False`; observation is dropped; simulation continues |
| InMemory gateway overflow | Configurable: drop oldest or raise |
| Gateway thread crash | Gateway runs in its own thread/async task; crash does not affect simulation loop |

**Key invariant**: `deliver()` returning `False` is a non-event for the simulation. The simulation never blocks on gateway I/O. Lost observations are a monitoring concern, not a simulation concern.

---

## 16. Hidden-Truth Leakage Prevention

### 16.1 Multi-Layer Defense (default-deny architecture)

```
Layer 1 (PRIMARY): ObservationPoint.fields.extract — EXPLICIT ALLOW-LIST
    → FieldExtractor only copies fields named in `extract`.
    → If reality model adds a new internal field tomorrow, it is
      INVISIBLE to observation by default — no configuration change needed.
    → This is the primary defense. Deny-list is defense-in-depth only.

Layer 2 (DEFENSE-IN-DEPTH): ObservationPoint.fields.deny
    → Explicit deny-list: "internal_truth", "solver_state", "degradation_truth"
    → Even if `extract` is misconfigured, these fields are stripped.
    → Last line of defense within the observation layer.

Layer 3: ObservationPolicy
    → Category-level: generalization of OutputPolicy; industrial mode blocks internal_truth

Layer 4: Projection
    → Consumer-level: MESProjection drops non-MES fields; IIoTProjection applies OutputPolicy

Layer 5: Gateway
    → Protocol-level: existing MqttGateway already rejects internal_truth category (line 72)
```

### 16.2 Test Enforcement (per slice)

```python
def test_default_deny_new_field_not_leaked():
    """A new internal field added to reality must NOT appear in any observation."""
    # Simulate reality model adding a new field "secret_debug_value"
    # Without updating any ObservationPoint config
    envelope = service.collect_for_point("ap04-completion")
    assert "secret_debug_value" not in envelope.payload
    assert "secret_debug_value" not in envelope.context

def test_allow_list_only_extracts_declared_fields():
    """Only fields in extract[] appear in the envelope payload."""
    point = ObservationPoint(
        fields=FieldPolicy(extract=("event_type", "result"))
    )
    envelope = service.collect_for_point(point.point_id)
    assert set(envelope.payload.keys()) == {"event_type", "result"}

def test_hidden_truth_not_in_mes_envelope():
    """MES observation must not contain solver state or true physical values."""
    envelope = service.collect_for_point("ap04-completion")
    assert "solver_state" not in envelope.payload
    assert "true_flow" not in envelope.payload

def test_internal_truth_blocked_by_policy():
    """Industrial mode policy must reject internal_truth category."""
    policy = ObservationPolicy(mode="industrial")
    assert not policy.can_observe(category="internal_truth")

def test_mqtt_gateway_rejects_internal_truth():
    """Existing invariant: MqttGateway must reject internal_truth."""
    with pytest.raises(ValueError, match="internal_truth"):
        gateway.publish_frame([SignalValue(name="x", category="internal_truth", ...)])
```

---

## 17. Compatibility Plan for M4 MESAdapter

### Strategy: Compatibility Façade

The M4 `MESAdapter` is preserved as a public API. Internally, it delegates to M5 components:

```python
class MESAdapter:
    """M4 compatibility façade. Delegates to M5 MESProjection + ControlBoundary."""

    def mes_to_simulation(self, mes_input: MESInput) -> dict[str, Any]:
        # Existing contract preserved
        boundary = ControlBoundary()
        request = boundary.validate_and_map(mes_input)
        return {
            "run_id": request.run_id,
            "orders": [o.order_id for o in mes_input.production_orders],
            "releases": [{"wip_id": r.wip_id, "source": r.source_id}
                         for r in mes_input.material_releases],
            "quality_count": len(mes_input.quality_requirements),
        }

    def simulation_to_mes(self, run_id, run_status, simulation_events):
        # Existing contract preserved
        projection = MESProjection()
        envelopes = _convert_dicts_to_envelopes(simulation_events, run_id)
        return projection.project(envelopes)
```

### Migration Path

1. **M5-S01–S04**: MESAdapter unchanged. New MESProjection developed in parallel.
2. **M5-S05**: MESAdapter internally delegates to MESProjection. Public API unchanged.
3. **Post-M5** (future): Deprecate MESAdapter when all consumers migrate to ObservationGateway + MESProjection.

---

## 18. TIPA Design Proofs

### 18.1 AP04 / ASSY-BB1 — Join Station

**Reality knows:**
- SSO2 WIP identity, RSO2 WIP identity
- Operator ID, fixture ID, pallet ID
- Join progress, alignment, physical timing
- Internal quality metrics

**MES observation (MESProjection) exposes only:**
- SSO2 identity (subject_id)
- RSO2 identity (context.rso2_id)
- Join completion (event_type=OPERATION_COMPLETED)
- Alignment result (payload.alignment)
- Genealogy relationship (correlation_id links both WIPs)

**Hidden from MES:**
- Physical timing details beyond completion
- Internal quality metrics not in spec
- Operator ID (unless configured)

**IIoT observation (IIoTProjection) may expose:**
- Machine signals (torque, alignment sensor, cycle time)
- Different from MES view

**Envelope example:**

```python
ObservationEnvelope(
    observation_id="obs-ap04-001",
    idempotency_key="tipa-run-1|evt-ap04-0040|ap04-completion|1.0",
    observation_type="event",
    run_id="tipa-run-1",
    simulation_time_s=45.0,
    occurred_at="2026-08-08T00:00:45.0Z",
    emitted_at="2026-08-08T14:30:01.234Z",
    source_domain="assembly",
    source_path="processor.AP04",
    subject_type="wip",
    subject_id="wip-0001",
    context={
        "station_id": "AP04",
        "flow_id": "base",
        "rso2_wip_id": "wip-0002",
        "join_type": "press-fit",
    },
    payload={
        "event_type": "PROCESS_COMPLETE",
        "result": "committed",
        "alignment": "pass",
    },
    correlation_id="wip-0001",
    causation_id="evt-ap04-0040",
)
```

### 18.2 AP06 / ASSY-TEST1 — Electrical Test

**MES observation exposes:**
- Motor/serial identity (context.serial_id)
- Test program (context.test_program)
- Selected resistance values (payload.resistance_r1, payload.resistance_r2)
- Selected manual checks (payload.manual_checks)
- Rotation/sound result (payload.rotation_test, payload.sound_test)
- Overall PASS/FAIL (payload.overall_result)
- Cycle complete (event_type=OPERATION_COMPLETED)

**Hidden from MES:**
- Raw sensor traces
- Intermediate test voltages
- Operator notes not in checklist

### 18.3 AP08 / Robot Visual Inspection

**MES projection exposes:**
- Serial (context.serial_id)
- Inspection complete (event_type=QUALITY_RESULT)
- PASS/NG (payload.disposition)
- Optional defect classification (payload.defect_class)

**IIoT projection exposes different signals:**
- Robot joint positions, camera trigger, cycle time
- Machine-level telemetry, not quality results

---

## 19. Detailed M5-S01 → M5-S05 Implementation Plan

### M5-S01: ObservationEnvelope + ObservationType

**Scope**: Define the core data structures only.

**Files to create:**
- `src/virtual_factory/observation/__init__.py`
- `src/virtual_factory/observation/envelope.py` — `ObservationEnvelope`, `ObservationType` enum

**Tests:**
- `tests/test_m5_s01_envelope.py`
  - Envelope construction with required fields
  - Envelope construction with optional context
  - `observation_id` uniqueness
  - Serialization round-trip (JSON)
  - Different `observation_type` payload shapes

**Acceptance:**
- All 823 existing tests green
- ~8 new tests green
- No M2–M4 modifications

---

### M5-S02: ObservationPoint + TriggerPolicy

**Scope**: Define observation point configuration and trigger evaluation.

**Files to create:**
- `src/virtual_factory/observation/point.py` — `ObservationPoint`, `TriggerPolicy`, `TriggerKind`, `FieldPolicy`
- `src/virtual_factory/observation/policy.py` — `ObservationPolicy` (generalizes `OutputPolicy`)

**Tests:**
- `tests/test_m5_s02_point.py`
  - ON_EVENT trigger matches correct events
  - ON_EVENT trigger ignores non-matching events
  - PERIODIC trigger fires at correct intervals
  - ON_CHANGE trigger fires on threshold crossing
  - FieldPolicy default-deny: new fields not in extract[] are invisible
  - FieldPolicy defense-in-depth: deny[] strips even if extract is misconfigured
  - ObservationPolicy blocks internal_truth in industrial mode

**Acceptance:**
- All existing tests green
- ~12 new tests green
- No M2–M4 modifications
- `OutputPolicy` import path still works (re-export from observation if needed)

---

### M5-S03: ObservationService

**Scope**: Wire observation points to runtime events and state.

**Files to create:**
- `src/virtual_factory/observation/service.py` — `ObservationService`
- `src/virtual_factory/observation/identity.py` — Identity helpers, idempotency

**Files to modify (minimal):**
- `src/virtual_factory/telemetry/telemetry_frame.py` — add `build_publishable_frame_via_service()` as opt-in path

**Tests:**
- `tests/test_m5_s03_service.py`
  - One reality event → one observation (event-triggered)
  - One reality event → multiple observations (different points)
  - One reality event → zero observations (no matching point)
  - Periodic observations from continuous state
  - On-change observations
  - Hidden truth not in envelope payload
  - Envelope identity is deterministic for same seed
  - Service with TIPA topology → envelopes for PROCESS_START, QUALITY_CHECK, WIP_COMPLETED

**Acceptance:**
- All existing tests green
- ~15 new tests green
- No M2–M4 semantic modifications

---

### M5-S04: Projections + Router + ControlBoundary

**Scope**: Consumer-specific projections, envelope routing, and reverse control boundary.

**Files to create:**
- `src/virtual_factory/observation/projections/__init__.py`
- `src/virtual_factory/observation/projections/base.py` — `ProjectionProtocol`
- `src/virtual_factory/observation/projections/mes_projection.py` — `MESProjection`
- `src/virtual_factory/observation/projections/iiot_projection.py` — `IIoTProjection`
- `src/virtual_factory/observation/router.py` — `ObservationRouter` (subscription-based routing)
- `src/virtual_factory/observation/control_boundary.py` — `ControlBoundary`, `SimulationRunRequest`

**Tests:**
- `tests/test_m5_s04_projections.py`
  - MESProjection: EVENT envelope → MESEvent with correct MESEventType
  - MESProjection: non-MES envelopes dropped
  - MESProjection: internal_truth fields absent from output
  - IIoTProjection: MEASUREMENT envelope → SignalValue-like dict
  - IIoTProjection: industrial mode blocks internal_truth
  - IIoTProjection: Sparkplug category mapping
  - ObservationRouter: one envelope → MESProjection only (subscription match)
  - ObservationRouter: one envelope → both MES + IIoT (two subscriptions)
  - ObservationRouter: one envelope → zero projections (no subscription match)
  - ObservationRouter: subscription by event_type, by source_path, by point_id
  - ControlBoundary: MESInput validated against SimulationDefinition
  - ControlBoundary: unknown source_id rejected
  - ControlBoundary: SimulationRunRequest preserves order/material info
  - TIPA AP04 proof: full path reality → envelope → router → MES projection
  - TIPA AP06 proof: selected fields only
  - TIPA AP08 proof: MES vs IIoT different projections via router

**Acceptance:**
- All existing tests green
- ~22 new tests green
- M4 MESAdapter tests still pass (no breaking changes)

---

### M5-S05: Gateway Protocol + Integration

**Scope**: ObservationGateway protocol, wrap existing gateways, end-to-end integration.

**Files to create:**
- `src/virtual_factory/protocols/observation_gateway.py` — `ObservationGatewayProtocol`
- `src/virtual_factory/protocols/file_gateway.py` — `FileObsGateway`

**Files to modify (minimal):**
- `src/virtual_factory/protocols/mqtt_gateway.py` — add `MqttObsGateway` wrapper
- `src/virtual_factory/assembly/mes_adapter.py` — internal delegation to M5 (façade only)

**Tests:**
- `tests/test_m5_s05_gateway.py`
  - MqttObsGateway wraps MqttGateway without breaking
  - FileObsGateway writes JSONL
  - Gateway failure returns False, simulation continues
  - InMemoryObsGateway for testing
  - Full integration: generic_demo.yaml → run → ObservationService → MESProjection → MqttObsGateway
  - Hidden truth blocked at all 4 layers
  - MESAdapter unchanged public API

**Acceptance:**
- All existing tests green (~840+ total)
- No M2–M4 breaking changes
- M4 MESAdapter tests green
- Full TIPA integration proof green

---

## 20. Tests / Acceptance Gate Per Slice

| Slice | New Tests (est.) | Cumulative | Key Gate |
|-------|-----------------|------------|----------|
| M5-S01 | 9 | 832 | Envelope construction (with idempotency_key), serialization |
| M5-S02 | 14 | 846 | Trigger matching, default-deny allow-list, policy enforcement |
| M5-S03 | 16 | 862 | Service wiring, hidden truth prevention, identity derivation |
| M5-S04 | 22 | 884 | Projection correctness, router subscriptions, control boundary |
| M5-S05 | 12 | 896 | Gateway isolation, full integration |

Each slice gate:
- [ ] All new tests pass
- [ ] All existing 823+ tests pass
- [ ] No M2 runtime modifications
- [ ] No M3 semantic modifications
- [ ] `internal_truth` does not leak in industrial mode
- [ ] Gateway failure does not corrupt simulation state
- [ ] M4 MESAdapter public API unchanged

---

## 21. Risks and Rejected Alternatives

### Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Over-engineering ObservationEnvelope | Medium | Start minimal; add fields only when needed by a concrete consumer |
| Breaking M4 MESAdapter contract | Low | Compatibility façade; no public API change |
| Performance overhead from envelope creation | Low | Envelopes are lightweight dataclasses; batch collection |
| Scope creep into Odoo integration | Medium | Strictly enforce "no Odoo RPC" in slice contracts |
| Duplicating existing gateway logic | Low | Wrap, don't replace; `MqttObsGateway` delegates to `MqttGateway` |

### Rejected Alternatives

| Alternative | Reason Rejected |
|-------------|----------------|
| ObservationEnvelope extends MESEvent | Violates principle 1: VF must not mirror MES models |
| Put ObservationPoint in assembly/ package | Observation is cross-domain (continuous + discrete); belongs in own package |
| Replace MESAdapter immediately | Violates principle 8: M4 architecture is stable; use façade instead |
| Add wall-clock timing to envelopes | Envelopes carry simulation time only; wall-clock is a gateway concern |
| Use Protobuf for ObservationEnvelope | Premature optimization; JSON/dict is sufficient for foundation |
| Build a centralized ESB/event bus | Violates principle 7; gateway dispatch is simple routing, not an ESB |
| Put gateway protocol in observation/ package | Violates principle 6: protocol concerns stay outside simulation domain |

---

## 22. Critical Questions — Answered

### Q1: Can current continuous signal/output abstractions be reused?

**Yes.** `SignalValue` remains the continuous-domain measurement primitive. `OutputPolicy` is generalized into `ObservationPolicy`. `build_publishable_frame()` is adapted to use `ObservationService` internally. Existing gateways are wrapped, not replaced.

### Q2: Should observation abstractions live in a generic package outside `assembly/`?

**Yes — `observation/` is a top-level package**, sibling to `assembly/`, `telemetry/`, `discrete/`. Observation spans both continuous (signals, measurements) and discrete (events, state) domains. It belongs at the cross-cutting layer.

### Q3: How is hidden truth prevented from leaking?

**Five-layer defense with default-deny architecture:**
1. `ObservationPoint.fields.extract` — **PRIMARY**: explicit allow-list. New internal fields are invisible by default.
2. `ObservationPoint.fields.deny` — defense-in-depth deny-list
3. `ObservationPolicy` — category-level (generalized `OutputPolicy`)
4. `Projection` — consumer-level strip
5. `Gateway` — protocol-level reject (existing `MqttGateway` check)

Key principle: if reality model adds a field tomorrow, it does NOT appear in any observation unless explicitly added to `extract[]`.

### Q4: How can one reality event feed different consumer projections?

`ObservationService` evaluates all `ObservationPoint` configurations against each reality event and produces `ObservationEnvelope[]`. The `ObservationRouter` then routes each envelope to one or more projections based on subscription rules:

- Subscription `event_type=PROCESS_COMPLETE` → MESProjection
- Subscription `source_path=AP04` → IIoTProjection

One envelope, two subscriptions, two consumer-specific outputs. The `ObservationPoint` never declares consumers — that's the router's job.

### Q5: How are gateway failures isolated?

`ObservationGatewayProtocol.deliver()` returns `bool`. `False` means "dropped, continue." Gateways run in their own execution context (thread/async). Simulation never blocks on gateway I/O. Lost observations are a monitoring concern.

### Q6: How do simulation time and wall time coexist?

- **`simulation_time_s`** (float): simulation-clock coordinate. Always present.
- **`occurred_at`** (ISO 8601 str, optional): simulated calendar timestamp. Populated when run has an epoch.
- **`emitted_at`** (ISO 8601 str): UTC wall-clock timestamp of envelope creation. Never simulation time.
- **Wall-clock time** (Unix float): gateway layer only — for timeout, retry, logging. Distinct from `emitted_at` which IS an envelope field but serves as an audit/emission timestamp, not a protocol-level clock.

No single field serves dual purpose. Consumers always know whether they're looking at sim time or real time by the field name and type.

### Q7: How are WIP/serial/business identities decoupled?

- `WipId` (e.g., `wip-0001`) — internal, auto-generated, carried in `correlation_id`
- Business serial/lot — carried in `ObservationEnvelope.context` as `serial_id`, `lot_id`
- External references — carried in `context.external_ref`
- Station/resource — carried in `context.station_id`
- The `ControlBoundary` maps external identities to internal at run start.

### Q8: What becomes of the M4 MESAdapter?

**Preserved as a compatibility façade.** Public API unchanged. Internally delegates to `MESProjection` and `ControlBoundary`. Deprecation only after all consumers migrate to `ObservationGateway` + `MESProjection`.

### Q9: What changes are actually required in M2–M4?

**None.** M5 is additive. Existing packages, classes, and tests are not modified. The only exception is M5-S05 adding a wrapper class in `protocols/` that does not change existing gateway behavior.

### Q10: Where is the smallest correct architectural seam for M5?

**Between `EventTraceEntry`/`RuntimeState` and `ObservationEnvelope`.**

```
EventTraceEntry / RuntimeState    ← reality (unchanged)
        │
        ▼
ObservationPoint[] evaluation     ← NEW seam
        │
        ▼
ObservationEnvelope[]             ← NEW consumer-neutral carrier
        │
        ▼
Projections + Gateways            ← NEW (or wrapped existing)
```

This seam is minimal, testable, and does not penetrate the simulation domain.

---

## 23. MES Project Follow-Up Backlog

*Separate from M5. For future MES integration work only.*

1. **Canonical event vocabulary mapping**: Map VF internal event types to a standard MES event vocabulary (ISA-95 style).
2. **Genealogy / lot traceability**: Model parent-child WIP relationships for assembly join/split operations.
3. **Checklist model**: Structured checklist with measurements, pass/fail, operator signature.
4. **Measurement model**: Typed measurements with unit, tolerance, method, equipment.
5. **Quality result model**: Aggregated quality disposition with defect codes.
6. **Idempotency by business key**: Enable `(order_id, operation_sequence, serial_id)` as dedup key.
7. **Control boundary depth**: Full work order → operation → workstation mapping.
8. **MES simulator** (separate project): A lightweight MES that consumes VF observations and produces production context.

---

## 24. Completion Confirmation

| Item | Status |
|------|--------|
| Current-state audit | ✅ Complete — sections 1.1–1.7 |
| Gap analysis | ✅ Complete — section 2 |
| Target architecture diagram | ✅ Complete — section 3 |
| Component responsibility table | ✅ Complete — section 4 |
| Observation flow | ✅ Complete — section 5 |
| Reverse control/context flow | ✅ Complete — section 6 |
| Proposed package/module/class structure | ✅ Complete — section 7 |
| ObservationPoint schema proposal | ✅ Complete — section 8 |
| ObservationEnvelope schema proposal | ✅ Complete — section 9 |
| Identity/context strategy | ✅ Complete — section 10 |
| Time semantics | ✅ Complete — section 11 |
| Trigger/sampling policy | ✅ Complete — section 12 |
| Projection responsibilities | ✅ Complete — section 13 |
| Gateway reuse/generalization plan | ✅ Complete — section 14 |
| Gateway failure semantics | ✅ Complete — section 15 |
| Hidden-truth leakage prevention | ✅ Complete — section 16 |
| Compatibility plan for M4 MESAdapter | ✅ Complete — section 17 |
| TIPA AP04/AP06/AP08 examples | ✅ Complete — section 18 |
| M5-S01 → M5-S05 implementation plan | ✅ Complete — section 19 |
| Tests/acceptance gate for every slice | ✅ Complete — section 20 |
| Risks and rejected alternatives | ✅ Complete — section 21 |
| MES Project Follow-up Backlog | ✅ Complete — section 23 |

**Files changed:**
- Updated: `docs/m5-architecture-gate.md` (SA correction round 1)

**No M5 production implementation was performed.**

---

## VF-DM-M5-ARCHITECTURE-GATE — SA Correction Round 1

### Changes Applied

| # | Correction | Sections Affected |
|---|-----------|------------------|
| 1 | **ObservationPoint no longer declares consumer** — removed `projections` field; added `ObservationRouter` as new layer between Envelope and Projections | 3, 4, 5, 7, 8, 13, 19, 20, Q4 |
| 2 | **Default-deny + explicit allow-list** — `FieldPolicy.extract` (primary) replaces `hidden` deny-list; `FieldPolicy.deny` is defense-in-depth only | 8, 16, Q3 |
| 3 | **Time semantics fixed** — `simulation_time_s` (float), `occurred_at` (ISO 8601 str, optional), `emitted_at` (ISO 8601 str, wall-clock). No field serves dual purpose. | 5, 9, 11, 18, Q6 |
| 4 | **Separate `idempotency_key`** — deterministic key (`run_id\|source_event_id\|point_id\|schema_version`) distinct from `observation_id` UUID | 9, 10 |

### Awaiting SA Review Round 2

```
M5 Architecture Gate
Status: CORRECTION APPLIED — awaiting re-review
M5-S01 authorization: NOT YET
```
