# VF-vNEXT-G10-C01 — G11 admission-plan consistency fix — Evidence

Correction: SA comment `5560434475` (base `5e66e7e0f7ea79e0ef918a18daa26439e9fd7ed9`).

## Blocker addressed

`configs/vnext/shwtp/shwtp_readiness_scope.json` → `g11_admission_plan.authorized_in_g11`
contained an item authorizing synthetic/reference black-box behavior for
T106/T108/T110, contradicting `execution_modes.synthetic_reference_execution =
PENDING_LATER_PIM_REVIEW` and `authz_separation.statement`.

## Change (smallest planning/test-only correction)

- `authorized_in_g11` is now structural-construction-only:
  1. Workspace / containment scopes / StructuralPath mirroring PIM canonical ids;
  2. container-only scopes for `PLANT-SHW` and every `AREA-SHW-*`;
  3. object/reference binding for skeleton-level units per inventory;
  4. executable-candidate classification only for T106/T108/T110
     (nothing executable authorized in G11).
- `PLAN.md` section 5 aligned.
- Three distinct concepts preserved and explicit:
  - structural construction = `AUTHORIZED_IN_G11`
  - synthetic/reference execution = `PENDING_LATER_PIM_REVIEW`
  - site-authorized execution = `NOT_AUTHORIZED`

## Strengthened invariant tests (`tests/test_vnext_g10_plan.py`)

Added:
- `test_authorized_in_g11_is_structural_construction_only` — fails if any
  `authorized_in_g11` item contains `execution`, `runtime`, `behavior`,
  `behaviour`, `black-box`, or `black_box` while synthetic/reference execution
  is pending.
- `test_executable_candidates_are_classification_only_in_g11` — asserts the
  classification-only wording and that T106/T108/T110 remain `allowed_later`.

G10 tests now 19 (was 17). Full suite 2005 passed.

## Unchanged

PIM, runtime authorization (`NOT_AUTHORIZED`), fidelity ceilings, inventory
roles, boundary contracts, and production runtime code.
