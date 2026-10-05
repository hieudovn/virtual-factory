# DDAY-B7-X01-C03 scope

## Authorized

1. Minimal export-session event cursor / watermark.
2. Live transport publishes each retained runtime event once per run/session.
3. RESET / new run resets the cursor.
4. Dedup applies to all six accepted event types.

## Kept

- `map_snapshot()` is a pure full projection
- `snapshot.recent_events` is not mutated
- `dday-bw-b1-v2`
- three `operating_state` rows as `EVENT_ONLY / NON_MEASUREMENT` metadata
- zero `signal/.../operating_state`
- QoS-1 fail-closed ACK
- deterministic timestamps
- topology / route / Capper / Compressor / overview / UI

## Not authorized

- Merge PR #101
- B7 deploy
- PlantOS #49
- Event bus / outbox / retry framework
