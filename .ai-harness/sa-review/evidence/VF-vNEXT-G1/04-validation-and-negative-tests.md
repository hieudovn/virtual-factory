# VF-vNEXT-G1 · Evidence 04 — Validation (fail-closed) + negative tests

## 1. Fail-closed invariants tested

| Invariant | Test | Result |
|---|---|---|
| missing/invalid parent | `test_missing_parent_fails_closed`, `test_invalid_parent_self_reference_fails_closed` | PASS |
| duplicate scope id (anywhere / same parent) | `test_duplicate_scope_id_fails_closed`, `test_duplicate_scope_id_anywhere_fails_closed` | PASS |
| containment cycle (2- and 3-node) | `test_containment_cycle_fails_closed`, `test_three_node_cycle_fails_closed` | PASS |
| object attached to nonexistent Scope | `test_object_resolution_and_not_found` (resolve_object against `ASSY-SL99`) | PASS |
| object not found in existing Scope | `test_object_resolution_and_not_found` (AP04 in ASSY-SL02) | PASS |
| executable-only assumption on container-only Scope | `test_executable_assumption_on_container_only_fails_closed`, `test_container_scope_guards_executable_assumption` | PASS |
| invalid structural path/reference | `test_structural_path_rejects_empty_and_separator`, `test_structural_path_rejects_bad_segment`, `test_empty_workspace_id_and_scope_id_fail_closed`, `test_object_ref_requires_scope_path` | PASS |
| duplicate object ids within a Scope | `test_duplicate_object_ids_within_scope_fails_closed` | PASS |
| determinism independent of input order | `test_build_is_deterministic_regardless_of_input_order` | PASS |

## 2. How validation is fail-closed

- All structural errors raise `StructuralValidationError` (subclass of
  `ValueError`) or `StructuralIdentityError`. There is no silent skip/repair.
- A container-only scope cannot be treated as executable-capable:
  `SimulationScope.require_executable()` raises.
- Resolution of a scope path or object ref that does not exist raises; it never
  returns a fabricated node.

## 3. Coverage

- `tests/test_workspace_validation.py` — all negative cases above.
- `tests/test_workspace_foundation.py` — model/identity/path/determinism units.
- `tests/test_workspace_config.py` — config seam + fixtures + lossless proofs.

All new G1 tests: **28 passed** (evidence 05).
