# 03 — Event Model & Alarm Specialization (Issue #42 §C, §D)

## 3.1 Event = runtime/activity fact

An Event is an immutable runtime/activity fact with conceptual fields:

| Field | Meaning |
|---|---|
| event identity | unique event id (deterministic idempotency where applicable) |
| source structural identity | `scope_id` / object id that produced it |
| run / scope context | `run_id` / scope path |
| event type / category | e.g. process event, quality event, lifecycle event |
| occurrence simulation / coordination time | `simulation_time_s` / coordination point |
| severity / status | where applicable |
| payload / reference | reference to an observation or domain context (not a copy of truth) |
| provenance | origin/run/scope provenance (evidence 06) |

**Immutable fact vs mutable workflow state:** the event fact is immutable
(append-style, like `ScheduledEvent` / `ObservationEnvelope`). Any
acknowledgement/status workflow state, if introduced later, is a **separate,
lower-authority projection layer** — not a mutation of the underlying event
fact. No full workflow engine is designed here.

## 3.2 Alarm ⊂ Event (frozen)

**`Alarm` is a specialization of `Event`, not a competing parallel truth model.**

- Repo precedent: `maintenance/event_generator.py` `AlarmEvent(MaintenanceEvent)`
  with `event_type=ALARM` — an alarm is already modeled as an event subtype.
- `core/schema.py` `AlarmConfig` defines an alarm as **derived from a
  measured/industrial signal** (validated `source_signal` link) — alarms are a
  projection of signal truth, not an independent store.
- `telemetry/alarm_manager.py` evaluates alarm configs against signal state →
  alarm samples (a projection).

**What makes an Event an Alarm (conceptual):** an event that asserts a
crossed-threshold / out-of-normal / attention-required condition over a signal
or domain state, carrying an alarm identity + active/clear/acknowledged status.

## 3.3 Alarm lifecycle vs underlying event fact

- The underlying **event fact** (e.g. "signal X crossed threshold at time T") is
  immutable and historical.
- **Alarm status** (active / acknowledged / cleared) is a contract-level
  projection/lifecycle over that fact; acknowledging or clearing an alarm does
  **not** mutate or remove the historical event fact.
- **Alarm List is a projection** over the event model, not a duplicate UI-owned
  alarm store. Event Timeline and Alarm List are two projections of the same
  event facts.

> VF does **not** import real-plant control/alarm-management authority unless
> explicitly simulation-scoped (non-decision).

## 3.4 Anti-drift checks

- Event and Alarm as independent stores → prevented (Alarm ⊂ Event).
- Alarm lifecycle mutating/removing the historical event fact → prevented
  (fact immutable; status is a projection).
- Duplicate UI-owned alarm store → prevented (Alarm List is a projection).
