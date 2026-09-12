# VF-vNEXT-G6 · Evidence 03 — Navigator + breadcrumb primitives (Issue #51 B/C)

`src/virtual_factory/ui/static/hierarchy.js` — shared plain-JS primitives
(no framework; one global `window.HIERARCHY`).

- `HIERARCHY.renderNavigator(mount, data, opts)` — nested navigator:
  workspace root row, recursive scopes, expand/collapse carets, `container`
  vs `executable` badge rendered from the G1 capability booleans, and
  path-qualified selection (`dataset.path` = canonical path string). Container
  selection is allowed (context) and never implies execution.
- `HIERARCHY.renderBreadcrumb(mount, pathString, opts)` — segment breadcrumb
  from the canonical path string (`TIPA / ASSY / ASSY-SL01`); each non-leaf
  segment is a path-qualified button.
- `HIERARCHY.executableScopePaths(data)` — flat list of executable scope paths.

Domain-agnostic by construction and by test: the file contains NO plant/line/
variant/depth literals (`hydraulic`, `thermal`, `ASSY-SL`, `AP0`, `TIPA` are
absent from its source). Ordering is the JSON/G1 order (already deterministic).
No domain SVG/inspector/station logic and no runtime mutation.

Additive wiring (mounts + script tags only; existing controllers untouched):
- `assy_demo.html` → `#vf-hierarchy-section` (crumb + navigator) inside the
  sidebar, loads `hierarchy.js` + `assy_context.js`.
- `index.html` (continuous) → `#vf-context-section` (crumb + navigator) in the
  sidebar, loads `hierarchy.js` + `continuous_context.js`.
- Additive CSS appended to `assy_demo.css` and `styles.css` (`.vf-context-*`,
  `.vf-hierarchy-*`), default-hidden until a script renders content.
