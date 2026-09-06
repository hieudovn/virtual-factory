# VF-vNEXT-G7 · Evidence 07 — Tests + regression results

## 1. New G7 tests

Command: `python -m pytest tests/test_run_control.py -q`

Result: **47 passed** (0 failures). Covers the Issue #52 test set:
1 lifecycle transitions + fail-closed guards; 2 immutable/coherent RunContextV2
+ one scenario authority; 3 workspace/container → deterministic descendant
executable scopes (no fake container participant); 4 executable → itself;
5 stale/wrong run_id cannot mutate; 6 pause/resume do not advance domain state;
7 stop terminal; 8 restart distinct run_id + source lineage; 9 replay distinct
run_id + no overwrite + explicit unavailable; 10 ASSY natural/common boundaries
only + unreachable fails closed (no fractional dwell); 11 standalone ASSY/domain
semantics preserved (runtime identity unchanged across step/reset); 12 continuous
behavior green; 13 reset capability-scoped (no terminal reuse); 14 container-only
never executable; 15 path-qualified effective target (API + UI static);
16 G1–G6 regressions green; 17 no G8+. Includes the G7-C01 tests:
single mutable active attempt (create superseded fails closed; superseded known
run id fails closed; API historical mutation 409); attempt-bound execution state
(restart/replay fresh context at initial time; source runtime untouched; reset
keeps same run_id + same runtime objects; prior records readable history).
Includes the G7-C02 tests (evidence 09): continuous bridge over the accepted
RuntimeService seam (one dt per boundary, in-context reset); root-only
continuous workspace (no invented hierarchy); TIPA + continuous independent
workspace authorities (coexistence, no cross-mutation, foreign target fail
closed, unknown workspace 404); continuous lifecycle + fresh restart; replay
unavailable without a pinned scenario; legacy engine semantics unchanged.

## 2. Regression groups (Issue #52)

| Group | Result |
|---|---|
| New G7 lifecycle/run-control tests | **47 passed** (incl. C01 + C02) |
| Existing UI/API + S04B gating tests | **134 passed** |
| G6 UI hierarchy tests | **31 passed** |
| G5 federation tests | **26 passed** |
| G4 coordinator/composition tests | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm_manager) | **328 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1953 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black; no JS lint configured) |

## 3. Flakes
None surfaced (ASSY oracle and full suite both clean).

## 4. Lint / type / compile / harness
- No configured ruff/mypy/black (unchanged).
- `python -m compileall -q src/virtual_factory/runcontrol src/virtual_factory/ui`
  → exit 0.
- No modified file outside the G7 allowlist (verify_changed_files PASS).
- Task-contract preflight: baseline matches `origin/main`
  `f5261c8ca18cd4e01779c0274b55270ba028b4e5`; branch `feature/vf-vnext-g7`
  created from required base `a10f581ca2e7a8b8b39c605fc54339ae88386922`; clean
  after commit.
