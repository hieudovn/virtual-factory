# VF-vNEXT-G26 — Browser Functional Validation Results

Environment
- Command: `python -m virtual_factory.main serve --host 127.0.0.1 --port 8099`
- URL: `http://127.0.0.1:8099/workspaces`
- Browser: VS Code integrated browser (Playwright-driven), desktop 1280x800 for
  layout checks; CDP `Network.clearBrowserCache` used before the post-fix run
  (static JS/CSS are cached by the browser; the repo's direct-serve pattern
  intentionally bypasses server-side caching, not the browser cache).

| # | Step | Result |
|---|---|---|
| A1 | Open `/workspaces` | PASS — page title "Virtual Factory — Workspace Shell"; layout renders |
| A2 | Selector sourced from backend registry | PASS — options: `TIPA — TIPA ASSY six sub-lines`, `shwtp — SH-WTP G21/G22 plant slice (5 scopes)` (GET `/vnext/workspaces`) |
| A3 | Initial load selects TIPA | PASS — identity `workspace_id=TIPA`, `run_id=TIPA-0001`, `scenario_id=tipa-default`; run-control target `TIPA` (after G26 fix) |
| A4 | Select TIPA | PASS — scope structure lists `TIPA/ASSY/ASSY-SL01..SL06` |
| A5 | STEP (TIPA) | PASS — session `running`, `step_count=1`, `last_time_s=120`; **6 live ASSY sub-lines** rendered (ASSY-SL01..SL06: sim time 120, conveyor `stopped`, WIP 0, motors 0, RSO2 buffer 0); trace shows 1 step with 6 participants |
| A6 | RESET (TIPA) | PASS — same `run_id`, `last_time_s=0`, trace cleared; STEP still advances |
| A7 | STOP (TIPA) | PASS — state `stopped`; STEP/RESET disabled by the UI (no invalid action possible) |
| A8 | NEW ATTEMPT (TIPA) | PASS — new `run_id` (TIPA-0012), state `created`, STEP re-enabled (in-UI recovery after STOP) |
| A9 | REPLAY (TIPA) | PASS — new `run_id` (TIPA-0011), state `created`, fresh attempt |
| A10 | Select shwtp | PASS — identity `shwtp`, `run_id=shwtp-0011`, `scenario_id=shwtp-g21-slice`; 5 scopes in order RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108 |
| A11 | STEP x3 (shwtp) | PASS — `step_count=3`, `last_time_s=3`; live values: T106 `inflow_m3_s=2`, `last_input_flow_m3_s=2`, `last_output_flow_m3_s=2`; T108 `inflow_m3_s=2`, `requested_outflow_m3_s=1.5`, `volume_m3`, `level_m`; trace 3 steps |
| A12 | Fidelity/status/assumed visible | PASS — per scope fidelity/status badges (`logical_only`/`first_order` x `accepted`/`scenario_assumed`); assumed note "NOT site truth; PIM remains authoritative"; DIST-P108 + RAW-INTAKE + T100 + T106 inbound link ASSUMED shown |
| A13 | Switch to TIPA and back | PASS — TIPA `step_count` unchanged (1) while shwtp was stepped; returning to shwtp shows `step_count=3` (inactive session not mutated) |
| A14 | Error conditions | PASS — `GET /vnext/workspaces/does-not-exist/view` -> 404; `POST .../control {action:"nope"}` -> 400; `POST /select {}` -> 400; `POST .../control {}` -> 400; server stayed up and responsive |
| A15 | Refresh / reload | PASS (after G26 fix) — selector repopulates from the registry; view + run-control target load immediately. Before the fix: the view waited up to one 3s poll and the run-control target stayed "no workspace" (see UX MINOR-1) |
| A16 | Browser console / runtime errors | PASS — no console errors/warnings and no unhandled promise rejections during the interaction pass. (Note: `ERR_CONNECTION_REFUSED` messages observed in an earlier window were caused by deliberately restarting the server mid-session — environmental, not a shell defect; they cleared after restart.) |
| A17 | Lifecycle actions backend-only vs UI | GAP FOUND + FIXED — backend exposes `new_attempt` and `replay`; the shell initially exposed only STEP/RESET/STOP. After STOP the session was terminal with no in-UI recovery, and deterministic replay was not demonstrable in-browser. See UX MAJOR-1. Now exposed: `NEW ATTEMPT`, `REPLAY`. |
| A18 | /assy-demo separation | PASS — link label "Open separate legacy ASSY demo UI (NOT this session)"; structure note "…NOT the same runtime or session… identity/state are not shared" |

Evidence artifacts (committed)
- `stability-results.json` (D — machine-readable)
- DOM/console values captured during A5/A11/A13/A14/A15 above
- Screenshots captured during the G26 session (TIPA live sub-lines; shwtp 5-scope
  live; desktop run-control bar). Screenshots are session artifacts (not
  committed to avoid binary bloat); the DOM text values above are the durable
  evidence.
