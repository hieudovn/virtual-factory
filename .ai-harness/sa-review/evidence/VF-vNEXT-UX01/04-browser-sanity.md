# VF-vNEXT-UX01 — Browser sanity (ASSY Structure / Model drawer & sidebar cleanup)

Server: `python -m virtual_factory.main serve --host 127.0.0.1 --port 8099` started detached from the
working tree at the UX01 head (pid file `.ai-harness/traces/r5_server.pid`). Page driven at
`/assy-demo?v=ux01` / `?v=ux01b` (the page HTML is heuristically cached), with the changed assets
cache-busted in the markup (`assy_demo.css?v=ux01`, `assy_context.js?v=ux01`) and CDP cache disabled.

## Required evidence — all 8 items observed

| # | Evidence item | Observed |
| --- | --- | --- |
| 1 | Default view has **no** Structural Context in the sidebar | `sidebarHasStructuralContext: false`, `sidebarHasHierarchyMount: false`; sidebar text = `LINE OVERVIEW | WIP ON LINE 6 | CREATED 0 | RELEASED 0 | HELD 0 | LEGEND | Raw Material … Material Flow | ↻ Reset Line | ⚠ Clear Alarms | ⬇ Export` → screenshot `shot-01-default-sidebar-clean.png` |
| 2 | Drawer **closed** by default | `drawerClass: "vf-drawer"`, `aria-hidden="true"`, rendered height `0`, trigger `aria-expanded="false"` |
| 3 | Drawer **open** | after `uiToggleStructure()`: `class="vf-drawer open"`, `aria-hidden="false"`, `aria-expanded="true"` → screenshot `shot-02-drawer-open-hierarchy.png` |
| 4 | Full hierarchy | rows: `TIPA (WORKSPACE)` → `ASSY Line (CONTAINER)` → `ASSY-SL01..ASSY-SL06 (EXECUTABLE)`; breadcrumb `TIPA`; meta line `WORKSPACE CONTAINER EXECUTABLE structural metadata only — selecting a container never implies execution` |
| 5 | Select sub-line **through the drawer** | clicking the `TIPA/ASSY/ASSY-SL03` label → breadcrumb `TIPA / ASSY / ASSY-SL03`, Frame A card highlight moves to `ASSY-SL03` → screenshot `shot-03-subline-selected-from-drawer.png` |
| 6 | Same run / session / time before-after | identity `CANONICAL SESSION TIPA · run TIPA-0001 · scenario tipa-default · profile tipa-assy-happy_path` **identical**, `CANONICAL STEP 000` **identical**, `/assy-demo/sub-lines` JSON **byte-identical** (`identical: {identity: true, step: true, subLines: true}`) |
| 7 | Frame A / Frame B no regression | Frame A = 6 cards before/after; double-click a card → `#frame-b` `display:flex`, `#frame-a` `display:none`, `#fb-sub-line-id = ASSY-SL04`, 150 station nodes + 16 WIP nodes rendered; `closeFrameB()` returns to Frame A → screenshots `shot-04-frame-b-no-regress.png`, `shot-05-frame-b-after-drawer-selection.png` |
| 8 | No severe console errors | full flow (load → open drawer → select SL04 → open Frame B → close → back to Frame A): `consoleErrors: []`, `severeConsoleErrors: []` |

## Post-flow state

`frameABack: true`, `drawerClosed: true`, `sidebarClean: true`, identity/step unchanged.

## Verdict

0 BLOCKER, 0 MAJOR, 0 MINOR. The structural context is an on-demand, presentation-only surface; the
sidebar keeps Line Overview / Legend / Actions; Frame A and Frame B are unchanged.
