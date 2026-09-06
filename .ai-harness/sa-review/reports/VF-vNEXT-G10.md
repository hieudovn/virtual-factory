# VF-vNEXT-G10 — SH-WTP Runtime Readiness & Scope Freeze — Report

Status: **VF-vNEXT-G10-C01 — READY FOR SA REVIEW** (planning/readiness-freeze gate; C01 G11-admission consistency fix applied).

## Objective

Freeze the SH-WTP runtime-readiness scope using the pinned PIM export
(`SHW-PIM-VF-EXPORT-v0.1` `v0.1` `SHW-PH03-v0.1`, semantic SHA
`f23f3c46…`, artifact hash `ea3361a4…`, PIM base `ec7f1266…`) as the sole
authoritative evidence, without inventing plant truth and without overriding
PIM runtime authorization (`NOT_AUTHORIZED`).

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G10.json` |
| Machine-readable plan | `configs/vnext/shwtp/shwtp_readiness_scope.json` |
| Human-readable plan | `configs/vnext/shwtp/PLAN.md` |
| Invariant tests | `tests/test_vnext_g10_plan.py` (19 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G10/01-readiness-scope-freeze.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G10 gate context + g10 group) |

## Plan summary

- **Inventory**: 29 evidence-traceable entries (plant / areas / units) with roles
  `container_only`, `object_only`, `reference_only`, `executable_candidate`.
- **Executable candidates**: T106 (OSF filtration, `LogicalOnly`), T108 (clean
  water tank, `FirstOrderReady`), T110 (wash water recovery, `FirstOrderReady`).
- **Fidelity**: `ParameterizedReady` / `CalibratedReady` BLOCKED (GAP-003/-004/-012).
- **Boundary contracts v0**: T106/T108/T110 fields tagged `PIM-supported` |
  `VF synthetic assumption` | `unknown/blocking`.
- **G11 admission**: structural construction only `AUTHORIZED_IN_G11`;
  synthetic/reference execution `PENDING_LATER_PIM_REVIEW`; site-authorized
  execution `NOT_AUTHORIZED`. T106/T108/T110 remain `executable_candidate`
  classification only — no executable behavior authorized in G11.
- **Topology**: containment (structural tree) distinct from connectivity;
  cross-area relations many-to-many; no A→B→C flattening.

## Regression evidence

- G10 invariant tests: **19 passed**.
- Canonical baseline (post-commit, clean tree): **PASS**.
- Full suite: **2005 passed**.
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No SH-WTP runtime implementation; no physics/control; no PIM modification; no
invented topology names; no fabricated parameters; no `ParameterizedReady` /
`CalibratedReady`; no `src/` production runtime change; no G11 construction.

## C01 correction (SA 5560434475)

Fixed the internal contradiction in `g11_admission_plan.authorized_in_g11`:
the synthetic/reference black-box item was removed and replaced with
executable-candidate classification only (nothing executable authorized in G11).
`PLAN.md` wording aligned; invariant tests strengthened so any
`authorized_in_g11` item that authorizes `execution` / `runtime` / `behavior` /
`black-box` behavior now fails the gate. PIM, runtime authorization, fidelity
ceilings, inventory roles, and boundary contracts unchanged.
