# 05 — Run Lifecycle and Control Modes

**Date:** 2026-08-05

---

## 1. Run State Machine

```
                 ┌─────────┐
         create  │ created │
       ─────────>│         │
                 └────┬────┘
                      │ initialize
                      ▼
                 ┌─────────┐
                 │initialized│
                 └────┬────┘
          ┌───────────┼───────────┐
          │ step      │ auto-run  │
          ▼           ▼           │
     ┌─────────┐ ┌─────────┐     │
     │ stepping│ │ running │     │
     └────┬────┘ └────┬────┘     │
          │           │           │
          │  pause    │  pause    │
          ▼           ▼           │
     ┌─────────────────────┐     │
     │       paused        │◄────┘
     └─────────┬───────────┘
               │ resume
               ▼
          ┌─────────┐
          │ running │ (or stepping)
          └────┬────┘
               │ complete / stop
               ▼
          ┌─────────┐      ┌─────────┐
          │completed│      │ stopped │
          └─────────┘      └─────────┘
                              ▲
                              │ error
                         ┌─────────┐
                         │ failed  │
                         └─────────┘
```

---

## 2. State Semantics

| State | Engine behavior | Allowed commands |
|-------|----------------|-----------------|
| `created` | Engine exists, not initialized | `initialize` |
| `initialized` | Ready to run, scheduler empty | `step`, `auto_run`, `stop` |
| `running` | Auto-advancing event loop | `pause`, `stop` |
| `stepping` | Single-step mode | `step` (next event), `auto_run`, `stop` |
| `paused` | Loop suspended, state preserved | `resume`, `step`, `stop` |
| `completed` | No pending events, terminal | `reset` |
| `stopped` | User-requested termination | `reset` |
| `failed` | Error during execution | `reset` (reinitialize) |

---

## 3. Modes

### 3.1 Manual Step Mode

**Decision: Step-one-event (not step-to-business-event)**

- Each `step()` pops and dispatches exactly one scheduled event.
- Not "step to next business event" — that requires domain knowledge the scheduler should not have.
- Phased refinement: M5 can add `step_to_event_type(type)` as a convenience, but core `step()` is one event.

### 3.2 Auto Mode

| Parameter | Default | Description |
|-----------|---------|-------------|
| Speed factor | 1x | Multiplier for wall-clock pacing |
| Max events/sec | 1000 | Backpressure cap |
| Update frequency | 10 Hz | Snapshot broadcast rate |

**Pacing:** `asyncio.sleep(dt / speed_factor)` between event loop iterations. Snapshot broadcasts at fixed frequency regardless of event rate.

### 3.3 Hybrid Mode

**Decision: Live injection (not pause-then-inject)**

- Commands are accepted while `running`.
- Command is converted to a `ScheduledEvent` and scheduled at `current_time + ε`.
- Deterministic: command event has known `simulation_time_s` and sequence.
- Audit trail: command → event → dispatch → state change — all recorded.

---

## 4. Command Handling

| Command | Valid states | Result |
|---------|-------------|--------|
| `initialize` | `created`, `stopped`, `failed` | State → `initialized` |
| `step` | `initialized`, `stepping`, `paused` | Dispatch one event, return snapshot |
| `auto_run` | `initialized`, `stepping`, `paused` | State → `running`, begin loop |
| `pause` | `running` | State → `paused`, loop suspended |
| `resume` | `paused` | State → `running`, loop resumed |
| `stop` | `initialized`, `running`, `stepping`, `paused` | State → `stopped` |
| `reset` | any terminal state | Reinitialize, State → `initialized` |
| `inject` | `running`, `stepping`, `paused` | Schedule command event at current_time |
| `hold` | `running`, `stepping`, `paused` | Schedule hold event for target node |
| `release` | `running`, `stepping`, `paused` | Schedule release event for target node |

---

## 5. Concurrency

- Single-threaded event loop (asyncio).
- One command at a time per run.
- Simultaneous commands queued and processed in arrival order.
- No distributed locking required for MVP.
