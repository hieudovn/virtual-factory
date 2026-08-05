# Slice 1 — Engine-Boundary Compatibility Seam Implementation Report

> **Date:** 2026-08-05
> **Author:** PM (AI Coding Agent)
> **Prompt:** `02-prompt-002-engine-boundary-compatibility-seam.md`

---

## 1. Status

**COMPLETED.** All acceptance criteria met. 196 tests pass (185 baseline + 11 new).

---

## 2. Baseline

| Item | Value |
|------|-------|
| **Full SHA** | `e9aea9040cd0a9f1eb8cca8d2ad347133f08e193` |
| **Branch** | `main` |
| **Python** | 3.11.9 |
| **Working-tree before** | 4 untracked files (assessment docs + XR001 CSVs) |
| **Working-tree after** | 4 modified + 8 untracked (assessment + test + engine files) |
| **Baseline tests** | 185 passed |

---

## 3. Design Implemented

```
Legacy YAML/config (no model_type)
        │
        ▼
  resolve_engine_kind(config)
        │ → "continuous_process" (default)
        ▼
  create_engine(config, dt_s, scenario)
        │
        ▼
  SimulationEngine (existing class, unchanged import path)
        │
        ▼
  Unchanged continuous behavior
```

### 3.1 New files

| File | Purpose |
|------|---------|
| `core/engine_contract.py` | `@runtime_checkable SimulationEngineProtocol` — structural protocol: `initialized`, `dt_s`, `initialize()`, `step()` |
| `core/engine_factory.py` | `resolve_engine_kind()` + `create_engine()` + `UnsupportedEngineError` |
| `tests/test_engine_boundary.py` | 11 tests covering factory, contract, characterization, compatibility |

### 3.2 Modified files

| File | Change |
|------|--------|
| `main.py` | Added `from ...engine_factory import create_engine`. `run_simulation()` uses `create_engine()` instead of `SimulationEngine(...)`. `SimulationEngine` import preserved. |
| `ui/runtime_service.py` | Added factory import. `_init_engine()` uses `create_engine()` instead of `SimulationEngine(...)`. `SimulationEngine` import preserved. |

---

## 4. Compatibility Mechanism

| Concern | How Addressed |
|---------|--------------|
| Legacy configs (no `model_type`) | Default to `"continuous_process"` — no new fields required |
| Explicit `model_type` | Supported: `"continuous_process"` |
| Unsupported engine kind | `UnsupportedEngineError` with kind name in message |
| Direct imports of `SimulationEngine` | Preserved — class still at same path, still importable |
| Existing behavior | `create_engine()` returns the same `SimulationEngine` class |
| Dict configs | `_safe_get_attr()` handles both `dict.get()` and `getattr()` |

---

## 5. Tests Added (11)

| # | Test | Result |
|---|------|--------|
| 1 | Legacy config (no model_type) → continuous_process | PASS |
| 2 | Explicit model_type=continuous_process → correct | PASS |
| 3 | Unsupported kind raises UnsupportedEngineError | PASS |
| 4 | Error message includes the unsupported kind | PASS |
| 5 | Legacy config creates SimulationEngine | PASS |
| 6 | Engine satisfies @runtime_checkable protocol | PASS |
| 7 | Explicit continuous config creates engine | PASS |
| 8 | Unsupported kind raises on create_engine | PASS |
| 9 | SimulationEngine satisfies protocol (structural) | PASS |
| 10 | Factory vs direct produce equivalent results | PASS |
| 11 | Direct import of SimulationEngine still works | PASS |

---

## 6. Final Test Evidence

```
196 passed, 0 failed, 4.42s
VF-1 WTP: 13/13
VF-2 PIM-native: 154/154
Main VF tests: 18/18
New Slice 1 tests: 11/11
```

---

## 7. Deviations from Prompt

**None.** All SA corrections applied:

- ✅ `SimulationEngine` class name and import path preserved
- ✅ `@runtime_checkable Protocol` used instead of ABC hierarchy
- ✅ No `model_type` added to `PlantMetadata`
- ✅ No `TimeManager` changes
- ✅ No `RuntimeState` changes
- ✅ No schema changes
- ✅ No discrete engine code or stubs
- ✅ No `_process_physics()` extraction
- ✅ No dependencies added

---

## 8. Risks Discovered

| Risk | Mitigation |
|------|-----------|
| `python -m virtual_factory validate` fails with `No module named virtual_factory.__main__` | Pre-existing issue (no `__main__.py`). Not caused by Slice 1. Use `virtual-factory` CLI script instead. |
| PytestCacheWarning (permission) | Pre-existing, not caused by Slice 1. |

---

## 9. Working-Tree Status

```
Modified:
  src/virtual_factory/core/engine_contract.py    (NEW)
  src/virtual_factory/core/engine_factory.py     (NEW)
  src/virtual_factory/main.py                    (modified)
  src/virtual_factory/ui/runtime_service.py      (modified)
  tests/test_engine_boundary.py                  (NEW)

Untracked (assessment docs, not part of Slice 1):
  docs/assessment/
  docs/plans/
  out/xr001-*.csv
```

---

## 10. Recommendation for Next Gate

**G1→G2: READY.**

The engine-boundary seam is in place. Legacy configs route correctly. The factory is ready to dispatch to a discrete engine when one exists.

Recommended Prompt 003 scope:

```
Option A (SA preferred): Model envelope + domain-schema dispatch + RunContext
Option B: Minimal discrete scheduler spike isolated from production paths
```

Per SA review, the decision between A and B depends on Slice 1 evidence. The factory seam is now complete — both options are unblocked.
