# 05-v2 — Run Lifecycle and Control Modes (Corrected)

**Date:** 2026-08-05  
**Replaces:** `05-run-lifecycle-and-control-modes.md`  
**Corrections:** F-005, F-006

---

## 1. RunStatus (C-005)

```python
class RunStatus(enum.Enum):
    CREATED = "created"           # Engine exists, not initialized
    READY = "ready"               # Initialized, bootstrap events scheduled
    RUNNING = "running"           # Auto loop active (controller-managed)
    PAUSED = "paused"             # Loop suspended, state preserved
    COMPLETED = "completed"       # Scheduler empty, no more events
    STOPPED = "stopped"           # User-requested termination
    FAILED = "failed"             # Error during execution
```

`stepping` is NOT a persistent status. Step is an operation, not a lifecycle state.

---

## 2. ExecutionMode (C-005)

```python
class ExecutionMode(enum.Enum):
    MANUAL = "manual"             # User calls step_event() explicitly
    AUTOMATIC = "automatic"       # Controller runs event loop with pacing
    HYBRID = "hybrid"             # Auto loop + accepted live commands
```

Mode is controller state, not engine state.

---

## 3. State Machine

```
            create
              │
              ▼
         ┌─────────┐
         │ CREATED │
         └────┬────┘
              │ initialize (schedules bootstrap events)
              ▼
         ┌─────────┐
         │  READY  │◄──────────────────────────┐
         └────┬────┘                           │
              │                                │
    ┌─────────┼─────────┐                      │
    │ step    │ auto_run│                      │
    ▼         ▼         │                      │
  (back    RUNNING ─────┤                      │
   to      │  │         │                      │
  READY)   │  │ pause   │                      │
           │  ▼         │                      │
           │ PAUSED ────┘ (resume)             │
           │  │                                │
           │  │ stop          reset            │
           ▼  ▼               │                │
      ┌──────────┐            │                │
      │ STOPPED  │            │                │
      └──────────┘            │                │
                              │                │
      scheduler empty         │                │
           │                  │                │
           ▼                  │                │
      ┌──────────┐            │                │
      │COMPLETED │            │                │
      └──────────┘            │                │
                              │                │
      handler error           │                │
           │                  │                │
           ▼                  │                │
      ┌──────────┐            │                │
      │ FAILED   │────────────┘                │
      └──────────┘                             │
                                               │
      reset (any terminal state) ──────────────┘
```

---

## 4. Bootstrap Events

`initialize()` must schedule initial events that start the simulation. Without bootstrap events, the scheduler is empty and `step_event()` would immediately complete.

Bootstrap is domain-specific and injected via the dispatcher protocol. The engine does not know what bootstrap events are.

---

## 5. Step Semantics

- `step_event()` pops one event from the scheduler.
- Dispatches to handler via `EventDispatcherProtocol`.
- Handler returns `HandlerOutcome` with follow-up events.
- Engine schedules follow-up events.
- Engine increments `snapshot_sequence`.
- Returns `RuntimeSnapshot`.
- Post-step status: `READY` (if events remain) or `COMPLETED` (if scheduler empty).

---

## 6. Allowed Commands per Status

| Status | Allowed Commands |
|--------|-----------------|
| `CREATED` | `initialize` |
| `READY` | `step_event`, `auto_run`, `stop` |
| `RUNNING` | `pause`, `stop`, inject commands* |
| `PAUSED` | `step_event`, `resume`, `stop`, inject commands* |
| `COMPLETED` | `reset` |
| `STOPPED` | `reset` |
| `FAILED` | `reset` |

*Inject commands: `line_in`, `line_out`, `hold`, `release`, `force_fail`, `breakdown`, `clear_breakdown`, `operator_unavailable`, `operator_available` — accepted live, applied at safe point.

---

## 7. Hybrid Intervention (C-006)

**Model: Live acceptance, safe-point application.**

1. Command arrives while `RUNNING`.
2. Controller validates command.
3. Controller assigns server-owned `command_sequence`.
4. Command enters per-run FIFO queue.
5. Between event dispatches (safe point), controller dequeues command.
6. Controller converts command to `ScheduledEvent` at `current_time_s` (exact, no epsilon).
7. Event scheduled with explicit `command_priority` (below normal domain events).
8. Scheduler assigns sequence.
9. Command result recorded: `accepted_simulation_time`, `result_event_id`.

**Determinism note:** Replay requires recording the command log (sequence, accepted time). Not automatically reproducible from seed alone.

---

## 8. Auto Mode (Controller)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `speed_factor` | 1.0 | Multiplier: 2.0 = 2x wall-clock speed |
| `max_events_per_second` | 1000 | Backpressure cap |
| `snapshot_broadcast_max_hz` | 10 | Cap on snapshot publication rate |

Controller loop:
```
while status == RUNNING:
    snapshot = engine.step_event()
    if snapshot.status in (COMPLETED, FAILED):
        break
    broadcast_if_needed(snapshot)
    apply_queued_commands()      # safe point
    await asyncio.sleep(pacing_delay)
```

Pacing: `pacing_delay = dt_simulation / speed_factor`, clamped to minimum 1ms.
