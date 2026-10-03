# DDAY-B2-C01 — 05. Scope audit

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `git`;
patch [`implementation.patch`](./implementation.patch).

## Complete C01 change set (vs the C01 baseline `0a1d18e`)

```
A  .ai-harness/tasks/DDAY-B2-C01.json
A  .ai-harness/tests/test_gate_report_provisional.py
A  .ai-harness/sa-review/evidence/DDAY-B2-C01/  (evidence pack + smoke + scope contract)
M  .ai-harness/scripts/run_task_gate.py
M  src/virtual_factory/assembly/line_runtime.py
M  tests/test_dday_b2_bottled_water_line.py
```

Code diff: 987 insertions / 21 deletions across 7 files.

| SA-allowed path (Issue #103) | Used |
|---|---|
| `src/virtual_factory/assembly/line_runtime.py` | yes — +2 semantic lines (plus docstring/comment) |
| `tests/test_dday_b2_bottled_water_line.py` | yes — T12 strengthened, 2 tests added |
| `.ai-harness/scripts/run_task_gate.py` | yes — report writer + PR-state alignment |
| harness tests under `.ai-harness/` | yes — 1 new focused test module |
| `.ai-harness/tasks/DDAY-B2-C01.json` | yes |
| `.ai-harness/sa-review/evidence/DDAY-B2-C01/` | yes |
| `.ai-harness/sa-review/reports/DDAY-B2-C01.md` | yes |
| `.ai-harness/sa-review/CURRENT.md` | yes |

**Nothing else was modified.** In particular the C01 change set does **not**
contain `src/virtual_factory/assembly/demo_controller.py`,
`demo_composition.py`, `station_contracts.py`, `quality_records.py`,
`conveyor.py`, `demo_snapshot.py` or any `src/virtual_factory/ui/` file — all of
which DDAY-B2 had touched or left alone and which C01 must not change.

## Allowlist verification (two independent checks, both PASS)

| Check | Baseline | Result |
|---|---|---|
| Harness allowlist diff | `origin/main` (`f5261c8`) | `FILE VALIDATION PASSED (37 file(s))`, exit 0 |
| C01-scope diff | C01 baseline (`0a1d18e`) | `FILE VALIDATION PASSED (7 file(s))`, exit 0 |

The harness check evaluates the whole branch diff from `origin/main`, which
legitimately includes the frozen DDAY-B1/B2 artifacts (including
`demo_controller.py`, which DDAY-B2 modified). Those are listed under
`allowed_paths` with an explicit note; the C01-scope check against `0a1d18e` is
what proves C01 touched only its own seven files. The scope-check contract copy is
[`scope-contract-c01-baseline.json`](./scope-contract-c01-baseline.json).

## Forbidden-path audit

`core/`, `telemetry/`, `protocols/`, `scenarios/`, `equipment/`, `balance/`,
`control/`, `instrumentation/`, `actuation/`, `assy_mes_bridge.py`,
`observation_bridge.py`, `demo_controller.py`, `demo_composition.py`,
`station_contracts.py`, `quality_records.py`, `conveyor.py`, `demo_snapshot.py`,
`ui/`, `simulators/`, `deploy/`, `docs/deployment/`, the compose files,
`Dockerfile`, `pyproject.toml`, `configs/plants/tipa_assy_demo.yaml`,
`validate_report_consistency.py`, `derive_status.py` and
`PM-EXECUTION-CONTRACT.md`: **all unmodified**.

## Validation-integrity audit (C01-B constraint)

| Constraint | Status |
|---|---|
| `validate_report_consistency.py` unmodified | **yes** (in forbidden_paths, untouched) |
| `derive_status.py` unmodified | **yes** (in forbidden_paths, untouched) |
| Exact-head invariants untouched | **yes** — all still `true`, enforced in P12 |
| Acceptance criteria not relaxed | **yes** — 14 criteria, 2 of them new and stricter (all steps executed / all steps PASS) |
| Validation still fail-closed | **yes** — negative controls in evidence 02 |

## B3+ scope audit

No 2D skin, no Water Treatment/Utilities/Warehouse runtime, no Capper
degradation, no PlantOS integration, no deployment, no MQTT/protocol change, no
OEE/KPI calculation, no new engine or module under `src/`.

## Residuals disclosed

1. The PR-state root cause remains in `.ai-harness/scripts/verify_remote_state.py`
   (outside the allowlist). The orchestrator aligns the representation; a
   follow-up could fix it at the source and remove the shim.
2. `PYTHONIOENCODING=utf-8` must not be forced when invoking the gate on Windows
   (subprocess round-trip encoding); this is an invocation detail, not a
   repository defect, and it does not affect CI.
3. Running the gate without a token cannot resolve the PR (`_resolve_pr` requires
   a token), so the token-authenticated path is the supported full-gate
   invocation.
