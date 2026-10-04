# DDAY-B5-C02 — Compressor Alarm / Classify / Control-Run — SA Review Report

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B5-C02/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B5-C02` |
| Authority | SA Issue `#109` (correction only); parents `#108` / `#107`; SA review on PR `#101` at `3b9cc8c` |
| Issue #109 access | GitHub Issues API returned 403 / GraphQL unresolved; contract authored from the SA review comment (2026-10-04T06:17:46Z, CORRECTION REQUIRED at `3b9cc8c`) plus the explicit user execution order |
| Objective | (1) threshold-based low-pressure alarm; (2) compressor-targeted classification enrichment; (3) matched control-run proof. Capper frozen. No fidelity expansion. |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-reviewed C01 head / C02 baseline | `3b9cc8c2d5afbeb47dae798592a5ce32b58131fc` — match at C02 start |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight before first C02 implementation write | `PRECHECK PASSED` after the contract commit |
| PR | `#101` OPEN, base `main` |

---

## Blocker 1 — pressure-threshold alarm

`ALARM_RAISED` is no longer emitted on `LOW_PRESSURE_WARNING` entry.
`observe_pressure()` compares the published 3-decimal air pressure to
`warning_threshold_bar` (5.80). Isolated short run:

- WARNING entry: pressure `6.24`, no alarm
- First alarm: pressure `5.80` while still in `LOW_PRESSURE_WARNING`
- Alarm timestamp precedes UNDERSUPPLY

---

## Blocker 2 — compressor-targeted classification

`classify(kind, code, target=...)` accepts `compressor` / `BW-UT-CMP01` /
`BW-CMP-SAG-01`. Default target remains Capper.

Compressor codes appear on:

- `compressor_scenario.downtime_code` / `failure_code`
- `ALARM_RAISED` / `ALARM_CLEARED`
- `SCENARIO_PHASE_CHANGED` for `LOW_PRESSURE_WARNING` and `UNDERSUPPLY`

They do not occupy the Capper top-level `classification` object and do not
change pressure, phase, or production.

---

## Verification gap — matched control run

Capper disabled in both runs.

| t | abnormal | abnormal total/good/fg | control total/good/fg |
|---|---|---|---|
| 284 | UNDERSUPPLY | 14/7/7 | 14/7/7 |
| 304 | RECOVERY | 14/7/7 | 15/8/8 |
| 340 | RECOVERY | 15/8/8 | 17/10/10 |

UNDERSUPPLY freezes the abnormal window. RECOVERY resumes production.

---

## Tests and smokes

| Scope | Result |
|---|---|
| C02 + C01 compressor tests | PASS |
| Capper tests (unchanged helper) | PASS |
| Full suite | **1743/1743 PASS**, exit 0 |
| SMOKE-BW-B5 / FACTORY / UI / BW | PASS |

Suite: 1740 (C01) → **1743** (C02). No test deleted or weakened.
Capper files unchanged vs `3b9cc8c`.

---

## Governance

- **Merge NOT authorized.** No merge performed.
- **No B6 started.**

Evidence: `.ai-harness/sa-review/evidence/DDAY-B5-C02/`
Report: `.ai-harness/sa-review/reports/DDAY-B5-C02.md`
