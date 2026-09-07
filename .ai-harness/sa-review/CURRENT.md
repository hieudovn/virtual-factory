# SA REVIEW INBOX

Task: VF-vNEXT-G12C-C01
Status: READY FOR SA REVIEW (SH-WTP Synthetic Runtime Admission Review — C01 authority-consistency fix)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G12B complete)
Prerequisite: Issue #59 (G12B) accepted; Issue #60 (G12C) current

Gate type:
REVIEW/ADMISSION gate — SH-WTP Synthetic Runtime Admission Review (G12C), per Issue #60.
Review only. No runtime implementation, no PIM change, no G4 projection, no site authorization.

Architecture baseline:
G1-G12B contracts authoritative; G12B final head = 65347f66daed873878c15dbd4cf1e48c0d291da1 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Pinned PIM (repo-first): hieudovn/plant-intelligence-model @ ec7f1266…; package
SHW-PIM-VF-EXPORT-v0.1 v0.1 (SHW-PH03-v0.1); semantic SHA f23f3c46…; artifact hash ea3361a4…

Candidate admission decisions (frozen):
- UNIT-SHW-L1-T106 (LogicalOnly) -> SYNTHETIC_REFERENCE_ALLOWED
- UNIT-SHW-L1-T108 (FirstOrderReady) -> SYNTHETIC_REFERENCE_ALLOWED (first authorized slice)
- UNIT-SHW-WASH-T110 (FirstOrderReady) -> BLOCKED_PENDING_EVIDENCE (unconfirmed recovery-return semantics)

Deliverables (planning/config/test only; no src change):
- configs/vnext/shwtp/shwtp_synthetic_runtime_admission.json — candidate admission matrix +
  synthetic assumption policy + runtime projection requirements (future gates) + G13 authorization plan
- configs/vnext/shwtp/ADMISSION.md
- tests/test_vnext_g12c_admission_review.py (16 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G12C gate context + g12c group)
- Evidence/report under .ai-harness/sa-review/

Frozen distinctions preserved:
- vf_runtime_authorization = NOT_AUTHORIZED; site_authorized_execution = NOT_AUTHORIZED.
- C01 scoped authorization: review_status = COMPLETE; authorization_mode = CANDIDATE_SCOPED;
  authorized_candidates = [T106, T108]; first_authorized_slice = [T108];
  blocked_candidates = [T110]. No blanket SH-WTP runtime authorization.
- Fidelity ceilings not exceeded; no ParameterizedReady/CalibratedReady/site-faithful claims.
- Synthetic assumptions explicit + provenance-marked, never relabeled plant truth.
- Raw G12B relations (FLOWS_TO/DISCHARGES_TO/CONNECTED_TO) cited only, never runtime-classified.
- No BoundaryPort/G4 projection/runtime code; no new executable candidates.

Regression (post-commit, clean tree): G12C 16 passed; full suite 2093 passed; complete canonical
vNext baseline PASS (g1..g12c + full_suite + compile/static/changed-files/preflight).

C01 (SA 5566580805): removed global PENDING_LATER_PIM_REVIEW; replaced with candidate-scoped
COMPLETE/CANDIDATE_SCOPED authorization; T108 first authorized G13 slice; T110 blocked;
site-faithful NOT_AUTHORIZED; regression added (no pending review with authorized candidates).

G12C started: YES (completed; G12C-C01 READY FOR SA REVIEW)
G13 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G12C.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G12C/01-admission-review.md
.ai-harness/sa-review/evidence/VF-vNEXT-G12C/02-c01-authority-consistency.md
