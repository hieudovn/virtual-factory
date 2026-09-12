# VF-vNEXT-G16 — SH-WTP Whole-Plant Federation Expansion Readiness Review

Gate: `VF-vNEXT-G16`
Base (required): `786e11f3604478f825c800852a7b3224f65c6a4e`
Status: READY FOR SA REVIEW

## Scope

Planning/review only — no runtime implementation. Defines the evidence-safe
expansion path from the proven T106→T108 federation toward whole-plant federated
execution.

## Implemented (additive, isolated)

- `configs/vnext/shwtp/shwtp_expansion_readiness.json` — deterministic
  machine-readable artifact: source pins, 29 per-unit decision records, relation
  projection plan (F01–F07 + next-slice), coverage matrix, next-slice
  recommendation, blocked-evidence list, architecture invariants, non-objectives.
- `configs/vnext/shwtp/EXPANSION-READINESS.md` — human-readable planning note.
- `tests/test_vnext_g16_readiness.py` (23 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G16 gate context +
  `g16_readiness` group.

## Decisions

- `UNIT-SHW-DIST-P108` → **NEXT_SLICE_CANDIDATE** (LogicalOnly distribution sink).
- 10 spine/side units + SLUDGE-T201 → LATER_CANDIDATE (LogicalOnly).
- T106 / T108 → accepted existing runtime candidates (IMPLEMENTED_ACCEPTED).
- PLANT + 7 areas → STRUCTURAL_ONLY.
- CHEM-DOSING / Line 2 / ELEC-MCC / AUTO-PLC → REFERENCE_ONLY.
- WASH-T110 → BLOCKED_PENDING_EVIDENCE.

## Next slice

`UNIT-SHW-DIST-P108` + projection candidate T108 → DIST-P108. Evidence: T108's
accepted G10 boundary contract output `clean_water_to_distribution_P108`
(PIM-supported) + REL-SHW-F05 (FLOWS_TO, DocumentConfirmed). LogicalOnly, no pump
physics, avoids T110/Line2/chemical/automation. Requires PIM confirmation of the
exact unit-level relation id before G17 runtime.

## Frozen boundaries preserved

T106/T108 equations/provenance; G4; G14A projection (2 ports / 1 binding);
explicit_lagged + identity locking; G15 evaluator; G7; PIM unchanged.
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`;
`vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`.
No T110/Line2/chemical/automation runtime; no new ports/bindings/participants; no
G17.

## Regression

- G16: 23 passed.
- Full suite: 2276 passed (2253 prior + 23 new).
- Complete canonical vNext baseline (g1..g13b + g14a + g14b + g15 + g16 +
  full_suite + compile/static/changed-files/preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G16/01-expansion-readiness.md`
