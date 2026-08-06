# 15 — Prompt VF-DM-M2-S01: DiscreteSimulationEngine Skeleton

## Role

Act as PM and implementation lead for M2-S01.

## Baseline

```text
Repository: hieudovn/virtual-factory
Branch: main (after M2-S00 planning approval)
HEAD: d5b345b (includes approved discrete kernel)
```

## Mission

Implement `DiscreteSimulationEngine` skeleton on top of the approved kernel (`DiscreteClock`, `ScheduledEvent`, `FutureEventScheduler`, `RunContext`).

## Deliverables

1. **`src/virtual_factory/discrete/engine.py`** — `DiscreteSimulationEngine`
   - Constructor accepts `RunContext`
   - `initialize()` — creates scheduler, sets up initial state
   - `step()` — pops one event, dispatches it, returns snapshot
   - `auto_run()` — event loop with pacing
   - `pause()` / `stop()` — lifecycle control
   - `status` property — `RunStatus` enum
   - Run state machine (Section 6 of 05-run-lifecycle)

2. **`src/virtual_factory/discrete/state.py`** — `DiscreteRuntimeState`
   - Run metadata, node/entity/route maps
   - `to_snapshot()` method

3. **`src/virtual_factory/discrete/snapshot.py`** — `VisualizationSnapshot`
   - Frozen dataclass with nodes, entities, routes, counters, allowed_actions

4. **`tests/test_discrete_engine.py`** — ~15 tests
   - Engine lifecycle (create → initialize → step → stop)
   - State transitions (valid + invalid)
   - 2-node source→sink integration (minimal proof)
   - Determinism test

## Exclusions

- NO handler registry (M2-S02)
- NO domain logic (M3)
- NO DiscreteRuntimeService (M2-S03)
- NO command model (M2-S04)
- NO visualization
- NO API endpoints
- NO TIPA configuration
- NO factory registration

## Acceptance

- 315 existing tests + ~15 new tests pass
- Engine lifecycle smoke test
- CI workflow added
