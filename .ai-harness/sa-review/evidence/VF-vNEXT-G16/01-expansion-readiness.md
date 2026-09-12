# VF-vNEXT-G16 — SH-WTP Whole-Plant Federation Expansion Readiness — Evidence

Gate: `VF-vNEXT-G16` · Planning/review only. No runtime implementation.

## 1. Proven baseline under review

`UNIT-SHW-L1-T106 (LogicalOnly) --REL-SHW-F01--> UNIT-SHW-L1-T108 (FirstOrder)`
via G14A projection + G14B explicit_lagged federation + G14B-C01 identity locking
+ G15 evaluation trace. Two-scope proof, not whole-plant proof.

## 2. Source pins (exact, verified by tests)

- PIM: `hieudovn/plant-intelligence-model @ ec7f1266d4a19e5201b689874a2a7a75a022fc5c`
  (`SHW-PIM-VF-EXPORT-v0.1 v0.1`, `SHW-PH03-v0.1`, semantic sha
  `f23f3c4614f50a1a2e3805f7e887433feb934915`, artifact hash
  `ea3361a4aca9d25927a4a76c792f3af184e1aabb`).
- Model fixture sha256 `e9c6703f...0729ea6`; seed skeleton + first-slice seed.
- G12B selected relationship ids: F01–F07.

## 3. Per-unit decisions (29 records)

- **NEXT_SLICE_CANDIDATE (1)**: `UNIT-SHW-DIST-P108` (LogicalOnly distribution sink).
- **LATER_CANDIDATE (12)**: RAW-INTAKE, T100, L1-T101, L1-T109, L1-T102, L1-T103,
  L1-T104, L1-T105, L1-T107, SLUDGE-T201 (LogicalOnly); T106 + T108 (runtime
  `IMPLEMENTED_ACCEPTED`).
- **STRUCTURAL_ONLY (8)**: PLANT-SHW + 7 areas (containment only).
- **REFERENCE_ONLY (7)**: CHEM-DOSING, L2-T101/L2-T105/L2-T106/L2-T108, ELEC-MCC,
  AUTO-PLC (PatternInferred / IndustryExpected).
- **BLOCKED_PENDING_EVIDENCE (1)**: WASH-T110.

`runtime_later = blocked` (G10) is not reinterpreted as runtime permission. Every
future candidate requires a PIM decision before any G4 runtime admission.

## 4. Boundary-contract v0 plans

Created for the 11 not-yet-implemented NEXT/LATER candidates (RAW-INTAKE, T100,
T101, T109, T102, T103, T104, T105, T107, DIST-P108, SLUDGE-T201): inputs,
outputs, supported properties, synthetic assumptions, unknown/blocking, fidelity
ceiling. No runtime behavior, no fabricated plant parameters. T106/T108 keep their
implemented G10 contracts.

## 5. Relation / projection plan

- F01 → PROJECTED_G14A.
- F02 / F03 → AMBIGUOUS_BLOCKED (T110 + REL-006).
- F04 / F05 → PROJECTION_CANDIDATE (DocumentConfirmed aggregates).
- F06 / F07 → REFERENCE_ONLY (PatternInferred).
- Next-slice projection candidate: T108 → DIST-P108 (evidence: T108 G10 contract
  output `clean_water_to_distribution_P108` + F05; requires PIM confirmation of
  the exact unit-level relation id).

No BoundaryPort / CompositionBinding / participant created; no generic
`FLOWS_TO => runtime binding` rule.

## 6. Next slice

`UNIT-SHW-DIST-P108` — one LogicalOnly black-box distribution sink directly
downstream of accepted T108. DocumentConfirmed (medium), LogicalOnly, no pump
physics, no T110/Line2/chemical/automation. PIM must confirm the exact
T108→DIST-P108 unit-level relation id before G17 runtime projection.

## 7. Whole-plant status

`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`;
`vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`.

## 8. Test evidence

- `tests/test_vnext_g16_readiness.py` — 23 tests PASS.
- Full suite 2276 passed (2253 prior + 23 new).
- Complete canonical vNext baseline PASS (see report `VF-vNEXT-G16.md`).

## 9. Preserved / unchanged

T106/T108 equations + provenance; G4 Coordinator/ExecutableParticipant/transfer;
G14A projection (still 2 ports / 1 binding); explicit_lagged + identity locking;
G15 evaluator; G7; PIM. No new runtime, ports, bindings, participants, or G17.
