# VF-vNEXT-G4 · Evidence 03 — Composition graph

`src/virtual_factory/composition/graph.py`.

## API

```python
@dataclass(frozen=True, slots=True)
class CompositionBinding: edge_id; source: PortRef; target: PortRef

class CompositionGraph:
    def __init__(self, workspace_id, bindings=(), ports=())
    bindings / edges          # deterministic canonical order
    nodes()                   # deterministic endpoint order
    has_binding(source, target)
    outbound(source) / inbound(target)
    registry                  # PortRegistry
```

## Frozen semantics

- Directed declared bindings with stable `edge_id`; endpoints resolve through
  authoritative G1 `StructuralPath`/`PortRef`.
- Cycles ARE allowed — no DAG requirement, acyclicity never used as a
  correctness shortcut.
- Deterministic enumeration independent of declaration order (bindings sorted by
  `(source, target, edge_id)`; nodes sorted by canonical endpoint string).
- Dangling endpoint refs fail closed (endpoint must be a declared boundary port).
- Duplicate `edge_id` and duplicate logical binding `(source, target)` fail
  closed.
- Cross-workspace binding fails closed (no workspace/domain-name hard-coding).
- Disconnected nodes allowed; fan-out deterministic.

## Proofs (`tests/test_composition_graph.py`)

- declaration-order permutations give identical binding order;
- cycles allowed (two-node cycle builds without error);
- dangling endpoint, duplicate edge id, duplicate logical binding, cross-workspace
  endpoint all fail closed;
- deterministic `nodes()`; deterministic fan-out; disconnected nodes allowed.
