# DDAY-B3 — 02. API / runtime binding proof

**Claim:** the dedicated Bottled Water UI is bound to the real B2 runtime — not to
mocked data — and the outward projection publishes raw facts only.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`api_binding`; live-HTTP smoke
[`smoke_bottled_water_ui.py`](./smoke_bottled_water_ui.py) (45 claims, exit 0).

## Endpoints added (complete set)

```
GET  /bottled-water-demo                     page
GET  /bottled-water-demo/static/{filename}   skin assets
GET  /bottled-water-demo/state               raw line facts projection
GET  /bottled-water-demo/unit/{unit_id}      read-only unit context
POST /bottled-water-demo/start | pause | resume | stop | reset
POST /bottled-water-demo/advance             presentation-clock tick
```

No other `/bottled-water-demo*` route exists — asserted by test
(`test_b3_09b_api_exposes_no_later_slice_endpoint`).

The runtime is selected by configuration (`BOTTLED_WATER_CONFIG`, defaulting to
the workspace `line.yaml`), mirroring the existing env-override pattern. The app
fails loudly if the configuration is not a generic single-line workspace.

## Binding to the real runtime

| Observation | Value |
|---|---|
| Initial state | `run_state=STOPPED`, counts `{0,0,0}`, `units_on_line=0` |
| After 8 cycles | counts `{total: 8, good: 1, reject: 0}`, `units_on_line=7`, `dwell_number=8`, `simulation_time_s=160.0`, `operating_state=RUNNING` |
| Inspection disposition | `PASS` (from the runtime's own quality resolver) |
| Occupied stations | 7, each carrying a real `BTL-…` unit id with `unit_type=bottle`, `product_code=WATER-500ML` |
| Route | 8 station ids, matching the frozen order (from the runtime route, not a UI constant) |
| Quality checkpoints | exactly `BW-FP-INS01`, derived from the runtime station contracts |

The station order rendered by the skin comes from `state.route` (measured: the
skin contains no second hard-coded route list), so the drawing follows the real
line.

## Outward projection: raw facts only

The projection carries: plant/line identity, unit metadata, run state, operating
state, simulation time, dwell number, nominal dwell, route, per-station occupancy
and unit status, `total`/`good`/`reject` counts, units on line, quality
checkpoints, last reject, and a bounded event window.

- **No KPI is calculated.** No OEE, availability, performance, quality %, energy
  per unit, utilization or health score appears anywhere (asserted by
  `test_b3_06b_projection_publishes_no_calculated_kpi`).
- **No hidden scenario truth is exposed.** The projection is composed from public
  runtime surfaces only (`line_facts()`, `last_quality_disposition()`,
  `trace`, `station_contracts`). The injected scenario configuration is not
  published.
- The `counts` object has exactly the three raw counters — no derived ratios.

## Runtime semantics preserved through the UI

| Control | Measured result |
|---|---|
| before START | no progression (`total == 0` after an `advance` request) |
| START | `run_state = RUNNING` |
| PAUSE | `run_state = PAUSED`, and the full state is unchanged after 3 further tick requests |
| RESUME | continues from the preserved simulation time (+1 nominal dwell) and continues production |
| STOP | `run_state = STOPPED`, `operating_state = STOPPED`, no further progression, no `FAULT` in the projection |
| RESET | `STOPPED`, counts `{0,0,0}`, `units_on_line=0`, `simulation_time_s=0.0`, `dwell_number=0` |

Because the runtime itself refuses to advance outside `RUNNING`, the ticking
presentation clock cannot violate operator semantics — PAUSE/STOP hold even while
the skin keeps polling.

## Interaction policy

Exactly five operator controls are exposed in the page
(`bw-btn-start`, `bw-btn-pause`, `bw-btn-resume`, `bw-btn-stop`, `bw-btn-reset`).
The skin can only call `/start`, `/pause`, `/resume`, `/stop`, `/reset` plus the
tick. No manual quality decision, release, retry, rework, checklist or approval
surface exists (asserted by tests, and the API returns 404 for such paths).
