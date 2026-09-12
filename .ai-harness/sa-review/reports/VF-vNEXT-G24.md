# VF-vNEXT-G24 — Multi-Workspace UI Switching + Monitoring Shell

Gate: `VF-vNEXT-G24`
Base (required): `320fc4ec1cfcf3b3ebb9566dbc79b3219ab2a33d` (G23 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Bring the G23 workspace registry/session selection onto the current FastAPI +
static HTML/CSS/JS UI as a small multi-workspace switching + monitoring shell.
UI is observer/controller only; the domain runtime remains the truth owner.

## Implemented (additive, isolated)

- `src/virtual_factory/ui/workspace_monitor.py` — headless `WorkspaceMonitor` +
  `build_platform_registry()` (G23 registry + G22 sessions).
- `src/virtual_factory/ui/api.py` — G24 endpoints (`/workspaces` shell page,
  `/vnext/workspaces`, `/vnext/workspaces/select`,
  `/vnext/workspaces/{id}/view`, `/vnext/workspaces/{id}/control`).
- `src/virtual_factory/ui/static/workspace_shell.{html,js,css}` — shell page.
- `src/virtual_factory/shwtp/expansion.py` — read-only
  `ShwtpPlantSlice.monitor_rows()` (observer projection only).
- `tests/test_vnext_g24_workspace_ui.py` (30 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G24 gate context +
  `g24_workspace_shell` group.

## Required semantics proven

- selector from backend registry (deterministic, registration-order independent);
- select TIPA -> TIPA session monitor that reuses the existing six-sub-line
  ASSY UI/runtime (`ui_page: /assy-demo`), no re-implemented visual;
- select shwtp -> accepted G21 5-scope slice
  (RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108) with live flow/tank values;
- switching never mutates the inactive workspace session;
- each view exposes the minimum monitor fields (identity, session state, sim
  time/step, structure, values, trace);
- run control acts only on the selected workspace/session;
- unknown workspace/session/action fails closed (service + HTTP 4xx);
- SH-WTP assumed topology/fidelity is never presented as site truth
  (`site_truth: false`, `assumed_topology`, fidelity/status badges);
- static shell page + endpoints served;
- G23 registry + G22 session semantics unchanged.

## Frozen boundaries preserved

G23 registry; G22 sessions; G21 slice; runcontrol untouched (no SH-WTP
reference); TIPA ASSY. No gateway routing, no MQTT/Kafka/production export, no
MES/PIM change, no G4 redesign, no domain semantics change, no T110/Line2.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G24: 30 passed.
- Full suite: PASS (see trace `g24_baseline.json`).
- Complete canonical vNext baseline
  (g1_workspace ... g23_workspace_registry, g24_workspace_shell, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G24/01-workspace-shell.md`
