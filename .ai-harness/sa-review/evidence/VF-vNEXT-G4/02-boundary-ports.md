# VF-vNEXT-G4 · Evidence 02 — Typed boundary ports

`src/virtual_factory/composition/ports.py`.

## API

```python
class PortDirection(str, Enum): IN = "in"; OUT = "out"
class PortCategory(str, Enum):
    MATERIAL = "material"          # physical flow
    UTILITY = "utility"            # energy flow
    INFORMATION = "information"    # observation flow
    COORDINATION = "coordination"  # event flow

@dataclass(frozen=True, slots=True)
class PortRef:   owner_scope: StructuralPath; port_id: str   # as_string() = "scope#port"

@dataclass(frozen=True, slots=True)
class BoundaryPort: ref; direction; category; unit=None; descriptor=None

class PortRegistry:  # fail-closed on duplicate port identity; deterministic
def check_port_compatibility(source, target) -> None   # fail-closed rules
```

## Frozen semantics

- Stable port identity within owning structural scope; full `PortRef` (scope path
  + port id) is authoritative; `port_id` unique within the owning scope.
- Direction explicit `in`/`out` — no ambiguous `inout` in the G4 baseline.
- Category is a frozen cross-scope flow; optional `unit`/`descriptor` are plain
  compatibility tags, NEVER PIM semantic authority.
- Port belongs to a Scope (a `PortRef` at the Workspace root is rejected).
- `check_port_compatibility`: source must be `out`, target must be `in`;
  categories must match; both-present unit must match (absent allowed, never
  fabricated); both-present descriptor must match.
- Port identity is VF structural/runtime boundary identity, not PIM canonical.

## Proofs (`tests/test_composition_ports.py`)

- canonical identity + no `canonical_signal_id`;
- workspace-root port rejected; empty/`#` port id rejected;
- duplicate port identity fail-closed; missing port fail-closed;
- out→in valid; in→in and out→out invalid; category/unit/descriptor mismatch
  fail-closed; absent unit allowed (not fabricated);
- registry order deterministic.
