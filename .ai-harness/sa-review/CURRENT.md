# SA REVIEW INBOX

Task: VF-vNEXT-G14B-C01
Status: READY FOR SA REVIEW (SH-WTP T106→T108 Explicit Lagged Federation — identity locking correction)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G14B complete)
Prerequisite: Issue #65 G14B (head 3e69e257a578c220594df92e136017ba0f846249); SA comment 5592283850 current

Gate type:
CORRECTION gate — SH-WTP federation participant identity locking (G14B-C01), per SA comment 5592283850 (Issue #65).

Architecture baseline:
G1-G14B contracts authoritative; G14B final head = 3e69e257a578c220594df92e136017ba0f846249 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- Both ShwtpT106Participant / ShwtpT108Participant fail closed at construction on run-id/workspace/scope-path mismatch against runtime.run_context.
- runtime.run_context.workspace_id == adapter workspace_id == "shwtp"; runtime.run_context.run_id == adapter run_id.
- T106 BoundaryTransfer.run_id == T106 runtime RunContext run_id == T106 step provenance run_id; T108 provenance keeps the same federation run identity.

Implemented (additive, isolated):
- src/virtual_factory/shwtp/federation.py: added _validate_runtime_identity; both participant constructors cross-check + lock identity to the runtime's immutable RunContextV2 (no mutation, no post-construction derivation).
- tests/test_vnext_g14b_federation.py: 8 new identity-locking regressions (63 tests total).
- .ai-harness/regression/vnext_baseline_manifest.json (G14B-C01 gate context + g14b_federation group).

Frozen boundaries preserved:
- explicit_lagged + one-window lag; F01 only; T106+T108 only; no T110; no F02-F07; no G4 change; no T106/T108 equation change; no F01 projection change; no policy expansion; no RunContext/G2 identity contract change.
- vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED; no workspace/container execution, no G15.

Regression (post-commit, clean tree): G14B 63 passed; full suite 2223 passed;
complete canonical vNext baseline PASS (g1..g13b + g14a + g14b + full_suite + compile/static/changed-files/preflight).

G14B-C01 started: YES (completed; READY FOR SA REVIEW)
G15 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G14B-C01.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G14B-C01/01-identity-locking.md
