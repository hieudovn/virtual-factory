# VF-vNEXT-G6 · Evidence 04 — ASSY + continuous additive integration (Issue #51 D/E)

## D — ASSY integration (additive, no ASSY UI rewrite)
- `static/assy_context.js` fetches the read-only `/api/ui/context` (TIPA) and
  renders the canonical hierarchy `TIPA -> ASSY (container) -> ASSY-SL01..06`
  through the shared navigator/breadcrumb (mounted in `#vf-hierarchy-section`).
- Selecting an executable `ASSY-SLxx` leaf binds to the EXISTING Frame A
  single-click selection seam (`ctrl._selectedSubLineId = leaf;
  ctrl._refreshCardStyles()`) — the exact path the ASSY UI already uses for
  card selection. It NEVER calls reset/step/reconstruction APIs and never
  touches ASSY SVG/inspector/station/WIP rendering (guarded by tests).
- `assy_demo.js` and the ASSY domain rendering are NOT modified; overview cards
  remain domain presentation; hydraulic/thermal are not treated as structure.
- Structural selection is side-effect free for runtimes: tests prove selecting
  sub-line paths repeatedly leaves every `TipaAssyFederation` runtime as the
  same object at the same simulation time (no reset/reconstruct).

## E — Continuous integration (truthful, minimal)
- `static/continuous_context.js` fetches `/api/ui/context/continuous` (ROOT-ONLY
  truthful context: workspace id `continuous_mvp_01`, empty hierarchy) and
  renders only the workspace-root breadcrumb/navigator — the continuous view
  does NOT invent a multi-level hierarchy.
- `app.js` is NOT modified; existing process SVG/telemetry/alarm/trend/builder/
  configuration behavior is retained (regression: `/status`, `/telemetry/latest`,
  `/alarms`, `/step`, editor/builder routes all green; continuous baseline 61).
- `index.html`/`continuous_context.js` contain no invented plant structure.

## H — Compatibility / no redesign
No existing routes or static-file references were removed or renamed; the new
endpoints are additive GETs. `tests/test_api.py` and the S04B route-gating tests
(`tests/test_demo_overview.py`) remain green.
