# DDAY-VF-UAT-01 scope — pre-deployment recon only

## Authorized this slice

1. Read-only SHA/profile/entrypoint/timestamp recon.
2. Read-only UAT broker/auth inspect if reachable; else UNKNOWN.
3. Read-only TDengine max source-time if reachable; else UNKNOWN.
4. Propose (do not implement) Docker launcher and warmup/window rule.

## Kept

- `dday-bw-b1-v2`
- FR1 cadence semantics
- QoS-1 fail-closed ACK
- `timestamp = 2026-10-03T00:00:00Z + simulation_time_s`

## Not authorized

- Deploy / start / modify UAT
- Implement launcher, compose, CLI, or warmup runtime
- PlantOS / TDengine writes
- Public MQTT
- Merge PR #101
- PlantOS PM handoff
