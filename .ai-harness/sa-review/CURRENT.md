# SA REVIEW INBOX

Task: VF-vNEXT-G23
Status: READY FOR SA REVIEW (Multi-Workspace Runtime Selection)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G22 complete)
Prerequisite: Issue #73 (G22) accepted; Issue #74 (G23) current

Gate type:
IMPLEMENTATION gate — Multi-Workspace Runtime Selection, per Issue #74.
Additive generic Workspace runtime registry/selector over TIPA + shwtp G22
sessions. Backend/platform selection only; no UI yet.

Base:
G22 head = 1c076525c62ab5c12e98fe970e035b4921cb62a0
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive, isolated):
- src/virtual_factory/runcontrol/registry.py (WorkspaceRuntimeRegistry,
  WorkspaceRuntimeInfo, WorkspaceRegistryError; domain-agnostic, no SH-WTP ref)
- tests/test_vnext_g23_registry.py (15 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G23 gate context +
  g23_workspace_registry group)

Frozen boundaries preserved:
G22 session semantics; G21/G20/G19/G18/G14/G15; TIPA ASSY; runcontrol G7
boundary. No UI, no gateway routing, no MES/PIM change, no G4 redesign, no
domain semantics change, no T110/Line2.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: G23 15 passed; full suite 2428 passed; complete canonical vNext
baseline PASS (see report).

G23 started: YES (completed; READY FOR SA REVIEW)
G24 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G23.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G23/01-workspace-registry.md
