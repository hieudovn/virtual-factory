# VF-vNEXT-G26 — Comprehensive Validation & UAT Readiness

Gate: `VF-vNEXT-G26` (comprehensive validation / UAT readiness)
Issue: #77
Base: `3c83176ce2a8a504637dfe674ea30b2332bc7968` (G25 head)
Model: Pro
Status: READY FOR SA REVIEW
Verdict: `UAT_DEMO_READY`

---

## 1. Purpose

Validate the accepted integrated multi-workspace MVP at the level a UAT audience
actually exercises — the browser — and decide whether the demo is ready. This
gate opens **no** new architecture and adds **no** product capability. It
produces browser functional evidence, a compact UAT checklist with results, a
classified UX issue list, a demo-scale stability smoke check, and a final
readiness verdict. Only small, evidence-driven UI fixes were permitted.

## 2. What was validated (browser, live server)

Server: `python -m virtual_factory.main serve --host 127.0.0.1 --port 8099`;
page: `/workspaces`.

- Selector is sourced from the backend registry: `TIPA`, `shwtp`.
- **TIPA**: select -> identity `TIPA` / `TIPA-0001` / `tipa-default`; `STEP` ->
  **six live ASSY sub-lines** (ASSY-SL01..SL06, simulation time 120, conveyor
  stopped, WIP 0, motors 0, RSO2 0) plus a trace with six participants.
- TIPA lifecycle: `STEP`, `RESET` (same run identity, `last_time_s -> 0`, trace
  cleared), `STOP` (terminal), `NEW ATTEMPT` (fresh run identity, STEP
  re-enabled), `REPLAY` (fresh run identity).
- **shwtp**: select -> 5-scope slice in order `RAW-INTAKE -> T100 -> T106 ->
  T108 -> DIST-P108`; `STEP` x3 -> `step_count=3`, `last_time_s=3`, live T106
  flows (2), T108 volume/level; fidelity/status badges and the assumed-topology
  notice visible.
- Switching isolation both directions: the inactive workspace session is never
  mutated (TIPA stayed at its own step/time while shwtp advanced, and vice
  versa).
- Error handling: unknown workspace -> 404; unknown action -> 400; missing
  `workspace_id` -> 400; missing `action` -> 400; server stayed up.
- Reload: selector repopulates; view and run-control target load immediately.
- Console: no console errors/warnings and no unhandled promise rejections.

## 3. UAT result

UAT-01..UAT-08 all **PASS** (TIPA select/run/live; TIPA lifecycle; SH-WTP
select/run; T108 multi-step values; switching isolation; deterministic replay;
fidelity/assumption clarity; error/recovery sanity).
See `evidence/VF-vNEXT-G26/03-uat-checklist-results.md`.

## 4. UX findings

- **MAJOR-1 (fixed):** the backend `new_attempt` / `replay` lifecycle actions had
  no UI. After `STOP` the session was terminal with no in-UI recovery, and
  deterministic replay was not demonstrable in the browser. Fixed by exposing
  `♻ NEW ATTEMPT` and `⟲ REPLAY` in the run-control bar.
- **MINOR-1 (fixed):** initial load did not call `select()`, so the view waited
  for the 3 s poll and the run-control target showed `no workspace`. Fixed by
  capturing the previous selection before rebuilding the option list and always
  calling `select(preferred)`.
- **MINOR-2 (not fixed):** the values table overflows ~38 px below ~700 px
  viewport width; 0 px at 1024/1280/1440. Desktop demo target; a broad CSS change
  was out of scope.
- **OBSERVATION-1..4 (not fixed, documented):** empty fidelity/status cells for
  TIPA structural sub-lines; native `<select>` truncation at narrow widths;
  `/assy-demo` separation is clear; browser caching of static JS/CSS requires a
  hard reload after edits (existing repo convention).

No BLOCKER was found. See `evidence/VF-vNEXT-G26/04-ux-issue-list.md`.

## 5. Stability (demo scale)

`stability_smoke.py` against the live server, executed twice:
`all_ok = true`, 17/17 checks, **270 steps** (120 TIPA + 150 shwtp), 20
workspace switches (TIPA run identity stable), `reset`/`replay`/`new_attempt`
for both workspaces, four bad-request classes handled, and the server still
serving afterwards. Wall time ~101–108 s including round trips (a timing
observation, not a performance claim). Not a load/performance benchmark.

## 6. Scope discipline and boundaries

- **No production Python changed.** Only two static shell assets changed:
  `src/virtual_factory/ui/static/workspace_shell.js` and
  `.../workspace_shell.html`.
- No new pytest module; G26 does not duplicate G1–G25 coverage. The canonical
  baseline (including the full suite) is the technical safety net.
- Frozen boundaries unchanged: no gateway routing / production export /
  multi-gateway / store-and-forward; no SH-WTP whole-plant or site-faithful
  work; no T110/Line2; no `/assy-demo` unification; no G4/G19/coupling redesign;
  no distributed execution; no broad UI redesign; no PIM/MES change.

## 7. Authority still NOT_AUTHORIZED

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

No authority broadening occurred in this gate.

## 8. Deliverables

1. `.ai-harness/sa-review/evidence/VF-vNEXT-G26/01-test-plan-coverage-matrix.md`
2. `.../02-browser-functional-results.md`
3. `.../03-uat-checklist-results.md`
4. `.../04-ux-issue-list.md`
5. `.../05-stability-readiness.md`, `stability_smoke.py`,
   `stability-results.json`, `stability-smoke.out`
6. `.../06-regression-summary.md`
7. `.../07-final-readiness-report.md`
8. This report.
9. Small UI fixes only (the two static shell files above).
10. Full canonical regression + full suite green at the pushed head.

## 9. Regression

- Complete canonical vNext baseline: **37/37 groups PASS** at the pushed head.
- `full_suite`: **2489 passed** (identical to G25 — G26 adds no test module and
  no production Python change).
- `checks_compile`, `checks_static_lint_type`, `checks_changed_files`,
  `checks_preflight`: PASS at the committed gate head.
- A pre-commit information run showed exactly one failing group
  (`checks_preflight`, dirty working tree — the expected state for any
  uncommitted gate); all 36 other groups including `full_suite` were PASS.

See `evidence/VF-vNEXT-G26/06-regression-summary.md`.

## 10. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G26/`

## 11. Gate status

`VF-vNEXT-G26 — READY FOR SA REVIEW`, verdict `UAT_DEMO_READY`. No PR opened,
nothing merged, no next gate started.
