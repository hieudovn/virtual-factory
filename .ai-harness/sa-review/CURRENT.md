# SA REVIEW INBOX

Task: VF-vNEXT-G14B
Status: READY FOR SA REVIEW (SH-WTP T106→T108 Explicit Lagged Federation — bounded synthetic/reference evaluation)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G14A complete)
Prerequisite: Issue #64 (G14A) accepted; Issue #65 (G14B) current

Gate type:
IMPLEMENTATION gate — SH-WTP T106→T108 Explicit Lagged Federation (G14B), per Issue #65.
Explicit one-window-lag coupling policy ONLY. No Gauss-Seidel/iterative/multirate, no T110/F02-F07, no plant-wide/workspace/container execution.

Architecture baseline:
G1-G14A contracts authoritative; G14A final head = 22a69e0cf61958d256fb2f61ce38ae0f3e207dca (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- exactly two participants shwtp/line1/l1_t106 + shwtp/line1/l1_t108 via the G14A F01 binding BIND-SHW-F01-T106-OUT-T108-IN
- coupling_policy = explicit_lagged (orchestration policy at the federation layer only)

Implemented (additive, isolated):
- src/virtual_factory/shwtp/federation.py (+ __init__ exports):
  * ShwtpFederationConfig (explicit scenario values, no hidden defaults; unsupported policy fails closed);
  * ShwtpT106Participant (stages one detached F01 BoundaryTransfer per window; rejects inbound);
  * ShwtpT108Participant (advance uses committed previous-boundary inflow + explicit requested outflow, never T106 state; commit validates exact F01 transfer and stores flow for NEXT window);
  * ShwtpFederation (reuses G4 Coordinator + G14A graph + G13B/G13 runtimes; window-preparation seam before run_window; deterministic serialize()).
- tests/test_vnext_g14b_federation.py (55 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G14B gate context + g14b_federation group)

Frozen boundaries preserved:
- T106 runtime (G13B 19 green) and T108 runtime (G13 28 green) NOT modified; provenance preserved (logical_only / first_order).
- G14A projection (20 green) unchanged; G4 Coordinator/participant/transfer semantics unchanged (no G4 file modified); PIM unchanged.
- vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED; no workspace/container execution, no G15.

Regression (post-commit, clean tree): G14B 55 passed; G14A 20; G13B 19; G13 28;
full suite 2215 passed; complete canonical vNext baseline PASS (g1..g13b + g14a + g14b + full_suite + compile/static/changed-files/preflight).

G14B started: YES (completed; READY FOR SA REVIEW)
G15 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G14B.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G14B/01-explicit-lagged-federation.md
