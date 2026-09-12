# VF-vNEXT-G16 — SH-WTP Whole-Plant Federation Expansion Readiness (Planning Note)

Planning/review gate only. No runtime implementation. Machine-readable artifact:
`configs/vnext/shwtp/shwtp_expansion_readiness.json`.

## Proven baseline

```
UNIT-SHW-L1-T106 (LogicalOnly) --REL-SHW-F01--> UNIT-SHW-L1-T108 (FirstOrder)
```
via G14A projection + G14B explicit_lagged federation + G14B-C01 identity locking
+ G15 evaluation trace. Two-scope proof, not whole-plant proof.

## Candidate decisions (planning only, NOT runtime authorization)

| Unit | Decision | Fidelity ceiling |
| --- | --- | --- |
| UNIT-SHW-DIST-P108 | **NEXT_SLICE_CANDIDATE** | LogicalOnly |
| UNIT-SHW-RAW-INTAKE, T100, L1-T101, L1-T109, L1-T102, L1-T103, L1-T104, L1-T105, L1-T107, SLUDGE-T201 | LATER_CANDIDATE | LogicalOnly |
| UNIT-SHW-L1-T106, UNIT-SHW-L1-T108 | LATER_CANDIDATE (runtime IMPLEMENTED_ACCEPTED) | LogicalOnly / FirstOrderReady |
| PLANT-SHW + all 7 areas | STRUCTURAL_ONLY | containment only |
| UNIT-SHW-CHEM-DOSING, Line 2 units, ELEC-MCC, AUTO-PLC | REFERENCE_ONLY | NotReady |
| UNIT-SHW-WASH-T110 | BLOCKED_PENDING_EVIDENCE | FirstOrderReady (blocked) |

`runtime_later = blocked` (G10) is NOT reinterpreted as runtime permission. Every
future candidate still requires a PIM decision before any G4 runtime admission.

## Next slice

**UNIT-SHW-DIST-P108** — one LogicalOnly black-box distribution sink directly
downstream of the accepted T108, with projection candidate T108 → DIST-P108.

Evidence: T108's accepted G10 boundary contract v0 output names
`clean_water_to_distribution_P108` (PIM-supported); REL-SHW-F05 (FLOWS_TO,
DocumentConfirmed) covers L1 → DIST. No pump physics (LogicalOnly), no T110,
no Line 2 / chemical / automation.

PIM gate: the exact unit-level relation id T108 → DIST-P108 is aggregate (F05)
and must be PIM-confirmed before any G17 runtime projection. G16 only classifies.

## Relation projection decisions

- REL-SHW-F01 → PROJECTED_G14A (already).
- REL-SHW-F02 / F03 → AMBIGUOUS_BLOCKED (T110 + REL-006).
- REL-SHW-F04 / F05 → PROJECTION_CANDIDATE (DocumentConfirmed aggregates).
- REL-SHW-F06 / F07 → REFERENCE_ONLY (PatternInferred).

No BoundaryPort / CompositionBinding / federation participant is created in G16.

## Whole-plant status

`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.
`vf_runtime_authorization = NOT_AUTHORIZED`; `site_authorized_execution = NOT_AUTHORIZED`.
