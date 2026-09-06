# SA REVIEW INBOX

Task: VF-vNEXT-G11
Status: READY FOR SA REVIEW (SH-WTP Structural Workspace Construction — structural construction gate)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G10 complete)
Prerequisite: Issue #55 (G10) accepted; Issue #56 (G11) current

Gate type:
IMPLEMENTATION gate — SH-WTP Structural Workspace Construction (G11), per Issue #56.
Structural construction ONLY. No runtime, connectivity, physics/control, or PIM write.

Architecture baseline:
G1-G10 contracts authoritative; G10 final head = 41017af82f9307fa12d115c7d4c67fc86ea38af4 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Construction source (VF-side authoritative):
- configs/vnext/shwtp/shwtp_readiness_scope.json (frozen G10 plan; read-only)
- Generic G1 Workspace/Scope/Object foundation reused (virtual_factory.workspace)
- External PIM pinned: hieudovn/plant-intelligence-model; SHW-PIM-VF-EXPORT-v0.1 v0.1 SHW-PH03-v0.1;
  semantic SHA f23f3c46…; artifact hash ea3361a4…; NOT_AUTHORIZED

Implemented (additive, structural only):
- src/virtual_factory/shwtp/structural.py + __init__.py:
  * deterministic single Workspace root `shwtp` (plant canonical PLANT-SHW as reference metadata);
  * containment tree materialized from G10/PIM skeleton: 8 top-level scopes (7 areas +
    plant-level dist_p108) + 20 unit scopes = 28 scope nodes == G10 inventory minus PLANT;
  * roles -> ScopeMode: container/object/reference -> CONTAINER_ONLY; T106/T108/T110
    executable_candidate -> EXECUTABLE_CAPABLE classification only (zero runtime);
  * VF local ids (lowercase aliases) distinct from canonical; canonical refs read-only metadata;
  * per-node metadata preserved exactly from G10 (role/fidelity/evidence/confidence/gaps/note);
  * deterministic serialize() structural inspection; fail-closed completeness checks.
- tests/test_vnext_g11_shwtp.py (22 invariant tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G11 gate context + g11_shwtp_structural group)

Frozen distinctions preserved:
- PIM = canonical authority (read-only); VF local identity/StructuralPath local; canonical never renamed.
- Containment tree != connectivity graph; no flow inferred from containment.
- structural_construction = AUTHORIZED_IN_G11; synthetic_reference_execution =
  PENDING_LATER_PIM_REVIEW; site_authorized_execution = NOT_AUTHORIZED; vf_runtime_authorization
  NOT_AUTHORIZED unchanged.
- No engine/bridge/coordinator/run-control participant/solver/behavior/state advancement on SH-WTP.
- No SH-WTP reference in virtual_factory.runcontrol (no G7 participant).
- TIPA/continuous behavior unchanged; no G12 work.

Regression (post-commit, clean tree): G11 22 passed; full suite 2027 passed; complete canonical
vNext baseline PASS (g1..g11 + full_suite + compile/static/changed-files/preflight).

G11 started: YES (completed; READY FOR SA REVIEW)
G12 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G11.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G11/01-structural-workspace-construction.md
