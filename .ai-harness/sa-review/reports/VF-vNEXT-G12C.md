# VF-vNEXT-G12C — SH-WTP Synthetic Runtime Admission Review — Report

Status: **READY FOR SA REVIEW** (admission review gate; no runtime).

## Objective

Review readiness and freeze a candidate-by-candidate decision telling G13 exactly
which SH-WTP subsystem(s), if any, may receive synthetic/reference black-box
behavior, without changing PIM, exceeding fidelity ceilings, or overstating site
fidelity.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G12C.json` |
| Admission matrix (JSON) | `configs/vnext/shwtp/shwtp_synthetic_runtime_admission.json` |
| Human-readable summary | `configs/vnext/shwtp/ADMISSION.md` |
| Invariant tests | `tests/test_vnext_g12c_admission_review.py` (13 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G12C/01-admission-review.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G12C gate context + g12c group) |

## Decision summary

| Candidate | Decision |
| --- | --- |
| `UNIT-SHW-L1-T106` | `SYNTHETIC_REFERENCE_ALLOWED` (LogicalOnly pass-through) |
| `UNIT-SHW-L1-T108` | `SYNTHETIC_REFERENCE_ALLOWED` (FirstOrderReady tank) |
| `UNIT-SHW-WASH-T110` | `BLOCKED_PENDING_EVIDENCE` (unconfirmed recovery-return semantics) |

## Key invariants preserved

- Fidelity ceilings not exceeded; no ParameterizedReady/CalibratedReady fabricated.
- `vf_runtime_authorization = NOT_AUTHORIZED`; `site_authorized_execution = NOT_AUTHORIZED`;
  `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`.
- Synthetic assumptions explicitly separated from PIM-supported facts and
  unknown/blocking items; synthetic assumption policy frozen for G13.
- Raw G12B relations (`FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO`) cited as evidence only,
  never runtime-classified.
- G13 plan: smallest meaningful slice = `UNIT-SHW-L1-T108` only; T106 optional later
  upstream logical source; T110 blocked. No default all-three authorization.
- No production runtime code, no PIM change, no G4 projection.

## Regression evidence

- New G12C tests: **13 passed**.
- Full suite: **2090 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No runtime implementation; no PIM modification; no G4 projection / BoundaryPort /
CompositionBinding / coordinator / run-control; no site authorization; no
ParameterizedReady/CalibratedReady; no new executable candidates; no G13.
