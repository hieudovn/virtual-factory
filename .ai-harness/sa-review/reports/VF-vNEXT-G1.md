# VF-vNEXT-G1 — Implement Workspace / Simulation Scope Foundation

> **C01 revision (Issue #46 SA review):** scope id uniqueness is now enforced
> WITHIN the structural parent namespace (not globally across the Workspace).
> Parent references are path-qualified (`StructuralPath`), so resolution never
> depends on a globally-unique bare id. The full `StructuralPath` is the
> authoritative unambiguous scope identity; path-based lookup is deterministic
> and fail-closed; bare-id convenience lookups raise on ambiguity instead of
> returning the first match. Positive tests prove duplicate local ids under
> different parents are valid; negative tests keep duplicate child ids under the
> SAME parent fail-closed. All other G1 contracts preserved.

> **C02 revision (Issue #46 SA review):** fixed the silent structural data-loss
> case in the builder. Top-level scopes MUST use `parent_path=None` (canonical);
> `parent_path == workspace_root` now fails closed instead of being silently
> dropped from the tree. An explicit completeness invariant/check guarantees
> every validated `ScopeSpec` materializes exactly once (node count ==
> declaration count, declared-path set == built-path set). Added the
> workspace-root-parent negative test and the declaration-count/tree-count
> completeness test. All C01 identity semantics and other G1 contracts preserved.

> **C03 revision (Issue #46 SA review):** removed the over-restrictive
> `_detect_self_nesting` guard. Repeated local scope ids along an ancestor chain
> (e.g. `W/Area-A/Line-1/Area-A`) are VALID when their full `StructuralPath`
> differs; local-id repetition is NOT a containment-cycle criterion. Fail-closed
> tree integrity is preserved via path-qualified parent existence, same-parent
> duplicate rejection, the canonical top-level rule (`parent_path=None`), and
> the completeness invariant. Added a positive repeated-ancestor-local-id test;
> all C01/C02 tests retained.

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G1` (GitHub Issue #46) + C02 |
| Program | Implementation phase following completed architecture umbrella #39 (`VF-vNEXT-ARCH`) |
| Gate mode | Accelerated implementation gate (only authorized implementation gate) |
| Architecture baseline | ARCH-01 `41903e18…` + ARCH-02 `40454487…` + ARCH-03 `392401bd…` + ARCH-04 `d5c155b6…` + ARCH-05 `8fafa119…` + ARCH-06 `41300d34…` |
| Production base SHA (`origin/main`, inspected before branching) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Branch | `feature/vf-vnext-g1` (from accepted ARCH-06 head `41300d34…`) |
| G1 head | `feature/vf-vnext-g1` pushed head (recorded in PM final response; `git rev-parse HEAD`) |
| G2+ started | **NO** |

## 1. Objective

Implement the minimal reusable structural foundation for
`Platform → Workspace → hierarchical Simulation Scope → Simulation Object`:
deterministic structural identity/path, container-only vs executable-capable
scope mode, fail-closed hierarchy/reference validation, a generic workspace
config/loading seam (`configs/workspaces/`, PH00 B9), and representative
fixtures proving lossless `TIPA → ASSY → ASSY-SL01..06` and a generic
continuous hierarchy without inventing SH-WTP site truth.

## 2. Implementation (production)

New dependency-light package `src/virtual_factory/workspace/`:

- `identity.py` — immutable `StructuralPath` (`workspace/scope/.../scope`) and
  `SimulationObjectRef`; deterministic, path-safe; distinct from PIM canonical id.
- `model.py` — `ScopeMode` (container_only / executable_capable), `Archetype`
  (informational), `SimulationObject`, `SimulationScope`, `Workspace`; immutable
  validated tree; `require_executable()` guard.
- `builder.py` — `ScopeSpec`/`ObjectSpec` + `build_workspace()`; fail-closed
  validation (missing path-qualified parent, same-parent duplicate ids,
  canonical top-level, completeness); deterministic ordering.
- `config.py` + `loader.py` — generic Pydantic manifest schema + YAML loading
  seam (`load_workspace_manifest`).
- `__init__.py` — public API.

New config fixtures: `configs/workspaces/tipa_assy_demo.yaml`,
`configs/workspaces/generic_continuous_demo.yaml`.

No existing production module was modified; `AssyLineRuntime` untouched.

## 3. Design invariants (evidence 02)

Nested containment tree; deterministic structural paths; scope ids unique
WITHIN their structural parent namespace (full `StructuralPath` is the
authoritative identity); container-only never treated as executable; archetype
is metadata not engine authority (ARCH-06 C01); structural identity never
equals PIM canonical identity; no workspace-name hard-coding; no God
registry/singleton.

## 4. Validation (evidence 04)

Fail-closed: missing/invalid path-qualified parent, duplicate child id under the
same parent, object on nonexistent Scope, object not found, executable assumption
on container-only, invalid path/reference, duplicate object ids, ambiguity in
bare-id lookup, completeness, determinism vs input order. Repeated local ids
along an ancestor chain are VALID (full path disambiguates; C03).

## 5. Lossless proofs (evidence 03)

- TIPA/ASSY: `TIPA(Workspace) → ASSY(container_only) → ASSY-SL01..06
  (executable_capable)` matches the canonical `AssyProductionLineIdentity`
  exactly (ids + hydraulic/thermal variants); no runtime/domain rewrite.
- Generic continuous: nested container-only areas + executable-capable units +
  generic object refs; no SH-WTP site truth, no evidence-maturity fields.

## 6. Test / regression results (evidence 05)

| Suite | Result |
|---|---|
| New G1 unit/negative/config tests | **32 passed** |
| ASSY regression oracle (incl. ARCH-05 C01 automated obligations) | **354 passed** (deterministic re-run; one transient pre-existing test-isolation flake recorded in evidence 05) |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1679 passed** (0 failures; no baseline exceptions) |
| Compile check | PASS (no configured ruff/mypy/black in repo) |

## 7. Non-decisions / deferred (evidence 06)

G2 Runtime Context + Provenance v2, G3 Observation/Event/Alarm alignment, G4
Coordinator/Ports, G5 ASSY federation, G6 UI primitives, G7 Scenario/Run
Control, G8 Regression baseline gate, G9 Semantic Binding, G10 SH WTP runtime —
all NOT implemented. No semantic binding, no coordinator, no provenance-v2, no
UI change, no `AssyLineRuntime` rewrite, no legacy WTP mini-engine change.

## 8. STOP-condition assessment (evidence 06 §2)

None triggered: no ARCH-01..06 decision changed; generic model represents both
fixtures without hard-coding; no runtime needed to function; PIM identity
separate; ASSY untouched (354 passed); config seam additive; no SH-WTP site
truth; scope did not expand into G2+.

## 9. Acceptance

| Criterion | Result |
|---|---|
| Generic Workspace/Scope/Object foundation in production code | PASS (`src/virtual_factory/workspace/`) |
| Nested containment + deterministic structural paths | PASS |
| Container-only vs executable-capable without fake runtime | PASS |
| Fail-closed validation | PASS |
| Generic config/loading seam | PASS |
| TIPA/ASSY lossless without runtime/domain rewrite | PASS |
| Generic continuous without site invention | PASS |
| No workspace-name hard-coding | PASS |
| PIM semantic identity separate | PASS |
| No G2+ implementation | PASS |
| Mandatory tests/regressions pass | PASS (32 + 354 + 61 + full 1679) |
| Working tree clean and head pushed | PASS (after push) |

## 9.1 C01 corrections applied

1. **Scope id local to structural parent (C01-1):** uniqueness enforced within
   the parent namespace, not globally; the full `StructuralPath` is the
   authoritative unambiguous identity.
2. **Path-qualified parent resolution:** `ScopeSpec.parent_path` (StructuralPath)
   replaces the bare `parent_scope_id`; resolution never depends on a
   globally-unique bare id.
3. **Ambiguity fail-closed:** bare-id `find_scope`/`find_object`/`scope_path_by_id`
   raise on ambiguity instead of returning the first match; path-based
   `find_scope_by_path`/`resolve_scope` is canonical.
4. **Tests:** added positive duplicate-local-id-under-different-parents tests
   (builder + config); kept duplicate-child-same-parent negative.
5. **All other G1 contracts preserved** (container/executable, no fake runtime,
   object ownership, PIM identity separation, deterministic build, TIPA/ASSY and
   generic-continuous fixtures).

## 9.2 C02 corrections applied

1. **Canonical top-level representation (C02-1):** top-level scopes MUST use
   `parent_path=None`; `parent_path == workspace_root` is rejected fail-closed
   in `_compute_paths` (previously it passed parent validation and was silently
   dropped from `Workspace.top_level_scopes`).
2. **Completeness invariant:** `_check_completeness` verifies the built tree
   node count equals the validated declaration count and the declared-path set
   equals the built-path set; a mismatch fails the build (no declaration may
   disappear).
3. **Tests:** added `test_workspace_root_parent_fails_closed` (negative) and
   `test_declaration_count_matches_tree_count_completeness` (positive).
4. **C01 semantics and all other G1 contracts preserved** (local scope id per
   parent, `StructuralPath` authoritative, ambiguity fail-closed, path-qualified
   parent resolution, container/executable, no fake runtime, object ownership,
   PIM identity separation, deterministic build, fixtures).

## 9.3 C03 corrections applied

1. **Repeated ancestor local id is NOT a cycle (C03-1):** removed the
   over-restrictive `_detect_self_nesting` guard; local-id repetition along an
   ancestor chain is allowed when full `StructuralPath`s differ.
2. **Fail-closed integrity preserved** via the four independent mechanisms:
   path-qualified parent existence, same-parent duplicate rejection, the
   canonical top-level rule (`parent_path=None`), and the completeness
   invariant. A parent cycle remains structurally unrepresentable (each scope
   path is its parent path plus one segment).
3. **Tests:** added `test_repeated_ancestor_local_id_is_valid`
   (`W/Area-A/Line-1/Area-A` builds and resolves by full path); removed the
   now-invalid self-nesting negative. All C01/C02 tests retained (same-parent
   duplicate rejection, workspace-root canonical, completeness, ambiguity,
   duplicate-local-id positives).

## 10. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G1/` — 6 files (01…06).

## 11. Final status

```text
VF-vNEXT-G1-C03 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G2 is NOT started.
