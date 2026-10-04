# DDAY-B5 — Capper Deterministic Abnormal Scenario — SA Review Report

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B5/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B5` |
| Authority | SA Issue `#107` (B5 only); parents `#105` / `#106`; PR `#101` |
| Objective | Deterministic Capper abnormal story `NORMAL → DEGRADING → WARNING → INTERMITTENT_STOP → RECOVERY` with raw facts/events and production impact |
| Non-deliverables | B6 PlantOS/MQTT, B7 deploy, generic scenario framework, bearing physics, KPI/health/RUL, manual fault trigger, quality-engine rewrite |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Causal model

Config-driven one-shot state machine in
`src/virtual_factory/workspaces/capper_degradation.py`. B1
`capper_degradation.contract.yaml` remains authoritative for phase order.

- Factor 0→1 across DEGRADING/WARNING, held at 1 during INTERMITTENT_STOP,
  then 1→0 in RECOVERY.
- `drive_load` / `motor_current` / `vibration_rms` follow the factor
  immediately.
- `bearing_temperature` first-order lags the factor (`tau = 12 s`).
- Effective line dwell = nominal × `cycle_time_factor` (composition layer).
- INTERMITTENT_STOP inhibits `_produce_one_cycle()`; debug `/advance` still
  forces one cycle.
- Scenario clock advances only while factory `run_state == RUNNING`.
- Operator STOP forces Capper `operating_state = STOPPED` (never FAULT).

No OEE/availability/performance/quality%/health/anomaly/RUL is computed.

---

## Changed files (B5 vs `b6dcb08`)

- `configs/workspaces/bottled-water-dday/scenarios/capper_degradation.runtime.yaml`
- `src/virtual_factory/workspaces/capper_degradation.py`
- `src/virtual_factory/workspaces/bottled_water.py`
- `src/virtual_factory/ui/api.py` (`/classify` + `/state` overlay)
- `src/virtual_factory/ui/static/bottled_water_demo.{js,html,css}`
- `tests/test_dday_b5_capper_scenario.py`
- bounded B3/B4 test updates (classify route; resume count; cadence at 100 s)
- `.ai-harness/tasks/DDAY-B5.json` and evidence/report/inbox

API/UI/topology/B2 discrete engine: no generic redesign.

---

## Verification (local)

| Check | Result |
|---|---|
| B5 tests | 12/12 PASS |
| B2/B3/B4 file set | PASS |
| Full suite | **1731/1731 PASS** |
| SMOKE-BW-B5 | PASS |
| SMOKE-BW-FACTORY | PASS |
| SMOKE-BW-UI | PASS |
| SMOKE-BW | PASS |

Visual: `10-visual-warning.png`, `10-visual-fault.png`, `10-visual-recovery.png`.

---

## Governance

- **Merge NOT authorized.** No merge performed.
- **No B6 started.**

Evidence: `.ai-harness/sa-review/evidence/DDAY-B5/`
