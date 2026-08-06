# 15-v2 — Prompt VF-DM-M2-S01: Pure DiscreteSimulationEngine Lifecycle

## 1. Role

Act as PM and implementation lead for M2-S01.

## 2. Baseline

```text
Repository: hieudovn/virtual-factory
Branch: main (after M2-S00-C01 SA approval)
HEAD: d5b345b (approved discrete kernel merged)
Tests: 315 passed
```

## 3. Mission

Implement a deterministic, synchronous, domain-neutral `DiscreteSimulationEngine` on top of the approved kernel. The engine depends on an injected `EventDispatcherProtocol`, not on domain logic.

## 4. Deliverables

### 4.1 `src/virtual_factory/discrete/engine.py`

```python
class DiscreteSimulationEngine:
    """Deterministic, synchronous, domain-neutral."""

    def __init__(self, run_context: RunContext, dispatcher: EventDispatcherProtocol): ...
    def initialize(self) -> None:
        """Schedule bootstrap events via dispatcher. Status → READY."""
    def step_event(self) -> RuntimeSnapshot:
        """Pop one event, dispatch, schedule follow-ups, return snapshot."""
    def stop(self, reason: str = "stopped") -> RuntimeSnapshot: ...
    def _complete(self, reason: str) -> RuntimeSnapshot: ...
    def _fail(self, error: str) -> RuntimeSnapshot: ...

    @property
    def status(self) -> RunStatus: ...
    @property
    def state(self) -> DiscreteRunState: ...
    def to_snapshot(self) -> RuntimeSnapshot: ...
```

### 4.2 `src/virtual_factory/discrete/state.py`

```python
class RunStatus(enum.Enum):
    CREATED, READY, RUNNING, PAUSED, COMPLETED, STOPPED, FAILED

@dataclass
class DiscreteRunState:
    run_id, status, simulation_time_s, processed_events,
    pending_events, last_event_id, stop_reason, failure_error,
    snapshot_sequence, diagnostics
```

### 4.3 `src/virtual_factory/discrete/snapshot.py`

```python
@dataclass(frozen=True)
class RuntimeSnapshot:
    schema_version, run_id, model_id, model_version,
    scenario_id, scenario_version, status, simulation_time_s,
    stop_reason, failure_error, processed_events, pending_events,
    last_event_id, snapshot_sequence, message_sequence,
    allowed_actions
```

### 4.4 `src/virtual_factory/discrete/dispatcher.py`

```python
@runtime_checkable
class EventDispatcherProtocol(Protocol):
    def dispatch(self, event: ScheduledEvent, run_state: DiscreteRunState) -> HandlerOutcome: ...

@dataclass(frozen=True)
class HandlerOutcome:
    event_id, success, follow_up_events, state_changes, error
```

### 4.5 `tests/test_discrete_engine.py` (~12 tests)

- Engine created in CREATED status
- initialize() → READY
- step_event() with test dispatcher returns RuntimeSnapshot
- step_event() increments processed_events and snapshot_sequence
- step_event() on empty scheduler → COMPLETED
- step_event() after COMPLETED raises
- Handler returns success=False → FAILED
- stop() → STOPPED with reason
- to_snapshot() produces correct RuntimeSnapshot
- Determinism: same seed + same events = same snapshot sequence

**Test double:** `StubDispatcher` that returns empty follow-ups for all events.

## 5. Exclusions

- NO handler registry (M2-S02)
- NO DiscreteRunState with node/entity/route fields
- NO assembly domain, source, sink, entity, node
- NO RunController, ExecutionMode, auto pacing (M2-S04)
- NO DiscreteRunService, API, WebSocket (M2-S07/M4)
- NO FastAPI adapters (M4)
- NO TIPA configuration
- NO factory registration
- NO asyncio, sleep, I/O in engine

## 6. Acceptance

- 315 existing + ~12 new tests pass
- CI workflow added
- Engine lifecycle smoke test
