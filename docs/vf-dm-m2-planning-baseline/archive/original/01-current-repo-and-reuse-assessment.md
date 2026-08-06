# 01 — Current Repository and Reuse Assessment

**Date:** 2026-08-05  
**Baseline:** `d5b345b` on `main`  
**Scope:** M2-S00 planning prerequisite

---

## 1. Repository State

| Item | Value |
|------|-------|
| HEAD | `d5b345b` |
| Branch | `main` |
| Python | 3.11.9 |
| Tests | 315 passed, 0 failed |
| CI | None configured |
| API/Dashboard | Functional (continuous process only) |
| Discrete kernel | Merged, not yet wired |

---

## 2. Backend Reuse Assessment

### 2.1 `RuntimeService` (`ui/runtime_service.py`)

**Classification: continuous-specific; do not reuse**

| Aspect | Finding |
|--------|---------|
| Engine ownership | Hard-coded to `SimulationEngine` via `create_engine(config, ...)` |
| State | `latest_snapshot`, `is_running`, `loop_task` — all single-engine |
| Lifecycle | `reset()`, `step_once()`, `start_loop()`, `stop_loop()` — continuous only |
| Telemetry | `_latest_frame_values()` returns `SignalValue` list |
| MQTT/OPC UA | Publishes `SignalValue` frames |
| DM reuse | **None** — must build separate `DiscreteRuntimeService` |

**Action:** Create `DiscreteRuntimeService` as a parallel class, not a subclass. Share only `create_engine()` factory pattern.

### 2.2 `main.py` (FastAPI application)

**Classification: reuse-after-extraction**

| Aspect | Finding |
|--------|---------|
| FastAPI app | Single `app = FastAPI()` with static mount |
| Endpoints | All under `/` — `/status`, `/start`, `/stop`, `/step`, `/run-steps`, `/reset`, `/telemetry/latest`, `/alarms`, `/api/plant-graph`, `/api/pid/*` |
| WebSocket | `/ws/telemetry` — continuous telemetry stream |
| CLI | `run_simulation()` — continuous-only |
| DM route | Add `/api/discrete/...` namespace |

**Action:** Keep existing endpoints unchanged. Add DM endpoints in separate router under `/api/discrete/`. Add DM WebSocket under `/ws/discrete/`.

### 2.3 `SignalValue` (`telemetry/signal_value.py`)

**Classification: continuous-specific; do not reuse as DM snapshot**

`@dataclass(frozen=True, slots=True)` with fields: `name`, `value`, `unit`, `category`, `timestamp_s`, `quality`, `source`.

DM needs a richer snapshot type with entity/WIP state, not just industrial signal measurements. The frozen-dataclass pattern is reusable; the fields are not.

**Action:** Define `DMVisualizationSnapshot` with DM-specific fields. Reuse frozen-dataclass pattern.

### 2.4 `PlantConfig` / `SignalConfig` (`core/schema.py`)

**Classification: continuous-specific; do not reuse**

Pydantic v2 models for continuous process plants: equipment, sensors, controllers, actuators, signals with categories (`industrial_signal`, `controller_signal`, `actuator_feedback`, `internal_truth`, `industrial_event`).

DM needs separate schema for topology, routing, entity types, process definitions.

**Action:** Create separate DM schema package. No inheritance from `PlantConfig`.

### 2.5 `engine_factory.py` / `engine_contract.py`

**Classification: reuse-as-is (contract pattern only)**

`SimulationEngineProtocol` is `@runtime_checkable`. `create_engine()` returns continuous engine for `continuous_process` kind. DM engine registration is explicitly prohibited per SA mandate until architecture is approved.

**Action:** Pattern reusable. Do not register DM engine yet.

### 2.6 Discrete Kernel (`discrete/`)

**Classification: reuse-as-is — the foundation for M2**

