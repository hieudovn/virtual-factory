# VF-ARCH-04 · Evidence 01 — Current-state UI/product inventory

## 1. Scope of this inventory

Repo-first discovery of every UI seam that participates in the product
interaction surface, classified per Issue #43 into exactly five buckets:

| Bucket | Meaning |
|---|---|
| **R — reusable platform primitive** | Belongs to the frozen shared shell/primitive set (survives as a platform concept). |
| **D — ASSY-discrete domain UX** | Domain presentation that belongs to the Discrete/ASSY archetype experience, not to the shared shell. |
| **G — generic-legacy platform capability** | Today's generic continuous/SCADA dashboard: reusable in principle, but legacy layout; platform capability concept survives, the exact legacy layout does not. |
| **X — demo-only** | Demo scaffolding (Happy Path badge, hard-coded demo step, single sub-line MES page); never frozen as product architecture. |
| **N — implementation detail not to freeze** | Concrete DOM/CSS/JS detail; the *concept* is frozen, the implementation is explicitly not. |

## 2. Verified file-level seams

| File | What it does (verified) | Bucket |
|---|---|---|
| `src/virtual_factory/ui/api.py` | FastAPI app: static mount + generic SCADA routes + `/assy-demo/*` + `/demo-assy-mes/*` | R (route contract), N (routing impl) |
| `src/virtual_factory/ui/static/index.html` | Generic continuous SCADA shell: sidebar (Monitoring: Process Flow/Telemetry/Alarms/Trends; Configuration: Fault Injection/OPC…) + panes | G |
| `src/virtual_factory/ui/static/app.js` | Generic polling: `ALARM_SIGNALS`, `APP.telemetry`/`APP.alarms` Maps, reset, `initAll`/`refreshAll` | G (N for map impl) |
| `src/virtual_factory/ui/static/editor.js` | Process-flow graph editor (nodes/edges, `ALARM_COLOURS`, alarm overlay) | G |
| `src/virtual_factory/ui/static/assy_demo.html` | ASSY shell: `vf-topbar` (logo + scenario badge Frame A; sub-line id + variant + scenario Frame B; live status; demo step; overview/settings/help) | D |
| `src/virtual_factory/ui/static/assy_demo.js` | Frame A overview (sub-line cards grouped hydraulic/thermal) + Frame B per-sub-line detail + Context Inspector (`ctrlB`, `_subLineId`/`_selectedStation`/`_selectedWipId`/`_contextType` sso2/rso2/offline) + MotionEngine | D |
| `src/virtual_factory/ui/static/assy_demo.css` | ASSY visual styling | N |
| `src/virtual_factory/ui/static/demo_assy_mes.html` | Single sub-line MES demo page (ASSY-SL01) | X |
| `src/virtual_factory/ui/runtime_service.py` | Engine façade behind UI routes | R (concept: runtime façade), N (impl) |

## 3. Route inventory (from `ui/api.py`)

### 3.1 Generic continuous SCADA (legacy platform capability)

`/`, `/health`, `/status`, `/telemetry/latest`, `/telemetry/history`, `/alarms`,
`/step`, `/run-steps`, `/start`, `/stop`, `/reset`, `/ws/telemetry` (websocket),
`/api/plant-graph`, `/api/model-types`, `/api/fault`, `/api/opcua/status`,
`/api/ai/generate`, `/api/ai/parse`, `/api/config/current`, `/api/config/switch`.

Observation for ARCH-04:
- `/start`, `/stop`, `/step`, `/reset`, `/run-steps` are **global run controls
  living inside the legacy shell** — this is the existing precedent for the
  Floating Simulation Control, but today they are domain-agnostic and
  unscoped. ARCH-04 re-frames them as a context-aware, minimal primitive (see
  evidence 04).
- `/api/fault` is a **simulation action** (injects a simulated fault) — distinct
  from runtime-model commands. ARCH-04 preserves this distinction (evidence 08).

### 3.2 ASSY demo domain routes

