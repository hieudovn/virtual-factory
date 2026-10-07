# DDAY-B3 — Bottled Water 2D Target-Line Skin — SA Review Report

## Status

**IMPLEMENTED — PR OPEN — READY FOR SA REVIEW**

Machine-derived by the full canonical task gate for this exact head; see
`.ai-harness/traces/DDAY-B3/gate-report.md` and `evidence.json`.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B3` |
| Authority | SA Issue `#104` (B3 only), PR `#101` |
| Objective | Dedicated Bottled Water 2D skin for the running B2 target line, reusing VF UI mechanics but with workspace-specific artwork and no foreign visual vocabulary |
| Non-deliverables | B4/B5/B6/B7 work, line-semantics change, snapshot/observation redesign, KPI calculation, manual operator workflows, material rewrite of the other skin |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-issued B3 baseline (Issue #104) | `f311edeeda595b3bcbc1a53dece5f9812a6435b1` — match at B3 start |
| `origin/main` (harness `expected_base_sha`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight before first B3 write | `PRECHECK PASSED`, exit 0, clean tree |

---

## Implementation (complete change set)

```
A .ai-harness/tasks/DDAY-B3.json
M src/virtual_factory/ui/api.py
A src/virtual_factory/ui/static/bottled_water_demo.html
A src/virtual_factory/ui/static/bottled_water_demo.js
A src/virtual_factory/ui/static/bottled_water_demo.css
A tests/test_dday_b3_bottled_water_ui.py
6 files changed, 2650 insertions(+)
```

`demo_controller.py` was permitted "only if a very small generic read/control seam
is required" and was **not required** — every runtime call the skin needs is
already public. It is not modified.

### Reuse map

Reused mechanics: SVG viewBox canvas, pan/zoom/zoom-fit interaction, selection +
floating popup pattern, presentation-clock pacing of engine ticks,
reduced-motion-aware unit movement, state-highlight conventions, runtime control
wiring, and the existing design-token conventions.

Not reused: the other line's skin assets, artwork, icons, layout, flow direction,
labels or APxx vocabulary. The Bottled Water skin is self-contained with its own
eight machine drawings (blower/hopper, spray rinser, filler manifold, capper head,
camera + light cone, label roll, case packer, palletizer) plus a bottle token.

### Runtime binding

New endpoints under `/bottled-water-demo`: page, static assets, `state`
(raw-fact projection), `unit/{unit_id}` (read-only), `start`, `pause`, `resume`,
`stop`, `reset`, and `advance` (the presentation-clock tick). Exactly five
operator controls exist in the page. The station order is read from the runtime
route, so the drawing follows the real line.

The projection publishes raw facts only — counts, states, positions, quality
dispositions, bounded event window. No KPI is calculated and no hidden scenario
truth is exposed.

### Interaction defects found and fixed during browser verification

1. **Pan swallowed clicks** — `setPointerCapture` on `pointerdown` retargeted
   `mouseup`/`click` to the canvas, making machines and bottles unclickable while
   the line ran. Capture now starts only after a real drag (>4 px).
2. **Station layer rebuilt every poll** — nodes were replaced between
   `pointerdown` and `click`. Stations are now built once per route and only
   attributes are updated; machines and bottles gained explicit hit areas.
3. **Event window too small** — the default (12) was below one cycle's event
   volume (~20–30), so the skin could drop a cycle between polls. Default is now 60.

---

## Evidence

| Item | File |
|---|---|
| 01 baseline, change set, reuse map | [01-baseline-and-reuse.md](../evidence/DDAY-B3/01-baseline-and-reuse.md) |
| 02 API/runtime binding proof | [02-api-runtime-binding.md](../evidence/DDAY-B3/02-api-runtime-binding.md) |
| 03 visual evidence + screenshots | [03-visual-evidence.md](../evidence/DDAY-B3/03-visual-evidence.md), [screenshots/](../evidence/DDAY-B3/screenshots) |
| 04 tests, regression, scope audit | [04-tests-and-scope.md](../evidence/DDAY-B3/04-tests-and-scope.md) |
| machine record | [machine-evidence.json](../evidence/DDAY-B3/machine-evidence.json) |
| browser record | [browser-evidence.json](../evidence/DDAY-B3/browser-evidence.json) |

### Acceptance criteria (Issue #104)

| # | Criterion | Result |
|---|---|---|
| 1 | Dedicated Bottled Water UI/route reachable and bound to B2 runtime | **PASS** — 8 cycles produce counts `{8,1,0}`, `units_on_line=7`, `dwell=8`, `t=160.0 s` from the real runtime |
| 2 | All 8 frozen stations visible in correct order | **PASS** — route and rendered station order equal the frozen route |
| 3 | Skin visually distinct; no APxx/TIPA labels/icons | **PASS** — 2241 rendered strings scanned across 10 states, 0 hits; page references only its own assets |
| 4 | Bottle/unit movement visible and corresponds to runtime positions | **PASS** — occupancy is a contiguous run matching `units_on_line`; bottles interpolate between station x positions |
| 5 | START/PAUSE/RESUME/STOP/RESET work through UI and preserve B2 semantics | **PASS** — pause freezes identically, resume continues from the preserved time, stop is controlled, reset restores the initial state |
| 6 | total/good/reject and line state visible and track runtime facts | **PASS** — facts strip mirrors `counts`, run/operating state, sim time, dwell |
| 7 | Inspection PASS/FAIL/reject visually observable without manual disposition | **PASS** — PASS and `NG — rejected` captured; no disposition surface exists (404) |
| 8 | Station/unit selection opens useful context without manual decisions | **PASS** — read-only station and unit inspectors; click proofs confirm the drawn element was hit |
| 9 | No B4/B5/B6/B7 implementation mixed in | **PASS** — none of the later-slice terms present; endpoint set is exactly the B3 set |
| 10 | Relevant UI/API/runtime regression tests pass | **PASS** — subset 141/141 |
| 11 | Full suite passes or flaky failure disclosed + rerun green | **PASS** — full suite 1689/1689, 0 failed; flake disclosed below |
| 12 | Exact-head invariant holds | **PASS** — verified by the gate |

### Tests

| Suite | Collected | Passed | Failed |
|---|---|---|---|
| B3 acceptance | 23 | 23 | 0 |
| UI/API/runtime regression | 141 | 141 | 0 |
| Full suite | 1689 | 1689 | 0 |

Suite progression: 1647 → 1664 (B2) → 1666 (B2-C01) → **1689** (B3).

Both required smokes PASS: `SMOKE-BW-UI` (45 live-HTTP claims) and `SMOKE-BW`
(B2 runtime unchanged).

### Screenshots

`01-target-line-running`, `02-paused`, `03-stopped`, `03b-after-reset`,
`04-inspection-station`, `05-bottle-inspector`, `06-reject-running`,
`07-reject-inspection`.

---

## Issues

| Type | Details |
|---|---|
| Tool failures | none |
| Unknown evidence | none |
| Contradictions | none |
| Pre-existing flake (disclosed) | `tests/test_demo_composition.py::test_reset_creates_fresh_configs` asserts `id()` disjointness across `reset()`; `id()` is a memory address, so the assertion is not guaranteed. Reproduced once during evidence generation while the full suite passed in the same run; root cause demonstrated deterministically. Outside the B3 allowlist and explicitly excluded by Issue #104, so not modified. Full suite and exact-head CI are green, satisfying criterion 11. |
| Baseline-diff artifact (disclosed) | `line_runtime.py` is in `allowed_paths` (not `forbidden_paths`) because DDAY-B2 modified it and it therefore appears in the diff from `origin/main`. It is **not** authorized for modification in B3; the B3-scope allowlist check against the B3 baseline passes with exactly the 6 B3 files. Same handling the SA accepted for C01. |

---

## Derived Status

| Field | Value |
|---|---|
| Derived status | from the full canonical task gate — see `.ai-harness/traces/DDAY-B3/evidence.json` |
| Requested gate | `ready_for_sa_review` |
| Merge authorization | **not granted** |
| Next-slice authorization | **not granted** |
