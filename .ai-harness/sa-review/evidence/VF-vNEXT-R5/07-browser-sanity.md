# VF-vNEXT-R5 — Browser sanity (implemented gate)

Server: `python -m virtual_factory.main serve --host 127.0.0.1 --port 8099` started detached from the
working tree at the R5 implementation head (pid file `.ai-harness/traces/r5_server.pid`).

Browser driving notes (reused from R2V/R4): the harness browser caches static JS aggressively
with no cache-bust, so the shell assets now carry `?v=r5` (the shell document itself was also
requested as `/workspaces?v=r5`). Playwright's stability check can time out on the run bar because
the 3 s poll mutates attributes; the controls were therefore driven programmatically
(`$eval(... .click())`), which is equivalent for a DOM button.

## 1. Workspace shell — `/workspaces` (canonical product path)

| Check | Result |
| --- | --- |
| Workspace selector | `TIPA`, `shwtp` (registry-backed, no continuous workspace) |
| Scenario selector (I1) | enabled with the 5 canonical ids: `tipa-default`, `tipa-happy-path`, `tipa-ap06-retest`, `tipa-ap08-reinspect`, `tipa-failed-final` |
| NEW RUN button (I1) | enabled for TIPA, `title` = "Start a fresh canonical run with the selected scenario (TIPA only)" |
| Run-control buttons (I4) | STEP enabled for `created`; every button carries `aria-disabled` + an explicit `title` reason when unavailable |
| Scope/structure tables (I3) | rendered inside `.ws-table-scroll` wrappers; **horizontal overflow = 0 px** at the harness viewport (~652 px) |
| Shared glossary (I5) | present in the footer with STEP / RESET / NEW ATTEMPT / NEW RUN / REPLAY / HOLD / JAM / OEE |
| NEW RUN with `tipa-failed-final` | **TIPA-0002** created, identity + session cards show `run_id TIPA-0002`, `scenario_id tipa-failed-final` (fresh canonical run via the shared run-id authority) |
| Screenshot | `shot-shell-newrun.png` |

## 2. Rich ASSY page — `/assy-demo` (canonical rich 2D retained)

| Check | Result |
| --- | --- |
| Canonical identity bar | `CANONICAL SESSION TIPA · run TIPA-0002 · scenario tipa-failed-final · profile tipa-assy-failed_final` — **the same session the shell just started**, with the attempt-bound profile (R5a-1) |
| Legacy G7 include (I6) | `legacyIncludePresent: false` — `run_control_context.js` is no longer mounted |
| Console errors | **0** (previously the R2V MINOR `404 /vnext/runs/current?workspace=TIPA`) |
| Frame A | 6 sub-line cards (`ASSY-SL01..ASSY-SL06`), each with the 12 stations (PRE-ASSY, AP01–AP11 incl. `AP04 (JOIN)`, `AP06 (TEST)`, `AP08 (VISION)`, `AP11 (FINAL)`), WIP/OUT/DW counters, `t=240s`, "↗ Double-click for detail" |
| Canonical STEP | `CANONICAL STEP 002` after STEP clicks on the shared session |
| Screenshot | `shot-assy-frame-a.png` |

## 3. Verdict

- No console errors on either canonical page.
- The shell scenario/NEW RUN control and the rich 2D page operate on ONE canonical session
  (TIPA-0002) with the correct attempt-bound profile.
- No legacy include, no legacy route traffic.
- 0 BLOCKER, 0 MAJOR, 0 MINOR defects observed in this sanity pass.