`DiscreteClock`, `ScheduledEvent`, `FutureEventScheduler`, `RunContext` — all approved and merged. These are the building blocks for `DiscreteSimulationEngine`.

**Action:** No changes needed. Build `DiscreteSimulationEngine` on top of this kernel.

---

## 3. Frontend Reuse Assessment

### 3.1 `app.js` — Classification: continuous-specific; replace-for-DM

| Aspect | Finding |
|--------|---------|
| Global state | `APP.telemetry`, `APP.alarms`, `APP.socket` — all continuous |
| Endpoint coupling | Hard-coded to `/status`, `/start`, `/stop`, `/step`, etc. |
| WebSocket | `/ws/telemetry` with `SignalValue` frame |
| Rendering | `innerHTML` full rebuild of telemetry table |
| DOM refs | 35+ `id` references to continuous-only elements |
| Dependency chain | `APP` → `EDITOR`, `BUILDER`, `TRENDS`, `SETTINGS` — all globals |

**Action:** Do NOT fork `app.js`. Build parallel `dm-app.js` with its own state and endpoints. Extract shared utilities to `shared/` first.

### 3.2 `editor.js` — Classification: replace-for-DM

| Aspect | Finding |
|--------|---------|
| Rendering | `svg.replaceChildren()` — full DOM teardown on every frame |
| Zoom/Pan | ViewBox-based, functional, reusable pattern |
| Node types | Equipment, sensor, controller, actuator — continuous categories |
| Edges | Measurement, control, actuation edges — continuous vocabulary |
| Stable IDs | `data-id` on node groups — pattern reusable |
| Selection | Click → property panel with PID sliders — continuous |
| Drag | Node repositioning with transform — reusable pattern |

**Action:** Build new `dm-renderer.js` using:
- Same zoom/pan pattern (reuse concept)
- Keyed incremental updates (NOT `replaceChildren`)
- DM node types: source, buffer, workstation, checkpoint, sink
- DM edge types: material flow, rework, line-in/out
- Same `data-id` convention for stable identity
- Separate entity/WIP token layer

### 3.3 `builder.js` — Classification: continuous-specific; do not reuse

Asset placement and port connection for process diagrams. Useful as a **reference** for future DM layout editor but not for MVP.

**Action:** Defer. DM MVP uses fixed TIPA layout template.

### 3.4 `icons.js` — Classification: extract-shared

| Aspect | Finding |
|--------|---------|
| 10 equipment icons | tank, pump, valve, pipe, heat exchanger, fan, sensor, controller, actuator, flow/level/pressure transmitters |
| 5 action icons | alert, settings, play, stop, step |
| `el()` helper | Pure SVG element creation — fully reusable |
| `MODEL_ICON_MAP` | Model-type → icon lookup pattern — reusable |
| DM needs | Conveyor, robot arm, AGV, workstation, buffer, checkpoint icons |

**Action:** Move `el()` to `shared/svg-utils.js`. Extend `MODEL_ICON_MAP` with DM types. Add DM-specific icons.

### 3.5 `widgets.js` — Classification: extract-shared

7 reusable widget classes: `TankLevelGauge`, `ValueBar`, `TrendChart`, `SliderControl`, `ToggleSwitch`, `NumberSpinner`, `DataTable`. Pure DOM, no framework, consistent pattern.

All are DM-relevant: utilization bars, trend charts, parameter sliders, toggles for machine state, job tables.

**Action:** Extract to `shared/widgets.js`. Add DM-specific widgets as needed.

### 3.6 `styles.css` — Classification: extract-shared

| Aspect | Finding |
|--------|---------|
| CSS variables | 28 design tokens in `:root` — fully generic |
| Dark theme | `body.dark` override |
| Layout classes | `.app-shell`, `.sidebar`, `.main-area`, `.right-panel` |
| Widget styles | All `.tank-gauge-*`, `.value-bar-*`, `.slider-*` patterns |
| Table styles | `.telemetry-table` |

