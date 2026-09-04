# VF-vNEXT-G1 · Evidence 04 — Validation (fail-closed) + negative tests

## 1. Fail-closed invariants tested

| Invariant | Test | Result |
|---|---|---|
| missing parent (path-qualified) | `test_missing_parent_fails_closed` | PASS |
| parent outside the workspace | `test_parent_outside_workspace_fails_closed` | PASS |
| workspace-root as parent_path (top-level MUST use None) | `test_workspace_root_parent_fails_closed` | PASS (fails closed) |
| duplicate child id under the SAME parent | `test_duplicate_child_id_same_parent_fails_closed` | PASS |
| duplicate local ids under DIFFERENT parents (positive) | `test_duplicate_local_scope_ids_under_different_parents_are_valid`, `test_config_duplicate_local_ids_under_different_parents` | PASS (valid + resolve by path) |
| containment self-nesting | `test_containment_self_nesting_fails_closed` | PASS |
| completeness: declaration count == tree count (positive) | `test_declaration_count_matches_tree_count_completeness` | PASS (node count == declarations; every declared path resolves) |
| object attached to nonexistent Scope | `test_object_resolution_and_not_found` (resolve_object against `ASSY-SL99`) | PASS |
| object not found in existing Scope | `test_object_resolution_and_not_found` (AP04 in ASSY-SL02) | PASS |
| executable-only assumption on container-only Scope | `test_executable_assumption_on_container_only_fails_closed`, `test_container_scope_guards_executable_assumption` | PASS |
| invalid structural path/reference | `test_structural_path_rejects_empty_and_separator`, `test_structural_path_rejects_bad_segment`, `test_empty_workspace_id_and_scope_id_fail_closed`, `test_object_ref_requires_scope_path` | PASS |
| duplicate object ids within a Scope | `test_duplicate_object_ids_within_scope_fails_closed` | PASS |
| bare-id lookup must not silently return first match | `test_bare_id_lookup_raises_on_ambiguity` (whole-workspace raise) + `test_subtree_bare_lookup_within_single_parent_is_ok` (unique subtree OK) | PASS |
| determinism independent of input order | `test_build_is_deterministic_regardless_of_input_order` | PASS |

## 2. How validation is fail-closed

- All structural errors raise `StructuralValidationError` (subclass of
  `ValueError`) or `StructuralIdentityError`. There is no silent skip/repair.
- A container-only scope cannot be treated as executable-capable:
  `SimulationScope.require_executable()` raises.
- Resolution of a scope path or object ref that does not exist raises; it never
  returns a fabricated node.
- Bare-id convenience lookups raise on ambiguity (duplicate local ids); the
  canonical public API is path-qualified (`find_scope_by_path`/`resolve_scope`).

## 3. Coverage

- `tests/test_workspace_validation.py` — negative cases.
- `tests/test_workspace_foundation.py` — model/identity/path/determinism/ambiguity.
- `tests/test_workspace_config.py` — config seam + fixtures + lossless proofs.

All new G1 tests: **32 passed** (evidence 05).
