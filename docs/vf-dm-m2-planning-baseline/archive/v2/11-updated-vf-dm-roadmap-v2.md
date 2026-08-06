# 11-v2 — Updated VF-DM Roadmap (Corrected)

**Date:** 2026-08-05  
**Replaces:** `11-updated-vf-dm-roadmap.md`  
**Corrections:** F-013 (7 M2 slices), F-014 (transport in M4)

---

## M2 — Discrete Runtime and Control Core (C-013)

| Slice | Branch | Objective | Key Deliverables |
|-------|--------|-----------|-----------------|
| **M2-S01** | `feature/dm-m2-s01` | Pure engine lifecycle + dispatcher port | `DiscreteSimulationEngine`, `EventDispatcherProtocol`, `RunStatus`, `step_event()`, empty-scheduler completion, test double dispatcher |
| **M2-S02** | `feature/dm-m2-s02` | Handler registry + dispatch outcome | `HandlerRegistry`, `HandlerOutcome`, `EventHandlerFn`, unknown event policy, error handling |
| **M2-S03** | `feature/dm-m2-s03` | Domain-neutral run state + trace | `DiscreteRunState`, `RuntimeSnapshot`, event trace ring buffer, snapshot sequence |
| **M2-S04** | `feature/dm-m2-s04` | Run controller + commands + modes | `DiscreteRunController`, `ExecutionMode`, command queue, safe-point application, auto pacing |
| **M2-S05** | `feature/dm-m2-s05` | Determinism + limits + safety | RNG ownership, max events, no-progress detection, replay metadata |
| **M2-S06** | `feature/dm-m2-s06` | Domain-neutral integration proof | Generic test domain, multi-handler flow, mode transitions |
| **M2-S07** | `feature/dm-m2-s07` | Framework-neutral run service | `DiscreteRunService`, one-run ownership, service-level smoke test |

**All M2 slices are domain-neutral.** No node, entity, route, source, sink, or assembly in M2.

---

## M3 — Assembly Domain and Flow Core

| Slice | Objective |
|-------|-----------|
| M3-S01 | Domain primitives: `NodeState`, `EntityState`, `RouteState`, `ResourceState` |
| M3-S02 | `SimulationTopology` loader + validator |
| M3-S03 | `ProcessDefinition` + `ScenarioParameters` contracts |
| M3-S04 | `RoutingSpec` with safe declarative conditions |
| M3-S05 | Assembly handlers: source, workstation, checkpoint, sink |
| M3-S06 | Fault handlers: rework, hold/release, breakdown, line-in/out |
| M3-S07 | Headless TIPA integration test |

---

## M4 — Transport and Visualization

| Slice | Objective |
|-------|-----------|
| M4-S00 | Fake-data UX spike (parallel to M2–M3) |
| M4-S01 | Extract shared UI utilities (icons, widgets, CSS tokens) + characterization tests |
| M4-S02 | FastAPI adapters: REST endpoints + WebSocket for DM |
| M4-S03 | `DMVisualizationSnapshot` projection |
| M4-S04 | DM renderer (keyed SVG, token layer) |
| M4-S05 | DM command client + run controls UI |
| M4-S06 | DM inspection panels |
| M4-S07 | TIPA layout template + E2E integration |

**FastAPI/WebSocket adapters are in M4, not M2.** This prevents M2 from depending on transport.

---

## M5 — TIPA Demo and Scenarios

| Slice | Objective |
|-------|-----------|
| M5-S01 | TIPA topology + routing + process YAML |
| M5-S02 | Baseline scenario |
| M5-S03 | Fault scenario (breakdown, quality, rework) |
| M5-S04 | Hybrid intervention scenario |
| M5-S05 | E2E demo smoke |

---

## M6 — Product Integration

- Layout editor
- Multi-run management
- Authentication
- Persistence

---

## M7 — Scaling and Hybrid

- Canvas renderer
- MES/PlantOS adapters
- Production scheduling
- Historical replay

---

## Fast-Track: M4-S00 (unchanged)

Parallel to M2–M3. Fake snapshot provider → UI team can build renderer independently. Converge at M4-S07.

---

## Rollback Boundaries

| Slice | Rollback |
|-------|----------|
| Any M2 slice | Delete slice files, revert to previous slice |
| M3-S07 | Delete `domain/`, keep M2 engine |
| M4-S07 | Delete `discrete/` UI, continuous dashboard untouched |
