# 10-v2 — Test, CI, and Performance Strategy (Corrected)

**Date:** 2026-08-05  
**Replaces:** `10-test-ci-and-performance-strategy.md`  
**Corrections:** F-012 (performance thresholds)

---

## 1. Performance Budgets — Separated (C-012)

### Limits (hard, enforced)

| Metric | Limit | Enforcement |
|--------|-------|-------------|
| Processed events per run | 1,000,000 | Engine rejects step beyond limit |
| Pending scheduler events | 100,000 | `schedule()` raises when full |
| Event summary ring buffer | 1,000 | Circular buffer, oldest evicted |
| WebSocket message hard limit | 200 KB | Server-side truncation + error |

### Targets (provisional, measured)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Snapshot serialization | < 10ms | `time.perf_counter()` in `to_snapshot()` |
| Command latency (REST) | < 100ms | Server receipt → response |
| Snapshot payload size | < 100 KB | `len(json.dumps())` |
| SVG update time | < 16ms (60fps) | `requestAnimationFrame` timing |
| Browser JS heap delta | < 20 MB over 5 min run | Chrome DevTools memory profiler |

---

## 2. Migration Triggers (C-012)

| Trigger | Measurement | Action |
|---------|-------------|--------|
| SVG update > 16ms sustained | Chrome Performance API | Evaluate Canvas token overlay |
| Snapshot > 100 KB | `len(json.dumps())` | Implement delta protocol |
| Command latency > 100ms p99 | Server-side timing | Profile dispatch; consider async |
| JS heap > 50 MB | Memory profiler | Paginate entity lists; virtualize |
| >3 deployments with different configs | Ops survey | Extract DM to separate service |

**Removed triggers:** JS module count, API endpoint count, operator survey — not architectural.

---

## 3. Test Matrix (unchanged structure, corrected scope)

### M2 Tests

| Slice | Focus | Count (provisional) |
|-------|-------|---------------------|
| M2-S01 | Engine lifecycle, step, status transitions | ~12 |
| M2-S02 | Handler registry CRUD, dispatch, error paths | ~10 |
| M2-S03 | RunState, RuntimeSnapshot, event trace | ~8 |
| M2-S04 | RunController, modes, command queue | ~10 |
| M2-S05 | Determinism, limits, no-progress, replay metadata | ~8 |
| M2-S06 | Domain-neutral integration proof | ~5 |
| M2-S07 | DiscreteRunService | ~8 |

### M4 UI Tests

| Focus | Count |
|-------|-------|
| Continuous characterization (before extraction) | ~5 |
| DM renderer unit | ~10 |
| DM controls + command client | ~8 |
| DM inspection | ~5 |
| Reconnect/resync | ~3 |

---

## 4. CI Pipeline

```yaml
# .github/workflows/vf-dm-ci.yml — introduced at M2-S01
name: VF-DM CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: python -m pytest -q --tb=short
      - run: virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml
```
