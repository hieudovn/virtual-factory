# 15-v3 — Prompt VF-DM-M2-S01: DiscreteSimulationEngine Lifecycle

## 1. Role

Act as PM and implementation lead for M2-S01.

## 2. Baseline

```text
Repository: hieudovn/virtual-factory
Branch: main (after M2-S00 gate closure)
HEAD: d5b345bc4941003cf6636ee1606bd259b37a5231
Tests: 315 passed
```

## 3. Mission

Implement a deterministic, synchronous, domain-neutral `DiscreteSimulationEngine` using the approved kernel and an injected `EventDispatcherProtocol`.

## 4. Deliverables

### 4.1 `src/virtual_factory/discrete/engine.py`

```python
class DiscreteSimulationEngine:
    def __init__(self, run_context: RunContext, dispatcher: EventDispatcherProtocol): ...
    def initialize(self, initial_events: Iterable[ScheduledEvent] = ()) -> RuntimeSnapshot: ...
    def step_event(self) -> RuntimeSnapshot: ...
    def stop(self, reason: str = "stopped") -> RuntimeSnapshot: ...
    def _complete(self, reason: str) -> RuntimeSnapshot: ...
    def _fail(self, error_code: str, error_detail: str | None = None) -> RuntimeSnapshot: ...
    @property
    def status(self) -> RunStatus: ...
    @property
    def state(self) -> DiscreteRunState: ...
    def to_snapshot(self) -> RuntimeSnapshot: ...
```

**Step semantics** (implement exactly):
1. Pop event from scheduler → `None` → `_complete("scheduler empty")`
2. Sync `DiscreteRunState.simulation_time_s = scheduler.current_time_s`
3. `outcome = dispatcher.dispatch(event)`
4. `not outcome.success` → `_fail(outcome.error_code, outcome.error_detail)`
5. Schedule each follow-up via `scheduler.schedule()` → failure → `_fail("schedule_error", ...)`
6. Commit: `processed_events += 1`, `pending_events = scheduler.pending_count`, `last_event_id = event.event_id`, `snapshot_sequence += 1`
7. `scheduler.is_empty` → `_complete("scheduler empty")`
8. Return `to_snapshot()`

One `snapshot_sequence` increment per transition (success or failure). No retry.

### 4.2 `src/virtual_factory/discrete/state.py`

```python
class RunStatus(enum.Enum):
    CREATED, READY, RUNNING, PAUSED, COMPLETED, STOPPED, FAILED

@dataclass
class DiscreteRunState:
    run_id: str
    status: RunStatus
    simulation_time_s: float
    processed_events: int
    pending_events: int
    last_event_id: str | None
    stop_reason: str | None
    failure_error: str | None
    snapshot_sequence: int
    diagnostics: dict[str, Any]
```

### 4.3 `src/virtual_factory/discrete/snapshot.py`

```python
@dataclass(frozen=True)
class RuntimeSnapshot:
    schema_version: str = "1.0.0"
    run_id: str
    model_id: str
    model_version: str | None
    scenario_id: str | None
    scenario_version: str | None
    status: str
    simulation_time_s: float
    stop_reason: str | None
    failure_error: str | None
    processed_events: int
    pending_events: int
    last_event_id: str | None
    snapshot_sequence: int
```

No `message_sequence`. No `allowed_actions`.

### 4.4 `src/virtual_factory/discrete/dispatcher.py`

```python
@runtime_checkable
class EventDispatcherProtocol(Protocol):
    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome: ...

@dataclass(frozen=True)
class HandlerOutcome:
    event_id: str
    success: bool
    follow_up_events: tuple[ScheduledEvent, ...]
    state_changes: tuple[str, ...]
    error_code: str | None = None
    error_detail: str | None = None
```

All follow-up events must have `sequence=None`.

### 4.5 `tests/test_discrete_engine.py`

**Test double:** `StubDispatcher` that returns `HandlerOutcome(success=True, follow_up_events=(), state_changes=(), event_id=event.event_id)` for all events.

**Required tests:**
- Engine created → `CREATED`
- `initialize()` with no events → `READY`
- `initialize()` with bootstrap events → `READY`, events scheduled
- `step_event()` on empty scheduler → `COMPLETED`
- `step_event()` with stub dispatcher → increments counters, returns snapshot
- `step_event()` after `COMPLETED` raises
- Dispatcher returns `success=False` → `FAILED`
- `stop()` → `STOPPED` with reason
- `snapshot_sequence` increments on each transition
- Identical ordered initial events + identical stub outcomes → identical snapshots

## 5. Exclusions

- NO `HandlerRegistry` (M2-S02)
- NO assembly domain (nodes, entities, routes, source, sink)
- NO `RunController`, `ExecutionMode`, auto pacing (M2-S04)
- NO `DiscreteRunService`, API, WebSocket (M2-S07, M4)
- NO RNG (M2-S05)
- NO `message_sequence`, `allowed_actions`
- NO TIPA, factory registration
- NO asyncio, sleep, I/O in engine

## 6. Acceptance (C02-13)

- Baseline: `d5b345bc4941003cf6636ee1606bd259b37a5231`
- All existing (315) + new tests pass
- Actual collected/passed counts reported (not prescribed)
- `virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml` passes
- `python -m simulators.vf2.main --package simulators/vf2/examples/sample_pim_package.json --validate-only` passes
- GitHub Actions CI workflow added and passing
