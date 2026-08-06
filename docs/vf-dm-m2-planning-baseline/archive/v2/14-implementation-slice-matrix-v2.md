# 14-v2 — Implementation Slice Matrix (Corrected)

**Date:** 2026-08-05  
**Replaces:** `14-implementation-slice-matrix.md`

---

## M2 — Discrete Runtime Core (7 slices, all domain-neutral)

| Slice | Branch | Key Files | Focus |
|-------|--------|-----------|-------|
| M2-S01 | `feature/dm-m2-s01` | `discrete/engine.py` | Engine lifecycle, dispatcher port, step_event, completion |
| M2-S02 | `feature/dm-m2-s02` | `discrete/handler.py` | HandlerRegistry, HandlerOutcome, dispatch |
| M2-S03 | `feature/dm-m2-s03` | `discrete/state.py`, `discrete/snapshot.py` | DiscreteRunState, RuntimeSnapshot, event trace |
| M2-S04 | `feature/dm-m2-s04` | `discrete/controller.py` | RunController, ExecutionMode, commands, safe-point |
| M2-S05 | `feature/dm-m2-s05` | `discrete/limits.py` | Determinism, RNG, max events, no-progress, replay metadata |
| M2-S06 | `feature/dm-m2-s06` | `tests/test_dm_integration.py` | Domain-neutral integration proof |
| M2-S07 | `feature/dm-m2-s07` | `ui/discrete_run_service.py` | DiscreteRunService, one-run ownership |

---

## M3 — Assembly Domain (7 slices)

| Slice | Focus |
|-------|-------|
| M3-S01 | Domain primitives: NodeState, EntityState, RouteState |
| M3-S02 | SimulationTopology loader |
| M3-S03 | ProcessDefinition + ScenarioParameters |
| M3-S04 | RoutingSpec with safe conditions |
| M3-S05 | Core handlers: source, workstation, checkpoint, sink |
| M3-S06 | Fault handlers: rework, hold, breakdown, line-in/out |
| M3-S07 | Headless TIPA integration |

---

## M4 — Transport + Visualization (7 slices)

| Slice | Focus |
|-------|-------|
| M4-S00 | Fake-data UX spike (parallel) |
| M4-S01 | Extract shared UI + characterization tests |
| M4-S02 | FastAPI adapters: REST + WebSocket |
| M4-S03 | DMVisualizationSnapshot projection |
| M4-S04 | DM renderer (keyed SVG, token layer) |
| M4-S05 | DM command client + controls |
| M4-S06 | DM inspection panels |
| M4-S07 | TIPA layout + E2E integration |

---

## M5 — TIPA Demo (5 slices)

| Slice | Focus |
|-------|-------|
| M5-S01 | TIPA YAML configs |
| M5-S02 | Baseline scenario |
| M5-S03 | Fault scenario |
| M5-S04 | Hybrid scenario |
| M5-S05 | E2E demo smoke |

---

## Exclusions per Slice

| Slice | Excludes |
|-------|----------|
| M2 (all) | Assembly domain, nodes, entities, routes, TIPA, FastAPI, WebSocket, visualization |
| M3 (all) | Visualization, API endpoints, WebSocket |
| M4 (all) | TIPA configuration, authentication, persistence |
| M5 (all) | Layout editor, multi-run, MES integration |
