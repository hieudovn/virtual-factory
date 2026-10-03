# DDAY-B4 — 03. Whole-factory raw state, hierarchy and taxonomy

Source of truth: [`machine-evidence.json`](machine-evidence.json) → `projection`,
`hierarchy`; full payload in [`factory-state-sample.json`](factory-state-sample.json).

## 1. One authoritative factory projection

`GET /bottled-water-demo/factory` — the only new endpoint — returns one
whole-factory raw projection. Top-level keys:

```
workspace_id  plant_id  plant_name  factory  hierarchy  nodes  balances
target_line   recent_events
```

No second schema universe is created: `target_line` is the **same**
`project_target_line()` implementation the B3 `/state` endpoint uses (the B3
production was *moved* into the composition module, not rewritten), and the
`nodes` tree is the raw-fact binding of the same runtime.

Captured sample (500 s of autonomous production):

```json
{
  "factory": {"run_state": "RUNNING", "operating_state": "RUNNING",
              "simulation_time_s": 500.0, "production_elapsed_s": 500.0,
              "dwell_number": 25},
  "balances": {
    "water": {"raw_water_feed_total_m3": 0.0878, "treated_water_total_m3": 0.0659,
              "ro_reject_total_m3": 0.0220, "tank_volume_m3": 0.3336,
              "tank_capacity_m3": 0.4, "tank_level_pct": 83.40,
              "product_water_total_m3": 0.0115, "water_draw_total_m3": 0.0122,
              "other_loss_total_m3": 0.0007},
    "materials": {"preform_count": 25, "cap_count": 22, "label_count": 20,
                  "case_count": 3, "pallet_count": 1},
    "energy": {"plant_active_power_kw": 60.9, "plant_energy_total_kwh": 9.0524,
               "base_load_kw": 6.0},
    "finished_goods": {"receipt_count": 18, "dispatch_count": 17,
                       "inventory_count": 1}
  },
  "recent_events": [
    {"event_type": "MACHINE_STATE_CHANGED", "source_id": "BW-DEMO-01",
     "detail": "run_state=RUNNING", "simulation_time_s": 0.0,
     "quality": "GOOD", "provenance": "SIMULATED_RAW"}
  ]
}
```

`22` nodes carry `69` attributable raw facts.

## 2. Signal binding / source contract preparation (§8)

Every fact is attributable, so B6 can map it without redesign:

```json
"BW-WT-TK01": {
  "source_id": "BW-WT-TK01", "entity_type": "asset",
  "parent_source_id": "BW-WT", "role": "storage",
  "equipment_class": "storage_tank", "workspace_id": "bottled-water-dday",
  "signals": {
    "level": {"value": 83.404, "unit": "%", "quality": "GOOD",
              "provenance": "SIMULATED_RAW", "simulation_time_s": 500.0},
    "volume_m3": {"value": 0.3336, "unit": "m3", ...}
  }
}
```

`workspace_id` (payload) + `source_id` (node key) + `signal_id` (inner key) +
`value` + `unit` + `quality` + `provenance` + `simulation_time_s` are all
present. Signal ids reuse the frozen B1 `signals.yaml` names where that
dictionary defines one (`level`, `water_flow`, `production_flow`,
`air_pressure`, `fill_rate`, `case_count`, `pallet_count`, `total_count`,
`good_count`, `reject_count`, `active_power`, `energy_total`,
`plant_active_power`, `plant_energy_total`, `operating_state`,
`inspection_result`). Conservation summaries publish at full precision so the
identities stay exactly checkable; instantaneous readings are rounded.

## 3. Hierarchy and taxonomy integrity (§3, §4)

Captured (`hierarchy`):

| Metric | Value |
| --- | --- |
| Nodes | 22 (1 plant, 5 areas, 16 assets) |
| Source ids unique | **true** |
| Every asset has exactly one parent | **true** |
| Every asset parent is an area | **true** |
| Projection matches the frozen B1 topology | **true** |
| Blower nodes | exactly 1 — `BW-FP-BLW01`, parent `BW-FP` |
| Assets under `BW-BP` | none (logical preparation area only) |
| All nodes carry `workspace_id = bottled-water-dday` | **true** |

Per-node taxonomy fields: `source_id`, `name`, `entity_type`
(`plant|area|asset`), `parent_source_id`, `role`, `equipment_class`,
`workspace_id` — plus the node's `signals`.

`equipment_class` is a genuine equipment taxonomy, not a copy of `role`
(both `feed` and `pump` map to `pump`; `treatment` maps to `ro_skid`):

```
blower, capper, case_packer, chiller, compressor, fg_interface, filler,
inspector, labeler, palletizer, power_meter, pump, rinser, ro_skid,
storage_tank
```

No FactoriX platform canonical identity is invented anywhere in VF: the
projection contains no `vendor`, `model_number`, `serial`, `canonical_id`,
`platform_id` or `device_id` field (`invented_identity_hits: []`).
`BW-FP` remains an **Area** with `role=production_line`; no PlantOS `Line`
entity was introduced.

## 4. Whole-factory area scope (§6)

| Area | Modelled | Published raw facts |
| --- | --- | --- |
| `BW-WT` Water Treatment | aggregate | raw `water_flow`, treated `production_flow`, cumulative raw/treated/reject m³, tank `level` and `volume_m3`, `operating_state` |
| `BW-BP` Bottle Preparation | logical only, **no asset** | `operating_state`, `preform_count` |
| `BW-FP` Filling & Packaging | detailed (B2/B3 unchanged) | `total_count`, `good_count`, `reject_count`, per-station `operating_state`, filler `fill_rate` + product/draw water, `cap_count`, `label_count`, `case_count`, `pallet_count`, `inspection_result` |
| `BW-UT` Utilities | aggregate | compressor `operating_state` + `air_pressure`, chiller/pump `operating_state`, per-asset `active_power`/`energy_total`, meter `plant_active_power` + `plant_energy_total` |
| `BW-WH` Warehouse / Dispatch | aggregate | `receipt_count`, `dispatch_count`, `inventory_count`, `operating_state` |

Utility causality captured (`utilities`):

| Signal | RUNNING | STOPPED |
| --- | --- | --- |
| compressor `air_pressure` (bar) | 6.4 (sagged) | 7.0 (recovered to setpoint) |
| compressor `operating_state` | `RUNNING` | `IDLE` |
| compressor `active_power` (kW) | 15.0 | 2.0 |
| line area `operating_state` | `RUNNING` | `STOPPED` |
| `plant_active_power_kw` | 60.9 | 12.2 |

## 5. Raw-fact boundary (§7)

`projection.kpi_hits` = **[]** and `projection.foreign_semantics_hits` = **[]**:
no OEE / availability / performance / quality % / energy-per-unit / utilization /
health score / predictive-maintenance field, and no `TIPA` / `assy` /
`pre-assy` / `SSO2` / `RSO2` / `AP05_JAM` / `APxx` vocabulary anywhere in the
projection, the node ids, the events or the skin. `FAULT` and `UNKNOWN` are never
emitted — no abnormal condition is modelled before B5 — so `STOPPED != FAULT`
holds by construction.
