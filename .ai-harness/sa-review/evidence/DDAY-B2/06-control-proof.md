# DDAY-B2 — 06. Control proof (START / PAUSE / RESUME / STOP / RESET)

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `controls`

Each control was driven through `DemoController` (the existing control entry
point) and observed through the runtime's raw facts.

| Observation | Result |
|---|---|
| Initial run state | `STOPPED` |
| No progression before START (facts identical, no unit produced) | **PASS** |
| State after START | `RUNNING` |
| State after PAUSE | `PAUSED` |
| PAUSE froze simulation time | **PASS** |
| PAUSE froze unit positions | **PASS** |
| PAUSE froze counts | **PASS** |
| State after RESUME | `RUNNING` |
| RESUME continued from the preserved simulation time | **PASS** (advanced exactly one dwell) |
| RESUME continued production from the preserved state | **PASS** |
| State after STOP | `STOPPED` |
| No progression after STOP | **PASS** |
| `operating_state` after STOP | `STOPPED` |
| No `FAULT` / no `DOWNTIME` anywhere in the trace | **PASS** |
| `LineRunState` members | `["PAUSED", "RUNNING", "STOPPED"]` |
| `FAULT` is not a run state | **PASS** |
| State after RESET | `STOPPED` |
| RESET zeroed all counters | **PASS** |
| RESET zeroed simulation time | **PASS** |
| RESET emptied the line | **PASS** |
| RESET cleared the trace | **PASS** |

## State distinction

| Required distinction | How B2 preserves it |
|---|---|
| `STOPPED != FAULT` | `LineRunState` has no `FAULT` member. A STOP is a control-plane transition; a fault does not exist as a line run state. The domain scan asserts the strings `FAULT`/`DOWNTIME` never appear in the Bottled Water runtime trace. |
| `IDLE != DOWNTIME` | `operating_state()` is derived as `STOPPED` / `IDLE` / `RUNNING` only; `IDLE` means *started but no unit on the line*. `DOWNTIME` is not produced by B2. |
| `UNKNOWN != STOPPED` | `UNKNOWN` is not produced; there is no unknown-value path in the generic profile, so the two can never be conflated. |

`FAULT`, `DOWNTIME` and `UNKNOWN` are deliberately **not** implemented in B2 —
they belong to the degradation/downtime slices (B5) and to PlantOS KPI semantics.
This is reported as a deferred gap, not as a satisfied requirement.

Asserted by `test_t07_*` … `test_t11_*` and by the live smoke
([`smoke_bottled_water.py`](./smoke_bottled_water.py)).
