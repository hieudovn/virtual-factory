# 14 — Implementation Slice Matrix

**Date:** 2026-08-05

---

## M2 — Discrete Runtime and Control Core

| Slice | Branch | Description | Files Created | Tests Added | Exit Criteria |
|-------|--------|-------------|--------------|-------------|---------------|
| **M2-S00** | (planning) | Architecture planning | 16 docs | N/A | SA approves |
| **M2-S01** | `feature/dm-m2-s01` | `DiscreteSimulationEngine` | `discrete/engine.py` | ~15 | Engine lifecycle, 2-node integration |
| **M2-S02** | `feature/dm-m2-s02` | Handler registry | `discrete/handler.py` | ~10 | Registry CRUD, dispatch |
| **M2-S03** | `feature/dm-m2-s03` | `DiscreteRuntimeService` | `ui/discrete_runtime_service.py`, API routes | ~10 | API endpoint smoke |
| **M2-S04** | `feature/dm-m2-s04` | Command model | `discrete/commands.py` | ~10 | Command round-trip |

**Total M2 tests:** ~45 new

---

## M3 — Assembly Domain and Flow Core

| Slice | Description | Tests |
|-------|-------------|-------|
| M3-S01 | Domain primitives | ~15 |
| M3-S02 | Topology loader | ~10 |
| M3-S03 | Routing engine | ~15 |
| M3-S04 | Workstation/checkpoint/sink handlers | ~20 |
| M3-S05 | Fault/rework/hold handlers | ~15 |
| M3-S06 | Full TIPA headless integration | ~10 |

**Total M3 tests:** ~85

---

## M4 — Interactive 2D Visualization

| Slice | Description | Tests |
|-------|-------------|-------|
| M4-S00 | Fake-data UX spike | N/A (throwaway) |
| M4-S01 | Extract shared UI | ~10 characterization |
| M4-S02 | DM renderer | ~15 |
| M4-S03 | DM controls + command client | ~10 |
| M4-S04 | DM inspection | ~10 |
| M4-S05 | TIPA layout + integration | ~10 |

**Total M4 tests:** ~55

---

## M5 — TIPA Demo and Scenarios

| Slice | Description | Tests |
|-------|-------------|-------|
| M5-S01 | TIPA topology YAML | ~5 |
| M5-S02 | TIPA routing YAML | ~5 |
| M5-S03 | Baseline scenario | ~5 |
| M5-S04 | Fault scenario | ~5 |
| M5-S05 | Hybrid scenario | ~5 |
| M5-S06 | E2E demo smoke | ~5 |

**Total M5 tests:** ~30

---

## Cumulative Test Projection

| Milestone | Cumulative Tests |
|-----------|-----------------|
| Baseline (M1) | 315 |
| M2 complete | ~360 |
| M3 complete | ~445 |
| M4 complete | ~500 |
| M5 complete | ~530 |
