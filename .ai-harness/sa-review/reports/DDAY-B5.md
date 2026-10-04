# DDAY-B5 — Capper Deterministic Abnormal Scenario — SA Review Report

## Status

**IN PROGRESS** — local implementation and B5 tests exist. Final machine
status will be derived by `run_task_gate.py` after exact-head CI.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B5` |
| Authority | SA Issue `#107` (B5 only); parent `#105`; PR `#101` |
| Objective | Deterministic Capper abnormal story `NORMAL → DEGRADING → WARNING → INTERMITTENT_STOP → RECOVERY` with raw facts/events and production impact |
| Non-deliverables | B6 PlantOS/MQTT, B7 deploy, generic scenario framework, bearing physics, KPI/health/RUL, manual fault trigger |
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

No OEE/availability/performance/quality%/health/anomaly/RUL is computed.

---

## Evidence

`.ai-harness/sa-review/evidence/DDAY-B5/`
