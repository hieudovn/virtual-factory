# VF-vNEXT-G2 · Evidence 03 — Provenance v2 envelope + truth labels

## 1. API

`src/virtual_factory/provenance/envelope.py`:

```python
@dataclass(frozen=True, slots=True)
class ProvenanceV2:
    workspace_id: str
    run_id: str
    scope_path: StructuralPath | None = None
    scenario_id: str | None = None
    origin_kind: OriginKind = OriginKind.SIMULATION
    fidelity: Fidelity | None = None
    data_status: DataStatus | None = None
    semantic_contract_version: str | None = None
    semantic_contract_sha: str | None = None
    evidence_note: str | None = None
    simulation_time_s: float | None = None
    step: int | None = None
    def to_dict(self) -> dict  # deterministic serialization
```

C01 note: `runtime_signal_id` is NOT a frame-level field (one frame-level value
would be stamped on every signal). It is derived per signal at record
construction in `ProvenancedFrame` (evidence 05 / 08).

`scope_path` (when present) MUST root in `workspace_id`:
`scope_path.workspace_id == workspace_id`, else `ProvenanceError` (C01-1).

## 2. Simulation truth labels (fail-closed)

| Rule | Enforcement |
|---|---|
| `origin_kind` is always `simulation` | enum + `__post_init__` rejects non-simulation |
| `data_status` ∈ {`synthetic`, `simulated_ground_truth`} only | enum + `__post_init__` |
| `fidelity` ∈ {`logical_only`, `synthetic_reference`, `first_order`} | enum |
| plain `measured`/`ground_truth` rejected for VF output | enum excludes them |
| `simulation_time_s` non-negative; `step` non-negative int | `__post_init__` |

## 3. Identity separation

- `runtime_signal_id` is a VF-internal execution key (e.g.
  `W/UNIT/FT-101`) — explicitly DISTINCT from the PIM-owned
  `canonical_signal_id`. It is per-signal: derived at record construction in
  `ProvenancedFrame` (never a single frame-level value; C01-2).
- `ProvenanceV2` has NO `canonical_signal_id` field and never serializes one;
  VF never fabricates PIM canonical identity (B1).
- `scope_path.workspace_id` must equal `workspace_id` when `scope_path` is
  present (C01-1).

## 4. Semantic pins (opaque, immutable — no PIM validation)

`semantic_contract_version` / `semantic_contract_sha` are optional, immutable,
and serialized. G2 does **not** validate them against PIM (G9 owns binding
validation and canonical-id resolution). They are passed through as opaque
strings only.

## 5. Immutability + determinism

Frozen dataclass; `to_dict()` has a fixed key order and is byte-identical across
calls for equal inputs.
