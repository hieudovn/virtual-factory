# DDAY-B4 — 04. Conservation and process consistency

Source of truth: [`machine-evidence.json`](machine-evidence.json) →
`conservation`, `utilities`.

## 1. Instrumented invariant run

A 4000-step deterministic run (200 target-line cycles) checked the invariants
**every single step**:

| Invariant | Result |
| --- | --- |
| `0 <= tank_volume <= tank_high_volume <= capacity` | holds |
| `tank_volume == initial + treated − water_draw` | holds |
| `treated == raw × recovery_factor` | holds |
| `ro_reject == raw − treated` | holds |
| `plant_energy_total` never decreases | holds |
| `FG inventory >= 0` | holds |
| `FG inventory == receipts − dispatch` | holds |
| good count never decreases | holds |
| material counters never decrease | holds |
| `label <= cap <= preform` | holds |
| feed delivers nothing while the tank is at the high limit | holds |
| **violations** | **0** |
| **identity errors** | **0** |

Tank volume range over the run: `0.2405 m³ … 0.3400 m³` against a high-level
volume of `0.34 m³` and a capacity of `0.4 m³` — the high-level rule engaged and
the tank never left its bounds. At the end of the run the level was `60.1 %`
(the low-level rule had just restarted the feed), so both hysteresis edges are
exercised.

Final conservation state after 4000 s:

```json
{"water": {"raw": 0.0878, "treated": 0.0659, "reject": 0.0220,
           "tank": 0.2405, "capacity": 0.4, "level_pct": 60.13,
           "product_water": 0.0990, "draw": 0.1053, "other_loss": 0.0063},
 "materials": {"preform": 200, "cap": 197, "label": 195,
               "case": 32, "pallet": 16},
 "energy": {"plant_active_power_kw": 60.9, "plant_energy_total_kwh": 68.26},
 "finished_goods": {"receipts": 193, "dispatch": 192, "inventory": 1}}
```

## 2. Water balance (§5.1)

`treated_water = raw_water_feed × recovery_factor` (`0.75`) and
`reject_water = raw_water_feed − treated_water` are exact (relative error
< 1e-12 in the run above, because the published values carry full precision).

```
tank_volume = initial + treated_in − filler_draw          # closes exactly
product_water = bottles_filled × bottle_volume            # 500 mL bottles
water_draw    = product_water / process_efficiency        # 0.94
other_loss    = water_draw − product_water                # rinse + losses
```

`bottles_filled` is counted from real line progress (units that completed the
configured `fill` station `BW-FP-FIL01`), so no independent water number is ever
generated.

**Bounded tank.** The feed modulates down as the tank approaches its high-level
volume and saturates exactly at `tank_high_volume_m3`; the latch then idles the
feed until the level falls to the low-level volume (hysteresis band
`60 % … 85 %`). Because the inflow is clamped to the remaining headroom, the tank
can never exceed the high limit — and therefore never the capacity. No membrane
physics and no hydraulic solver are modelled.

## 3. Packaging material balance (§5.2)

Cumulative counters tied to real production, counted by unit id from the line
trace:

| Counter | Source |
| --- | --- |
| `preform_count` | units introduced at line entry (== `total_count`) |
| `cap_count` | units that completed `BW-FP-CAP01` |
| `label_count` | units that completed `BW-FP-LAB01` |
| `case_count` | `units completed BW-FP-CPK01 // bottles_per_case` (aggregate) |
| `pallet_count` | `case_count // cases_per_pallet` (aggregate) |

**Rejected bottles still consume already-used material**: the reject test
(`test_b4_12b`, and the B3 `ALWAYS_FAIL` smoke) drives a failing inspection and
asserts `capped >= rejects` with `cap_count == capped`, while `label_count`
(units that reached the labeler) stays at or below the cap count. Counters never
reset silently within a run — asserted every step in the instrumented run and in
`test_b4_06`/`test_b4_04`.

## 4. Energy conservation (§5.3)

`energy_total += active_power × dt_hours`, integrated per asset and at the meter.
Identity verified exactly:

```
plant_energy_total == Σ asset energy_total + base_load × simulated_time
```

with `base_load_kw = 6.0`. At the end of the 4000 s run:
`Σ asset energy = 61.594 kWh`, `6.0 kW × 4000 s / 3600 = 6.667 kWh`,
total `68.261 kWh` — matching `plant_energy_total_kwh = 68.2608`.

`plant_active_power` is a **sum**, never an independent number:

```
12.2 kW = 6.0 base + 6.2 standby        (STOPPED / PAUSED loads)
60.9 kW = 6.0 base + 54.9 production    (RUNNING)
```

Cumulative energy is monotonic and only moves when simulated time moves
(`test_b4_14b`: untouched across 200 paused steps; exactly
`standby_kw × 600 s / 3600` across 600 stopped steps at the settled standby
load).

## 5. Utility causal rules (§5.4)

First-order deterministic response, no thermodynamics:

* production runs → compressed-air demand rises → **pressure sags to 6.4 bar**
  and the compressor loads (15 kW);
* line stops → demand drops → **pressure recovers to the 7.0 bar setpoint** the
  compressor unloads to `IDLE` at 2.0 kW standby;
* chiller and utility pump track production / water-treatment activity, so the
  plant load falls from 60.9 kW to 12.2 kW on a controlled stop.

All four causal relationships are asserted in `test_b4_13` and captured under
`utilities`.

## 6. Warehouse balance (§5.5)

`FG_inventory = receipts − dispatch`, with receipts taken from completed **good**
production (`good_count`) and dispatch a configured deterministic drain
(4 bottles/min) that only runs while simulated time advances and stock exists.
Inventory never goes negative; no WMS logic, no route optimisation, no batch
semantics.

## 7. State-machine consistency (§5.6)

* `STOPPED != FAULT` — `FAULT` is never emitted (B5 owns abnormal conditions).
* `IDLE != downtime` — no downtime event exists in B4.
* Filler stopped → `fill_rate` published as `0.0` while the plant is stopped.
* Compressor stopped → standby load only, never full-load compressed air.
* PAUSE freezes process progression (see §4 of `02-autonomous-runtime.md`).
* Cumulative energy only increases according to the modelled standby/base load.
