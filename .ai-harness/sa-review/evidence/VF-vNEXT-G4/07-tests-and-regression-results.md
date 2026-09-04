# VF-vNEXT-G4 · Evidence 07 — Tests + regression results

## 1. New G4 tests

Command: `python -m pytest tests/test_composition_ports.py
tests/test_composition_graph.py tests/test_composition_transfer.py
tests/test_composition_coordinator.py -q`

Result: **49 passed** (0 failures). Includes the C01 authority corrections
(producer ownership, window authority, graph-level multi-producer, endpoint
scope resolution, participant time contract).

## 2. Regression groups (Issue #49)

| Group | Result |
|---|---|
| New G4 tests | **49 passed** (incl. C01) |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 observation + alarm_manager) | **328 passed** |
| Core graph/port/runtime (plant_graph, runtime_factory, runtime_service, engine_boundary, controller_boundary) | **21 passed** |
| Discrete runtime/scheduler (discrete_engine/kernel/run_controller + event_trace) | **279 passed** |
| ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1842 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 3. Flakes

None surfaced in the G4 runs (ASSY oracle and full suite both clean).

## 4. Lint / type / compile / harness

- No configured ruff/mypy/black (unchanged).
- `python -m compileall -q src/virtual_factory/composition` → exit 0.
- Task-contract preflight: baseline matches (`origin/main` =
  `f5261c8ca18cd4e01779c0274b55270ba028b4e5`); clean after commit (evidence 08).
- Changed-file validation against the G4 allowlist: PASS (15 files).
