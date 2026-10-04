# DDAY-B5 — Capper Hero + Compressor Secondary — SA Review Report

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B5/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B5` |
| Authority | SA Issue `#107` (B5 only, including the Compressor addendum); parents `#105` / `#106`; PR `#101` |
| Objective | Capper hero `BW-CAP-DEG-01` plus simpler secondary compressor `BW-CMP-SAG-01`; both deterministic, independently testable, non-overlapping in the default demo |
| Conservative note | Live `#107` could not be re-fetched (GitHub App token has no issues:read). Implementation follows the original Capper contract plus the 2026-10-04 instruction that Capper is the hero and Compressor is the simpler secondary utility scenario. |
| Non-deliverables | B6 PlantOS/MQTT, B7 deploy, generic scenario framework, bearing/compressor-train physics, KPI/health/RUL, manual fault trigger, quality-engine rewrite |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Causal model

### Capper hero — `BW-CAP-DEG-01`

Config-driven one-shot state machine in
`src/virtual_factory/workspaces/capper_degradation.py`. B1
`capper_degradation.contract.yaml` remains authoritative for phase order.

`NORMAL → DEGRADING → WARNING → INTERMITTENT_STOP → RECOVERY`

- Production impact is composition-level dwell stretch / inhibit.
- One alarm pair and one downtime pair.
- Classification enriches existing context only.

### Compressor secondary — `BW-CMP-SAG-01`

Sibling helper in `src/virtual_factory/workspaces/compressor_pressure.py`.
Not a generic scenario framework and not `equipment/compressor_train.py`.

`NORMAL → PRESSURE_SAG → RECOVERY`

- Overlays existing B4 `air_pressure` only while sagging/recovering.
- One alarm pair. No downtime. No production inhibit.
- Default `NORMAL` duration is 240 s, so PRESSURE_SAG cannot overlap the
  Capper hero window (Capper RECOVERY completes at t=210).
- Independently disableable at factory construction.

No OEE/availability/performance/quality%/health/anomaly/RUL is computed.

---

## Verification (local)

| Check | Result |
|---|---|
| B5 Capper + Compressor tests | PASS |
| Full suite | **1739/1739 PASS** |
| SMOKE-BW-B5 | PASS |
| SMOKE-BW-FACTORY | PASS |
| SMOKE-BW-UI | PASS |
| SMOKE-BW | PASS |

Visual: `10-visual-{warning,fault,recovery,compressor-sag,compressor-recover}.png`

---

## Governance

- **Merge NOT authorized.** No merge performed.
- **No B6 started.**
