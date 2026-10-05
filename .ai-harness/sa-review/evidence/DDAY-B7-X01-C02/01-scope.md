# DDAY-B7-X01-C02 scope

## Authorized

1. Stop synthesizing `MACHINE_STATE_CHANGED` from current `operating_state` snapshot values.
2. Fail-closed QoS-1 ACK: timeout, missing ACK, and negative rc are not delivered.

## Kept

- `dday-bw-b1-v2`
- three `operating_state` rows as `EVENT_ONLY / NON_MEASUREMENT` metadata
- zero `signal/.../operating_state`
- all six event types
- deterministic timestamps
- topology / route / Capper / Compressor / overview

## Not authorized

- Merge PR #101
- B7 deploy
- PlantOS #49
