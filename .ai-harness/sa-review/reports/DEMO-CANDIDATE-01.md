# DEMO-CANDIDATE-01 — TIPA ASSY Integrated Rehearsal & Hardening

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `DEMO-CANDIDATE-01` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline | `494c12e265d297a389e4463848b9c0b6aafed0b1` (current branch tip) |
| Head | `59d560766647e23683e2b9b3b53880223412a301` (this gate) |
| Production code changed | **NO** (rehearsal / validation / evidence only) |

## Demo candidate summary

```text
Build SHA:            494c12e (branch tip; M6-INT-01-C01 6ccd6a5 accepted ancestor)
Environment:          VF_ENABLE_S04B_OVERVIEW=1 · port 8000 · /assy-demo (contract)
Happy path:           R1 PASS — MTR-0001 released @1680s; AP04 parents SSO2-0001+RSO2-0001;
                      UI journey verified (overview→select→flow→genealogy→AP06/AP08/AP11→release)
AP06 scenario:        R2 PASS — target ASSY-SL03; AP06 [FAIL(1), PASS(2)]; 2 distinct MES obs
AP08 scenario:        R3 PASS — target ASSY-SL02; AP08 [NG(1), PASS(2)]; 2 distinct MES obs
FAILED_FINAL:         R4 PASS — WIP not released; quality failed_final; 0 release observations
MANUAL sanity:        R5 PASS — gate awaits action; no auto-complete; legacy timing; outbound equiv
Timing what-if:       T1 actual=120 overrun=0 (no bottleneck) · T2 actual=135 overrun=15 AP05 ·
                      T3 actual=120 overrun=0 (bottleneck gone)
MES outbound:         PASS — 4 message types; no duplicates (672/672 unique by
                      run_id|source_event_id|gateway_id); JSONL path writes; stable run identity
3x repeatability:     PASS — 3/3 identical (release 1680s, 64 obs, 1 released)
Process restart:      PASS — full stop + restart from contract; all endpoints 200; clean state
Automated tests:      1554 passed + 2 documented pre-existing failures (unchanged)
BLOCKER-21AUG:        none
HIGH:                 none
POLISH:               P1 reload auto-resets demo (clean start by design);
                      P2 6-sub-line observation volume high (all unique, expected)
POST-DEMO:            D1 optional resume/confirm before reset-on-reload;
                      D2 external MES receiver integration (separate; JSONL/InMemory fallback)
```

## Rehearsal matrix

See `evidence/DEMO-CANDIDATE-01/rehearsal-matrix.md` (R1–R5 machine-generated).

- R1 HAPPY_PATH: released MTR-0001 @1680s; AP04 parents `[SSO2-0001, RSO2-0001]`;
  64 observations; 0 second-poll deliveries; 1 released.
- R2 AP06 FAIL→RETEST→PASS: target `ASSY-SL03`; AP06 history `[FAIL(1), PASS(2)]`;
  2 MES observations, record ids `[QR-0002, QR-0003]`; 0 duplicates.
- R3 AP08 NG→REINSPECT→PASS: target `ASSY-SL02`; AP08 history `[NG(1), PASS(2)]`;
  2 MES observations, record ids `[QR-0006, QR-0007]`.
- R4 FAILED_FINAL: WIP not released; status `failed_final`; AP06 `[FAIL(1), FAIL(2)]`;
  0 AP11 RELEASE observations.
- R5 MANUAL sanity: awaiting-after-dwell true; no auto-complete; MANUAL timing legacy
  (`op.timing is None`); resolved `AP06 PASS` via explicit command; 1 outbound quality obs.

## Timing / bottleneck

See `evidence/DEMO-CANDIDATE-01/timing.md`:

| Fixture | max actual_dwell_s | max overrun_s | worst bottleneck |
|---|---|---|---|
| T1 baseline (nominal 120, AP05 90) | 120.0 | 0.0 | — |
| T2 forced AP05 bottleneck (~135) | 135.0 | 15.0 | AP05 |
| T3 improvement (~65) | 120.0 | 0.0 | — |

## UI synchronization

Validated in a single continuous browser session on `http://127.0.0.1:8000/assy-demo`
(canonical 14-Aug visual baseline):

- Frame A 6-sub-line overview; select + Frame B detail.
- UI physical occupancy == snapshot `positions[]` (SSO2/MTR WIPs match API).
- AP04 genealogy context matches `GenealogyStore` (`MTR-0001 ← SSO2-0001 + RSO2-0001 @ AP04`).
- Quality badges/events match runtime: AP06 PASS, AP08 PASS, AP11 FINAL_QC PASS,
  and exception states `FAIL (attempt 1)` / `NG (attempt 1)` + retest/reinspect PASS.
- Released WIP no longer on physical line (`RELEASED: 1`, motor removed).
- No stale operation from previous WIP observed; reset clears visible state.

Screenshots: `evidence/DEMO-CANDIDATE-01/ui/` (9 images).

## MES outbound validation

See `evidence/DEMO-CANDIDATE-01/mes-outbound.md` + `repeatability.md`.

- Deterministic gateway path (InMemory + JSONL).
- No duplicate after repeat poll; all 672 live-server observations unique by
  `(run_id, source_event_id, gateway_id)`.
- AP04 genealogy, AP06/AP08 attempts, AP11 PASS, AP11 RELEASE all present.
- Stable run identity after reset (R1 → R2; idempotency keys unique by run).
- External MES ingestion not built in this gate (out of scope); JSONL/InMemory
  fallback recorded; actual receiver integration classified separately (D2).

## Repeatability / restart

- 3× consecutive clean HAPPY_PATH rehearsals identical (deterministic release
  time 1680s, 64 observations, 1 released) — see `repeatability.md`.
- Full process restart from the Demo Environment Contract: server stopped,
  restarted with `VF_ENABLE_S04B_OVERVIEW=1` on port 8000; all endpoints 200;
  clean initial state; one happy-path run succeeds.

## Automated regression

Full repository suite: **1554 passed, 2 failed** — the two documented
historical pre-existing failures, unchanged:
- `TestVScenarioSwitch::test_scenario_switch_resets_state`
- `TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

No new failures.

## Deviations

- No production code changed. Findings P1/P2 are POLISH (no fix required for
  21-Aug); D1/D2 are POST-DEMO.

## Recommendation

```text
DEMO-CANDIDATE PASS
```
