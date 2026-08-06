# 06-v3 — Event Dispatch and State Contracts (Final)

**Date:** 2026-08-05  
**Replaces:** `06-...-v2.md`  
**Corrections:** V2-F02, V2-F03

---

## 1. EventDispatcherProtocol (C02-02)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EventDispatcherProtocol(Protocol):
    """Injected port — engine depends on this, not on domain.

    The dispatcher owns or receives AssemblyRuntimeState internally.
    It does NOT receive DiscreteRunState — handlers must not mutate
    engine lifecycle state.
    """

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        """Dispatch one event. Returns immutable outcome.

        The engine schedules follow-up events from the outcome.
        Handlers never receive the scheduler.
        """
        ...
```

If future handlers need read-only run metadata, define an immutable `DispatchContext` in a later slice. Do not expose mutable `DiscreteRunState` to handlers.

---

## 2. HandlerOutcome (C02-03)

```python
@dataclass(frozen=True)
class HandlerOutcome:
    """Immutable result of one event dispatch.

    Equality is based on event_id, success, follow_up_events,
    state_changes, error_code, and error_detail.
    Wall-clock timing diagnostics are excluded from equality.
    """

    event_id: str
    success: bool
    follow_up_events: tuple[ScheduledEvent, ...]  # sequence=None on all
    state_changes: tuple[str, ...]                 # diagnostic only
    error_code: str | None = None
    error_detail: str | None = None
```

**Rules:**
- All follow-up events must have `sequence=None` (unscheduled).
- Engine validates and schedules them.
- `state_changes` are human-readable diagnostic strings — excluded from determinism checks.
- `error_code` uses a fixed vocabulary: `"no_handler"`, `"handler_error"`, `"invalid_target"`, etc.

---

## 3. Handler Function Signature

```python
EventHandlerFn = Callable[[ScheduledEvent], HandlerOutcome]
```

The handler receives only the event. Assembly state is accessed through the concrete M3 dispatcher/registry which the handler belongs to.

---

## 4. Concrete Dispatcher (M2-S02)

```python
class HandlerRegistry:
    """Maps event_type → handler. Owns AssemblyRuntimeState in M3."""

    def register(self, event_type: str, handler: EventHandlerFn) -> None:
        """Register a handler. Raises on duplicate event_type."""

    def dispatch(self, event: ScheduledEvent) -> HandlerOutcome:
        """Find handler by event_type, call it, normalize result."""
```

### Dispatch Behavior

| Scenario | HandlerOutcome |
|----------|---------------|
| Known event_type, handler succeeds | `success=True`, follow_ups populated |
| Known event_type, handler raises | `success=False`, `error_code="handler_error"`, `error_detail=str(exc)` |
| Unknown event_type | `success=False`, `error_code="no_handler"` |

---

## 5. Slice Ownership (C02-04)

| Contract | Owned By |
|----------|----------|
| `RunStatus` | M2-S01 |
| `DiscreteRunState` v1 | M2-S01 |
| `RuntimeSnapshot` v1 | M2-S01 |
| `EventDispatcherProtocol` | M2-S01 |
| `HandlerOutcome` | M2-S01 |
| `DiscreteSimulationEngine` | M2-S01 |
| `HandlerRegistry` (concrete) | M2-S02 |
| Handler registration + duplicate policy | M2-S02 |
| Unknown-event policy | M2-S02 |
| Handler exception normalization | M2-S02 |
| Bounded event trace | M2-S03 |
| Richer diagnostics | M2-S03 |
| Snapshot hardening | M2-S03 |

---

## 6. Engine Scheduling (C02-12)

```python
def step_event(self) -> RuntimeSnapshot:
    # 1. Pop event from scheduler
    event = self._scheduler.pop_next()
    if event is None:
        return self._complete("scheduler empty")

    # 2. Sync run-state time from scheduler clock
    self._run_state.simulation_time_s = self._scheduler.current_time_s

    # 3. Dispatch
    outcome = self._dispatcher.dispatch(event)

    # 4. If dispatch failed, transition to FAILED
    if not outcome.success:
        return self._fail(outcome.error_code, outcome.error_detail)

    # 5. Schedule follow-ups (engine is sole owner)
    for follow_up in outcome.follow_up_events:
        try:
            self._scheduler.schedule(follow_up)
        except FutureEventSchedulerError as exc:
            return self._fail("schedule_error", str(exc))

    # 6. Commit (single snapshot increment)
    self._run_state.processed_events += 1
    self._run_state.pending_events = self._scheduler.pending_count
    self._run_state.last_event_id = event.event_id
    self._run_state.snapshot_sequence += 1

    # 7. Check completion
    if self._scheduler.is_empty:
        return self._complete("scheduler empty")

    return self.to_snapshot()
```

**Key rules:**
- One `snapshot_sequence` increment per committed or failed transition.
- `simulation_time_s` synced from scheduler clock after pop.
- `pending_events` updated after follow-up scheduling.
- No retry on failure.
