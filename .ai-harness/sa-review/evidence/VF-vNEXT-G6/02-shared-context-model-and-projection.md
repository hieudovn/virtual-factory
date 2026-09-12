# VF-vNEXT-G6 · Evidence 02 — Shared context model + read-only projection (Issue #51 A)

`src/virtual_factory/ui/hierarchy.py` — pure read-only projection of the
accepted G1 Workspace/Scope authority for the UI.

- `simulation_scope_to_dict(scope)` — recursive: `scope_id`, canonical
  `path` (`StructuralPath.as_string()`), `mode`, `container_only`,
  `executable_capable`, `archetype`, `display_name`, `objects`, `children`.
- `workspace_to_dict(workspace)` — `workspace_id`, `path`, `display_name`,
  `description`, recursive `scopes`.
- `structural_context(workspace, *, scope_path=None, object_id=None)` —
  read-only selection context:
  - workspace-level when no scope path (monitoring context);
  - scope-level when a scope is selected (container-only allowed but never
    implies executability; `executable_controls_implied=False`);
  - object-level ONLY when `object_id` resolves in the SELECTED scope
    (Inspector context). No object is ever fabricated.
- `parse_path` / `_resolve_scope` — path-qualified; bare ids are never lookup
  authority; unknown paths fail closed (`UiHierarchyError`).
- `root_only_context(workspace_id, ...)` — truthful minimal context when no
  authoritative multi-level G1 hierarchy exists (continuous): a workspace root
  with NO invented nested scopes.

Rules satisfied:
- derived from G1 structural authority only (no second hierarchy model);
- canonical full `StructuralPath` preserved internally and in every `path`;
- bare local ids are display labels only (tests prove duplicate local ids under
  different parents raise on bare-id lookup);
- no PIM canonical identity fabrication;
- no runtime state mutation (functions are pure; Workspaces are frozen).

## Read-only API (additive GET endpoints in `api.py`)
- `GET /api/ui/hierarchy?workspace=TIPA` — canonical TIPA structural tree.
- `GET /api/ui/context?workspace=TIPA&path=...&object_id=...` — selection
  context (default: workspace). Invalid path → 400; unknown workspace → 404.
- `GET /api/ui/context/continuous` — truthful ROOT-ONLY continuous context
  (workspace id `continuous_mvp_01`, empty hierarchy).
All three are read-only GETs; no run-control semantics.
