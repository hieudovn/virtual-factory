# 10 — Test, CI, and Performance Strategy

**Date:** 2026-08-05

---

## 1. Test Matrix

### Runtime Tests

| Layer | What to Test | Framework |
|-------|-------------|-----------|
| Engine lifecycle | initialize → step → auto_run → pause → stop | pytest |
| Event dispatch | handler registry, unknown event, handler error | pytest |
| State transitions | valid/invalid transitions, edge cases | pytest |
| Determinism | same seed + same inputs = same state | pytest |
| Termination | empty scheduler → completed | pytest |
| Command ordering | multiple commands in correct sequence | pytest |

### Domain Tests

| Layer | What to Test |
|-------|-------------|
| Entity conservation | entities created = entities consumed + in flight |
| Queue capacity | buffer overflow rejected |
| Routing | correct route selection, priority order |
| Rework | entity returns to workstation, counter increments |
| Blocked/starved | downstream full → upstream blocked |
| Resource ownership | operator assigned to one workstation at a time |

### Contract Tests

| Layer | What to Test |
|-------|-------------|
| Schema validation | topology, routing, layout YAML validation |
| Snapshot correctness | state → snapshot → matching fields |
| API envelope | request/response format validation |
| WebSocket envelope | message type validation |
| Version mismatch | old snapshot version → resync |

### Visualization Tests

| Layer | What to Test |
|-------|-------------|
| Continuous characterization | Dashboard renders correctly after extraction |
| DM renderer unit | Node rendering, edge rendering, token positioning |
| Snapshot store | Buffer, delta detection, version tracking |
| Command client | Send command, receive result, error handling |
| Reconnect/resync | Client reconnects, receives full snapshot |

---

## 2. CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/vf-dm-ci.yml
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

**Timing:** Introduce in M2-S01 (first engine code). Not before.

---

## 3. Performance Budgets (Provisional)

| Metric | Budget | Notes |
|--------|--------|-------|
| Pending events | 100,000 | Scheduler capacity |
| Processed events/run | 1,000,000 | Audit log cap |
| Concurrent WIP entities | 1,000 | Entity state map |
| Visible tokens | 500 | Token layer rendering |
| Snapshot size | 100 KB | Max JSON payload |
| Server update rate | 10 Hz | Snapshot broadcast |
| UI render rate | 30 fps | SVG animation target |
| Command latency | < 100 ms | Round-trip |
| Browser memory | < 50 MB | DOM + snapshot buffer |
| SVG node count | < 200 | Before Canvas migration consideration |

---

## 4. Migration Thresholds

| Trigger | Action |
|---------|--------|
| >200 SVG nodes with tokens | Evaluate SVG+Canvas token overlay |
| >60 fps animation required | Evaluate Canvas renderer |
| >20 JS modules in discrete/ | Evaluate frontend framework |
| >5 engineers editing UI | Evaluate shared component library |
| DM endpoints > 20 | Extract DM to separate FastAPI router module |
| Snapshot size > 200 KB | Implement delta protocol |

---

## 5. Branch Strategy

```
main              ← merged, stable, SA-gated
feature/dm-m2-s01 ← DiscreteSimulationEngine
feature/dm-m2-s02 ← Handler registry + domain primitives
feature/dm-m3-*   ← Assembly domain
feature/dm-m4-*   ← Visualization
feature/dm-m5-*   ← TIPA integration
```

---

## 6. Review Package Format (per slice)

```
review-exports/dm-m2-s01/
  patch.diff
  manifest.md
  test-output.txt
  collect-output.txt
  smoke-output.txt
```
