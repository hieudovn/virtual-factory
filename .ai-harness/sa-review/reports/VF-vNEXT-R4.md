# VF-vNEXT-R4 — ASSY Full Parity Closure on the Canonical Runtime

Gate type: **IMPLEMENTATION** (the only authorized implementation gate) + authorized
SA review amendment (cross-workspace UI consistency **audit**, review/report only).
Issue: https://github.com/hieudovn/virtual-factory/issues/83 (comment `5643565581`)

- Repository: `hieudovn/virtual-factory`
- Branch: `feature/vf-vnext-r4`
- Base (technical, R3-C01 head): `75725508d2894f5afaa1ec10134e64a8874e86df`
- Expected base sha (origin/main): `f5261c8ca18cd4e01779c0274b55270ba028b4e5` · contract: `.ai-harness/tasks/VF-vNEXT-R4.json`
- Head: (this implementation commit)
- Harness preflight: **PASSED**
- Authority refs: R0 (#78 CLOSED/frozen), R2 (#80 CLOSED), R2V (#82 PASS), R3 (#81) + R3-C01 CLOSED

## PART A — R4 ASSY parity implementation

### A1. What was closed (Issue #83 scope)

1. **AP05 jam / recover** on the canonical session;
2. **run-to-terminal** as bounded canonical orchestration;
3. **OEE / final summary** as a read-only canonical projection;
4. **scenario selection = fresh canonical run** (never in-place mutation);
5. remaining `/assy-demo` product-path deferrals removed;
6. R2V minor console `404 /vnext/runs/current?workspace=TIPA` fixed locally;
7. parity/regression closure against the accepted ASSY behaviour;
8. bounded hygiene: the R3 same-runtime assertion was strengthened (test bypass removed).

### A2. Canonical fault ownership (one authority)

- `src/virtual_factory/runcontrol/assy_bridge.py` — `AssyExecutionBridge` now owns the
  AP05 fault lifecycle: `jam_sub_line()` (raised clock + raised window sequence read from
  the canonical runtime, idempotent while faulted), `recover_sub_line()` (fail-closed
  unless ≥1 canonical window advanced with the line frozen; resolved = raised + 120 s),
  `fault_for()` / `fault_read_model()` (read-only, all six sub-lines), `jammed_sub_line_ids`.
  Jammed lines are excluded from the coordination window exactly like held lines and are
  cleared by a capability-scoped reset.
- `src/virtual_factory/assembly/assy_mes_bridge.py` — the projection no longer owns fault
  state on the canonical path: `poll()` reads `composition.faults` (the canonical read
  model) and `_emit_canonical_lifecycle()` derives FAULT/STOPPED run-status,
  `EXCEPTION_RAISED/RESOLVED` (mes.issue) and `DOWNTIME_START/END` from it, with the
  canonical raised/resolved clocks and the canonical 120 s downtime. OEE downtime comes
  from the canonical fault lifecycle (`_canonical_downtime` keyed per run + sub-line).
  The legacy demo lifecycle path is unchanged when no canonical read model is bound.

### A3. Run-to-terminal / OEE / scenario

- `ui/assy_experience.py`: `jam()`, `recover()`, `terminal_reached()` (every canonical
  sub-line released ≥1 WIP), `run_to_terminal(max_windows)` (repeatedly calls the canonical
  `session.advance()`; bounded 1..200 with fail-closed guard; deterministic stop),
  `select_scenario()` (= fresh canonical run), `fault_state()` read model;
  `DEFERRED_FEATURES` is now **empty** (no capability remains deferred).
- `ui/assy_output.py`: canonical fault read model is injected into the output composition
  shim; new `oee_summary()` (read-only, idempotent, canonical run id, canonical downtime)
  and `fault_state()`.
- `ui/workspace_monitor.py` + `runcontrol/session.py`: a fresh-run seam
  (`WorkspaceMonitor.new_run()` + `build_tipa_scenario_run_factory()`) where **all TIPA
  runs share ONE run-id authority**, so a scenario change yields a genuinely fresh
  canonical run id while the previous run is stopped/terminal and kept as read-only
  `run_history`. No G22 identity semantics were changed and no second authority exists.
- `ui/api.py`: `/assy-demo/jam`, `/assy-demo/recover`, `/assy-demo/run-to-terminal`,
  new `/assy-demo/oee` and `/assy-demo/scenario` are canonical (no more 409 deferral);
  `POST /assy-demo/reset {"scenario": ...}` with a different scenario performs the same
  fresh-run semantic; all payloads keep `legacy_runtime_authority: false`.
- Static bindings: `assy_demo.js/.html` restore JAM / RECOVER / TERMINAL / OEE controls
  and enable the scenario selectors (fresh-run semantics); `run_control_context.js` skips
  the legacy G7 probe on canonical pages (R2V 404 fix, client-side, no new route).

### A4. Evidence (machine-derived, `evidence/VF-vNEXT-R4/`)

| Evidence | Proof | Result |
|---|---|---|
| `01-same-session-authority.json` | shell / rich / jam / recover / run-to-terminal / OEE / observations / MES all report the **same canonical run id**; exactly **1 federation + 1 session + 0 legacy controllers** | PASS |
| `02-jam-recovery.json` | target `ASSY-SL03` frozen at 360 s/0 motors while the five others advance; Frame B equals Frame A truth; canonical issue `EXCEPTION_RAISED @ AP05 (t=360)`, canonical `DOWNTIME_START (120 s)`; **projection owns no fault state** (`_fault {}`, `_jam_pending {}`); recover resumes and catches up | PASS |
| `03-run-to-terminal.json` | bounded canonical run reaches the deterministic terminal condition in N windows; **manual N-step run is state-identical per sub-line** (positions/genealogy/production/quality); `max_windows` 0/500 fail closed | PASS |
| `04-oee-summary.json` | `/assy-demo/oee` 200, 6 summaries, canonical run id in every payload/key, faulted line `downtime_s = 120 s` (others 0), keys/counts idempotent on repeat, snapshot (time/production/positions) unchanged by reads | PASS |
| `05-scenario-fresh-run.json` | `POST /assy-demo/scenario` → `fresh_run`: new run id + pinned scenario/profile, previous run stopped and recorded in `run_history`, shell/rich/output scenario identity agree, new run at step 0, unknown scenario fails closed with identity unchanged, and the scenario actually changes domain behaviour (failed-final rejects) | PASS |
| `06-parity-oracle.json` | HAPPY_PATH: genealogy 48, releases 6, quality 66, 12 canonical positions; AP06 retest >1 attempt, AP08 reinspect >1 attempt, FAILED_FINAL rejects (`reason_code=failed_final`); replay deterministic per sub-line; six-line independence under hold; R3 output identity + authoritative projection epoch | PASS |
| `07-browser-sanity.md` | compact live-browser pass (Frame A/B, controls, scenario selector, console/network hygiene) | PASS (0 BLOCKER/MAJOR; 1 OBSERVATION) |

### A5. Regression

- Focused R4 tests: **27 passed** (`tests/test_vnext_r4_canonical_parity.py`).
- Full suite: **2625 passed** (R3-C01 head 2598 → +27; no regression).
- Canonical baseline (now 42 groups incl. `r4_canonical_parity` + the four harness checks):
  **recorded at the pushed head in the SA submission**.
- Migrated obsolete ownership assertions (capability preserved): the two R2 deferral tests,
  the R3 R4-deferral test and the R3/C01 `DEFERRED_FEATURES` assertions are now canonical
  capability assertions; the R3 same-runtime assertion lost its `or True` bypass.
- Observation/MES contract suites (`test_m6_int_01`, `test_assy_mes_bridge_v1`,
  `test_assy_mes_03_evidence`, `test_vf_contract_finality_01`) pass **unchanged**.

### A6. Boundaries (NOT done)

No R5 legacy deletion/consolidation, no SH-WTP expansion or redesign, no gateway/protocol
work, no external MES/PIM change, no generic G4/G22 redesign, no broad UI redesign, no
`AssyLineRuntime` rewrite (the accepted public `hold`/`reset` seams were sufficient), no
rebase onto main, no merge.

Authority unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`;
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## PART B — VF Cross-Workspace UI Consistency Audit (review/report only)

> Deliberately separated from the R4 implementation evidence above. Full text:
> `reports/VF-CROSS-WORKSPACE-UI-AUDIT.md`. **No UI was redesigned in R4.**

- Reviewed: workspace shell/selector + shared run controls, TIPA rich ASSY experience,
  SH-WTP workspace/monitor experience, identity/status/fidelity/provenance presentation,
  navigation/drill-down, lifecycle controls, monitoring/telemetry conventions, practical
  visual layout.
- **MUST BE COMMON** (7 items): shell/chrome + selector, workspace/run/scenario identity
  block, lifecycle + run-control vocabulary, authority/`legacy_runtime_authority`/
  `site_truth` statements, fidelity/provenance labelling, run-state vocabulary,
  error/deferred response conventions.
- **MAY BE DOMAIN-SPECIFIC** (5 items): the ASSY Frame A/B discrete 2D canvas + inspector
  vs the SH-WTP scope/unit monitor table; drill-down style; fault/OEE/scenario controls
  (ASSY only); identity extras (`profile_id`, projection epoch vs assumed topology);
  telemetry shape (outbound observation/MES vs slice monitor rows).
- **CURRENT INCONSISTENCIES**: **0 BLOCKER, 0 MAJOR, 3 MINOR, 3 OBSERVATION** —
  (I1) shell has no scenario control while the rich ASSY page now starts fresh runs;
  (I2) SH-WTP has no dedicated UI page (`ui_page: None`) while TIPA advertises
  `/assy-demo`; (I3) shell scope table overflows horizontally at 652 px
  (`overflow_x = 50`) while the rich page does not; (I4) two different "unavailable
  action" presentations (disabled vs note-based fail-closed); (I5) label/legend drift
  between shell and ASSY inspector; (I6) the legacy G7 run-control include on `/assy-demo`
  is structurally unused (now guarded).
- **RECOMMENDED OWNER/GATE**: I1/I3/I4/I5 → **R5** UI productization (I1 only if a shell
  scenario control is wanted; the canonical fresh-run seam already exists); I2 → **R5 +
  the SH-WTP expansion gate** (not authorized here); I6 → **R5** (legacy decommissioning).
  **No item was fixed in R4** (all are outside the bounded ASSY epicenter), and no item is
  a BLOCKER/MAJOR, so no SA stop was required.
- **NO-REDESIGN RECOMMENDATION**: keep domain-specialized canvases (disable the temptation
  to replace ASSY 2D with a generic dashboard) and converge only on the platform level:
  one shell/identity/navigation grammar, one lifecycle + run-control vocabulary, one
  authority/provenance/status language, one availability/failure convention.

## Verdict

`VF-vNEXT-R4 — READY FOR SA REVIEW` · `ASSY_CANONICAL_PARITY_COMPLETE`
