# VF-vNEXT-G11 — SH-WTP Structural Workspace Construction — Report

Status: **READY FOR SA REVIEW** (structural construction gate; no runtime).

## Objective

Materialize the SH-WTP structural Workspace hierarchy from the accepted frozen G10 plan using the
generic G1 Workspace/Scope/Object foundation. Deterministic structural construction only; no
executable behavior, no connectivity graph, no runtime, no PIM change.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G11.json` |
| Structural module | `src/virtual_factory/shwtp/` (`structural.py` + `__init__.py`) |
| Invariant tests | `tests/test_vnext_g11_shwtp.py` (22 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G11/01-structural-workspace-construction.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G11 gate context + g11 group) |

## Implementation summary

- Single deterministic root: `Workspace` id `shwtp` (`shwtp/`), plant canonical reference `PLANT-SHW`.
- Containment tree: 8 top-level scopes (7 areas + plant-level `dist_p108`) and 20 unit scopes under
  their areas = 28 scope nodes == G10 inventory minus PLANT root. Containment from pinned PIM skeleton;
  `wash_t110` homed under `line1` per G10 slice note.
- Roles: `container_only`/`object_only`/`reference_only` -> `CONTAINER_ONLY`; T106/T108/T110
  `executable_candidate` -> `EXECUTABLE_CAPABLE` classification only (zero runtime).
- VF local ids distinct from canonical ids; canonical references are read-only metadata.
- Metadata (role/fidelity/evidence/confidence/gaps) preserved exactly from G10.
- Deterministic `serialize()` structural inspection.

## Authorization preserved

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `structural_construction = AUTHORIZED_IN_G11`
- `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`
- `site_authorized_execution = NOT_AUTHORIZED`

## Regression evidence

- New G11 structural tests: **22 passed**.
- Full suite: **2027 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No SH-WTP runtime/executable behavior; no solver/physics/control/state advancement; no runtime bridge;
no coordinator/run-control participant; no connectivity graph; no invented Area/Unit; no PIM
modification; no override of `NOT_AUTHORIZED`; no G12+ work.
