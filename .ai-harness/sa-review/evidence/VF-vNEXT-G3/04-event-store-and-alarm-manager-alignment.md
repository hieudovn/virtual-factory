# VF-vNEXT-G3 · Evidence 04 — EventStore + AlarmManager alignment

## 1. EventStore (`src/virtual_factory/telemetry/event_store.py`)

Adapted from the mutable `list[dict]` skeleton to an append-only typed store:

```python
class EventStore:
    def append(self, fact: EventFact) -> int   # typed; rejects non-EventFact
    def __len__(self) -> int
    def __iter__(self) -> Iterator[EventFact]  # append order
    @property
    def events(self) -> tuple[EventFact, ...]  # read-only snapshot (append order)
    def to_records(self) -> list[dict[str, Any]]
```

- Append-only: `append()` validates the value is an `EventFact` (no arbitrary
  mutable dict truth).
- Deterministic read order = append order; repeated reads stable.
- No mutation/deletion workflow in G3 (no `remove`/`clear`/`pop`/`update`).
- Not a historian/database; Event Timeline / Alarm List, when projected, are
  read-only views over these same facts.
- Backward-compatible read name `events` (now immutable tuple snapshot).
- Zero existing importers of the old dict-typed skeleton in `src/` or `tests/`
  (verified), so the typed change breaks nothing.

## 2. AlarmManager (`src/virtual_factory/telemetry/alarm_manager.py`)

Additive, backward-compatible:

- `AlarmManager(alarms, *, event_store=None)` — new optional injection; owns an
  append-only `EventStore` by default (exposed via `.event_store`).
- `evaluate(state, config, timestamp_s) -> list[SignalValue]` is UNCHANGED in
  signature, return, runtime `industrial_event` writes, threshold semantics and
  `AlarmState` content.
- On alarm occurrence/state changes it appends an immutable `AlarmEventFact`
  (`event_type=alarm.assert` / `alarm.clear`) to `self.event_store`. Smallest
  correct contract (C01-2): a first INACTIVE observation establishes a baseline
  (no fact); a first ACTIVE observation emits an `assert` occurrence fact (so a
  later clear is never an orphan); subsequent active<->inactive transitions
  emit assert/clear; stable active/inactive emits no duplicate facts.
- `AlarmState` remains a mutable DERIVED projection (current active/severity/
  message/last_value/time). Updating it never mutates stored facts.
- Emitted facts carry no fabricated G1/G2/PIM identity (legacy continuous
  manager supplies no workspace/provenance).

## 3. Runtime stays the sole mutable truth

- `AlarmManager.evaluate` continues to write the current alarm output
  (`industrial_event` `SignalValue`) into runtime `RuntimeState`; Event facts
  are downstream and never feed back into runtime truth.
- Existing alarm/telemetry behavior preserved: `test_alarm_manager.py` 6 tests
  unchanged and green.

## 4. Proofs

- `tests/test_event_store.py`: typed append accepted; dict append rejected;
  append order deterministic; no mutation/deletion API; events snapshot
  read-only; stored fact cannot be retroactively changed; to_records stable.
- `tests/test_alarm_event_facts.py`: legacy single-evaluation behavior;
  baseline emits no fact; activation+clear transitions emit assert/clear facts;
  stable condition emits none; AlarmState is derived and never mutates facts;
  runtime state authoritative; emitted facts fabricate no identity.
