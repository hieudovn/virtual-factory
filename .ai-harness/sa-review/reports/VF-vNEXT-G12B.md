# VF-vNEXT-G12B — SH-WTP PIM Reference Connectivity Materialization — Report

Status: **READY FOR SA REVIEW** (PIM reference connectivity materialization; no runtime).

## Objective

Materialize the exact SH-WTP PIM connectivity relationship facts (F01-F07) into
the accepted generic G12A `ReferenceConnectivityGraph`, preserving raw PIM
relation types and epistemic/status metadata without reclassifying semantics,
changing containment, or generating runtime connectivity.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G12B.json` |
| Materialization module | `src/virtual_factory/shwtp/connectivity.py` (+ `__init__` exports) |
| Invariant tests | `tests/test_vnext_g12b_shwtp.py` (19 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G12B/01-pim-reference-connectivity.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G12B gate context + g12b group) |

## Implementation summary

- Frozen PIM pins + frozen `PimReferenceRelation` slice of exactly the F01-F07
  connectivity facts (repo-first inspection of pinned `model.yaml`).
- Endpoints are PIM canonical references (`authority="hieudovn/plant-intelligence-model"`,
  `entity_kind="ProcessConnection"`) — PROC-* accepted without becoming G11 Scopes.
- Raw relation types preserved verbatim (`FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO`);
  no six-class reclassification; F06/F07 remain `FLOWS_TO`.
- F02/F03 preserve the PIM `REL-006` "known-but-unconstrained" warning.
- Every edge `runtime_effect = none`; no BoundaryPort/G4/coordinator/run-control.
- Deterministic `serialize()` + source summary.

## Authorization preserved

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`
- `site_authorized_execution = NOT_AUTHORIZED`

## Regression evidence

- New G12B tests: **19 passed**.
- Full suite: **2077 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No PIM modification; no six-class semantic taxonomy projection; no PROC-* into
containment; no PART_OF mapping; no relation inference from containment/names/
order; no G4 semantics change; no runtime projection; no execution authorization
change; no G13.
