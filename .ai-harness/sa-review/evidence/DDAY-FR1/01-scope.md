# DDAY-FR1 scope

## Authorized

1. One machine-readable D-Day runtime profile.
2. Exact mapping of all 22 EXPORTED measurements to FAST / MEDIUM / SLOW / COUNT.
3. Live transport applies mixed cadence.
4. EVENT_ONLY operating_state and the six event types stay event-driven.

## Kept

- `dday-bw-b1-v2`
- `map_snapshot()` as a pure full projection
- QoS-1 fail-closed ACK
- export-session event cursor
- deterministic timestamps
- topology / route / Capper / Compressor / overview / UI

## Evidence SHA

`machine-evidence.json` `head` must identify reviewed implementation `dd6cfe466832b4c167f49861d27f718291f78699`.

## Not authorized

- Merge PR #101
- B7 deploy
- PlantOS PM handoff
- PlantOS #49 / #54
- New simulation engine
