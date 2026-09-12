# VF-vNEXT-R4 — compact browser / UAT parity sanity (evidence G)

Environment: live product server `python -m virtual_factory.main serve --host 127.0.0.1
--port 8099` started from this branch's working tree (reports `source_sha` = contract
commit `9aaa479`, R4 changes uncommitted at the time of the run); integrated browser,
effective viewport **652 x 407** (the harness browser does not honour viewport resize).
Static assets were loaded with the HTTP cache disabled (CDP `Network.setCacheDisabled`)
so the current binding files were exercised, not cached copies.

## Frame A / Frame B (rich experience preserved)
- `/assy-demo` opens with the canonical identity bar
  `CANONICAL SESSION TIPA · run TIPA-0001 · scenario tipa-default · profile tipa-assy-happy_path`.
- Frame A shows exactly **six** sub-line cards (`ASSY-SL01..06`), `overflow_x = 0`
  (no page-level overflow); screenshot `shot-frame-a.png`.
- Double-clicking a card opens Frame B (2D line): 12 stations (`PRE-ASSY`, `AP01..AP11`),
  conveyor, `PACKED GOODS`, WIP tokens (`SSO2-0005..0009`, `MTR-0001..0004`) and quality
  events (`PASS MTR-0002 @ AP06 · PASS MTR-0001 @ AP06`); screenshots
  `shot-frame-b.png` / `shot-frame-b-jam.png`.

## R4 canonical controls (bindings only)
- The restored controls are present and visible in the Frame B panel:
  `#btn-jam` (53 px), `#btn-recover` (84 px), `#btn-terminal` (86 px), `#btn-oee` (51 px).
- `#btn-jam` → canonical note `canonical AP05 jam on ASSY-SL03`;
  `#btn-recover` → `canonical recovery on ASSY-SL03` (the line's clock resumed to 960 s);
  `#btn-oee` → `OEE (read-only) run TIPA-0001 · 0 summary(ies)` (0 is correct: no
  released/rejected WIP had been produced yet in that live run).
- Scenario selector is **enabled** on both footers (`#scenario-select`,
  `#fb-scenario-select`) with the R4 title "pinned run input; selecting a scenario
  starts a FRESH canonical run (R4)"; options `HAPPY_PATH`, `AP06_FAIL_RETEST_PASS`,
  `AP08_NG_REINSPECT_PASS`, `FAILED_FINAL`.

## Console / network hygiene
- With the cache disabled the rich page produced **no console errors and no failed
  requests** (`bad = []`, `errs = []`), including **no** `404 GET
  /vnext/runs/current?workspace=TIPA` — the R2V minor is fixed (client-side guard in
  `run_control_context.js`; the legacy route contract itself is unchanged and still
  404s for TIPA).

## Workspace shell / SH-WTP (audit evidence)
- `/workspaces` + SH-WTP selection renders the generic monitor view for `shwtp`
  (`run_id shwtp-0001`, `scenario_id shwtp-g21-slice`, scope table with
  fidelity/status, `site_truth: false` note); screenshot `shot-shwtp-shell.png`.
- Observation: the shell view at the 652 px harness viewport has
  `overflow_x = 50` (minor horizontal overflow of the scope table) — recorded as an
  OBSERVATION in the cross-workspace audit (not a blocker, not touched in R4).

## Verdict
No BLOCKER/MAJOR browser defect found. Frame A/B parity, the canonical jam/recover/
terminal/OEE bindings and the fresh-run scenario selector all behave coherently on the
canonical session.