**Action:** CSS variables and layout patterns are directly reusable. DM adds its own renderer and token-layer styles. No need to fork.

### 3.7 `index.html` — Classification: reuse-after-extraction

Static shell with sidebar + process panel + right panel structure. The layout skeleton (`.app-shell`, `.sidebar`, `.main-area`, `.right-panel`) is directly reusable for DM.

**Action:** Add DM-specific panels via tab/route switching. Keep continuous panels intact.

---

## 4. Summary Classification Matrix

| File | Classification | Rationale |
|------|---------------|-----------|
| `runtime_service.py` | continuous-only | Single continuous engine ownership, `SignalValue` frames |
| `main.py` | reuse-after-extraction | Shared FastAPI, add `/api/discrete/` namespace |
| `signal_value.py` | continuous-only | DM needs richer snapshot |
| `schema.py` (PlantConfig) | continuous-only | DM needs separate topology/routing schema |
| `engine_factory.py` | reuse-as-is (pattern) | Contract pattern reusable; no DM registration yet |
| `engine_contract.py` | reuse-as-is | Protocol pattern |
| `discrete/` (kernel) | reuse-as-is | Foundation for M2 |
| `app.js` | continuous-only | Build parallel `dm-app.js` |
| `editor.js` | replace-for-DM | Full rebuild, continuous node types; new DM renderer |
| `builder.js` | continuous-only | Defer DM layout editor |
| `icons.js` | extract-shared | `el()`, `MODEL_ICON_MAP`, add DM icons |
| `widgets.js` | extract-shared | All 7 widgets DM-relevant |
| `styles.css` | extract-shared | All CSS variables, layout, dark theme |
| `index.html` | reuse-after-extraction | Layout skeleton reusable |
| `resizer.js` | extract-shared | Panel resize with localStorage |
| `settings.js` | continuous-only | Fault injection UI |

---

## 5. Extraction Sequence

```
Phase 1: Extract shared (before any DM UI code)
  1. Create ui/static/shared/ directory
  2. Move icons.js → shared/icons.js (add DM icons)
  3. Move widgets.js → shared/widgets.js
  4. Extract CSS variables to shared/tokens.css
  5. Extract el() to shared/svg-utils.js
  6. Add characterization tests for continuous dashboard

Phase 2: Build DM modules (parallel to continuous)
  7. Create ui/static/discrete/ directory
  8. dm-app.js (DM state, endpoints, WS)
  9. dm-renderer.js (keyed SVG, DM node types)
  10. dm-snapshot-store.js
  11. dm-command-client.js
  12. dm-run-controls.js
  13. dm-inspection.js
  14. layouts/tipa-final-assembly-v1.js

Phase 3: Integrate
  15. Update index.html with DM panels
  16. Add DM endpoint routing in main.py
  17. Add DiscreteRuntimeService
```

---

## 6. Continuous Dashboard Protection

| Risk | Mitigation |
|------|-----------|
| Extraction breaks continuous dashboard | Characterization tests before any extraction |
| Shared module changes break continuous | Version shared modules; continuous pins known version |
| DM code leaks into continuous panels | Separate directories, separate globals |
| Prototype code becomes production | DM code under `discrete/` from day one, with tests |

---

## 7. Key Findings for Architecture

1. **No virtual DOM or framework** — vanilla JS with direct DOM manipulation. DM can adopt the same approach for MVP.
2. **`editor.js` full rebuild is the biggest technical debt** — DM renderer must use keyed incremental updates from the start.
3. **30+ DOM `id` references in `app.js`** — tight coupling to continuous dashboard. DM must have its own DOM namespace.
4. **CSS variable system is clean and reusable** — 28 tokens cover all needs.
5. **Widget pattern is consistent and framework-agnostic** — easy to extend for DM.
6. **`RuntimeService` is a single-owner singleton** — DM needs its own parallel service.
7. **No authentication, no CI** — address in M2 planning.
