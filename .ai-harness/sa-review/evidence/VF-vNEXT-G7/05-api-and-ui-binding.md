# VF-vNEXT-G7 · Evidence 05 — Minimal generic API + UI binding (Issue #52 D, E, 12, 15)

## API (`ui/api.py`, additive `/vnext/runs/*`)
- `POST /vnext/runs` — create run (`target_path` required; optional
  `scenario_id`/`model_id`/`profile`/`random_seed`) → 201 run record.
- `GET /vnext/runs/current` — active run or 404.
- `GET /vnext/runs/{run_id}` — status/context.
- `POST /vnext/runs/{run_id}/{start|step|pause|resume|stop|reset|restart|replay}`
  — every mutation requires an explicit `run_id`; stale/wrong → 404; invalid
  transition / replay-unavailable → 409; bad target → 400.

Responses expose run identity, lifecycle state, `target_path` (path-qualified),
`target_kind`, deterministic `effective_scopes`, `scenario_id` (when known),
`step_count`/`last_time_s` (only truthfully available), `last_result`/`failure`.
No fake readiness or fake replay capability.

Legacy `/step`, `/start`, `/stop`, `/reset`, `/assy-demo/*` are untouched.

## UI binding (`run_control_context.js`, additive)
- Hidden until a `/vnext/runs/current` run exists; shows path-qualified
  `target_path`, `target_kind`, state, truthful time, and effective scopes.
- Minimal Run/Pause/Resume/Step/Stop/Reset buttons drive the `/vnext/runs/*`
  seam only (never repoint legacy controls). Buttons are capability/state-driven
  (disabled when not applicable). Container/workspace targets are shown as
  orchestration targets (kind), never as executable.
- Mounted as a hidden `#vf-run-control-section` in `assy_demo.html`; additive
  CSS in `assy_demo.css`. Existing ASSY layout/domain rendering untouched.

Proven by tests: `TestApiSurface` (end-to-end lifecycle via HTTP, path-qualified
target, stale 404, replay-unavailable 409, container no-exec),
`TestContinuousAndReset` (continuous `/step`/`/telemetry/latest`/`/status` green),
`TestStaticUiAndNoG8` (additive JS, no legacy repointing, no G8 tokens).
