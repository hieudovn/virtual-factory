# DDAY-B4 — Full-Factory Basic Simulation + Autonomous Runtime — SA Review Report

## Status

**IMPLEMENTED — PR OPEN — READY FOR SA REVIEW**

Machine-derived by the full canonical task gate for this exact head; see
`.ai-harness/traces/DDAY-B4/gate-report.md` and `evidence.json`.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B4` |
| Authority | SA Issue `#105` (B4 only), PR `#101` |
| Objective | Turn the detailed Bottled Water demo into a small but coherent whole-factory simulation with a server-side autonomous runtime, conservation/process consistency and a FactoriX-IIoT-ready asset taxonomy |
| Parent | DDAY-B3 / Issue `#104` CLOSED |
| Non-deliverables | B5 degradation storyline, B6 PlantOS/MQTT integration, B7 deployment, KPI calculation, deep physics, batch/recipe, WMS/MES workflows, manual quality/rework/release, TIPA/APxx semantics, a polished whole-factory UI |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-issued B4 baseline (Issue #105) | `23b6208266751a8c508b0d96fd7a736dffc5676c` — match at B4 start |
| `origin/main` (harness `expected_base_sha`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight before first B4 write | `PRECHECK PASSED`, exit 0, clean tree |

---

## Implementation (complete change set)

```
A configs/workspaces/bottled-water-dday/factory.yaml
A src/virtual_factory/workspaces/__init__.py
A src/virtual_factory/workspaces/bottled_water.py
M src/virtual_factory/ui/api.py
M src/virtual_factory/ui/static/bottled_water_demo.html
M src/virtual_factory/ui/static/bottled_water_demo.js
M tests/test_dday_b3_bottled_water_ui.py
A tests/test_dday_b4_bottled_water_factory.py
M .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py
M .ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py
A .ai-harness/tasks/DDAY-B4.json
A .ai-harness/sa-review/evidence/DDAY-B4/**            (evidence pack)
A .ai-harness/sa-review/reports/DDAY-B4.md
M .ai-harness/sa-review/CURRENT.md
```

Machine-checked list and diff: `scope-contract-b4-baseline.json`,
`implementation.patch`.

**Untouched frozen foundation:** `assembly/line_runtime.py`,
`assembly/demo_controller.py`, `core/`, `telemetry/`, `protocols/`,
`scenarios/`, `ui/runtime_service.py`, `main.py`. No second engine, no forked
ASSY engine, no new telemetry/scenario/protocol/historian/persistence layer.

### Architecture / reuse

A single new domain module composes the existing pieces:

* `BottledWaterFactory` owns exactly one `DemoController` (the B2 generic
  single-line seam), so the skin, the factory projection and the autonomous
  runner share one runtime instance.
* The aggregate area models (Water Treatment, Bottle Preparation, Utilities,
  Warehouse/Dispatch) are small deterministic integrators over configured
  parameters; there is no process physics.
* The factory hierarchy/taxonomy is read from the **frozen B1
  `topology.yaml`** — the only hierarchy source of truth; nothing is duplicated
  and no FactoriX platform canonical ID is created.
* The B3 projection was **moved** into the module as `project_target_line()`
  and is reused by both `/state` and the factory projection, so there is one
  implementation of the target-line facts.
* The autonomous runner mirrors the existing `RuntimeService.start_loop()` /
  `_run_loop()` asyncio pattern; wall clock paces ticks only, simulation truth
  stays deterministic.

### Autonomous runtime

`_bw_autorun_loop()` is created in the FastAPI lifespan and cancelled on
shutdown; `factory_autorun` / `factory_tick_interval_s` let deterministic
harnesses opt out. The B3 skin now polls `GET /state` and never requests a
production step; the five operator controls are unchanged. `/advance` is kept
only as the documented manual/debug seam.

### Control interpretation (documented)

`PAUSE` freezes the simulated clock completely (§2). `STOP` is a *controlled*
stop: production stops, the plant stays energized, the clock keeps running and
only explicitly modelled standby/base load accrues energy (§5.3/§5.6). `FAULT`
is never emitted because no abnormal condition is modelled before B5, so
`STOPPED != FAULT` holds by construction.

---

## Evidence (see `.ai-harness/sa-review/evidence/DDAY-B4/`)

| File | Content |
|---|---|
| `01-baseline-scope-and-reuse.md` | baseline, scope decisions, reuse map |
| `02-autonomous-runtime.md` | headless autonomy proof, control semantics, clock interpretation |
| `03-factory-state-and-taxonomy.md` | whole-factory projection, signal binding, hierarchy/taxonomy |
| `04-conservation-and-process-consistency.md` | water/material/energy/FG balances, utility causality |
| `05-determinism-ui-and-tests.md` | deterministic replay, B3 observer-only, tests, disclosures |
| `machine-evidence.json` | all machine-captured evidence |
| `factory-state-sample.json` | full captured factory projection |
| `smoke_bottled_water_factory.py` | live-HTTP `SMOKE-BW-FACTORY` harness |
| `junit-b4*.xml` | B4 / regression / rerun / full-suite test records |
| `implementation.patch`, `scope-contract-b4-baseline.json` | diff and machine scope |
| `flaky_reset_disclosure.py`, `flaky-reset-disclosure.txt` | pre-existing flake root cause |

### Headline results

| Claim | Result |
|---|---|
| Autonomous progression with **zero** client `/advance` calls | PASS |
| Progression with the B3 page **never opened** | PASS |
| Whole-factory projection | 22 nodes / 69 attributable raw facts |
| Hierarchy matches the frozen B1 topology | PASS (unique ids, one parent per asset, no duplicate Blower) |
| Conservation invariants over 4000 steps | 0 violations, 0 identity errors |
| Tank bounds | `0.2405 … 0.3400 m³` (high 0.34, capacity 0.4), high-level rule engaged |
| Energy identity | `plant = Σ asset + base load × time`, exact |
| Deterministic replay | identical digest sequences; RESET returns the initial digest |
| Calculated KPI / foreign vocabulary leakage | 0 hits in the projection and the skin |
| B3 skin | observer-only, still works as a control surface |
| Full test suite | 1716 passed, exit 0 |

---

## Scope audit

* Only paths authorized by Issue #105 §12 / the B4 contract were modified.
* `line_runtime.py` and `demo_controller.py` were **not** modified — the B2
  generic seam already sufficed, so no "smallest reusable abstraction" extraction
  was needed.
* No forbidden path was touched: `core/`, `telemetry/`, `protocols/`,
  `scenarios/`, `ui/runtime_service.py`, `main.py`, `deploy/`, `pyproject.toml`.
* Two B3 test assertions were **strengthened** (no `/advance` from the skin) and
  three offline B3 harnesses were given `factory_autorun=False` because B4
  authorizes the clock-authority change; nothing was deleted or relaxed. Fully
  disclosed in `05-determinism-ui-and-tests.md` §4.
* No merge, no B5 work, no scope expansion.

---

## Machine gate status

See `.ai-harness/traces/DDAY-B4/gate-report.md` and the `task_gate` block of
`machine-evidence.json`. This report is updated with the machine-derived status
in the gate-status commit; the PM does not self-certify `COMPLETE`, `CLOSED` or
`SA APPROVED`.
