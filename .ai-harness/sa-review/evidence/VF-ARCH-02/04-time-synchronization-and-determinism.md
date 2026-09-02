# 04 — Time, Synchronization & Deterministic Ordering (Issue #41 §D, §E)

## 4.1 Time concepts (frozen; no numerical algorithm chosen)

| Concept | Meaning | Owner |
|---|---|---|
| Workspace / composition time | The coordination-level time frame of a run (advance ticks, coordination points). | Coordinator/run context |
| Scope-local simulation time | An executable scope's own simulation clock (`simulation_time_s` / `TimeManager.current_time_s` / ASSY `released_at_sim_s`). | Scope runtime |
| Synchronization boundary / exchange point | A declared point where cross-scope data/flow is exchanged (commit/collect). | Coordinator (declares), scopes (honor) |
| Internal timestep / event cadence | The scope's own advance granularity (`dt_s` tick, event schedule, dwell+index). | Scope runtime |
| Wall-clock / UI speed | Presentation pacing (e.g. `speed_factor`), unrelated to correctness. | UI/service layer |

**Critical invariant (frozen):** synchronized composition does **NOT** require
identical internal timestep or identical scheduler across scopes. Continuous,
discrete-event, and state-machine scopes may coexist with different cadences,
synchronized only at declared exchange points.

### High-level synchronization modes (categories, not algorithms)

| Mode | Semantics |
|---|---|
| `common_advance` | Coordinator advances all participating scopes by one composition step per cycle (ASSY `COMMON_DEMO_CLOCK` precedent). No equal-sim-time requirement. |
| `exchange_barrier` | Each participating scope advances **only within a coordinator-authorized deterministic coordination window/horizon** toward the next declared exchange boundary (different internal timesteps/schedulers/cadences allowed inside that bounded window); **no free-running advancement**. Exchange/commit order remains declared and deterministic. |
| `event_coordination` | Coordinator sequences declared inter-scope events at coordination points. |

These are categories of the contract; choosing numerical solvers (Continuous) or
event-scheduling internals (Discrete) is deferred to implementation gates.

## 4.2 Deterministic ordering contract

1. **Advance/exchange/commit phases** are ordered and declared: per coordination
   point, the order is (a) advance scopes, (b) perform boundary exchange,
   (c) commit/collect outcomes.
2. **Stable ordering rule:** when multiple scopes/events are ready at the same
   coordination point, order is determined by a declared stable key (e.g.
   deterministic `scope_id` order), never by dict/set iteration, hash, random,
   or time-of-day.
3. **Explicit inputs:** version, config, scenario, seed, and dependency pins are
   declared inputs; same inputs → same ordered execution/results.
4. **No uncontrolled nondeterminism:** iteration order and RNG are seeded/declared
   (ASSY already derives a stable per-sub-line seed from base seed + ordinal).
5. **Replay vs snapshot restore distinction:** replay = deterministic
   re-execution from explicit inputs; snapshot restore = restoring captured
   state. Storage/checkpoint implementation is deferred.
6. **Wall-clock concurrency must not change semantics:** parallel or wall-clock
   execution may not alter simulation semantics or ordering.

## 4.3 Conformance with repo evidence

- `core/TimeManager` fixed-step `dt_s` tick vs `discrete/` event scheduler vs
  ASSY dwell+index — three distinct cadences already coexist in the repo,
  confirming the invariant that one cadence is not required.
- `AssyDemoComposition.step_all()` explicitly asserts **no equal `simulation_time_s`**
  across contexts — direct evidence for `common_advance` without forced equal time.
- `discrete/` `replay metadata` and ASSY stable per-sub-line seed are precedents
  for the deterministic-ordering contract.
