# VF-vNEXT-G3 · Evidence 05 — Observation context/provenance seam

## 1. Decision (Issue #48 A + F)

Existing `ObservationEnvelope` / `ObservationService` are consumer-neutral,
immutable-downstream-fact, and heavily tested — they are preserved UNCHANGED.
The G1/G2 alignment is a small additive seam module
`src/virtual_factory/observation/alignment.py` that carries workspace identity,
structural scope path and G2 provenance onto an observation ONLY when explicitly
supplied.

## 2. API

```python
@dataclass(frozen=True, slots=True)
class ObservationStructuralContext:
    workspace_id: str
    scope_path: StructuralPath | None = None
    run_id: str | None = None
    provenance: ProvenanceV2 | None = None

def carry_structural_context(
    envelope: ObservationEnvelope,
    context: ObservationStructuralContext | None,
) -> ObservationEnvelope
```

- `context is None` → returns the SAME envelope unchanged (legacy flow: nothing
  fabricated, nothing mutated).
- otherwise returns a NEW envelope (input never mutated) whose read-only
  `context` mapping carries reserved keys: `vf.workspace_id`, `vf.scope_path`
  (canonical string), `vf.run_id`, `vf.provenance` (canonical JSON string of the
  G2 `ProvenanceV2` serialized dict — immutable, C04).

## 2b. Run-identity coherence (C01-1, fail-closed)

- when `context.run_id` is present it MUST equal `envelope.run_id`;
- when `context.provenance` is present, `provenance.run_id` MUST equal
  `envelope.run_id` (so if both are present all three agree);
- a pre-existing reserved `vf.*` key may only be repeated with the SAME value;
  a conflicting value fails closed (never silently overwritten).

## 3. Non-fabrication + fail-closed

- Values are carried only from an explicit context; there is no defaulting.
- `ObservationStructuralContext` validates: non-empty `workspace_id`;
  `scope_path.workspace_id == workspace_id`; `provenance.workspace_id ==
  workspace_id` when both present; non-empty `run_id` when present.
- Existing observation identity (run_id, model_id, idempotency_key,
  source/subject, quality, schema_version) is never collapsed or replaced.
- No PIM canonical identity / evidence maturity fabricated.
- `vf.provenance` is validated as a full G2 `ProvenanceV2` serialization
  (rehydrated through the G2 enums/invariants; invalid truth labels / malformed
  / missing / extra fields fail closed) and carried as an immutable canonical
  JSON string, so a completed Observation's provenance cannot be mutated
  afterwards (C04).

## 4. Relationship freeze (F)

- Observation = downstream fact/projection from runtime truth (unchanged).
- Event = occurrence/activity fact (evidence 02).
- Alarm is Event specialization (evidence 03).
- Some events may reference/produce observations later; neither Observation nor
  Event becomes mutable runtime authority.

## 5. Proofs (`tests/test_observation_alignment.py`)

- legacy flow unchanged without context (same envelope, no `vf.*` keys);
- envelope immutable (frozen);
- explicit structural context carried into a NEW envelope; original untouched;
  existing identity not collapsed;
- fail-closed on workspace/scope and workspace/provenance mismatch; empty
  workspace rejected;
- carried provenance is a faithful, valid ProvenanceV2 serialization with
  `data_status=synthetic`, no canonical/evidence keys;
- no fabrication when scope/provenance absent;
- C03/C04: full pre-existing reserved vf.* state validation matrix (evidence 10)
  and provenance lifecycle immutability/validation (evidence 11).
