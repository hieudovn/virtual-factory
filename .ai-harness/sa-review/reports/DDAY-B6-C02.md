# DDAY-B6-C02 — selected dictionary coverage + timestamp semantics

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `B6 CLOSED`.

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B6-C02` |
| Authority | SA Issue `#112` (C02 only); parent `#111`; B6 `#110`; PR `#101` |
| Issue #112 access | REST 403. Contract authored from SA comment 5978193630 + user C02 order |
| Scope | Dictionary coverage + timestamp semantics only |
| Out of scope | PlantOS ingest/history proof (SA Blocker 3), overview/Capper/Compressor/MQTT/PlantOS edits |

## Correction

1. Selected dictionary now exports existing Capper speed/cycle_time/cap_torque, Compressor active_power/energy_total, FG dispatch_count, and filler fill_rate.
2. Compressor `load` and line `target_rate` are machine-readable UNAVAILABLE / NOT EXPORTED.
3. `timestamp` is disclosed as simulated-source UTC; `simulation_time_s` remains separate; VF does not generate receipt time.

NOT authorized: merge, B7, PlantOS production changes, or the later ingest-proof slice.
