# VF-vNEXT-G3 · Evidence 02 — Typed immutable Event fact model

## 1. API (`src/virtual_factory/telemetry/event_fact.py`)

```python
class EventCategory(str, Enum):
    PROCESS = "process"
    ACTIVITY = "activity"
    QUALITY = "quality"
    LIFECYCLE = "lifecycle"
    ALARM = "alarm"          # Alarm ⊂ Event

@dataclass(frozen=True, slots=True)
class EventFact:
    event_id: str                       # stable event identity
    event_type: str                     # occurrence classification at creation
    category: EventCategory
    simulation_time_s: float            # occurrence (simulation) time
    run_id: str | None = None
    workspace_id: str | None = None     # G1 identity only when explicitly supplied
    scope_path: StructuralPath | None = None   # G1 structural scope path (optional)
    source: str | None = None
    severity: str | None = None         # occurrence classification (not workflow status)
    status: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)  # deep-frozen
    correlation_id: str | None = None
    causation_id: str | None = None
    provenance: ProvenanceV2 | None = None   # G2 reference/value where appropriate
    def to_dict(self) -> dict[str, Any]     # deterministic, key-stable
```

## 2. Invariants

- Frozen (slots) dataclass; field reassignment raises `FrozenInstanceError`.
- `payload` is deep-frozen via a recursive `_freeze` (mappings → MappingProxyType,
  lists → tuple, JSON-compatible scalars only; callables/non-finite floats
  rejected). No retroactive dict mutation is possible.
- `event_id`/`event_type` non-empty; `category` must be an `EventCategory`;
  `simulation_time_s` numeric `>= 0` (bool rejected).
- Workspace/scope consistency fail-closed: if both present,
  `scope_path.workspace_id == workspace_id`, and
  `provenance.workspace_id == workspace_id` when workspace is present.
- `to_dict()` deterministic key-stable serialization; payload/provenance
  serialized as plain JSON-compatible structures.

## 3. No fabrication

- No PIM `canonical_signal_id` field, no evidence-maturity field. Serialized dict
  contains no `canonical_signal_id` / `evidence` keys.
- `workspace_id`/`scope_path`/`run_id`/`provenance` are optional; absent unless
  explicitly supplied (legacy/alarm-manager facts carry none).

## 4. Proofs

- `tests/test_event_fact.py`: immutability; deep-frozen payload; deterministic
  serialization + stable key order; missing/invalid identity fails closed;
  category enum required; invalid time fails closed; workspace/scope mismatch
  fails closed; provenance carried without canonical/evidence; provenance
  workspace mismatch fails closed; AlarmEventFact proofs (evidence 03).
