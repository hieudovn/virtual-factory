# DDAY-B6 — PlantOS Local Integration Proof + Whole Factory Overview

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B6/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B6` |
| Authority | SA Issue `#110` (B6 only); parent B5 `#107`; PR `#101` |
| Issue #110 access | GitHub Issues API 403 / GraphQL unresolved / public HTML 404. Contract authored from B1 B6 MQTT contract + user Lightweight Whole Factory Overview update + SA B5 CLOSED comment 5977353319 |
| Objective | Local PlantOS-compatible integration proof over the existing autonomous factory, plus a bounded five-area overview with relationships, raw values, abnormal phase, and BW-FP drill-down |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-closed B5 baseline | `449685a3c4c394b4e0654b720ff11f77205b4b48` — match at B6 start |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight | `PRECHECK PASSED` after the contract commit |
| PR | `#101` OPEN, base `main` |

---

## Integration proof

Workspace-local mapper `plantos_export.py` projects the existing factory
snapshot onto B1 MQTT JSON. An in-memory sink records current values,
historian samples and events. IDs resolve against frozen
`plantos_mapping` (Plant `BW-DEMO-01`, Areas `BW-WT/BP/FP/UT/WH`,
`BW-FP` remains an Area). Existing `MqttGateway.publish_raw` can carry a
mapped payload; `protocols/` and `telemetry/` are unchanged vs `449685a`.

REST debug path: `GET /bottled-water-demo/plantos-export`.

---

## Whole Factory Overview

`GET /bottled-water-demo/overview` reads `GET /bottled-water-demo/factory`.

- Five accepted areas with key raw values
- Process/utility relationships
- Area abnormal state from public Capper/Compressor phase
- Drill-down `BW-FP` → existing `/bottled-water-demo` F&P UI

No second simulator, no duplicate topology, no PlantOS KPI, no full HMI.

---

## Verification

| Check | Result |
|---|---|
| Full suite | 1757/1757 PASS |
| SMOKE-BW-B6 / B5 / FACTORY / UI / BW | PASS |
| protocols/telemetry vs `449685a` | unchanged |
| Capper/Compressor helpers | not edited |

Evidence: `.ai-harness/sa-review/evidence/DDAY-B6/`

**Merge NOT authorized. B7 NOT started.**
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED.
