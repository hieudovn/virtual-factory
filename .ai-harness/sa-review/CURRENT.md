# SA REVIEW INBOX

Task: VF-ARCH-04-C01
Status: READY FOR SA REVIEW (C01: hierarchy lossless with ARCH-01, Step execution-mechanism neutral, command-level/reset semantics preserved)
Parent: Issue #39 VF-vNEXT-ARCH (prerequisite: ARCH-03 #42 CLOSED as completed)

Gate type:
Architecture / design gate — documentation & evidence only (no production
implementation)

Architecture baseline:
ARCH-01 @ feature/vf-arch-01 41903e186e96a05726483e4a17b9ac2d9cd56655
ARCH-02 @ feature/vf-arch-02 40454487acb4d5667872168a88c8b742c29cb975
ARCH-03 @ feature/vf-arch-03 392401bdfaf1ee2acf4ebcd204dbcfa419359e4c
Production baseline: canonical main @ f5261c8 (unchanged; not merged)

Target principle: Unified architecture != identical layout.

Frozen decisions:
- Platform Shell: one shared chrome (context strip, global nav,
  breadcrumb/hierarchy, run/scenario visibility, floating control slot, health
  surface, workspace/scope switching). Anti-responsibilities: never owns domain
  truth; never duplicates monitoring state; never a God UI; never hosts
  domain/plant controls; never hard-codes by workspace name; never imposes
  identical layout.
- Hierarchy + context: Workspace -> Scope -> Object path + run/scenario; tree =
  structure, graph = connectivity; container vs executable scope; federated
  child independently addressable; selected object != selected scope; no
  workspace-name hard-coding. ASSY lossless ARCH-01 mapping: TIPA = Workspace,
  ASSY = child Simulation Scope, ASSY-SL01..06 = child Simulation Scopes,
  station/AP/WIP/carrier = Simulation Objects.
- Floating Simulation Control: minimal run-control primitive — Time, Run/Pause,
  Step, Reset, Speed + compact run/scenario context. Excludes scenario editor,
  replay editor, domain process controls, plant-control actions.
  Context-aware but command-semantics preserving: create/start/stop = workspace
  orchestration, pause/resume/step = scope execution actions; Step =
  execution-mechanism neutral; Reset state = in-context, never erases run
  history; displays effective command target; commands via ARCH-02 interfaces.
- Context Inspector: object-centric, projection-only. Generic tabs: Overview,
  State, Signals, current-run Live Trend, Events/Alarms, Actions,
  Evidence/Provenance + capability-driven domain extensions (ASSY:
  Quality/Genealogy/Checklist/Retest/Reinspect; Continuous: Process/Control/
  Balance/Quality/Parameters; Batch: Recipe/Phase/Material/Hold-Release/
  Genealogy). Not a second domain state store.
- Monitoring: scope-centric, projection-only, 0..N views per scope. Widget
  categories: numeric/text, status/boolean, table, alarm list, event timeline,
  live chart, gauge/level/bar, equipment card, quality summary. Live chart =
  bounded current-run Live Series (not Historian); Alarm List = projection
  (not an independent store).
- Inspector vs Monitoring: "Object X ra sao?" vs "Scope/Area Y ra sao?" — same
  facts, different perspective, no duplicate mutable state.
- Archetype presentation patterns: Discrete (line/sub-line/station/WIP),
  Continuous (process/equipment/instrument, monitoring/analysis), Batch
  (recipe/phase/material). Patterns, not mandatory layouts.
- Capability-driven UI: available / not_applicable / not_ready / restricted /
  degraded / error / required-missing -> visibility/enablement/transparency
  matrix; never hard-coded by workspace name.
- Health/readiness presentation: UI displays readiness + shows blockers +
  navigates to source; never invents score, upgrades, hides blocker, or becomes
  evaluator.
- Action authority: simulation / runtime-model / plant-operational labels;
  no implied plant control; all mutations via ARCH-02 interfaces.

Conceptual mappings:
- ASSY = reference Discrete Experience, preserved without loss or rewrite
  assumptions (Shell / Inspector / Monitoring mapping); unchanged until ARCH-05.
- SH WTP = Continuous conceptual mapping (area/equipment/instrument; process/
  control/balance/quality) — illustrative only, no invented site truth.

C01 corrections applied:
- Hierarchy restored to ARCH-01 lossless TIPA/ASSY mapping (ASSY not retyped as
  Workspace; sub-line not downgraded from Scope to Object; standalone demo =
  presentation precedent only).
- Step is execution-mechanism neutral (one authorized advancement per the active
  executable scope/runtime contract; no discrete scheduler assumption).
- Floating Control is context-aware but command-semantics preserving
  (create/start/stop = workspace orchestration; pause/resume/step = scope
  execution actions; reset state in-context, never erases run history;
  effective command target displayed explicitly).

STOP conditions: none triggered.

Production code changed: NO
ARCH-05 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-04.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-04/ (9 files: 01…09)





