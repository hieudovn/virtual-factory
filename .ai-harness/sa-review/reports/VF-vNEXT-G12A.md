# VF-vNEXT-G12A — Generic Reference Connectivity Graph Foundation — Report

Status: **VF-vNEXT-G12A-C01 — READY FOR SA REVIEW** (generic inert reference graph foundation; C01 endpoint-identity consistency fix applied).

## Objective

Implement the smallest generic, immutable, deterministic Reference Connectivity
Graph foundation — the `ReferenceConnectivityGraph` layer of the frozen
architecture, strictly before any projection to VF Boundary Contracts/Ports/G4.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G12A.json` |
| Reference graph module | `src/virtual_factory/connectivity/` (`reference_graph.py` + `__init__.py`) |
| Invariant tests | `tests/test_vnext_g12a_reference_graph.py` (31 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G12A/01-reference-graph-foundation.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G12A gate context + g12a group) |

## Implementation summary

- `ReferenceEndpoint(authority, entity_id, entity_kind=None)` — generic external
  semantic node reference; frozen identity `(authority, entity_id)` (entity_kind
  excluded from equality/hash); no `StructuralPath`; external ids never renamed.
- `ReferenceEdge(...)` — immutable, provenance-rich, inert edge with
  `runtime_effect="none"` enforced (non-"none" fails closed).
- `ReferenceConnectivityGraph(edges)` — deterministic, fail-closed:
  fan-out/fan-in/many-to-many/cycles/non-Scope endpoints; duplicate edge id and
  duplicate exact logical relation `(source, target, relation_type)` rejected;
  order-independent enumeration; deterministic `serialize()`.
- No BoundaryPort/PortDirection/PortCategory/PortRegistry/coordinator/run-control;
  no G4 semantics change; no containment coupling; no SH-WTP/PROC-*/PIM
  hard-coding; no universal relation-class enum; no runtime projection.

## Regression evidence

- New G12A tests: **31 passed**.
- Full suite: **2058 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No SH-WTP edge materialization; no F01-F07 classification; no PROC-* -> Scope
mapping; no runtime projection; no G4 changes; no G11 containment changes; no
runtime authorization change; no G12B.

## C01 correction (SA 5560719582)

Froze endpoint identity to `(authority, entity_id)`: `entity_kind` is now
`field(compare=False, hash=False)` (descriptive metadata excluded from
equality/hash). Graph construction fails closed when the same endpoint identity
carries conflicting `entity_kind` metadata (missing vs known included).
`inbound()` / `outbound()` / `has_edge()` / duplicate-logical-relation checks
now all follow the frozen identity rule.
