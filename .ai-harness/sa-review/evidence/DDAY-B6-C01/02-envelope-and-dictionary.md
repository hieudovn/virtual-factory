# DDAY-B6-C01 — envelope and selected dictionary

## Envelope

MQTT topic (unchanged):

`virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}`

Outward payload now includes:

- `contract_version`: `dday-bw-b1-v1` (reused from `signals.yaml`)
- `workspace_id`: `bottled-water-dday`
- `plant_source_id`: `BW-DEMO-01`
- `source_id`: VF source ID (topic `asset_id` is the compatibility alias)
- `timestamp`: ISO-8601 UTC from frozen epoch `2026-10-03T00:00:00.000Z` +
  `simulation_time_s`
- `simulation_time_s`: separate simulation-clock field
- `unit` / `quality` / `provenance`
- selected-dictionary metadata: semantic role, datatype, cadence,
  `plantos_mapping_key`

`timestamp_s` is no longer the boundary timestamp.

## Selected dictionary

Machine-readable allowlist:

`configs/workspaces/bottled-water-dday/plantos_export.dictionary.yaml`

Families: WT, production, Capper, Compressor, FG, energy.

Unmapped signals/events raise `UnmappedExportError`. `map_snapshot()` only
walks dictionary entries, so unlisted node signals are not exported and do
not become PlantOS semantics.
