# VF-vNEXT-G2 · Evidence 02 — Generic runtime context (RunContextV2) + invariants

## 1. API

`src/virtual_factory/provenance/context.py`:

```python
@dataclass(frozen=True, slots=True)
class RunContextV2:
    workspace_id: str                         # G1 Workspace identity (required)
    run_id: str                               # one simulation execution (required)
    scope_path: StructuralPath | None = None  # owning/effective executable scope
    scenario_id: str | None = None
    scenario_version: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    profile: str | None = None                # informational execution/profile descriptor
    random_seed: int | None = None
    environment: str | None = None
    source_run_id: str | None = None          # lineage metadata (no orchestration)
    def to_dict(self) -> dict  # deterministic key-stable serialization
```

## 2. Invariants (frozen)

| # | Invariant | Enforcement |
|---|---|---|
| C1 | Immutable (frozen dataclass) | `frozen=True, slots=True` |
| C2 | Deterministic, key-stable serialization | `to_dict()` fixed key order |
| C3 | `workspace_id` / `run_id` required non-empty | `__post_init__` |
| C4 | Optional ids non-empty when present | `__post_init__` |
| C5 | `scope_path` must be a `StructuralPath` | type check |
| C6 | `random_seed` int (not bool) and non-negative when present | `__post_init__` |
| C7 | `profile` is informational — NOT engine-cardinality authority; any mechanism-neutral value accepted (continuous/discrete/batch/hybrid share the same contract) | by design + tests |
| C8 | `source_run_id` lineage is metadata only — no replay/reset orchestration | by design + tests |
| C9 | No PIM canonical id field exists (never fabricated) | no such attribute |

## 3. Identity separation (proof)

`workspace_id`, `scope_path` (full `StructuralPath`), `run_id`, `scenario_id`,
`model_id`, and `profile` are distinct fields with distinct values — never
collapsed/aliased into one string. The generic context has no
`canonical_signal_id`/`canonical_object_id` field (PIM identity is read-only and
absent in G2).

## 4. Mechanism neutrality

Continuous (`profile="continuous_process"`), discrete
(`profile="discrete_manufacturing"`), batch, and composed/hybrid all construct
the SAME `RunContextV2` type. There is no `1 executable scope = 1 engine`
assumption and no `engine_kind` authority (ARCH-06 C01). `profile` maps from the
PH00 `runtime.engine` compatibility descriptor when present.
