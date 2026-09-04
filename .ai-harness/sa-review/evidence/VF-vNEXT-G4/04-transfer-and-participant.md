# VF-vNEXT-G4 · Evidence 04 — Immutable staged transfer + participant seam

## 1. BoundaryTransfer (`composition/transfer.py`)

```python
@dataclass(frozen=True, slots=True)
class BoundaryTransfer:
    transfer_id; source: PortRef; target: PortRef; binding_id; window_id
    simulation_time_s; workspace_id
    run_id=None
    payload: Mapping = {}   # DEEP-FROZEN, JSON-compatible
    def to_dict(self) -> dict  # deterministic
```

- Detached/immutable: payload deep-frozen at construction (mappings →
  MappingProxyType, lists → tuple, JSON-compatible scalars only). Callables and
  arbitrary runtime objects are rejected.
- No live reference to another runtime's mutable state: a producer's later
  mutation of its source dict does not change the staged transfer; a consumer
  cannot mutate the producer state through the payload.
- Identity/authority fail-closed: both endpoint scopes must be in the transfer's
  `workspace_id`; `run_id` optional (carried, never fabricated). No PIM canonical
  id.

## 2. ExecutableParticipant (`composition/participant.py`)

```python
class ExecutableParticipant(Protocol):
    scope_path: StructuralPath
    current_time_s: float
    def advance_to(target_time_s) -> tuple[BoundaryTransfer, ...]
    def commit_transfers(inbound: Sequence[BoundaryTransfer]) -> None
```

- Mechanism-neutral: does NOT imply one engine per scope, identical internal dt,
  identical scheduler, or that `SimulationEngineProtocol.step()` is the only
  mechanism.
- `advance_to` lands local time at the requested boundary using the participant's
  own cadence; moving time backward is forbidden.
- Staged outbound transfers are returned detached; inbound committed later only
  through the declared consumer boundary interface.

## 3. Proofs

- `tests/test_composition_transfer.py`: payload detached from producer mutation;
  payload immutable; fields frozen; callables/runtime objects rejected; workspace
  identity fail-closed; deterministic + plain JSON serialization; no PIM
  canonical.
- `tests/test_composition_coordinator.py`: participant protocol exercised by a
  generic fixed-substep / event-cadence test participant.
