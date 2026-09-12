# VF-vNEXT-UX01 — ASSY Structural Context Drawer & Sidebar Cleanup

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `ASSY_STRUCTURE_UX_CONSISTENT`**

| Field | Value |
| --- | --- |
| Gate | VF-vNEXT-UX01 (Issue #87, authoritative SA task contract) |
| Gate type | UX-only correction — **no simulation-architecture change** |
| Branch | `feature/vf-vnext-ux01` |
| Required base / branch point | `4105e3a` (R5-C01 status pin) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`) |
| Task contract | `.ai-harness/tasks/VF-vNEXT-UX01.json` |
| Harness preflight | PASSED |
| Baseline | see §6 (recorded in `CURRENT.md`) |

---

## 1. Requirement → delivered

| Requirement | Delivered |
| --- | --- |
| Remove the fixed *Structural Context* from the left sidebar by default | `#vf-hierarchy-section` (title, breadcrumb, navigator, note) moved out of `<nav id="vf-sidebar">` entirely; the sidebar no longer contains it (or any hierarchy mount) |
| Keep the sidebar for Line Overview / Legend / Actions | Sidebar unchanged: Line Overview (WIP/CREATED/RELEASED/HELD), Legend (7 swatches), Actions (Reset Line / Clear Alarms / Export). The (already invisible, scriptless) `#vf-run-control-section` markup was deliberately **left untouched** — it is not in the authorized change list |
| Move the hierarchy to a **Structure / Model** drawer opened from the top bar | New top-bar trigger `#vf-structure-btn` (`▤`, `aria-controls="vf-structure-drawer"`, `aria-expanded`) + `<aside id="vf-structure-drawer" class="vf-drawer">` with header/close/body, Esc-close, closed by default |
| Minimum hierarchy `TIPA → ASSY Line → ASSY-SL01..ASSY-SL06` | Rendered from the canonical `GET /api/ui/context` (workspace `TIPA` → container `ASSY` → six executable leaves); observed rows: `TIPA (WORKSPACE)`, `ASSY Line (CONTAINER)`, `ASSY-SL01..06 (EXECUTABLE)` |
| Drawer uses the current visual language | New `.vf-drawer*` rules reuse the existing floating-panel language (`--vf-bg-popup`, `--vf-border`, `--vf-radius-lg`, `--vf-shadow-lg`, accent) plus scoped light-theme overrides for `.vf-hierarchy-*` / crumb classes (`#vf-structure-drawer …`) |
| WORKSPACE / CONTAINER / EXECUTABLE = secondary metadata | Kind labels are small uppercase badges; the drawer carries an explicit note *"structural metadata only — selecting a container never implies execution"*; hierarchy rows are the primary content |
| Sub-line selection = presentation/monitoring context only | The drawer reuses the **existing** authoritative `POST /assy-demo/select` seam (single call site, fail-closed: UI commits only after the backend accepts). Measured: same `run_id`, identical step, byte-identical `/assy-demo/sub-lines` projection |
| Preserve Frame A six-line overview and Frame B rich 2D | Frame A 6 cards before/after; Frame B opens with `fb-sub-line-id = ASSY-SL04`, 150 station nodes / 16 WIP nodes, same canonical identity; `closeFrameB()` restores Frame A |
| No SH-WTP work, no runtime/lifecycle/route authority change | Only static ASSY UI assets changed (plus tests/evidence); no Python source touched, no endpoint added/changed, no SH-WTP file touched |

## 2. Exact changes

| File | Change |
| --- | --- |
| `src/virtual_factory/ui/static/assy_demo.html` | top-bar trigger button; new `#vf-structure-drawer` aside (hierarchy mounts + secondary-metadata legend); `#vf-hierarchy-section` removed from the sidebar; `assy_demo.css?v=ux01` / `assy_context.js?v=ux01` cache-busting |
| `src/virtual_factory/ui/static/assy_demo.css` | new `.vf-drawer*` block + scoped light-theme hierarchy/crumb styling + narrow-width media query |
| `src/virtual_factory/ui/static/assy_context.js` | `wireDrawer()` (open/close, Esc, `uiToggleStructure`/`uiCloseStructure`, closed by default) called from `boot()`; selection seam untouched (still exactly one `fetch('/assy-demo/select')`, still fail-closed, still no step/reset/scenario) |
| `tests/test_ui_hierarchy.py` | new `TestAssyStructureDrawerUX01` (6 tests): sidebar clean, drawer closed/triggered, visual language + secondary metadata, toggle presentation-only, minimum hierarchy, selection non-mutation |
| `.ai-harness/tasks/VF-vNEXT-UX01.json` | gate contract |
| `.ai-harness/sa-review/evidence/VF-vNEXT-UX01/` | `generate_evidence.py`, `01-sidebar-cleanup.json`, `02-drawer-and-hierarchy.json`, `03-selection-non-mutation.json`, `04-browser-sanity.md`, 5 screenshots |
| `.ai-harness/sa-review/{CURRENT.md,reports/VF-vNEXT-UX01.md}`, `.ai-harness/regression/vnext_baseline_manifest.json` | status/report/regression gate context |

## 3. Evidence (machine-generated)

| Artefact | Verdict |
| --- | --- |
| `01-sidebar-cleanup.json` | `STRUCTURAL_CONTEXT_REMOVED_FROM_SIDEBAR` — sidebar has no hierarchy section/mount; Line Overview + Legend + Reset Line retained |
| `02-drawer-and-hierarchy.json` | `STRUCTURE_DRAWER_WIRED_TO_CANONICAL_CONTEXT` — trigger/aria, closed-by-default markup, mounts inside the drawer, reused tokens, 3 kind badges + note, minimum hierarchy matches `TIPA`/`ASSY`/`ASSY-SL01..06` |
| `03-selection-non-mutation.json` | `SELECTION_IS_PRESENTATION_ONLY` — select 200 + echo, identity keys unchanged, `selection_is_presentation_only` set, sub-line projection unchanged, no new run id |
| `04-browser-sanity.md` | all 8 required browser items observed; 0 console errors; 0 BLOCKER/MAJOR/MINOR |

## 4. Not done (explicitly)

No redesign; no runtime/lifecycle/route authority change; no new endpoint; no SH-WTP work; no Frame A/B
renderer refactor (`assy_demo.js` untouched); no change to the de-authorized legacy families; the dead
`#vf-run-control-section` sidebar markup was left as found (outside the authorized list); no merge.

## 5. Test/regression

- New focused tests: **6** (`TestAssyStructureDrawerUX01`) — full suite **2669 passed** (base `4105e3a`: 2663).
- R1–R5/R5-C01 suites and the observation/MES contract suites: green (no Python source changed).
- Canonical baseline (all 43 groups, incl. `r5_single_system`): recorded in `CURRENT.md`.

## 6. Authority (unchanged)

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

**STOP — awaiting SA review. SH-WTP expansion is not started.**
