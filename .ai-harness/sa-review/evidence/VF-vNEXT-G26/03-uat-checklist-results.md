# VF-vNEXT-G26 — Compact UAT Checklist / Results

Format: Precondition -> User actions -> Expected -> Actual -> PASS/FAIL -> Evidence.
All scenarios run against the live `/workspaces` shell (server on :8099).

---

## UAT-01 — TIPA select / run / live monitoring

- Precondition: server running; `/workspaces` open.
- Actions: select `TIPA`; press `STEP`.
- Expected: identity TIPA; 6 live ASSY sub-lines appear with per-sub-line values.
- Actual: `run_id=TIPA-0001`, `state=running`, `step_count=1`, `last_time_s=120`;
  sub-lines ASSY-SL01..SL06 each `simulation_time_s=120`, `conveyor=stopped`,
  `wip=0`, `motors=0`, `rso2=0`.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A4/A5.

## UAT-02 — TIPA lifecycle

- Precondition: TIPA selected, one step taken.
- Actions: `RESET`; `STEP`; `STOP`; `NEW ATTEMPT`; `REPLAY`.
- Expected: reset clears trace and returns time to 0 (same run identity); stop is
  terminal; new attempt/replay create fresh run identities and re-enable STEP.
- Actual: RESET -> `last_time_s=0`, trace cleared, same `run_id`; STEP -> advances
  again; STOP -> `state=stopped`, STEP/RESET disabled; NEW ATTEMPT ->
  `TIPA-0012 created`, STEP enabled; REPLAY -> `TIPA-0011 created`.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A6–A9, A17.

## UAT-03 — SH-WTP select / run

- Precondition: shell open.
- Actions: select `shwtp`; press `STEP` (x3).
- Expected: accepted G21 5-scope slice in order; live values.
- Actual: scopes RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108; `step_count=3`,
  `last_time_s=3`; T106 flows = 2; T108 `volume_m3`/`level_m` live.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A10/A11.

## UAT-04 — T108 flow / volume / level multi-step

- Precondition: shwtp selected.
- Actions: `STEP` repeatedly; observe T108.
- Expected: volume/level change deterministically with inflow 2.0 / requested
  outflow 1.5.
- Actual: T108 `inflow_m3_s=2`, `requested_outflow_m3_s=1.5`, task
  `time_s`/`volume_m3`/`level_m` present and updating per step (e.g. after 3 steps
  `volume_m3=49.5`, `level_m=2.475`).
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A11.

## UAT-05 — Workspace switching / isolation

- Precondition: TIPA stepped (step_count=1); shwtp running (step_count=3).
- Actions: switch TIPA -> shwtp -> TIPA.
- Expected: the inactive workspace session is never mutated.
- Actual: TIPA stayed `step_count=1`, `run_id=TIPA-0001`; shwtp stayed
  `step_count=3`, `run_id=shwtp-0011`.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A13; `stability-results.json`
  `repeated_switching` (20 switches, TIPA run_id stable).

## UAT-06 — Deterministic replay

- Precondition: a stepped session.
- Actions: `REPLAY`, then re-step; compare with the original run.
- Expected: fresh run identity with deterministic re-execution.
- Actual: TIPA REPLAY -> `TIPA-0011` fresh attempt; re-stepping reproduces the
  same per-sub-line trace semantics (proved numerically in
  `tests/test_vnext_g25_acceptance.py` and `test_vnext_g22_session.py`; observed
  here as a fresh identical-state attempt). shwtp REPLAY identical pattern.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A9; G25/G22 tests (baseline).

## UAT-07 — Fidelity / assumption / site-truth clarity

- Precondition: shwtp selected.
- Actions: inspect structure/values and notices.
- Expected: assumed/scenario topology and fidelity must never read as site truth.
- Actual: each scope shows `fidelity` (`logical_only`/`first_order`) and `status`
  (`accepted`/`scenario_assumed`); assumed scopes/links flagged; explicit notice
  "VF simulated SH-WTP slice only. Assumed/scenario topology and fidelity labels
  are NOT site truth; PIM remains authoritative."; TIPA view labels `/assy-demo`
  as a separate legacy runtime (identity/state not shared).
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A12/A18.

## UAT-08 — Error / recovery sanity

- Precondition: shell open.
- Actions: trigger invalid calls (unknown workspace, unknown action, missing
  body); then STOP a session and recover.
- Expected: errors handled without killing the server; the operator can recover.
- Actual: 404 (unknown workspace), 400 (unknown action), 400 (missing
  workspace_id/action) — server responsive afterwards; STOP -> session terminal,
  then NEW ATTEMPT recovers a runnable session in-UI.
- Result: **PASS**
- Evidence: `02-browser-functional-results.md` A14/A17;
  `stability-results.json` `bad_requests_handled`, `responsive_after`.

---

## Summary

| Scenario | Result |
|---|---|
| UAT-01 TIPA select/run/live | PASS |
| UAT-02 TIPA lifecycle | PASS |
| UAT-03 SH-WTP select/run | PASS |
| UAT-04 T108 multi-step values | PASS |
| UAT-05 Switching/isolation | PASS |
| UAT-06 Deterministic replay | PASS |
| UAT-07 Fidelity/assumption clarity | PASS |
| UAT-08 Error/recovery | PASS |

Two UX defects were found and fixed under G26's "allowed small fixes" (see
`04-ux-issue-list.md`): initial-load selection (MINOR-1) and missing UI exposure
of `new_attempt`/`replay` (MAJOR-1).
