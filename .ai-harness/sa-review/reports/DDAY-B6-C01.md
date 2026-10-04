# DDAY-B6-C01 — VF→PlantOS contract fidelity

## Status

Machine status is derived by the full canonical task gate. See
`.ai-harness/sa-review/evidence/DDAY-B6-C01/` and the gate trace.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or
`B6 CLOSED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B6-C01` |
| Authority | SA Issue `#111` (C01 only); parent B6 `#110`; PR `#101` |
| Issue #111 access | GitHub Issues API 403 / GraphQL unresolved. Contract authored from SA PR comment 5977969895 + user C01 order |
| Objective | Correct VF→PlantOS envelope, selected dictionary, fail-closed mapping, durable B5 examples, and PlantOS compatibility/gap disclosure. Keep the Whole Factory Overview accepted. |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-reviewed B6 baseline | `9e76f406246ecd989eda1f23def283fa93408e1b` — match before first C01 write |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| PR | `#101` OPEN, base `main` |

---

## Correction

1. Versioned envelope with `contract_version=dday-bw-b1-v1`, `plant_source_id`,
   `source_id`, UTC `timestamp`, and separate `simulation_time_s`. MQTT topic
   and source IDs preserved.
2. Selected export dictionary covering WT / production / Capper / Compressor /
   FG / energy. Fail-closed on unmapped signals.
3. VF in-memory sink disclosed as adapter-only. PlantOS ingest/historian is
   **not** claimed. Exact gap recorded in
   `.ai-harness/sa-review/evidence/DDAY-B6-C01/03-plantos-gap.md`.
4. Durable Capper warning+downtime/recovery and Compressor
   warning/undersupply/classification envelopes, plus process and condition
   history samples, from the accepted B5 scenarios.

Whole Factory Overview: unchanged / accepted.

---

## PlantOS gap (STOP that claim)

PlantOS repo is not in this environment and is not cloneable with the current
token. Actual PlantOS ingestion/history cannot be proven without SA
authorization to grant PlantOS repo access and, if needed, a minimal PlantOS
adapter/ingest change. C01 does not edit PlantOS production code.

---

NOT authorized: merge, B7, or any later slice.
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED.
