# 14-v3 — Slice Matrix (Final)

**Date:** 2026-08-05  
**Replaces:** `14-...-v2.md`  
**Corrections:** V2-F03 (slice ownership aligned)

---

## M2-S01 — Pure Engine Lifecycle

| Item | Detail |
|------|--------|
| **Owns** | `RunStatus`, `DiscreteRunState`, `RuntimeSnapshot`, `EventDispatcherProtocol`, `HandlerOutcome`, `DiscreteSimulationEngine` |
| **Branch** | `feature/dm-m2-s01` |
| **Excludes** | HandlerRegistry, RunController, service, API, RNG, domain |

## M2-S02 — Handler Registry

| Item | Detail |
|------|--------|
| **Owns** | `HandlerRegistry` (concrete), registration/duplicate policy, unknown-event policy, handler exception normalization |
| **Branch** | `feature/dm-m2-s02` |

## M2-S03 — Event Trace + Diagnostics

| Item | Detail |
|------|--------|
| **Owns** | Bounded event trace ring buffer, richer diagnostics, snapshot hardening |
| **Branch** | `feature/dm-m2-s03` |

## M2-S04 — Run Controller + Commands

| Item | Detail |
|------|--------|
| **Owns** | `DiscreteRunController`, `ExecutionMode`, command queue, safe-point, `allowed_actions` projection |
| **Branch** | `feature/dm-m2-s04` |

## M2-S05 — Determinism + Safety

| Item | Detail |
|------|--------|
| **Owns** | RNG ownership, max-events limit, no-progress detection, replay metadata |
| **Branch** | `feature/dm-m2-s05` |

## M2-S06 — Integration Proof

| Item | Detail |
|------|--------|
| **Owns** | Domain-neutral integration test (generic test domain) |
| **Branch** | `feature/dm-m2-s06` |

## M2-S07 — Run Service

| Item | Detail |
|------|--------|
| **Owns** | `DiscreteRunService`, one-run ownership, service smoke test |
| **Branch** | `feature/dm-m2-s07` |

---

## M3 (Assembly Domain, 7 slices)
## M4 (Transport + Visualization, 7 slices)
## M5 (TIPA Demo, 5 slices — TIPA config begins M5-S01)
