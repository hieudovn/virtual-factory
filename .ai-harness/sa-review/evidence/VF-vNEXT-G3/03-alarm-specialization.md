# VF-vNEXT-G3 · Evidence 03 — Alarm ⊂ Event specialization

## 1. Model

`AlarmEventFact(EventFact)` — a real subtype of the platform `EventFact`, not a
second authoritative entity:

```python
@dataclass(frozen=True, slots=True)
class AlarmEventFact(EventFact):
    alarm_id: str = ""                 # alarm dimension (NOT a duplicate event id)
    alarm_kind: str = ""               # high | low | bad_quality | equals | not_equals
    transition: str = "assert"         # assert | clear  (occurrence classification)
    threshold: float | int | str | bool | None = None
    message: str | None = None
    def to_dict(self): ...             # base dict + nested "alarm" metadata block
```

- Category is enforced to be `EventCategory.ALARM`.
- Every emitted alarm fact IS an `EventFact` (`isinstance(fact, EventFact)`
  holds), so an alarm fact can be stored/read through the generic Event seam.
- Alarm-specific metadata (`alarm_id`, `alarm_kind`, `transition`, `threshold`,
  `message`) rides beside the shared event identity — `alarm_id` is a dimension
  of the fact, never a parallel event-id authority (`alarm_id != event_id`).
- Mutable current alarm condition/state is the derived projection
  `AlarmManager.states` (`AlarmState`) and never mutates the historical fact.

## 2. Alarm occurrence vs alarm condition/state (ARCH-03 C01)

| Tier | Type | Nature |
|---|---|---|
| Alarm Event / occurrence | `AlarmEventFact` | immutable historical fact (assert/clear occurrence) |
| Alarm Condition/State | `AlarmState` (AlarmManager) | mutable DERIVED projection of the current runtime condition |

## 3. Proofs

- `tests/test_event_fact.py`: `test_alarm_fact_is_event_specialization`
  (`isinstance(fact, EventFact)` and `category is ALARM`);
  `test_alarm_fact_requires_alarm_metadata` (empty alarm_id/alarm_kind or
  invalid transition fails closed); `test_alarm_fact_category_must_be_alarm`;
  `test_alarm_fact_serialization_is_deterministic` (nested `alarm` block;
  `alarm_id != event_id`).
- `tests/test_alarm_event_facts.py`: activation/clear transitions produce
  `AlarmEventFact`s; stable condition emits no duplicates; `AlarmState` updates
  never change stored facts; runtime truth stays authoritative (evidence 04).
