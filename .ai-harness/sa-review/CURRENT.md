# SA REVIEW INBOX

Task: VF-vNEXT-G13-C01
Status: READY FOR SA REVIEW (SH-WTP T108 Standalone Synthetic First-Order Runtime — C01 identity/provenance closure)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G12C complete)
Prerequisite: Issue #60 (G12C) accepted; Issue #61 (G13) current

Gate type:
IMPLEMENTATION gate — SH-WTP T108 Standalone Synthetic First-Order Runtime (G13), per Issue #61.
First authorized executable slice ONLY (T108). No T106/T110, no G4, no federation, no PIM change.

Architecture baseline:
G1-G12C contracts authoritative; G12C-C01 final head = 63c0060590a6493161bb4c47ae92161822fde58f (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- canonical UNIT-SHW-L1-T108 (read-only PIM reference); VF StructuralPath shwtp/line1/l1_t108
- standalone synthetic/reference first-order tank accumulator

Implemented (additive, isolated):
- src/virtual_factory/shwtp/runtime.py (+ __init__ exports):
  * T108Config(capacity_m3, tank_area_m2, initial_volume_m3, dt_s) — explicit, no hidden defaults;
  * T108TankRuntime — isolated attempt; exact-target validation (only shwtp/line1/l1_t108;
    workspace/container targets rejected); deterministic step (explicit overflow + empty-tank
    saturation + mass-balance guard); reset; detached immutable snapshot; attempt isolation;
  * provenance via reused G2 RunContextV2/ProvenanceV2: OriginKind.SIMULATION + DataStatus.SYNTHETIC
    + Fidelity.FIRST_ORDER; no measured/site labels; optional G9 semantic pins threaded when supplied.
- tests/test_vnext_g13_t108.py (28 tests; C01: locked T108 canonical ref + snapshot provenance regressions)
- .ai-harness/regression/vnext_baseline_manifest.json (G13 gate context + g13 group)

Frozen boundaries preserved:
- Only T108 implemented; T106 later/optional; T110 blocked; vf_runtime_authorization NOT_AUTHORIZED;
  site_authorized_execution NOT_AUTHORIZED.
- No FLOWS_TO/DISCHARGES_TO/CONNECTED_TO -> BoundaryPort/CompositionBinding/runtime projection;
  G12A/B reference graph inert.
- No modification of equipment.process_dynamics.py / legacy continuous engine; no G7 redesign;
  no new global engine; no G4 semantics change.

Regression (post-commit, clean tree): G13 28 passed; full suite 2121 passed; complete canonical
vNext baseline PASS (g1..g13 + full_suite + compile/static/changed-files/preflight).

C01 (Issue #62): locked T108 canonical reference (removed caller override); T108State/snapshot
carries truthful G2 provenance (simulation/synthetic/first_order, time+step); 4 focused tests added.

G13 started: YES (completed; G13-C01 READY FOR SA REVIEW)
G14 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G13.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G13/01-t108-runtime.md
.ai-harness/sa-review/evidence/VF-vNEXT-G13/02-c01-identity-provenance.md
