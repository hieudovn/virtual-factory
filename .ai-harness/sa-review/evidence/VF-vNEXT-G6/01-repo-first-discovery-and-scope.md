# VF-vNEXT-G6 · Evidence 01 — Repo-first discovery + scope

## Authorization
GitHub Issue #51 (`VF-vNEXT-G6 — Shared Hierarchical UI Primitives`). Required
base `d1419cec3bd87d283ee9dcb03c412479a794359d` (accepted G5-C01 head). Branch
`feature/vf-vnext-g6`. Model Flash.

## Repo-first facts
- Frontend is plain FastAPI + static HTML/CSS/JS (no framework build step).
  Static files live in `src/virtual_factory/ui/static/` mounted at `/static`;
  pages `GET /` → `index.html` (continuous dashboard) and
  `GET /assy-demo` → `assy_demo.html` (ASSY UI). `app.js` = continuous main
  controller; `assy_demo.js` = self-contained ASSY controllers
  (Frame A `ctrl` overview, Frame B `ctrlB` detail) with SVG primitive library.
- `api.py` (`create_app` factory) serves monitoring JSON, editor/builder APIs,
  and ASSY demo routes; S04B overview/detail endpoints are gated by
  `VF_ENABLE_S04B_OVERVIEW`.
- No existing G1 Workspace/Scope JSON serializer; no workspace/scope concept in
  the UI; no hierarchy endpoint. G1 `Workspace`/`SimulationScope`/
  `StructuralPath` are frozen and provide no `to_dict`.
- G5 federation provides the canonical TIPA structure
  (`build_tipa_workspace`, `sub_line_path`, `assy_scope_path`) — G1 authority.
- Continuous plant id = `continuous_mvp_01`; the continuous runtime has NO
  authoritative multi-level G1 hierarchy (single plant, no scope tree).
- No browser/playwright tests exist; existing UI tests are FastAPI TestClient
  contract tests (`tests/test_api.py`) plus route-gating scans
  (`tests/test_demo_overview.py`). G6 uses the same static/contract approach.

## Scope decisions (conservative; recorded)
- All production work is additive inside `src/virtual_factory/ui/`:
  new `hierarchy.py` (read-only projection), new static JS
  (`hierarchy.js` shared primitives; `assy_context.js`, `continuous_context.js`
  additive adapters), additive HTML mounts + script tags in `index.html` and
  `assy_demo.html`, additive CSS in `styles.css`/`assy_demo.css`, and read-only
  GET endpoints in `api.py`. `app.js` and `assy_demo.js` are NOT modified
  (ASSY/continuous domain rendering preserved).
- Hierarchy is derived from G1 `StructuralPath` only; no second model; no PIM
  fabrication; no runtime mutation. Continuous uses a truthful ROOT-ONLY
  context (no invented scopes). No G7 run-control/replay API.

## Changed files (scope)
All within the G6 allowlist: `src/virtual_factory/ui/api.py`, new
`src/virtual_factory/ui/hierarchy.py`, `static/hierarchy.js`,
`static/assy_context.js`, `static/continuous_context.js`, `static/index.html`,
`static/assy_demo.html`, `static/styles.css`, `static/assy_demo.css`,
`tests/test_ui_hierarchy.py`, plus G6 evidence/report/CURRENT and the task
contract. No file outside the allowlist was modified.
