# DDAY-B7-X01-C01 — event-only operating_state + v2 contract + QoS-1 drain

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, `B6 CLOSED`, or `NEXT SLICE AUTHORIZED`.

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B7-X01-C01` |
| Authority | SA Issue `#114` (C01 only); parent `#113`; PR `#101` |
| Issue #114 access | REST 403 / GraphQL unresolved. Contract authored from the user C01 order |
| Baseline | SA-closed B6-C02 head `f0f5428e21d3f63f22c3e1419600dd63a30b1f75` |
| Scope | (1) enum `operating_state` event-only / non-measurement; (2) `dday-bw-b1-v2`; (3) QoS-1 + bounded tail drain |
| Out of scope | merge, deploy, PlantOS #49, Capper/Compressor edits, overview redesign, topology/route change |

## Correction

1. Selected `BW-FP` / `BW-FP-CAP01` / `BW-UT-CMP01` `operating_state` enums are no longer PlantOS measurement signals. They travel as `MACHINE_STATE_CHANGED` events with `transport_kind=event_only_non_measurement`.
2. Contract version is `dday-bw-b1-v2` on the workspace contract, `signals.yaml`, export dictionary, and envelope.
3. Existing `MqttGateway.publish_raw` defaults to QoS 1 and `disconnect` drains the outstanding publish tail within a bounded timeout.

Preserved: Bottled Water topology/route, deterministic simulated-source UTC timestamps, all six event types, Capper/Compressor helpers, Whole Factory Overview, KPI/OEE ownership.

NOT authorized: merge of PR #101, B7 VPS/Docker deploy, or PlantOS #49.
