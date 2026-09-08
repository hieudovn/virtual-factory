# SA REVIEW INBOX

Task: VF-vNEXT-G14A
Status: READY FOR SA REVIEW (SH-WTP T106→T108 Runtime Projection Contract — explicit inert F01 projection)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G13-C01 complete)
Prerequisite: Issue #63 (G13B) accepted; Issue #64 (G14A) current

Gate type:
IMPLEMENTATION gate — SH-WTP T106→T108 Runtime Projection Contract (G14A), per Issue #64.
Explicit inert projection ONLY. No execution/federation, no F02-F07/T110, no generic FLOWS_TO auto-projection.

Architecture baseline:
G1-G13-C01 contracts authoritative; G13B final head = 2cea59f8fbb7ce974d4b9404469c085d98cdeca6 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- exactly one PIM relationship REL-SHW-F01 (FLOWS_TO, DocumentConfirmed):
  PROC-SHW-L1-T106-OUT-FLOW -> PROC-SHW-L1-T108-IN-FLOW
- VF StructuralPaths shwtp/line1/l1_t106 -> shwtp/line1/l1_t108

Implemented (additive, isolated):
- src/virtual_factory/shwtp/projection.py (+ __init__ exports):
  * frozen F01 pins; fail-closed cross-check against accepted G12B connectivity slice;
  * exactly 2 BoundaryPorts (T106 OUT/MATERIAL/m3/s/volumetric_flow, T108 IN/MATERIAL/m3/s/volumetric_flow);
  * check_port_compatibility enforced; exactly 1 CompositionBinding; inert CompositionGraph;
  * ProjectionRecord (frozen) + ShwtpF01Projection.serialize() deterministic;
  * VF-local PortRefs only (never PIM canonical ids).
- tests/test_vnext_g14a_projection.py (20 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G14A gate context + g14a_f01_projection group)

Frozen boundaries preserved:
- Only F01; F02-F07 not projected; T110 absent/blocked.
- T106 runtime (G13B 19 green) and T108 runtime (G13 28 green) NOT modified; no runtime
  mutation on construct/inspect.
- No coordinator/run-control execution, no value transfer, no shared clock, no federation;
  G12A/B inert; G4 semantics unchanged; PIM unchanged.
- vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
  no workspace/container execution, no G14B.

Regression (post-commit, clean tree): G14A 20 passed; full suite 2160 passed;
complete canonical vNext baseline PASS (g1..g13b + g14a + full_suite + compile/static/changed-files/preflight).

G14A started: YES (completed; READY FOR SA REVIEW)
G14B started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G14A.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G14A/01-f01-projection-contract.md
