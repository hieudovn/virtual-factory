# VF Cross-Workspace UI Consistency Audit

Audit type: **REVIEW / REPORT ONLY** (Issue #83 SA amendment comment `5643565581`).
No redesign, no SH-WTP change, no generic-dashboard replacement of the ASSY 2D view, no
second UI/runtime authority. All findings below are based on reading the current product
code/routes and on a compact live-browser pass (see
`evidence/VF-vNEXT-R4/07-browser-sanity.md` and its screenshots).

Architecture principle applied:

> Unified VF product experience != identical domain layout.
> Common shell, identity, navigation, lifecycle and platform status should be coherent;
> domain simulation canvases may differ according to archetype.

## 1. MUST BE COMMON

| Element | Current shared implementation | Note |
|---|---|---|
| Platform shell chrome + workspace selector | `ui/static/workspace_shell.{html,js,css}` served at `/workspaces`; registry-backed selector (`GET /vnext/workspaces`) | One shell for both workspaces |
| Workspace / run / scenario identity block | `workspace_id`, `run_id`, `scenario_id` (+ `description`) in `_base_view`; the rich ASSY page mirrors it in `#vf-canonical-identity` | Same field names/order |
| Shared run-control vocabulary | Shell: `▶ STEP`, `↻ RESET`, `■ STOP`, `♻ NEW ATTEMPT`, `⟲ REPLAY` → `POST /vnext/workspaces/{id}/control {action}`; rich ASSY: `RESET / STEP / AUTO / PAUSE` bound to the same session | Same action names, same session semantics |
| Identity/authority statement | `authority: canonical_tipa_runtime_session`, `legacy_runtime_authority: false`, `site_truth: false` on canonical payloads; `ui_note` explaining the shared session | Consistent wording |
| Provenance / fidelity labelling | SH-WTP: `fidelity` + `status` columns + "NOT site truth; PIM remains authoritative"; TIPA: `site_truth: false` + synthetic-profile provenance | Both are honest about non-site truth |
| Lifecycle state vocabulary | `created / running / paused / stopped / failed` everywhere (`RunState`), surfaced in both UIs | Single vocabulary |
| Error / deferred conventions | `{status, detail|reason, authority, legacy_runtime_authority}` shaped JSON with 400/404/409 codes; empty `DEFERRED_FEATURES` after R4 | Uniform fail-closed shape |

## 2. MAY BE DOMAIN-SPECIFIC

| Aspect | TIPA ASSY | SH-WTP | Why it may differ |
|---|---|---|---|
| Domain canvas | Frame A six-line overview cards + Frame B 12-station 2D discrete conveyor with WIP tokens, motion and genealogy | No dedicated canvas page (`ui_page: None`); monitor table of scopes/units with fidelity/status and key values | Discrete-flow vs process-unit archetype |
| Drill-down | Card → sub-line detail (Frame B), station/WIP inspector, event strip | Scope rows → values table (registry/monitor hierarchy) | Different structural hierarchy |
| Fault/interaction surface | jam / recover / run-to-terminal / OEE read / scenario fresh-run | none (not in SH-WTP scope) | Domain capability, not shell concern |
| Identity extras | `profile_id`, sub-line ids, projection epoch/namespace | `assumed_topology`, inbound-link assumptions, canonical unit ids | Domain semantics |
| Monitoring conventions | outbound Observation/MES read models (frames, delivery trace, OEE) | slice `monitor_rows()` (time/values per scope) | Different telemetry shape |

## 3. CURRENT INCONSISTENCIES

| # | Inconsistency | Evidence | Severity |
|---|---|---|---|
| I1 | The workspace-shell TIPA view has **no scenario selector** (read-only `scenario_id`), while the rich ASSY page now has an enabled scenario selector that starts a fresh canonical run. A user changing scenario in the rich UI sees the shell identity change (correct) but cannot initiate the change from the shell. | `ui/static/workspace_shell.js` (no scenario control); `workspace_monitor._base_view` exposes `scenario_id` read-only; `/assy-demo` selector enabled in R4 | MINOR |
| I2 | **SH-WTP has no dedicated UI page**: selecting `shwtp` shows the generic monitor table, and its `ui_page` is `None`, while TIPA advertises `ui_page: /assy-demo`. | `_shwtp_view_extra` (`ui_page: None`), absence of any SH-WTP static asset, browser pass on `/workspaces` | MINOR |
| I3 | Shell scope table **overflows horizontally** (`overflow_x = 50`) at narrow (652 px) viewports; the rich ASSY page does not (`overflow_x = 0`). | browser measurement on the SH-WTP shell view | MINOR |
| I4 | Shell run-control buttons are disabled purely by session state (`created`), whereas the rich page's controls (jam/recover/terminal/OEE) are always enabled and fail closed server-side with a `detail` message shown in the canonical note. Two different "unavailable" presentations. | `run_control_context.js` capability-driven disabling vs `assy_demo.js` note-based failure surfacing | OBSERVATION |
| I5 | Terminology drift for the same concept: shell says "kind / role" + "fidelity"/"status"; the rich ASSY inspector says "variant"/"line state"/"effective scenario". Neither is wrong, but no shared legend exists across pages. | shell `SCOPE / UNIT STRUCTURE` table vs Frame B inspector labels | OBSERVATION |
| I6 | The legacy G7 run-control context block is included by `/assy-demo` but is structurally unused there (it was the source of the R2V 404); after the R4 client guard it is hidden silently. | `assy_demo.html` script include; `run_control_context.js` canonical-page guard | OBSERVATION |

No BLOCKER or MAJOR inconsistency was found; nothing required an architectural change, so
the audit did not stop the gate.

## 4. SEVERITY SUMMARY

| Severity | Count | Items |
|---|---|---|
| BLOCKER | 0 | — |
| MAJOR | 0 | — |
| MINOR | 3 | I1, I2, I3 |
| OBSERVATION | 3 | I4, I5, I6 |

## 5. RECOMMENDED OWNER / GATE

| # | Recommendation | Owner / gate |
|---|---|---|
| I1 | Add a shell-level scenario/new-run control that calls the SAME canonical fresh-run seam (`monitor.new_run` / `POST /assy-demo/scenario` semantics) — display-only today; do NOT invent a second run authority. | **R5** (shell/UI productization) — not touched in R4 (out of the bounded ASSY epicenter; the fresh-run seam already exists for reuse) |
| I2 | Decide whether SH-WTP gets a dedicated process-view page or remains a monitor-only workspace. | **R5 + SH-WTP expansion gate** (explicitly not authorized in R4) |
| I3 | Make the shell scope table responsive (wrap/min-width on the `details` column). | **R5 / UI productization** (shell is shared chrome, not ASSY-specific) |
| I4 | Unify the "unavailable action" presentation (single convention: disabled-with-reason vs note-based failure). | **R5 / UI productization** |
| I5 | Publish a short cross-workspace label/legend glossary in the shared shell. | **R5 / documentation + UI** |
| I6 | Either drop the legacy G7 include from `/assy-demo` or keep the guard until the legacy context is retired. | **R5** (legacy decommissioning is explicitly R5 scope) |

## 6. NO-REDESIGN RECOMMENDATION

Keep the domain-specialized canvases (ASSY discrete 2D vs SH-WTP process units) and
converge on the **platform level** only:

1. one shell/chrome, one workspace selector, one identity block (workspace/run/scenario);
2. one run-control + lifecycle vocabulary (`created/running/paused/stopped/failed`,
   STEP/RESET/STOP/NEW ATTEMPT/REPLAY) bound to the workspace's single session;
3. one authority/provenance/status language (`authority`, `legacy_runtime_authority`,
   `site_truth`, fidelity labels);
4. one navigation grammar (selector → workspace view → domain drill-down), with the
   domain view free to be an overview grid (ASSY Frame A) or a unit/scope table (SH-WTP);
5. one failure/availability convention.

This preserves the accepted rich ASSY experience (and its 2D parity) while making the VF
product feel like one coherent tool across workspaces. No implementation was performed in
this audit.
