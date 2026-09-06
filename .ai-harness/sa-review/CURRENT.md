# SA REVIEW INBOX

Task: VF-vNEXT-G12B
Status: READY FOR SA REVIEW (SH-WTP PIM Reference Connectivity Materialization — inert reference facts)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G12A complete)
Prerequisite: Issue #58 (G12A) accepted; Issue #59 (G12B) current

Gate type:
IMPLEMENTATION gate — SH-WTP PIM Reference Connectivity Materialization (G12B), per Issue #59.
Inert reference facts ONLY. No PIM change, no runtime projection, no G4 change, no G13.

Architecture baseline:
G1-G12A contracts authoritative; G12A final head = 4d916a3ddeaa1890c637c1db2d51d292434cd059 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Frozen architecture (G12B implements only the first arrow):
PIM semantic relationships -> VF ReferenceConnectivityGraph -> later explicit
interpretation/projection -> Boundary Contracts/Ports -> G4 CompositionGraph -> Runtime

Pinned PIM (repo-first):
- repo hieudovn/plant-intelligence-model @ ec7f1266d4a19e5201b689874a2a7a75a022fc5c
- package SHW-PIM-VF-EXPORT-v0.1 v0.1 (SHW-PH03-v0.1); semantic SHA f23f3c46…; artifact hash ea3361a4…
- model fixture examples/song-hong-wtp/model_fixture/model.yaml

Implemented (additive):
- src/virtual_factory/shwtp/connectivity.py (+ __init__ exports):
  * frozen PIM source pins + frozen PimReferenceRelation slice = exactly F01-F07
    process/connectivity facts (FLOWS_TO/DISCHARGES_TO/CONNECTED_TO verbatim);
  * endpoints = ReferenceEndpoint(authority=hieudovn/plant-intelligence-model,
    entity_id=<canonical>, entity_kind=ProcessConnection) — PROC-* as non-Scope endpoints;
  * F02/F03 preserve REL-006 "known-but-unconstrained" warning; every edge runtime_effect=none;
  * build_shwtp_reference_graph() -> G12A ReferenceConnectivityGraph;
  * ShwtpReferenceConnectivity.serialize() = source summary + deterministic graph serialization.
- tests/test_vnext_g12b_shwtp.py (19 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G12B gate context + g12b group)

Frozen distinctions preserved:
- Raw PIM relation types preserved; NO six-class reclassification; F06/F07 not name-classified.
- No PART_OF/containment-derived edges; no G11 containment change (28 scopes unchanged).
- No BoundaryPort/PortDirection/PortCategory/CompositionBinding/coordinator/run-control/state.
- vf_runtime_authorization NOT_AUTHORIZED; synthetic_reference_execution PENDING_LATER_PIM_REVIEW;
  site_authorized_execution NOT_AUTHORIZED — all unchanged.

Regression (post-commit, clean tree): G12B 19 passed; full suite 2077 passed; complete canonical
vNext baseline PASS (g1..g12b + full_suite + compile/static/changed-files/preflight).

G12B started: YES (completed; READY FOR SA REVIEW)
G13 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G12B.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G12B/01-pim-reference-connectivity.md
