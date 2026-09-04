# SA REVIEW INBOX

Task: VF-vNEXT-G1-C02
Status: READY FOR SA REVIEW (C02: canonical top-level parent=None; completeness invariant — no declared scope disappears)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate)
Prerequisite: ARCH-06 / Issue #45 CLOSED by SA as completed

Gate type:
Accelerated implementation gate — production structural foundation (G1)

Architecture baseline:
ARCH-01 @ 41903e18…, ARCH-02 @ 40454487…, ARCH-03 @ 392401bd…,
ARCH-04 @ d5c155b6…, ARCH-05 @ 8fafa119…, ARCH-06 @ 41300d34…
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented:
- src/virtual_factory/workspace/ (identity.py, model.py, builder.py, config.py,
  loader.py, __init__.py): generic Workspace -> hierarchical Simulation Scope ->
  Simulation Object foundation; ScopeMode container_only/executable_capable;
  Archetype informational; deterministic StructuralPath + SimulationObjectRef;
  fail-closed build_workspace validation (missing path-qualified parent,
  duplicate child id under same parent, self-nesting, mode guard, object
  ownership, ambiguity in bare-id lookup); generic config/loading seam.
  Scope ids unique WITHIN their structural parent namespace (NOT global); full
  StructuralPath is the authoritative identity. Top-level scopes MUST use
  parent_path=None; parent_path == workspace_root fails closed (C02).
  Completeness invariant: every validated declaration materializes exactly once
  (node count == declaration count).
- configs/workspaces/tipa_assy_demo.yaml (lossless TIPA -> ASSY -> ASSY-SL01..06)
  + configs/workspaces/generic_continuous_demo.yaml (no SH-WTP site truth).
- tests/test_workspace_{foundation,validation,config}.py.
- No AssyLineRuntime change; no G2+ implementation; no workspace-name
  hard-coding; PIM canonical identity separate.

Test / regression results:
- New G1 tests: 32 passed.
- ASSY regression oracle (ARCH-05 incl. C01 automated obligations): 354 passed
  (deterministic re-run; one transient pre-existing test-isolation flake noted).
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1679 passed (0 failures; no baseline exceptions).
- Compile check PASS (no configured ruff/mypy/black in repo).

C01 corrections applied:
- Scope id uniqueness now WITHIN structural parent namespace (not global).
- Parent references path-qualified (StructuralPath); resolution never depends on
  a globally-unique bare id.
- Full StructuralPath = authoritative unambiguous identity; path-based lookup
  deterministic + fail-closed.
- Bare-id lookups (find_scope/find_object/scope_path_by_id) raise on ambiguity.
- Positive tests for duplicate local ids under different parents; negative test
  for duplicate child ids under same parent kept.

C02 corrections applied:
- Canonical top-level representation: top-level scopes MUST use parent_path=None;
  parent_path == workspace_root fails closed (was silently dropped from tree).
- Completeness invariant/check: every validated ScopeSpec materializes exactly
  once (declaration count == tree node count).
- Added workspace-root-parent negative test and declaration-count/tree-count
  completeness positive test.
- All other G1 contracts preserved.

Deferred to G2+ (NOT implemented): runtime context + provenance-v2 (G2),
observation/event/alarm alignment (G3), coordinator/ports (G4), ASSY federation
(G5), UI primitives (G6), scenario/run control (G7), regression baseline gate
(G8), semantic binding (G9), SH WTP runtime (G10).

STOP conditions: none triggered.

G2 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G1.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G1/ (6 files: 01…06)





