# VF-vNEXT-G24 — Multi-Workspace UI Switching + Monitoring Shell — Evidence

Gate: `VF-vNEXT-G24` · Implementation gate (UI shell over G23 registry + G22 sessions).
Base: `320fc4ec1cfcf3b3ebb9566dbc79b3219ab2a33d` (G23 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/ui/workspace_monitor.py` — headless (no fastapi import at
  top) shell authority:
  - `build_platform_registry()` -> a G23 `WorkspaceRuntimeRegistry` registering
    the two accepted workspaces (shwtp + TIPA) with the accepted G22 session
    factories.
  - `WorkspaceMonitor` keeps ONE live `RuntimeSession` per workspace (created
    lazily via `registry.select`); selection never mutates/resets the inactive
    workspace's session; `control(workspace_id, action)` applies step/reset/
    stop/new_attempt/replay to that workspace's session only; unknown workspace
    or action fails closed.
  - `view(workspace_id)` returns a read-only monitor payload:
    workspace identity + description, session (run/scenario/state/step_count/
    last_time_s), simulation time/step, scope/unit structure, key current
    values/status, live trace tail, site-truth basis + assumed-topology list
    (SH-WTP), and a `ui_page` affordance (TIPA -> `/assy-demo`).
- `src/virtual_factory/ui/api.py` — G24 endpoints (additive):
  `GET /workspaces` (shell page), `/vnext/workspaces` (registry-backed selector
  source), `/vnext/workspaces/select`, `/vnext/workspaces/{id}/view`,
  `/vnext/workspaces/{id}/control`. Unknown workspace/session/action -> 4xx.
- `src/virtual_factory/ui/static/workspace_shell.{html,js,css}` — the shell
  page: workspace selector from the backend registry; TIPA reuses the existing
  six-sub-line ASSY UI (`/assy-demo`); shwtp shows the accepted G21 5-scope
  slice monitor (RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108) with
  fidelity/status badges; shared run bar targets the selected workspace only.
- `src/virtual_factory/shwtp/expansion.py` — `ShwtpPlantSlice.monitor_rows()`
  (read-only, detached per-scope observer rows). No physics/domain-semantics
  change; no runcontrol change.

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| selector from backend registry | `GET /vnext/workspaces` -> registry metadata; deterministic `("TIPA","shwtp")` |
| TIPA reuses existing 6-sub-line ASSY UI/runtime | TIPA view has 6 sub-line structure + `ui_page: "/assy-demo"`; monitor only (no re-implemented visual) |
| shwtp shows accepted G21 5-scope slice | view structure = RAW-INTAKE, T100, T106, T108, DIST-P108 (order preserved) + live tank/flow values via `monitor_rows()` |
| switching does not mutate inactive session | step shwtp, switch TIPA, switch back -> shwtp step_count unchanged |
| each view minimum fields | identity + session + simulation + structure + values + trace present for both workspaces |
| control only affects selected workspace | control("shwtp","step") leaves TIPA session step_count unchanged |
| unknown workspace/session/action fails closed | `WorkspaceMonitorError` + HTTP 404/400; registry `WorkspaceRegistryError` |
| SH-WTP not presented as site truth | view `site_truth: false`, `assumed_topology` list, per-scope fidelity/status badges, `ui_page: null` |
| static shell page + endpoints served | `GET /workspaces` 200; js/css present; selector/control wired to `/vnext/workspaces*` |
| G23/G22/G21 unchanged | registry fresh-session independence; slice/session/TIPA advance; constants unchanged; full suite green |

## 3. Preserved / unchanged

G23 registry semantics; G22 sessions; G21 slice; runcontrol untouched (still no
SH-WTP reference); no gateway routing / MQTT / export / MES-PIM / G4 / domain
semantics / T110 / Line2 change. UI is observer/controller only.

## 4. Test evidence

- `tests/test_vnext_g24_workspace_ui.py` — 30 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G24.md`).
