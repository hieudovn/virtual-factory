# DDAY-FR1 contract/dictionary compatibility

Contract `dday-bw-b1-v2` is unchanged. B1 dictionary cadence
strings remain metadata. Live transport uses the FR1 profile class.

| source_id | signal_id | B1 cadence | D-Day class |
|---|---|---|---|
| `BW-WT-FEED01` | `water_flow` | `2s` | `SLOW` |
| `BW-WT-RO01` | `production_flow` | `2s` | `SLOW` |
| `BW-WT-TK01` | `level` | `2-5s` | `SLOW` |
| `BW-FP` | `total_count` | `on_change_or_1s` | `COUNT` |
| `BW-FP` | `good_count` | `on_change_or_1s` | `COUNT` |
| `BW-FP` | `reject_count` | `on_change_or_1s` | `COUNT` |
| `BW-FP-CAP01` | `motor_current` | `1s` | `FAST` |
| `BW-FP-CAP01` | `drive_load` | `1s` | `FAST` |
| `BW-FP-CAP01` | `vibration_rms` | `1-2s` | `FAST` |
| `BW-FP-CAP01` | `bearing_temperature` | `2-5s` | `MEDIUM` |
| `BW-FP-CAP01` | `speed` | `1s` | `FAST` |
| `BW-FP-CAP01` | `cycle_time` | `per_cycle_or_1s` | `FAST` |
| `BW-FP-CAP01` | `cap_torque` | `per_cycle_or_1s` | `FAST` |
| `BW-FP-FIL01` | `fill_rate` | `1s` | `MEDIUM` |
| `BW-UT-CMP01` | `air_pressure` | `2s` | `MEDIUM` |
| `BW-UT-CMP01` | `active_power` | `1-2s` | `MEDIUM` |
| `BW-UT-CMP01` | `energy_total` | `2-5s` | `SLOW` |
| `BW-WH-FG01` | `inventory_count` | `on_change_or_1s` | `COUNT` |
| `BW-WH-FG01` | `receipt_count` | `on_change_or_1s` | `COUNT` |
| `BW-WH-FG01` | `dispatch_count` | `on_change_or_1s` | `COUNT` |
| `BW-UT-PWR01` | `plant_active_power` | `1-2s` | `MEDIUM` |
| `BW-UT-PWR01` | `plant_energy_total` | `2-5s` | `SLOW` |
