# SA REVIEW INBOX

Task: VF-vNEXT-G16
Status: READY FOR SA REVIEW (SH-WTP Whole-Plant Federation Expansion Readiness Review)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G15 complete)
Prerequisite: Issue #66 (G15) accepted; Issue #67 (G16) current

Gate type:
PLANNING/REVIEW gate — SH-WTP Whole-Plant Federation Expansion Readiness Review (G16), per Issue #67.
Review/classification only. NO new runtime, ports, bindings, participants, plant-wide execution.

Architecture baseline:
G1-G15 contracts authoritative; G15 final head = 786e11f3604478f825c800852a7b3224f65c6a4e (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- classify all reviewed SH-WTP units with exactly one planning decision; choose exactly one evidence-safe next slice or NO_NEXT_RUNTIME_SLICE_WITH_CURRENT_EVIDENCE; whole-plant runtime stays NOT_AUTHORIZED / NOT_IMPLEMENTED.

Implemented (additive, isolated):
- configs/vnext/shwtp/shwtp_expansion_readiness.json (source pins, 29 per-unit decision records, relation projection plan F01-F07 + next-slice, coverage matrix, next-slice recommendation, blocked evidence, invariants).
- configs/vnext/shwtp/EXPANSION-READINESS.md (planning note).
- tests/test_vnext_g16_readiness.py (23 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G16 gate context + g16_readiness group)

Frozen boundaries preserved:
- T106/T108 equations + provenance unchanged; G4/Coordinator/participant/transfer unchanged; G14A projection (2 ports / 1 binding) unchanged; explicit_lagged + identity locking unchanged; G15 evaluator unchanged; PIM/G7 unchanged.
- No T110/Line2/chemical/automation runtime; no new ports/bindings/participants; no plant-wide execution.
- vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Decisions summary:
- NEXT_SLICE_CANDIDATE: UNIT-SHW-DIST-P108 (LogicalOnly distribution sink; next projection T108 -> DIST-P108).
- LATER_CANDIDATE: 12 (RAW-INTAKE, T100, L1-T101/109/102/103/104/105/107, SLUDGE-T201, T106/T108 implemented-accepted).
- STRUCTURAL_ONLY: 8 (PLANT + 7 areas). REFERENCE_ONLY: 7. BLOCKED_PENDING_EVIDENCE: 1 (WASH-T110).

Regression (post-commit, clean tree): G16 23 passed; full suite 2276 passed;
complete canonical vNext baseline PASS (g1..g13b + g14a + g14b + g15 + g16 + full_suite + compile/static/changed-files/preflight).

G16 started: YES (completed; READY FOR SA REVIEW)
G17 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G16.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G16/01-expansion-readiness.md
