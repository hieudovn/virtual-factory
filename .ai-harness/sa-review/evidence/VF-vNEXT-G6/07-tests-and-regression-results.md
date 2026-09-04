# VF-vNEXT-G6 · Evidence 07 — Tests + regression results

## 1. New G6 tests

Command: `python -m pytest tests/test_ui_hierarchy.py -q`

Result: **26 passed** (0 failures). Covers the Issue #51 test set:
1 recursive hierarchy serialization preserves canonical StructuralPath;
2 deterministic G1 order; 3 container-only vs executable capability;
4 path-qualified selection / no ambiguous bare-id authority;
5 exact TIPA -> ASSY -> six sub-lines (projection + API);
6 ASSY-SLxx selection maps to the same sub-line context without
resetting/reconstructing runtimes; 7 structural selection does not change ASSY
domain semantics (no reset/step/reconstruction calls; domain scripts
untouched); 8 continuous view retains existing behavior and is ROOT-ONLY (no
invented hierarchy); 9 Inspector (object) vs Monitoring (scope) distinct;
10 no G7 run-control/replay/orchestration API (read-only GET route scan);
11 no G8+ (allowlist + module checks).

## 2. Existing UI/API/S04B-gating tests (directly relevant)
`test_api.py`, `test_demo_overview.py`, `test_ops03_interaction.py`,
`test_ops04_c01.py` → **134 passed** (0 failures).

## 3. Regression groups (Issue #51)

| Group | Result |
|---|---|
| New G6 tests | **26 passed** |
| G5 federation tests | **26 passed** |
| G4 composition tests | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm_manager) | **328 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1901 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black; no JS lint configured) |

## 4. Flakes
None surfaced (ASSY oracle and full suite both clean).

## 5. Lint / type / compile / harness
- No configured ruff/mypy/black (unchanged); plain-JS static files have no
  configured linter.
- `python -m compileall -q src/virtual_factory/ui tests/test_ui_hierarchy.py`
  → exit 0.
- No modified file outside the G6 allowlist (verify_changed_files PASS).
- Task-contract preflight: baseline matches `origin/main`
  `f5261c8ca18cd4e01779c0274b55270ba028b4e5`; branch `feature/vf-vnext-g6`
  created from required base `d1419cec3bd87d283ee9dcb03c412479a794359d`; clean
  after commit.
