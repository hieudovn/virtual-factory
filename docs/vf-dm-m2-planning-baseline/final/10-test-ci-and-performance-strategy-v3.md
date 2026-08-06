# 10-v3 — Test, CI, Performance (Final)

**Date:** 2026-08-05  
**Replaces:** `10-...-v2.md`  
**Corrections:** V2-F09 (snapshot size)

---

## 1. Limits (hard)

| Metric | Limit |
|--------|-------|
| Processed events/run | 1,000,000 |
| Pending scheduler events | 100,000 |
| Event summary ring buffer | 1,000 |
| WS envelope hard limit | 200 KB |

## 2. Targets (provisional, measured)

| Metric | Target |
|--------|--------|
| Snapshot payload | < 100 KB |
| Snapshot serialization | < 10ms |
| Command latency | < 100ms |
| SVG update time | < 16ms |

## 3. Migration Triggers

| Trigger | Action |
|---------|--------|
| Snapshot > 100 KB | Delta protocol |
| SVG update > 16ms sustained | Canvas token overlay |
| Command latency > 100ms p99 | Profile dispatch |
| JS heap > 50 MB | Paginate entities |

## 4. CI

GitHub Actions introduced at M2-S01. Runs full pytest + smoke on every push.

## 5. Test Strategy (unchanged)
