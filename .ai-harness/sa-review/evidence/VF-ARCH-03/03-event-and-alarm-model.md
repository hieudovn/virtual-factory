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
| severity / classification | occurrence/fact classification captured at event creation (NOT mutable workflow/lifecycle status) |
| payload / reference | reference to an observation or domain context (not a copy of truth) |
| provenance | origin/run/scope provenance (evidence 06) |

**Immutable fact vs mutable workflow state (C01):** the event fact is immutable
(append-style, like `ScheduledEvent` / `ObservationEnvelope`). Any
`status`/severity field on the Event is constrained to an **occurrence/fact
classification captured at event creation**. Mutable workflow/lifecycle status
(acknowledgement, active/clear, shelving) belongs to a **separate projection/
state axis**, never inside the immutable Event fact. No full workflow engine is
designed here.

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
or domain state. Distinguish two tiers (C01-1):

- **Alarm Event / Alarm occurrence** — the **immutable historical Event fact**
  (threshold entered, alarm asserted, alarm cleared as an occurrence event).
- **Alarm Condition / Alarm State** — the **mutable derived/projection state**
  over the event stream / runtime condition (active/inactive,
  acknowledged/unacknowledged; shelved if ever added later).

## 3.3 Alarm lifecycle vs underlying event fact

- The **Alarm Event fact** (threshold entered / alarm asserted / alarm cleared)
  is immutable and historical.
- The **Alarm Condition/State** (active/inactive, acknowledged/unacknowledged)
  is a mutable projection over the event stream; acknowledgement/clear workflow
  state must **not** mutate the original Alarm Event fact.
- **Alarm List** may project the current Alarm Condition/State plus historical
  event references; it is **not** an independent truth store. Event Timeline and
  Alarm List are two projections of the same event facts.
- No full alarm workflow engine is designed here.

> VF does **not** import real-plant control/alarm-management authority unless
> explicitly simulation-scoped (non-decision).

## 3.4 Anti-drift checks

- Event and Alarm as independent stores → prevented (Alarm ⊂ Event).
- Alarm lifecycle mutating/removing the historical event fact → prevented
  (fact immutable; status is a projection).
- Duplicate UI-owned alarm store → prevented (Alarm List is a projection).
