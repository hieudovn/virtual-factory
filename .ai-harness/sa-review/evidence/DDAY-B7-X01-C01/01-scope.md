# DDAY-B7-X01-C01 scope

## Authorized

1. Enum `operating_state` transport: event-only / non-measurement via `MACHINE_STATE_CHANGED`.
2. Contract bump `dday-bw-b1-v1` → `dday-bw-b1-v2`.
3. Acknowledged QoS-1 MQTT `publish_raw` and bounded tail drain before disconnect.

## Frozen

- Capper helper/contract/runtime
- Compressor helper/contract/runtime
- Whole Factory Overview assets
- Topology / route
- Deterministic simulated-source UTC timestamps
- Six event types
- KPI / OEE ownership (VF does not calculate)

## Not authorized

- Merge PR #101
- B7 VPS / Docker deploy
- PlantOS #49
- PlantOS production-code changes
