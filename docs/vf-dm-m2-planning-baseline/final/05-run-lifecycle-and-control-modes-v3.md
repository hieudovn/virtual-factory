# 05-v3 — Run Lifecycle and Control Modes (Final)

**Date:** 2026-08-05  
**Replaces:** `05-...-v2.md`  
**Corrections:** V2-F01, V2-F05, V2-F06, V2-F07

---

## 1. RunStatus (unchanged)

```python
class RunStatus(enum.Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"      # Controller-managed
    PAUSED = "paused"        # Controller-managed
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
```

---

## 2. ExecutionMode (unchanged)

```python
class ExecutionMode(enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"
```

Controller owns mode; engine owns status.

---

## 3. Bootstrap (C02-01)

```python
def initialize(
    self,
    initial_events: Iterable[ScheduledEvent] = (),
) -> RuntimeSnapshot:
    """Schedule bootstrap events and transition to READY.

    - Bootstrap events are created OUTSIDE the engine.
    - Events must have sequence=None (unscheduled).
    - Engine validates and schedules them via the scheduler.
    - Zero initial events is allowed (empty scheduler).
    - Engine has no TIPA/domain knowledge.
    """
```

**Example usage (in test or M3):**
```python
bootstrap = [
    ScheduledEvent(event_id="boot-1", simulation_time_s=0.0, event_type="init_source"),
]
engine.initialize(initial_events=bootstrap)
```

---

## 4. State Transition Authority (C02-07)

| Status | Who Owns Transition | Method |
|--------|---------------------|--------|
| `CREATED → READY` | Engine | `initialize(initial_events)` |
| `READY → RUNNING` | Engine (requested by Controller) | `_transition_to(RUNNING)` — M2-S04 |
| `RUNNING → PAUSED` | Engine (requested by Controller) | `_transition_to(PAUSED)` — M2-S04 |
| `PAUSED → RUNNING` | Engine (requested by Controller) | `_transition_to(RUNNING)` — M2-S04 |
| `READY → COMPLETED` | Engine | `_complete(reason)` |
| `* → STOPPED` | Engine | `stop(reason)` |
| `* → FAILED` | Engine | `_fail(code, detail)` |

Controller owns `ExecutionMode` and pacing. Controller requests status transitions through validated engine methods (implemented in M2-S04).

---

## 5. Safe-Point Ordering (C02-06)

```
while status == RUNNING:
    # 1. Apply queued commands BEFORE next event
    apply_queued_commands_at_safe_point()

    # 2. Step one event
    snapshot = engine.step_event()

    # 3. Break on completion/failure
    if snapshot.status in (COMPLETED, STOPPED, FAILED):
        # Apply any remaining commands before final broadcast
        apply_queued_commands_at_safe_point()
        broadcast(snapshot)
        break

    # 4. Broadcast committed snapshot
    broadcast(snapshot)

    # 5. Pace
    await asyncio.sleep(pacing_delay)
```

**Why commands before event:** A command accepted during previous dispatch must apply before the next domain event. Prevents command loss when scheduler becomes empty.

---

## 6. Intervention Priority (C02-06)

At the same `simulation_time_s`:

```
1. Currently executing event commits first (already popped)
2. Intervention events (commands converted to events)
3. Ordinary next domain events at that time
4. Scheduler sequence resolves ties within same priority band
```

Intervention priority band is an explicit, documented value (e.g., `priority=10` for commands, `priority=50` for domain events). No epsilon.

---

## 7. Allowed Commands per Status (unchanged)

| Status | Allowed |
|--------|---------|
| `CREATED` | `initialize` |
| `READY` | `step_event`, `auto_run`, `stop` |
| `RUNNING` | `pause`, `stop`, inject* |
| `PAUSED` | `step_event`, `resume`, `stop`, inject* |
| Terminal | `reset` |

---

## 8. Auto Mode (Controller, unchanged)

```
speed_factor: 1.0 (default)
max_events_per_second: 1000
snapshot_broadcast_max_hz: 10
```
