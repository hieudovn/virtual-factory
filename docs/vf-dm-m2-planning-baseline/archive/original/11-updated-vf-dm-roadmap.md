# 11 — Updated VF-DM Roadmap

**Date:** 2026-08-05

---

## M2 — Discrete Runtime and Control Core

| Slice | Objective | Deliverables | Tests | Exit Criteria |
|-------|-----------|-------------|-------|---------------|
| **M2-S00** | Architecture planning | This planning pack (16 files) | N/A | SA approves pack |
| **M2-S01** | `DiscreteSimulationEngine` | Engine class, lifecycle, event loop | Engine lifecycle, state transitions | 2-node source→sink integration test |
| **M2-S02** | Handler registry + dispatch | Registry, handler protocol, `DispatchResult` | Registry CRUD, dispatch, error paths | All handler scenarios pass |
| **M2-S03** | `DiscreteRuntimeService` | Service class, REST endpoints, WebSocket | API tests, WS message tests | Endpoint smoke test |
| **M2-S04** | Command model | Command envelope, validation, audit | Command validation, state machine | Command round-trip test |

**Branch:** `feature/dm-m2-s01` (per slice)

---

## M3 — Assembly Domain and Flow Core

| Slice | Objective |
|-------|-----------|
| **M3-S01** | Domain primitives: `NodeState`, `EntityState`, `RouteState` |
| **M3-S02** | Topology loader + validator |
| **M3-S03** | Routing engine + entity lifecycle handlers |
| **M3-S04** | Source, workstation, checkpoint, sink handlers |
| **M3-S05** | Rework, hold/release, breakdown, line-in/out handlers |
| **M3-S06** | Domain integration test: full TIPA flow (headless) |

---

## M4 — Interactive 2D Visualization

| Slice | Objective |
|-------|-----------|
| **M4-S00** | Fake-data UX spike (no real engine) |
| **M4-S01** | Extract shared UI foundation |
| **M4-S02** | DM renderer + token layer |
| **M4-S03** | DM command client + run controls |
| **M4-S04** | DM inspection panels |
| **M4-S05** | TIPA layout template + integration |

---

## M5 — TIPA Assembly Template and Demo Scenarios

| Slice | Objective |
|-------|-----------|
| **M5-S01** | TIPA topology YAML + validation |
| **M5-S02** | TIPA routing YAML |
| **M5-S03** | Baseline scenario (no faults) |
| **M5-S04** | Fault scenario (breakdown, quality fail, rework) |
| **M5-S05** | Hybrid intervention scenario |
| **M5-S06** | End-to-end demo + smoke tests |

---

## M6 — Product Integration and Authoring

- Layout editor (drag-drop)
- Multi-run comparison
- Authentication
- Persistence

---

## M7 — Productization, Scaling, and Hybrid

- Canvas renderer migration
- MES/PlantOS/PIM adapters
- Production scheduling
- Historical replay

---

## Fast-Track: M4-S00 Fake-Data UX Spike

Parallel to M2 runtime development. Fake snapshot provider → UI team can build renderer without waiting for real engine.

**Convergence:** When real engine is ready (M3-S06), swap fake provider for real `DiscreteRuntimeService`. Same snapshot contract ensures no UI changes needed.

---

## Rollback Boundaries

| Slice | Rollback |
|-------|----------|
| M2-S01 | Delete `engine.py`, revert to kernel only |
| M3-S06 | Delete `domain/`, keep engine + kernel |
| M4-S05 | Delete `discrete/` UI, keep continuous dashboard |
