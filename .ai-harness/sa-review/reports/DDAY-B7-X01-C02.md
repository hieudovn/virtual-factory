# DDAY-B7-X01-C02 — no synthesized state events + fail-closed QoS-1 ACK

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `NEXT SLICE AUTHORIZED`.

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B7-X01-C02` |
| Authority | SA Issue `#115` (C02 only); parent `#114`; `#113`; PR `#101` |
| Issue #115 access | REST 403. Contract authored from SA comment 5987569082 + user C02 order |
| Baseline | rejected C01 head `97e313ab0df6efb19b4374cfd857940f9e5c76fd` |
| Scope | Remove synthesized state events; fail-close QoS-1 ACK |
| Out of scope | merge, deploy, PlantOS #49, Capper/Compressor/overview/topology edits |

## Correction

1. `map_snapshot()` no longer projects `event_only_states` into `MACHINE_STATE_CHANGED` messages. State events come only from runtime `recent_events`.
2. `publish_raw` / `publish_via_existing_mqtt` / `disconnect` treat unacknowledged, timed-out, or negative-rc publishes as explicit failures. Delivered counts increment only after confirmed ACK.

NOT authorized: merge of PR #101, B7 deploy, or PlantOS #49.
