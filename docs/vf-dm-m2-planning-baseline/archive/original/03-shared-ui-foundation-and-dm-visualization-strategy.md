# 03 — Shared UI Foundation and DM Visualization Strategy

**Date:** 2026-08-05

---

## 1. Target Module Architecture

```
ui/static/
├── shared/                          ← NEW: extracted from continuous
│   ├── svg-utils.js                 ← el(), namespace helpers (from icons.js)
│   ├── icons.js                     ← MODEL_ICON_MAP + DM icons added
│   ├── widgets.js                   ← 7 widget classes (from widgets.js)
│   ├── viewport.js                  ← zoom/pan/inspection (extracted from editor.js)
│   ├── api-client.js                ← fetch wrapper, error handling (new)
│   ├── ws-client.js                 ← WebSocket reconnect/polling (extracted from app.js)
│   └── styles/
│       ├── tokens.css               ← CSS variables (from styles.css :root)
│       └── layout.css               ← grid, sidebar, panels (from styles.css)
│
├── continuous/                      ← RENAMED: keep existing behavior
│   ├── continuous-app.js            ← was app.js, continuous-only state
│   ├── continuous-renderer.js       ← was editor.js, unchanged
│   ├── continuous-telemetry.js      ← telemetry table + alarms
│   ├── continuous-settings.js       ← was settings.js
│   └── continuous-builder.js        ← was builder.js
│
├── discrete/                        ← NEW: DM-specific
│   ├── dm-app.js                    ← DM application state, endpoint binding
│   ├── dm-renderer.js               ← Keyed SVG, DM node/edge types
│   ├── dm-snapshot-store.js         ← Snapshot buffer, delta detection
│   ├── dm-command-client.js         ← Command dispatch, result handling
│   ├── dm-run-controls.js           ← Start/step/pause/reset UI
│   ├── dm-inspection.js             ← Node/entity inspector panels
│   ├── dm-token-layer.js            ← Entity/WIP animation layer
│   └── layouts/
│       └── tipa-final-assembly-v1.js  ← Fixed coordinates for AP01–AP06
│
└── index.html                       ← Updated: tabs for continuous + discrete
```

---

## 2. Current-to-Target File Map

| Current File | Target | Action |
|-------------|--------|--------|
| `app.js` | `continuous/continuous-app.js` | Rename, strip DM references |
| `editor.js` | `continuous/continuous-renderer.js` | Rename, unchanged |
| `builder.js` | `continuous/continuous-builder.js` | Rename |
| `settings.js` | `continuous/continuous-settings.js` | Rename |
| `icons.js` | `shared/icons.js` | Extract, add DM icons |
| `widgets.js` | `shared/widgets.js` | Extract |
| `styles.css` | `shared/styles/tokens.css` + `layout.css` | Split tokens from component styles |
| `resizer.js` | `shared/resizer.js` | Extract |
| (none) | `shared/svg-utils.js` | New: extract `el()` from icons.js |
| (none) | `shared/api-client.js` | New: generic fetch wrapper |
| (none) | `shared/ws-client.js` | New: extracted from app.js |
| (none) | `discrete/*` | New: 8 DM modules |

---

## 3. Extraction Sequence

### Phase 1: Extract shared (safe — continuous unchanged)

1. Create `shared/` directory
2. Move `icons.js` → `shared/icons.js`
3. Extract `el()` to `shared/svg-utils.js`
4. Move `widgets.js` → `shared/widgets.js`
5. Extract CSS variables to `shared/styles/tokens.css`
6. Extract `resizer.js` → `shared/resizer.js`
7. Create `shared/api-client.js` and `shared/ws-client.js` (new)
8. Add characterization tests for continuous dashboard
9. **Gate:** 315 tests + smoke pass, dashboard renders correctly

### Phase 2: Rename continuous (clean separation)

1. Rename `app.js` → `continuous/continuous-app.js`
2. Rename `editor.js` → `continuous/continuous-renderer.js`
3. Rename `builder.js` → `continuous/continuous-builder.js`
4. Rename `settings.js` → `continuous/continuous-settings.js`
5. Update import paths in `index.html`
6. **Gate:** Dashboard functional, zero regression

### Phase 3: Add DM modules (parallel development)

1. Create `discrete/` directory
2. Build `dm-app.js` (DM state, endpoints)
3. Build `dm-renderer.js` (keyed SVG)
4. Build remaining DM modules
5. **Gate:** DM panels render, no continuous breakage

---

## 4. SVG Rendering Design

### Key Principles (violating `editor.js` patterns)

| editor.js (current) | dm-renderer.js (target) |
|---------------------|------------------------|
| `svg.replaceChildren()` every frame | Create elements once, update attributes |
| No stable sub-element IDs | `data-*` attributes on all updatable elements |
| Category-based color map | Node-type-based color map |
| Measurement/control/actuation edges | Material flow, rework, line-in/out edges |
| Single SVG layer | Separate layers: nodes, edges, tokens |

### Token Animation Layer

- Entity/WIP tokens are `<g>` elements with `transform` animation
- CSS `transition: transform 0.3s ease` for movement
- Tokens update position on snapshot change
- Animation is purely visual — simulation time is authoritative

---

## 5. Continuous Renderer Protection

| Risk | Mitigation |
|------|-----------|
| DM code changes break continuous SVG | Separate `<svg>` elements, separate renderer instances |
| Shared module changes break continuous | Version shared modules; continuous pins specific version |
| Global CSS conflicts | DM uses prefixed classes: `.dm-*` |
| `index.html` changes break layout | Characterization tests on DOM structure |
