# DDAY-VF-UAT-01-C01 scope — durable Bottled Water MQTT runtime

## Authorized this slice

1. Add `virtual-factory dday-bw-runtime`.
2. Add compose artifact `deploy/dday-vf-uat.compose.yml` (not executed on UAT).
3. Start a fresh deterministic Bottled Water run, apply FR1 cadence, keep events event-driven.
4. ACK the final STOPPED event, then drain/disconnect. Fail closed on MQTT errors.
5. Allow repeated deterministic source timestamps across separate runs.

## Kept

- `dday-bw-b1-v2`
- FR1 profile `dday-bw-runtime-fr1`
- QoS-1 fail-closed ACK
- `timestamp = 2026-10-03T00:00:00Z + simulation_time_s`
- PlantOS Edge #92 owns live freshness/dedup

## Not authorized

- UAT Docker build/run or live EMQX connection
- Source-time floor / STOPPED warmup / reservation / checkpoint
- Wall-clock synchronization of source time
- PlantOS / TDengine writes
- Topology / signal / scenario / contract / KPI ownership change
- Merge of PR #101
- PlantOS PM handoff
