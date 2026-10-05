# DDAY-B7-X01-C03 — export-session event cursor / watermark

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `NEXT SLICE AUTHORIZED`.

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B7-X01-C03` |
| Authority | SA Issue `#116` (C03 only); parent `#115`; `#114`; `#113`; PR `#101` |
| Issue #116 access | REST 403. Contract authored from SA comment 5987870111 + user C03 order |
| Baseline | rejected C02 head `39428b08ff5fbd19efe6dc0701bb64bafa73bf83` |
| Scope | Minimal export-session cursor so retained `recent_events` publish once |
| Out of scope | merge, deploy, PlantOS #49, Capper/Compressor/overview/UI/topology edits |

## Correction

1. `map_snapshot()` stays a pure full projection of the retained event window.
2. The live transport path keeps a tiny per-run/session watermark over runtime event identity and publishes only unseen events of all six accepted types.
3. RESET / new run resets that cursor. Failed/unacked QoS-1 publishes do not mark an event as delivered.

NOT authorized: merge of PR #101, B7 deploy, or PlantOS #49.
