# DDAY-B4 — 02. Autonomous server-side runtime

Source of truth: [`machine-evidence.json`](machine-evidence.json) → `autonomy`.

## 1. The server owns the production clock

```python
# src/virtual_factory/ui/api.py
async def _bw_autorun_loop(interval_s: float) -> None:
    factory = _get_bw_factory()
    while True:
        await asyncio.sleep(interval_s)
        factory.step()
```

The runner is created in the FastAPI **lifespan** (the same pattern as the
existing `RuntimeService.start_loop()/_stop_loop()`), paced by
`clock.tick_interval_s`, and is cancelled cleanly on shutdown. The interval is
**wall-clock pacing only**: simulation truth is produced exclusively by
`BottledWaterFactory.step()` from configuration, so it stays deterministic.

Determinism is preserved because `step(N)` is internally decomposed into
sub-steps of at most `clock.integration_step_s` (1 s):

```
step(20.0)  ==  20 x step(1.0)        # proven, see 05-determinism
```

## 2. Headless autonomy proof (no browser, no `/advance`)

The captured run issued **only** these HTTP calls:

```
POST /bottled-water-demo/reset        # deterministic start
GET  /bottled-water-demo/factory      # polling, 40 samples over 2.1 s
POST /bottled-water-demo/start        # operator control
GET  /bottled-water-demo              # once, to show the page still serves
```

* `advance_requests`: **0** — no client ever requested a production step.
* `browser_opened`: **false** — the target-line page was never loaded before
  production was observed.
* `progression_without_advance`: **true**.

Captured timeline (`autonomy.samples`, wall-clock 0.05 s per 1.0 simulated
second):

| wall s | sim time s | dwell | bottles produced | energy kWh |
| --- | --- | --- | --- | --- |
| 0.002 | 10.0 | 0 | 0 | 0.0339 |
| … | … | … | … | … |
| 2.099 | 49.0 | 1 | 1 | 0.7752 |
| final | 50.0 | 2 | 2 | 0.7944 |

Note the first sample: `sim time = 10 s` **while STOPPED**. This is the
documented STOP interpretation (see §4) — a stopped plant is still energized,
its clock runs and only standby/base load accrues energy — yet production
counters stay at zero:

```
autonomy.stopped_state = {
  "run_state": "STOPPED",
  "counts":          {"total": 0, "good": 0, "reject": 0},
  "counts_after_0_6s": {"total": 0, "good": 0, "reject": 0},
  "simulation_time_s_after_0_6s": 10.0,
  "plant_energy_total_kwh_after_0_6s": 0.0339
}
```

"Closing / not opening the B3 page does not stop simulation" is therefore proven
twice: the headless capture above never opens it, and
`SMOKE-BW-FACTORY` asserts progression with the page unopened.

## 3. Control semantics with the autonomous clock

`determinism.control_semantics` (same composition, driven deterministically):

| Action | run_state | sim time s | counts.total | Notes |
| --- | --- | --- | --- | --- |
| START + 100 s | `RUNNING` | 100.0 | 5 | producing |
| PAUSE + 200 s | `PAUSED` | 100.0 | 5 | clock frozen, conserved quantities frozen |
| RESUME + 100 s | `RUNNING` | 200.0 | 10 | continues from preserved state |
| STOP + 200 s | `STOPPED` | 400.0 | 10 | production frozen; no FAULT |

* `pause_freezes_conserved_quantities`: **true**
* `stop_halts_production_only`: **true**, `fault_present`: **false**
* RESET returns the deterministic initial state (see 05-determinism).

## 4. Documented control interpretation (requires SA awareness)

Issue #105 says both:

* §2 — "PAUSE → simulated progression freezes, state preserved";
* §5.3 — "STOPPED/PAUSED demand must be coherent with equipment state" and
  §5.6 — "cumulative energy may only increase according to explicitly modeled
  standby/base load".

B4 resolves these as follows and states it explicitly:

| State | Simulated clock | Production | Energy | Reported loads |
| --- | --- | --- | --- | --- |
| `RUNNING` | advances | advances | production loads | running |
| `PAUSED` | **frozen** | frozen | **frozen** (Δt = 0) | standby |
| `STOPPED` | advances | **frozen** | **standby + base load only** | standby |

`PAUSE` is treated as "simulated progression freezes" (§2) literally, so no
simulated time passes and every conserved quantity is frozen. `STOP` is a
*controlled* stop, not a de-energised plant: the clock keeps running and only
explicitly modelled standby/base load accrues energy, which is exactly the
allowance §5.3/§5.6 make. Both interpretations are also reflected in the unit
tests (`test_b4_03`, `test_b4_05`, `test_b4_14b`) and in `SMOKE-BW-FACTORY`.
