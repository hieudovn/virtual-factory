# VF-vNEXT-G12C — SH-WTP Synthetic Runtime Admission Review — Evidence

Gate: `VF-vNEXT-G12C` · Review/admission only (no runtime, no PIM change, no G4 projection).

## 1. Candidate admission matrix (frozen decisions)

| Candidate | Fidelity | Boundary v0 | Decision |
| --- | --- | --- | --- |
| `UNIT-SHW-L1-T106` (OSF filtration) | `LogicalOnly` | present | `SYNTHETIC_REFERENCE_ALLOWED` |
| `UNIT-SHW-L1-T108` (clean water tank) | `FirstOrderReady` | present | `SYNTHETIC_REFERENCE_ALLOWED` |
| `UNIT-SHW-WASH-T110` (wash recovery) | `FirstOrderReady` | present | `BLOCKED_PENDING_EVIDENCE` |

Full matrix (canonical id, VF StructuralPath, G10 role, fidelity ceiling, boundary
contract availability, PIM-supported inputs/outputs/properties, synthetic/pinned
assumptions, unknown/blocking, G12B relations, admission, rationale) is in
`configs/vnext/shwtp/shwtp_synthetic_runtime_admission.json`.

## 2. Decision rationale

- **T106** — LogicalOnly logical pass-through black-box; no filtration physics/equations.
  Input/output existence PIM-supported; values synthetic scenario inputs; missing
  filtration/hydraulic/quality params (GAP-003/-004/-010) remain unknown. Ambiguous
  wash/backwash relations (F02/F03, REL-006) are cited, never reclassified.
- **T108** — the only G10 FirstOrderReady simple tank; minimum first-order
  mass-accumulation with explicit synthetic volume/geometry + flow assumptions. This is
  the smallest meaningful executable slice.
- **T110** — output return destination is VF-inferred ("must be confirmed by PIM before
  first-order use"); its G12B relations are PatternInferred + REL-006
  "known-but-unconstrained". Authorizing it would require semantically resolving an
  ambiguous recovery-return relation → `BLOCKED_PENDING_EVIDENCE`.

## 3. Frozen authority / no fabrication

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`
- `structural_construction = AUTHORIZED_IN_G11`
- No ParameterizedReady / CalibratedReady / SiteVerified / SourceMapped / site-faithful
  or control-interlock claim. Fidelity ceilings not exceeded.

## 4. Synthetic assumption policy (frozen for G13)

synthetic values explicitly declared + provenance-marked; never relabeled measured/site
truth; defaults scenario/config inputs (no hidden magic constants); unknown plant
parameters stay unknown; LogicalOnly = logical/state/reference only; FirstOrderReady =
minimum first-order + explicit synthetic assumptions.

## 5. Runtime projection readiness (future gates only)

For each ALLOWED candidate, later work required before G4 composition: endpoint→scope/
boundary interpretation, boundary port definitions, unit/type compatibility,
cardinality/merge policy, coordinator timing/order. NOT implemented in G12C.

## 6. G13 authorization plan (smallest meaningful slice)

- First slice: `UNIT-SHW-L1-T108` only.
- `UNIT-SHW-L1-T106` authorized as optional later upstream logical source (not first slice).
- `UNIT-SHW-WASH-T110` blocked pending PIM evidence.
- No default authorization of all three.

## 7. Test evidence

- `tests/test_vnext_g12c_admission_review.py` — 13 tests PASS.
- Full suite: 2090 passed (2077 prior + 13 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G12C.md`.

## 8. Unchanged

PIM; G11 containment; G12A generic graph; G12B inert connectivity; G4 composition;
run-control; semantic binding; runtime authorization; no G13.
