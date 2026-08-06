# 11-v3 — Updated VF-DM Roadmap (Final)

**Date:** 2026-08-05  
**Replaces:** `11-...-v2.md`  
**Corrections:** V2-F10 (TIPA milestone)

---

## M2 — Discrete Runtime Core (7 slices, domain-neutral)

| Slice | Branch | Key Deliverable |
|-------|--------|----------------|
| M2-S01 | `feature/dm-m2-s01` | `DiscreteSimulationEngine`, `EventDispatcherProtocol`, `HandlerOutcome`, `RunStatus`, `DiscreteRunState`, `RuntimeSnapshot` |
| M2-S02 | `feature/dm-m2-s02` | `HandlerRegistry`, registration policy, dispatch |
| M2-S03 | `feature/dm-m2-s03` | Bounded event trace, diagnostics, snapshot hardening |
| M2-S04 | `feature/dm-m2-s04` | `DiscreteRunController`, `ExecutionMode`, command queue, safe-point |
| M2-S05 | `feature/dm-m2-s05` | Determinism, RNG, max-events limit, no-progress safety, replay metadata |
| M2-S06 | `feature/dm-m2-s06` | Domain-neutral integration proof |
| M2-S07 | `feature/dm-m2-s07` | `DiscreteRunService`, one-run ownership |

---

## M3 — Assembly Domain (7 slices)

| Slice | Focus |
|-------|-------|
| M3-S01 | Domain primitives |
| M3-S02 | `SimulationTopology` loader |
| M3-S03 | `ProcessDefinition` + `ScenarioParameters` |
| M3-S04 | `RoutingSpec` safe conditions |
| M3-S05 | Core handlers |
| M3-S06 | Fault handlers |
| M3-S07 | **Generic parallel-assembly headless integration** (C02-11) |

---

## M4 — Transport + Visualization (7 slices)

| Slice | Focus |
|-------|-------|
| M4-S00 | Fake-data UX spike |
| M4-S01 | Extract shared UI + characterization tests |
| M4-S02 | FastAPI adapters: REST + WS + `SnapshotMessage` envelope |
| M4-S03 | `DMVisualizationSnapshot` projection |
| M4-S04 | DM renderer |
| M4-S05 | DM command client + controls |
| M4-S06 | DM inspection |
| M4-S07 | **Built-in TIPA-shaped layout template + generic/fake integration** (C02-11) |

---

## M5 — TIPA Demo (5 slices) (C02-11)

| Slice | Focus |
|-------|-------|
| M5-S01 | **TIPA topology, process, routing, layout binding package** |
| M5-S02 | Baseline scenario |
| M5-S03 | Fault scenario |
| M5-S04 | Hybrid scenario |
| M5-S05 | **TIPA end-to-end demo smoke** |

TIPA-specific operational configuration and integration begins in M5, not M3 or M4.

---

## M6 — Product Integration
## M7 — Scaling and Hybrid
