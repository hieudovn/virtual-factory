# SA REVIEW INBOX

Task: VF-vNEXT-G12A
Status: READY FOR SA REVIEW (Generic Reference Connectivity Graph Foundation — inert reference graph layer)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G11 complete; Issue #57 superseded)
Prerequisite: Issue #56 (G11) accepted; Issue #57 BLOCKED -> CLOSED not_planned; Issue #58 (G12A) current

Gate type:
IMPLEMENTATION gate — Generic Reference Connectivity Graph Foundation (G12A), per Issue #58.
Inert, generic, deterministic reference graph ONLY. No runtime, ports, coordinator, or SH-WTP.

Architecture baseline:
G1-G11 contracts authoritative; G11 final head = 90019909d22edf966a30a5b94b0356e892defc83 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Frozen architecture (G12A implements only layer 2):
PIM -> ReferenceConnectivityGraph -> explicit later projection/mapping ->
VF Boundary Contracts/Ports -> G4 CompositionGraph -> Coordinator/Runtime

Implemented (additive, generic):
- src/virtual_factory/connectivity/reference_graph.py + __init__.py:
  * ReferenceEndpoint(authority, entity_id, entity_kind=None) — generic external
    semantic node identity; no StructuralPath; external ids never renamed;
  * ReferenceEdge(edge_id, source, target, relation_type, evidence_ref,
    confidence/status/gaps optional, runtime_effect="none" enforced) — immutable, inert;
  * ReferenceConnectivityGraph — deterministic fail-closed: fan-out/fan-in/
    many-to-many/cycles/non-Scope endpoints; duplicate edge id + duplicate exact
    logical relation (source,target,relation_type) rejected; order-independent
    enumeration + deterministic serialize().
- tests/test_vnext_g12a_reference_graph.py (26 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G12A gate context + g12a group)

Frozen distinctions preserved:
- Reference graph completely separate from G1 containment (no edge inferred from ancestry).
- No BoundaryPort/PortDirection/PortCategory/PortRegistry/coordinator/run-control/state
  propagation; no G4 semantics change; no runtime projection.
- No SH-WTP/PROC-*/PIM relation-name/plant-specific vocabulary hard-coding; no universal
  relation-class enum.
- runtime_effect = none on every edge (enforced at construction).

Regression (post-commit, clean tree): G12A 26 passed; full suite 2053 passed; complete
canonical vNext baseline PASS (g1..g11 + g12a + full_suite + compile/static/changed-files/
preflight).

G12A started: YES (completed; READY FOR SA REVIEW)
G12B started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G12A.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G12A/01-reference-graph-foundation.md
