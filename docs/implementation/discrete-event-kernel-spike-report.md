# Discrete Event Kernel Spike — Implementation Report (003E)

**Prompt:** 003E  
**Branch:** `feature/discrete-event-kernel`  
**Baseline:** `7d5e5b0bb2f7ec32dfa235065c920059f5bfbb98`  
**Date:** 2026-08-05

---

## Objective

Close the final MappingProxyType payload-validation bypass (E-001), update scheduler docstring, run full evidence, commit and push.

---

## Correction E-001 — MappingProxyType validation bypass

All mappings (dict, `MappingProxyType`, any `collections.abc.Mapping`) are now revalidated recursively — none are trusted based on type alone. The `isinstance(payload, MappingProxyType)` shortcut has been removed.

`_validate_and_freeze()` uses `isinstance(value, Mapping)` and revalidates every key and value. `_to_plain()` uses `isinstance(value, Mapping)` for serialization.

`dataclasses.replace(event, sequence=N)` continues to work correctly with nested mappings.

## Docstring Fix
`scheduler.py` docstring updated: "caller-provided sequence is ignored" → "caller-assigned sequence is rejected".

---

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| Discrete kernel | 118 | ✅ passed |
| Engine boundary | 12 | ✅ passed |
| Other (pre-existing) | 185 | ✅ passed |
| **Total** | **315** | **0 failed** |

---

## Smoke Tests

| Command | Result |
|---------|--------|
| `virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml` | ✅ Valid (3/3, 33/33) |
| `python -m simulators.vf2.main --package ... --validate-only` | ✅ Validation OK |

---

## Known Limitations

- `_seen_ids` grows unbounded with scheduler lifetime
- Cancellation/rescheduling unsupported
- Payload JSON-compatible only (string keys, no callables, all mappings revalidated)
- Kernel only — no `DiscreteSimulationEngine`, no handler registry

## Status

- **Commit status:** COMMITTED + PUSHED
- **Branch:** `feature/discrete-event-kernel`
- **Merge status:** NOT MERGED

---

## Objective

Apply the final narrow event-contract and evidence corrections per SA Gate G2→G3 review of 003C.

---

## Corrections (C-001 through C-005)

### C-001 — Non-string payload keys rejected
Payload dict keys are validated with `isinstance(key, str)`. Non-string keys raise `EventRecordError("mapping keys must be str")`. No silent coercion via `str(k)`.

### C-002 — Caller-assigned sequence rejected
`schedule()` checks `event.sequence is not None` **before** any state mutation (capacity, ID set, counter, time). Raises `FutureEventSchedulerError("sequence is scheduler-owned")`. Rejection is side-effect-free: counter not incremented, ID not added, count unchanged, time unchanged. Same event ID can be re-submitted with `sequence=None`.

### C-003 — Atomic push-back directly tested
Monkeypatches `_clock.advance_to` to raise `DiscreteClockError`. Confirms `pop_next()` raises `FutureEventSchedulerError`, pending count stays 1, `peek_next()` returns same event, clock unchanged.

### C-004 — Correct CLI smoke commands
`virtual-factory validate` (installed command, not `python -m`) — ✅ Valid, 3/3 equipment connected, 33/33 publishable. VF2 validate-only — ✅ Validation OK.

### C-005 — Documentation updated
All known limitations documented below.

---

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| Discrete kernel | 110 | ✅ passed |
| Engine boundary | 12 | ✅ passed |
| Other (pre-existing) | 185 | ✅ passed |
| **Total** | **307** | **0 failed** |

---

## Smoke Tests

| Command | Result |
|---------|--------|
| `virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml` | ✅ Valid (3/3 connected, 33/33 publishable) |
| `python -m simulators.vf2.main --package ... --validate-only` | ✅ Validation OK |

---

## Known Limitations

- `_seen_ids` grows with total scheduled event IDs for the scheduler lifetime (unbounded set).
- Cancellation and rescheduling remain unsupported.
- Payload is restricted to JSON-compatible values only (no callables, no arbitrary objects, string keys only).
- The kernel is not yet an executable discrete engine; it has no event-handler registry, dispatch, or entity lifecycle.
- This package (`virtual_factory/discrete/`) is a discrete-event **kernel** only — `DiscreteSimulationEngine` is not yet implemented.

---

## SA Mandate Compliance

| Mandate | Status |
|---------|--------|
| No SimPy dependency | ✅ |
| No schema changes | ✅ |
| Internal heapq scheduler | ✅ |
| Data-driven events (no callbacks) | ✅ |
| Code under `src/virtual_factory/discrete/` | ✅ |
| No discrete registration in factory | ✅ |
| No TIPA/manufacturing logic | ✅ |
| Event true immutability (frozen dataclass) | ✅ |
| Payload recursively immutable, no key coercion | ✅ |
| Caller-assigned sequence rejected | ✅ |
| Atomic push-back directly tested | ✅ |
| Ordering: time → priority → sequence | ✅ |
| Correct installed CLI smoke | ✅ |

## Status

- **Commit status:** NOT COMMITTED
- **Push status:** NOT PUSHED
- **Merge status:** NOT MERGED
