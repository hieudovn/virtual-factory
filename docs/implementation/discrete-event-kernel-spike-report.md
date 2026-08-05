# Discrete Event Kernel Spike — Implementation Report

**Branch:** `feature/discrete-event-kernel`  
**Baseline:** `7d5e5b0bb2f7ec32dfa235065c920059f5bfbb98`  
**Final commit:** `66cdbc8c3e8aa69fbd97480cebe794794a222f3e`  
**Date:** 2026-08-05  
**Gate:** G2→G3 APPROVED

---

## 1. Objective

Implement a minimal deterministic discrete-event simulation kernel under `src/virtual_factory/discrete/`. No manufacturing domain logic, no callbacks, no external dependencies (SimPy), no schema changes.

---

## 2. Package Design

```
src/virtual_factory/discrete/
├── __init__.py       Package init
├── clock.py          DiscreteClock — monotonic, forward-only, scheduler-owned
├── events.py         ScheduledEvent — frozen dataclass, deep payload validation
├── scheduler.py      FutureEventScheduler — heapq-based, stable, data-driven
└── run_context.py    RunContext — frozen, validated run metadata
```

---

## 3. DiscreteClock

Monotonic clock independent of the continuous `TimeManager`.

| Rule | Behavior |
|------|----------|
| Initial time | `0.0` (configurable) |
| Forward-only | raises `DiscreteClockError` on backward |
| Same-time advance | allowed |
| NaN / infinity | rejected |
| Negative time | rejected |
| Bool input | rejected |
| Type | int or float, stored as float |
| Mutable access | not exposed outside scheduler |

---

## 4. ScheduledEvent

`@dataclass(frozen=True, slots=True)` — genuinely immutable.

| Field | Constraints |
|-------|-------------|
| `event_id` | Non-empty str (required) |
| `simulation_time_s` | Numeric, finite, >= 0 |
| `event_type` | Non-empty str |
| `target_id` | str |
| `priority` | int, not bool |
| `sequence` | `None` before scheduling; assigned by scheduler |
| `payload` | Recursively validated JSON-compatible `Mapping` or `None` |
| `correlation_id` | Non-empty str if provided, or `None` |
| `causation_id` | Non-empty str if provided, or `None` |

### Payload Validation

- All mappings (dict, `MappingProxyType`, any `collections.abc.Mapping`) are **revalidated recursively** — none are trusted based on type alone.
- Allowed value types: `None`, `bool`, `int`, finite `float`, `str`, `Mapping[str→allowed]`, `list`/`tuple[allowed]`.
- Callables, arbitrary objects, and non-finite floats are rejected at any depth.
- Mapping keys must be `str` — integer keys and other non-string keys are rejected without coercion.
- Lists are frozen to `tuple`; mappings are frozen to `MappingProxyType`.
- `to_dict()` returns detached plain `dict`/`list` structures. Mutating the output has no effect on the event.
- `dataclasses.replace(event, sequence=N)` works correctly with nested frozen payloads.
- External mutation of the input payload dict has no effect on the stored event.

---

## 5. FutureEventScheduler

Stable min-heap scheduler using `heapq`. No callbacks, no handler registry.

### Ordering

```
simulation_time_s → priority → sequence
```

No UID or random component. Sequence is a per-scheduler monotonic counter starting at 1.

### Scheduling

| Rule | Behavior |
|------|----------|
| Caller-assigned sequence | Rejected before any state mutation |
| Past-time events | Rejected (`time < current_time_s`) |
| Current-time events | Accepted |
| Duplicate `event_id` | Rejected (`_seen_ids` set) |
| Capacity | Default 100,000; raises when full |
| Sequence assignment | `dataclasses.replace(event, sequence=N)` |

### Inspection (non-mutating)

- `pending_count`
- `is_empty`
- `peek_next()`
- `pending_snapshot(limit: int | None = None)` with validation (rejects negative/bool/float)

### Execution

- `pop_next()` — atomic: if clock rejects advance, event is pushed back, no loss.
- `pop_all()` — yields all in order.

---

## 6. RunContext

`@dataclass(frozen=True, slots=True)` — fully validated immutable run metadata.

| Field | Constraint |
|-------|------------|
| `run_id` | Non-empty str (required) |
| `model_id` | Non-empty str (required) |
| `engine_kind` | Fixed `"discrete_manufacturing"` |
| `model_version` | Non-empty str or `None` |
| `scenario_id` | Non-empty str or `None` |
| `scenario_version` | Non-empty str or `None` |
| `random_seed` | int >= 0, not bool |
| `environment` | Non-empty str (default `"demo"`) |
| `source_kind` | Fixed `"simulation"` |

---

## 7. Slice 1 Corrections (F-001 to F-005)

| ID | Description |
|----|-------------|
| F-001 | `create_engine()` returns `SimulationEngineProtocol` |
| F-002 | `_safe_get_attr()` uses `isinstance(obj, Mapping)`, no broad `Exception` catch |
| F-003 | Explicit discriminator: raw YAML → inject `model_type` → `PlantConfig.model_validate()` |
| F-004 | Characterization test: (name, category, unit, timestamp_s) + LT102_LEVEL value + lifecycle |
| F-005 | Removed unused `SimulationEngine` imports |

---

## 8. Changed Files

```
A  docs/implementation/discrete-event-kernel-spike-report.md
M  src/virtual_factory/core/engine_factory.py         (F-001, F-002)
A  src/virtual_factory/discrete/__init__.py
A  src/virtual_factory/discrete/clock.py
A  src/virtual_factory/discrete/events.py
A  src/virtual_factory/discrete/scheduler.py
A  src/virtual_factory/discrete/run_context.py
M  src/virtual_factory/main.py                        (F-005)
M  src/virtual_factory/ui/runtime_service.py          (F-005)
A  tests/test_discrete_kernel.py                      (118 tests)
M  tests/test_engine_boundary.py                      (F-003, F-004)
```

11 files, +1768/-24.

---

## 9. Test Results

| Suite | Count | Status |
|-------|-------|--------|
| Discrete kernel | 118 | passed |
| Engine boundary | 12 | passed |
| Other (pre-existing) | 185 | passed |
| **Total** | **315** | **0 failed** |

---

## 10. Smoke Tests

| Command | Result |
|---------|--------|
| `virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml` | Valid (3/3 connected, 33/33 publishable) |
| `python -m simulators.vf2.main --package ... --validate-only` | Validation OK |

---

## 11. Known Limitations

- `_seen_ids` grows unbounded with total scheduled event IDs for the scheduler lifetime.
- Cancellation and rescheduling are unsupported.
- Payload is restricted to JSON-compatible values only (string keys, no callables, no arbitrary objects).
- The kernel has no event-handler registry, dispatch, or entity lifecycle.
- This package (`virtual_factory/discrete/`) is a discrete-event **kernel** only — `DiscreteSimulationEngine` is not yet implemented.

---

## 12. Status

- **Committed:** `66cdbc8` on `feature/discrete-event-kernel`
- **Pushed:** `origin/feature/discrete-event-kernel`
- **Merged:** Not merged into `main`
- **Gate:** G2→G3 APPROVED
