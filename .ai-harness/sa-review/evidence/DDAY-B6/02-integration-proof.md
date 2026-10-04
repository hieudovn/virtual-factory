# DDAY-B6 — 02. PlantOS-compatible local integration proof

Source: [`machine-evidence.json`](machine-evidence.json), [`export-sample.json`](export-sample.json).

## Mapper

`src/virtual_factory/workspaces/plantos_export.py` is a view over
`BottledWaterFactory.snapshot()`. It does not own a clock, a line runtime, or
a second topology.

Topic pattern (B1):

```
virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}
```

Sample topics from a 12 s run:

- `virtual-factory/bottled-water-dday/signal/BW-DEMO-01/run_state`
- `virtual-factory/bottled-water-dday/signal/BW-WT-FEED01/water_flow`
- `virtual-factory/bottled-water-dday/event/BW-DEMO-01/MACHINE_STATE_CHANGED`

Signal payload fields: `workspace_id`, `asset_id`, `signal_id`, `value`,
`unit`, `timestamp_s`, `quality`, `provenance` (`SIMULATED_RAW`).
Event payload fields: `workspace_id`, `event_type`, `asset_id`,
`simulation_time_s`, `provenance`, plus `reason_code` / `scenario_id` when
present.

## ID resolution

Frozen `topology.yaml` `plantos_mapping` is used as contract metadata:

| PlantOS entity | VF id |
|---|---|
| Plant | `BW-DEMO-01` |
| Areas | `BW-WT`, `BW-BP`, `BW-FP`, `BW-UT`, `BW-WH` |
| Line mapping | `BW-FP` → Area (`role=production_line`) |
| Machines | Asset |

`id_resolution.resolved = true`, `unresolved_ids = []`.
Current values (75) match the factory snapshot node signals.

## Historian and events

`PlantosLocalIngestion` is an in-memory sink attached to the existing factory.
It records signal samples after each `step()` / control mutation and keeps
unique events (`MACHINE_STATE_CHANGED`, `SCENARIO_PHASE_CHANGED`, plus
downtime/alarm on longer runs).

REST debug path: `GET /bottled-water-demo/plantos-export`.

Optional transport: existing `MqttGateway.publish_raw` (unchanged) can carry
a mapped payload. `protocols/` and `telemetry/` were not edited.

## Boundary

No OEE / availability / health score / hidden degradation factor appears in
the export bundle.
