# SH-WTP Synthetic Runtime Admission Review (VF-vNEXT-G12C)

Review/admission only. No runtime implementation, no PIM change, no G4 projection, no site authorization.

## Decision summary (candidate by candidate)

| Candidate | Fidelity | Boundary v0 | Decision |
| --- | --- | --- | --- |
| `UNIT-SHW-L1-T106` (OSF filtration) | `LogicalOnly` | present | `SYNTHETIC_REFERENCE_ALLOWED` |
| `UNIT-SHW-L1-T108` (clean water tank) | `FirstOrderReady` | present | `SYNTHETIC_REFERENCE_ALLOWED` |
| `UNIT-SHW-WASH-T110` (wash recovery) | `FirstOrderReady` | present | `BLOCKED_PENDING_EVIDENCE` |

## Rationale (short)

- **T106** — LogicalOnly logical pass-through black-box; no filtration physics; inputs/outputs
  PIM-supported existence, values synthetic; missing filtration/hydraulic/quality parameters stay
  unknown; ambiguous wash/backwash relations are cited, never reclassified.
- **T108** — the only G10 FirstOrderReady simple tank; mass-accumulation with explicit synthetic
  volume/geometry + flow assumptions; smallest meaningful executable slice.
- **T110** — output return destination is VF-inferred ("must be confirmed by PIM"); its G12B
  relations are PatternInferred + REL-006 "known-but-unconstrained"; authorizing it would require
  semantically resolving an ambiguous recovery-return relation → blocked pending PIM evidence.

## Frozen authority

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `structural_construction = AUTHORIZED_IN_G11`
- `review_status = COMPLETE`
- `authorization_mode = CANDIDATE_SCOPED`
- `authorized_candidates = [UNIT-SHW-L1-T106, UNIT-SHW-L1-T108]`
- `first_authorized_slice = [UNIT-SHW-L1-T108]`
- `blocked_candidates = [UNIT-SHW-WASH-T110]`

Synthetic/reference execution is authorized ONLY for the explicitly listed candidates
(candidate-scoped). There is NO blanket SH-WTP runtime authorization; T110 remains blocked;
site-faithful execution remains NOT_AUTHORIZED. No ParameterizedReady / CalibratedReady /
site-faithful / control-interlock behavior is authorized.

## G13 plan (first authorized slice)

- First authorized slice: **`UNIT-SHW-L1-T108`** (FirstOrderReady clean-water tank).
- `UNIT-SHW-L1-T106` authorized as an optional later upstream logical source, not part of the first slice.
- `UNIT-SHW-WASH-T110` blocked pending PIM evidence.

## Synthetic assumption policy (frozen for G13)

- synthetic values explicitly declared + provenance-marked;
- never relabeled measured/site truth;
- defaults are scenario/config inputs, not hidden magic constants;
- unknown plant parameters stay unknown;
- LogicalOnly: logical/state/reference behavior only (no fabricated physics);
- FirstOrderReady: minimum first-order behavior + explicit synthetic assumptions.

## Runtime projection (future gates only, NOT implemented here)

For each ALLOWED candidate, before G4 composition: endpoint→scope/boundary interpretation,
boundary port definitions, unit/type compatibility, cardinality/merge policy, coordinator
timing/order.