`/assy-demo`, `/assy-demo/static/{filename}`, `/assy-demo/reset`, `/assy-demo/step`,
`/assy-demo/observations`, `/assy-demo/snapshot`, `/assy-demo/jam`,
`/assy-demo/recover`, `/assy-demo/run-to-terminal`, `/assy-demo/mes-messages`,
`/assy-demo/mes-trace`, `/assy-demo/version`, `/assy-demo/operation-command`,
`/assy-demo/station-action`, `/assy-demo/run-mode`, `/assy-demo/select`,
`/assy-demo/overview`, `/assy-demo/sub-lines`, `/assy-demo/sub-line/{sub_line_id}`.

Observation: `station-action`, `operation-command`, `run-mode`, `select`,
`jam`, `recover` are **runtime-model actions scoped to the ASSY domain** — they
belong to domain UX, not to the shared shell. This is the concrete precedent
that domain controls must NOT be promoted into global shell controls.

### 3.3 Single-sub-line MES demo routes

`/demo-assy-mes`, `/demo-assy-mes/reset`, `/demo-assy-mes/start`,
`/demo-assy-mes/pause`, `/demo-assy-mes/step`, `/demo-assy-mes/jam`,
`/demo-assy-mes/recover`, `/demo-assy-mes/snapshot`, `/demo-assy-mes/messages`.

Observation: demo-only scaffolding (hard-coded `ASSY-SL01` page). Not frozen.

## 4. UX affordance inventory (what the user can actually do today)

| Affordance | Where | Classification |
|---|---|---|
| Sidebar pane navigation (Process Flow / Telemetry / Alarms / Trends / Faults / OPC) | `index.html` | G → maps to Monitoring View Composition (scope-centric panes) |
| Run controls (start/stop/step/reset/run-steps) | `index.html` + `api.py` | R → maps to Floating Simulation Control primitive |
| Telemetry/alarm live panels | `index.html` + `app.js` | G → Monitoring projection |
| Process-flow graph with alarm colours | `editor.js` | G → scope-centric process view (Continuous archetype) |
| Frame A: sub-line overview cards (hydraulic/thermal groups, selected card) | `assy_demo.js` | D → Discrete archetype scope navigation |
| Frame B: per-sub-line line layout + status cards | `assy_demo.js` | D → Discrete archetype scope detail |
| Context Inspector (`ctrlB`) on station/WIP/offline context | `assy_demo.js` | D → the reference **Context Inspector** implementation |
| Overview / Settings / Help top-bar buttons | `assy_demo.html` | R (Shell chrome) |
| Scenario badge (HAPPY_PATH), demo step counter | `assy_demo.html` | X → maps conceptually to run/scenario context display, but demo-only values |
| MES message panel / trace | `demo_assy_mes.html`, `/assy-demo/mes-*` | D → Discrete archetype MES projection |

## 5. Cross-ARCH contract dependencies (already frozen, consumed here)

- **ARCH-01** (hierarchy): Workspace → Scope → nested Scope → Object; container vs
  executable scope; child federated but independently addressable. → evidence 03.
- **ARCH-02** (lifecycle/composition): run control semantics (start/pause/step/
  reset) are **workspace/scope-scoped commands through declared interfaces**; UI
  must not bypass them. → evidence 04, 08.
- **ARCH-03** (observation/event/capability/readiness): Monitoring and Inspector
  are **projections** over Observation/Event facts; capability state = the single
  authority for UI visibility/enablement; readiness = deterministic aggregation,
  never a hidden evaluator. → evidence 05, 06, 08.

## 6. Inventory conclusion

The repository already contains every precedent ARCH-04 needs, with no
conflicting accepted authority:

1. A legacy generic continuous shell (`index.html`/`app.js`/`editor.js`) that is
   the prototype of the **shared shell + Monitoring** but whose layout is legacy
   (not frozen).
2. An accepted **ASSY Discrete Experience** (`assy_demo.html`/`js`) with
   Frame A/B + Context Inspector — the reference Discrete UX to preserve.
3. Concrete separation of **simulation actions** (`/api/fault`) vs
   **runtime-model actions** (`/reset`, `/start`, `/stop`, `/step`,
   `/station-action`, `/operation-command`) — the precedent for action authority.
4. **No plant-control authority** anywhere — consistent with ARCH-04's rule that
   VF must never imply real plant control.
5. **No workspace-name hard-coding** in the ASSY UI's operation inspector
   (capability-driven dispatch precedent).

No STOP condition is triggered by the current state.
