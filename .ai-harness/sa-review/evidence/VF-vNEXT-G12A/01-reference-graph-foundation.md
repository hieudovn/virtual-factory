# VF-vNEXT-G12A — Generic Reference Connectivity Graph Foundation — Evidence

Gate: `VF-vNEXT-G12A` · Generic inert reference graph foundation (no runtime, no ports, no SH-WTP).

## 1. Architecture placement

New package `src/virtual_factory/connectivity/` implements only the
`ReferenceConnectivityGraph` layer of the frozen architecture:

`PIM -> ReferenceConnectivityGraph -> explicit later projection/mapping
 -> VF Boundary Contracts/Ports -> G4 CompositionGraph -> Coordinator/Runtime`

G4 composition, G1 workspace, run-control, semantic, and SH-WTP packages are
untouched (no imports from them in the new module).

## 2. Endpoint identity (generic, external)

`ReferenceEndpoint(authority, entity_id, entity_kind=None)`:
- `authority` = source/authority identity; `entity_id` = external/canonical
  entity id; `entity_kind` = optional descriptive metadata (never a VF runtime
  type). No `StructuralPath` required; external ids are never renamed.
- Fail closed: empty authority/entity_id/entity_kind; the canonical separator
  `::` is forbidden inside any field (reversible `authority::entity_id` form).

## 3. Reference edge (immutable, inert)

`ReferenceEdge(edge_id, source, target, relation_type, evidence_ref,
confidence=None, status=None, gaps=(), runtime_effect="none")`:
- `relation_type` is a free non-empty string (no universal enum).
- `evidence_ref` (provenance) required non-empty.
- `runtime_effect` must be exactly `"none"` — any other value fails closed
  (stronger than a default), so every G12A edge is inert by construction.

## 4. Graph invariants (fail closed, deterministic)

`ReferenceConnectivityGraph(edges)`:
- accepts arbitrary valid endpoints/edges; supports fan-out, fan-in,
  many-to-many, cycles, and endpoints that are not VF Scopes;
- rejects duplicate edge id and duplicate exact logical relation under the
  frozen rule `(source, target, relation_type)` — same endpoints with different
  relation type are allowed;
- deterministic node/edge enumeration and serialization independent of input
  order (edges sorted by `(source, target, relation_type, edge_id)`, endpoints
  sorted by `authority::entity_id`).

## 5. Serialization

`serialize()` returns `schema`, `edge_count`, `runtime_effect`, sorted
`endpoints` (authority/entity_id/entity_kind), and sorted `edges`
(edge_id/source/target/relation_type/evidence_ref/confidence/status/gaps/
runtime_effect). Gaps serialized in sorted order.

## 6. Test evidence

- `tests/test_vnext_g12a_reference_graph.py` — 26 tests PASS.
- Full suite: 2053 passed (2027 prior + 26 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G12A.md`.

## 7. Unchanged

G4 composition semantics, G1 containment, run-control, semantic binding,
SH-WTP structural workspace, runtime authorization, and all plant-specific
vocabulary. No SH-WTP/PROC-*/PIM id hard-coding in the generic module. No G12B.
