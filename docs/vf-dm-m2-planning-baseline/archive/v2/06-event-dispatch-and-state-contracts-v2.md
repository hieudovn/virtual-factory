# 06-v2 — Event Dispatch and State Contracts (Corrected)

**Date:** 2026-08-05  
**Replaces:** `06-event-dispatch-and-state-contracts.md`  
**Corrections:** F-001, F-002, F-004

---

## 1. EventDispatcherProtocol (C-004)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EventDispatcherProtocol(Protocol):
    """Injected port — engine depends on this, not on domain handlers."""

    def dispatch(
        self,
        event: ScheduledEvent,
        run_state: DiscreteRunState,
    ) -> HandlerOutcome:
        """Dispatch an event. Returns outcome with follow-up events.
        
        The dispatcher may mutate domain state internally, but the engine
        only sees the outcome. Follow-up events are scheduled by the engine,
        NOT by the handler.
        """
        ...
```

---

## 2. HandlerOutcome (C-004)

```python
@dataclass(frozen=True)
class HandlerOutcome:
    """Result of dispatching one event to a handler."""

    event_id: str                          # The dispatched event
    success: bool
    follow_up_events: list[ScheduledEvent] # For engine to schedule
    state_changes: list[str]               # Human-readable, diagnostic only
    error: str | None = None               # Set when success=False
```

**Rules:**
- Handlers do NOT receive the `FutureEventScheduler`.
- Handlers return follow-up events; the engine validates and schedules them.
- One scheduling path: engine only.
- Handler failure → `success=False`, `error` set → engine transitions to `FAILED`.
- No automatic retry. No partial state recovery within the handler.

---

## 3. Handler Registration (M2-S02)

```python
class HandlerRegistry:
    """Maps event_type → handler function."""

    def register(self, event_type: str, handler: EventHandlerFn) -> None: ...

    def dispatch(
        self,
        event: ScheduledEvent,
        run_state: DiscreteRunState,
    ) -> HandlerOutcome:
        """Find handler, call it, return outcome."""
        ...
```

### Dispatch Behavior

| Scenario | HandlerOutcome |
|----------|---------------|
| Known event_type, handler succeeds | `success=True`, follow_up_events populated |
| Known event_type, handler raises | `success=False`, error=str(exception) |
| Unknown event_type | `success=False`, error="no handler for {type}" |
| Handler returns no follow-ups | `follow_up_events=[]` (valid) |

---

## 4. State Mutation Constraints (C-004)

Handlers mutate domain state (M3 `AssemblyRuntimeState`) directly — this is trusted in-process code for MVP.

**Fail-stop rules:**
1. Handler mutation is validated before commit (transition methods on state).
2. Handler failure → run transitions to `FAILED` — no automatic recovery.
3. Failed state is diagnostic only — partial mutations are preserved for debugging.
4. No automatic retry.
5. Behavior is explicitly documented as MVP trade-off.

**Future (M6+):** Consider immutable state + replace pattern for stronger guarantees.

---

## 5. Handler Function Signature

```python
EventHandlerFn = Callable[
    [ScheduledEvent, DiscreteRunState],
    HandlerOutcome,
]
```

The handler receives only the event and the mutable state. It does not receive the scheduler, the engine, or any I/O handles.

---

## 6. Engine Scheduling (M2-S01)

In `step_event()`:

```python
def step_event(self) -> RuntimeSnapshot:
    event = self._scheduler.pop_next()
    if event is None:
        return self._complete("scheduler empty")
    
    outcome = self._dispatcher.dispatch(event, self._run_state)
    
    if not outcome.success:
        return self._fail(outcome.error)
    
    # Engine is the ONLY component that schedules follow-ups
    for follow_up in outcome.follow_up_events:
        self._scheduler.schedule(follow_up)
    
    self._run_state.processed_events += 1
    self._run_state.last_event_id = event.event_id
    self._run_state.snapshot_sequence += 1
    
    if self._scheduler.is_empty:
        return self._complete("scheduler empty")
    
    return self.to_snapshot()
```
