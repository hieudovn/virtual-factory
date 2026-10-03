# DDAY-B4 — 01. Baseline, scope and reuse map

Task: **DDAY-B4 — Full-Factory Basic Simulation + Autonomous Runtime**
SA contract: `hieudovn/virtual-factory` Issue #105
Repository: `hieudovn/virtual-factory` · Branch: `sa/dday-track-b-20261003` · PR #101
Contract: [`.ai-harness/tasks/DDAY-B4.json`](../../../tasks/DDAY-B4.json)

## 1. Baseline

| Item | Value |
| --- | --- |
| SA expected baseline (Issue #105) | `23b6208266751a8c508b0d96fd7a736dffc5676c` |
| Branch head at first B4 write | `23b6208266751a8c508b0d96fd7a736dffc5676c` (match) |
| `origin/main` at preflight | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (unchanged) |
| Working tree at preflight | clean |
| Preflight result | PASS (exit 0) |

`expected_base_sha` in the contract is `origin/main`, because the harness
(preflight / changed-file allowlist) compares against `origin/main`; the SA
baseline is recorded separately as `sa_expected_baseline_sha`. This is the same
convention used, and disclosed, in DDAY-B2/B2-C01/B3.

## 2. What B4 adds — and what it does not

B4 turns the B3 target-line demo into a **small but coherent whole-factory
simulation** with a **server-side autonomous runtime**. It adds exactly one new
domain module plus configuration, one new read-only endpoint and an asyncio
runner; everything else is reuse.

| Concern | Decision |
| --- | --- |
| Discrete line engine | **Reused unchanged** — `AssyLineRuntime` via `DemoController` |
| B2 line semantics | **Unchanged** (route, dwell, counts, quality/reject, run states) |
| B3 target-line projection | **Moved, not rewritten** — one implementation, `project_target_line()` |
| New simulation engine | **Not created** |
| New telemetry framework / protocol gateway / historian / persistence | **Not created** |
| KPI calculation | **Not created** (FactoriX IIoT / PlantOS own it) |
| Factory hierarchy | **Read from the frozen B1 `topology.yaml`** — single source of truth |
| PlantOS `Line` entity | **Not created** — `BW-FP` stays an `Area` with `role=production_line` |
| Browser as production clock | **Removed** — the server owns the clock; the skin is observer-only |

## 3. Reuse map

```
                       ┌──────────────────────────────────────────┐
  configs/workspaces/  │  BottledWaterFactory (NEW, B4)           │
  bottled-water-dday/  │  src/virtual_factory/workspaces/          │
  ├── topology.yaml ──►│  bottled_water.py                        │
  │   (B1, frozen)     │                                          │
  │   hierarchy +      │  ┌────────────────────────────────────┐  │
  │   taxonomy source  │  │ aggregate area models              │  │
  ├── line.yaml ──────►│  │  BW-WT water balance + bounded tank│  │
  │   (B2, frozen)     │  │  BW-BP logical preparation         │  │
  ├── signals.yaml     │  │  BW-UT utilities + energy          │  │
  │   (B1, raw facts)  │  │  BW-WH dispatch / FG balance       │  │
  └── factory.yaml ───►│  └────────────────────────────────────┘  │
      (NEW, B4)        │                                          │
                       │  component ──────────► DemoController     │
                       │                        (B2, reused)       │
                       │                          └─ AssyLineRuntime│
                       │                             (B2/B3, as-is)│
                       └──────────────────────────────────────────┘
                                     ▲                 ▲
        asyncio runner (api.py, NEW) ┘                 └ observer/control
        autonomous server-side clock                      endpoints (B3, reused)
```

| B4 artefact | Kind | Reuse / origin |
| --- | --- | --- |
| `configs/workspaces/bottled-water-dday/factory.yaml` | new config | aggregate parameters only; declares `hierarchy_source: topology.yaml` |
| `src/virtual_factory/workspaces/bottled_water.py` | new module | composes `DemoController`; reads the frozen B1 topology; owns the aggregate models and the factory clock |
| `src/virtual_factory/ui/api.py` | edited | `_bw_autorun_loop` mirrors the existing `RuntimeService.start_loop()/_run_loop()` asyncio pattern; adds `GET /bottled-water-demo/factory`; the B3 endpoints now delegate to the whole-factory composition |
| `src/virtual_factory/ui/static/bottled_water_demo.js` | edited | the presentation clock no longer drives production: it only polls state |
| `src/virtual_factory/ui/static/bottled_water_demo.html` | edited | the rate control is relabelled as a display refresh control |
| `src/virtual_factory/assembly/line_runtime.py` | **untouched** | B2/B3 frozen foundation |
| `src/virtual_factory/assembly/demo_controller.py` | **untouched** | the B2 generic single-line seam already sufficed |
| `src/virtual_factory/core/`, `telemetry/`, `protocols/`, `scenarios/` | **untouched** | forbidden |

No shared package hierarchy was created outside `src/virtual_factory/workspaces/`
and no `core/`, `telemetry/`, `protocols/` or `scenarios/` change was required, so
no `STOPPED — SA ARCHITECTURE REVIEW REQUIRED` condition was triggered.

## 4. Files touched by this slice

See [`scope-contract-b4-baseline.json`](scope-contract-b4-baseline.json) for the
machine-checked list (diff against the B4 baseline `23b6208`), and
[`implementation.patch`](implementation.patch) for the full diff.

Prior-slice artefacts that appear in the diff against `origin/main` (the B1
configs, the B2 runtime, the B3 skin and earlier evidence/reports) are listed in
the contract's `allowed_paths` **only so the allowlist diff check is truthful**;
they are not authorized for modification in B4. The authoritative statement of
what B4 actually changed is the diff against the B4 baseline above.
