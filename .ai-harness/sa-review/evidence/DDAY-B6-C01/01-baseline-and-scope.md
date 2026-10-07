# DDAY-B6-C01 — baseline and scope

Authority: SA Issue #111 (unread live; REST 403 / GraphQL unresolved).
Contract source: PR #101 comment 5977969895 (2026-10-04T08:07:58Z,
CORRECTION REQUIRED at `9e76f406246ecd989eda1f23def283fa93408e1b`) plus the
user C01 execution order.

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-reviewed B6 head | `9e76f406246ecd989eda1f23def283fa93408e1b` |
| origin/main | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| PR | #101 |
| Overview | Accepted; no redesign |

## In scope

- Versioned envelope (`contract_version`, `workspace_id`, `plant_source_id`,
  `source_id`, UTC `timestamp`, unit/quality/provenance, `simulation_time_s`)
- Selected D-Day export dictionary + fail-closed mapping
- Durable Capper / Compressor / process / condition examples from accepted B5
  scenarios
- PlantOS repo compatibility attempt without PlantOS production-code changes
- Exact bounded gap if ingest/history cannot be proven

## Out of scope

- Overview redesign
- Capper/Compressor helper edits
- Generic protocol/telemetry edits
- PlantOS production-code changes
- Merge / B7
