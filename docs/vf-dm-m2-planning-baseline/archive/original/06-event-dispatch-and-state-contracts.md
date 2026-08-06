# 06 — Event Dispatch and State Contracts

**Date:** 2026-08-05

---

## 1. Handler Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EventHandlerProtocol(Protocol):
    def __call__(
        self,
        event: ScheduledEvent,
        state: DiscreteRuntimeState,
        scheduler: FutureEventScheduler,
    ) -> list[ScheduledEvent]:
        """Handle an event, mutate state, and return follow-up events to schedule."""
        ...
```

| Rule | Description |
|------|-------------|
| Mutation | Handler mutates `state` directly (authoritative) |
| Follow-up | Returns list of new `ScheduledEvent` for the scheduler |
| No I/O | Handlers must not do I/O, network, or UI calls |
| Idempotency | Handlers must be deterministic given same (event, state) |
| Error | On error, raise → engine catches → run → `failed` |

---

## 2. Dispatch Result

```python
@dataclass(frozen=True)
class DispatchResult:
    event: ScheduledEvent
    follow_up_events: list[ScheduledEvent]
    state_changes: list[str]       # Human-readable change descriptions
    duration_us: int               # Handler execution time
    success: bool
    error: str | None = None
```

---

## 3. Handler Registry

```python
class HandlerRegistry:
    def register(self, event_type: str, handler: EventHandlerProtocol) -> None: ...
    def dispatch(
        self, event: ScheduledEvent, state: DiscreteRuntimeState, scheduler: FutureEventScheduler
    ) -> DispatchResult: ...
    def has_handler(self, event_type: str) -> bool: ...
```

| Scenario | Behavior |
|----------|----------|
| Unknown event type | `dispatch()` returns `DispatchResult(success=False, error="no handler for {type}")` |
| Invalid target | Handler validates target; raises `ValueError` → engine catches |
| Handler raises | Engine catches → run state → `failed` |
| No follow-up | Handler returns `[]` → scheduler unchanged |

---

## 4. DiscreteRuntimeState

Separate from continuous `RuntimeState`. No shared base class.

```python
@dataclass
class DiscreteRuntimeState:
    run_id: str
    status: RunStatus               # enum: created, initialized, running, etc.
    simulation_time_s: float
    model_id: str
    model_version: str | None
    scenario_id: str | None

    # Domain state
    nodes: dict[str, NodeState]
    routes: dict[str, RouteState]
    entities: dict[str, EntityState]     # WIP/material tracking
    resources: dict[str, ResourceState]  # operator/equipment availability

    # Diagnostics
    event_count: int
    last_event: ScheduledEvent | None
    counters: dict[str, int]        # throughput, rework, failures, etc.

    # Commands
    pending_commands: list[CommandResult]

    def to_snapshot(self) -> VisualizationSnapshot: ...
```

---

## 5. NodeState (generic, not TIPA-specific)

```python
@dataclass
class NodeState:
    node_id: str
    node_type: str              # source, buffer, workstation, checkpoint, sink
    display_name: str
    status: str                 # idle, processing, blocked, starved, faulted, held
    queue_count: int
    queue_capacity: int
    current_entity_id: str | None
    progress: float             # 0.0 → 1.0 for current work
    active_fault: str | None
    active_hold: bool
    counters: dict[str, int]
```

---

## 6. EntityState

```python
@dataclass
class EntityState:
    entity_id: str
    entity_type: str
    current_node_id: str
    current_route_id: str | None
    source_id: str
    destination_id: str | None
    quality_status: str          # untested, passed, failed, rework
    rework_count: int
    created_time_s: float
```

---

## 7. State Transition Validation

- State mutations only through handler dispatch.
- `to_snapshot()` produces immutable projection.
- Snapshot version increments on each mutation.
- No external code may mutate `DiscreteRuntimeState` directly.
