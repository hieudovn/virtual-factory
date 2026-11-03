# 02 — Factory-clock / exact-time advance seam

## What exists today

`AssyLineRuntime` holds a private float `_simulation_time_s` exposed read-only
through `simulation_time_s` (`src/virtual_factory/assembly/line_runtime.py:531`).
It advances in exactly two places:

- `execute_dwell()` adds the computed `actual_dwell` (`line_runtime.py:887-995`,
  increment at `:992`);
- `index_line()` adds the configured `index_movement_duration_s`
  (`line_runtime.py:1764-1789`, increment at `:1771`).

`actual_dwell` is `max(nominal_dwell, max_remaining_station_time)`
(`line_runtime.py:940-955`), so the next timestamp is a function of the current
station load, not a caller-supplied horizon.

A separate deterministic scheduler exists but is **not wired** to ASSY:

- `DiscreteClock.advance_to()` supports monotonic target time
  (`src/virtual_factory/discrete/clock.py:46-62`);
- `FutureEventScheduler.peek_next()` / `pop_next()` provide event ordering and
  clock advance (`src/virtual_factory/discrete/scheduler.py:161-228`).

`AssyLineRuntime` has no scheduler, no `advance_to`, no `next_event_time`, and no
`propose`/`commit` boundary. The only similarly named method is
`advance_cycle()` (`line_runtime.py:769`), which is the generic-profile
feed→dwell→index cycle and is not an exact-time API.

## Six contexts and lockstep

`AssyDemoComposition.step_all` records
`DEMO_EXECUTION_POLICY: COMMON_DEMO_CLOCK`, then states "Each context advances
independently via step_context()" and "No assertion about equal
simulation_time_s" (`demo_composition.py:322-338`). `demo_step_number` is a
presentation counter, not a common simulated timestamp. An existing regression
explicitly asserts that simulation times are not forced equal
(`tests/test_demo_composition.py:352-364`).

Therefore:

- six contexts can propose/advance independently;
- there is no global event boundary, no canonical tie order and no atomic
  cross-line commit;
- there is no API to pause/advance a context to a specified horizon and stop on
  an exact event boundary.

## Probe result

`06-probe-commands-and-output.md` records:

```text
has_advance_to = false
has_next_event_time = false
time-advance-like API = ["_advance_operation", "advance_cycle"]
```

## Decision

| Seam | Result |
|---|---|
| Read simulated time | Supported (`simulation_time_s`) |
| Pause by simply not stepping | Supported operationally, but not an authoritative run-state transition |
| Advance to exact specified horizon | **NO SUPPORT** |
| Next-event timestamp discovery | **NO SUPPORT** |
| Six-line lockstep on one factory clock | **NO SUPPORT** in current runtime; requires a coordinator adapter |

Per the G1A design rule ("If exact event-bounded advancement is unsupported,
integration must STOP rather than stamp an independent line step with a
fabricated common timestamp"), G3-A must not claim integrated clock support from
the current code.
