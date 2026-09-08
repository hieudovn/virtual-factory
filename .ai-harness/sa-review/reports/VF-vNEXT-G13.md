# VF-vNEXT-G13 — SH-WTP T108 Standalone Synthetic First-Order Runtime — Report

Status: **VF-vNEXT-G13-C01 — READY FOR SA REVIEW** (first authorized SH-WTP executable slice; C01 identity/provenance closure applied).

## Objective

Implement the first authorized SH-WTP executable slice: `UNIT-SHW-L1-T108` at
`shwtp/line1/l1_t108` as a standalone synthetic/reference first-order tank
accumulator, under explicit synthetic assumptions and truthful provenance, without
projecting PIM relations into G4 or broadening runtime authority.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G13.json` |
| Runtime module | `src/virtual_factory/shwtp/runtime.py` (+ `__init__` exports) |
| Invariant tests | `tests/test_vnext_g13_t108.py` (28 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G13/01-t108-runtime.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G13 gate context + g13 group) |

## Implementation summary

- Explicit config: `capacity_m3`, `tank_area_m2`, `initial_volume_m3`, `dt_s`; per-step
  scenario inputs `inflow_m3_s` / `requested_outflow_m3_s` (no hidden defaults).
- Deterministic step with explicit overflow (`overflow_m3`) and empty-tank saturation
  (applied outflow limited by available inventory, never negative volume); fail-closed
  mass-balance guard.
- Lifecycle: fresh attempt init, one deterministic `dt_s` step, in-context reset, detached
  immutable snapshot; fresh attempts isolated.
- Provenance: `simulation` + `synthetic` + `first_order` via reused G2 `RunContextV2` /
  `ProvenanceV2`; no site/measurement labels.
- Exact-target: only `shwtp/line1/l1_t108`; workspace/container targets rejected.

## Boundaries honored

- No T106/T110 runtime; no G4 projection; no BoundaryPort/CompositionBinding/coordinator;
  G12A/B reference graph inert; no `FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO` conversion.
- Legacy `equipment.process_dynamics.py` untouched; continuous/compressor behavior unchanged.
- Admission authority preserved (COMPLETE / CANDIDATE_SCOPED / T108 first / T110 blocked /
  NOT_AUTHORIZED).

## Regression evidence

- New G13 tests: **28 passed**.
- Full suite: **2121 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No T106/T110 runtime; no G4 projection; no federation/plant-wide run; no hydraulics/
chemistry/control/calibration; no PIM change; no G7 redesign; no new global engine; no G14.

## C01 correction (Issue #62)

Locked the T108 canonical reference (removed the caller ``canonical_id`` override; always
``UNIT-SHW-L1-T108``) and added truthful G2 provenance to the detached
``T108State``/``snapshot()`` (``simulation``/``synthetic``/``first_order``, time + step
index, optional semantic pins only when supplied). Focused regression tests added
(28 total). No runtime/G4/PIM/T106/T110/G14 expansion.
