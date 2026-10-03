# DDAY-B2 — Bottled Water Hero Line Runtime Reuse — SA Review Report

## Status

**IMPLEMENTED — PR OPEN — READY FOR SA REVIEW**

(Status as reported by the PM; the authoritative machine-derived status is
produced by `.ai-harness/scripts/derive_status.py` through the DDAY-B2 task gate
— see [`.ai-harness/traces/DDAY-B2/gate-report.md`](../traces/DDAY-B2/gate-report.md).
The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.)

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B2` |
| Repository | `hieudovn/virtual-factory` |
| Source of authority | SA Issue `#102` — "DDAY-B2 — Bottled Water Hero Line Runtime Reuse" |
| PR | `#101` (base `main`) |
| Objective | Reuse the existing VF discrete foundation serving the legacy indexed line to make the Bottled Water Filling & Packaging route runnable, automated and deterministic |
| Deliverables | Runnable Bottled Water runtime/config on the frozen 8-station route; generic automated unit flow; deterministic timing/replay; `total/good/reject` counts with invariant; automatic Inspection quality (PASS continues, FAIL rejects); START/PAUSE/RESUME/STOP/RESET; preserved legacy regression |
| Non-deliverables | B3 2D skin, B4 full-factory runtime, B5 Capper degradation scenario, B6 PlantOS integration, B7 deployment, OEE/KPI calculation, MQTT redesign, PIM work, PLC integration, manual operator workflows |
| Forbidden actions | Push to `main`; merge; start B3+; modify forbidden paths; implement legacy domain behaviour in the Bottled Water workspace; publish calculated KPIs; delete/weaken tests; self-certify |
| Stop conditions | Second engine or `core/` redesign; legacy coupling requiring more than a small localized extension; file outside allowlist; baseline mismatch/advance; legacy regression break; B3+ scope creep |
| Authorization boundary | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `sa/dday-track-b-20261003` |
| SA-issued B2 baseline (Issue #102) | `cb908c66ab1de03e1798d9609fdf46d0fc42e675` |
| Branch head at B2 start | `cb908c66ab1de03e1798d9609fdf46d0fc42e675` — **match** |
| Expected base SHA (harness semantics = `origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Actual `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — **match, not advanced** |
| Pre-execution local HEAD | `cb908c6` |
| Pre-execution working tree | clean |
| Preflight (before first B2 write) | `PRECHECK PASSED`, exit 0 |

Baseline semantics are recorded explicitly in the contract
(`expected_base_sha`, `sa_expected_baseline_sha`, `baseline_semantics_note`)
because the harness compares `expected_base_sha` against `origin/main` while the
SA-issued baseline is the branch head. Both were verified true.

---

## Implementation

| Field | Value |
|---|---|
| Contract commit | `211c3ef` — DDAY-B2 task contract authored from SA Issue #102 |
| Implementation commit | `135113d` — Bottled Water hero line reuse on the existing discrete runtime |
| Evidence commit | `9314d52` — evidence pack |
| Changed files | `configs/workspaces/bottled-water-dday/line.yaml` (A), `src/virtual_factory/assembly/line_runtime.py` (M), `src/virtual_factory/assembly/demo_controller.py` (M), `tests/test_dday_b2_bottled_water_line.py` (A), `.ai-harness/tasks/DDAY-B2.json` (A) |
| Diffstat vs B1 baseline | 5 files changed, 1356 insertions(+), 17 deletions(-) |
| Unexpected files | none — the changed-file set is complete (see evidence 10) |
| Full patch | [evidence/DDAY-B2/implementation.patch](../evidence/DDAY-B2/implementation.patch) |

---

## Reuse summary

Reused unchanged: the deterministic indexed stop-and-go engine
(`AssyLineRuntime.execute_dwell()` / `index_line()`), config-driven line
definition, the operation-execution foundation and station contracts,
deterministic timing and seed, WIP lifecycle / carrier / conveyor mechanics,
quality-record mechanics, the controller pattern, and the frozen legacy
regression suite.

Smallest generic extensions added (never a Bottled Water hard-code):
configuration-derived station contracts; a configured quality checkpoint in place
of the fixed station map; capability-based final disposition instead of a literal
station id; generic single-material unit entry; and a config-gated
`on_fail: reject` ejection so a failed inspection neither blocks the line nor is
counted good.

Deliberately **not** used: the legacy hard-coded topology, the six-sub-line
composition, the MES bridge and the observation bridge (the latter two are also
forbidden paths). None of them was modified.

The Bottled Water outward raw-fact surface is
`DemoController.line_facts()` → `AssyLineRuntime.line_facts()`. It publishes raw
facts only — no OEE, availability, performance, quality%, energy-per-unit,
utilization or health score.

---

## Evidence

### Route

Configured route equals the frozen order, 8 stations, one contract per position,
and exactly one quality-capable station (`BW-FP-INS01`). An observed unit
traversal (`UNIT_ENTERED` + `WIP_MOVED`) reproduces the whole route in order.
→ [04-route-proof.md](../evidence/DDAY-B2/04-route-proof.md)

### Quality and counts

| Scenario | Cycles | total | good | reject | on line | invariant |
|---|---|---|---|---|---|---|
| PASS | 8 | 8 | 1 | 0 | 7 | PASS |
| ALWAYS_FAIL | 12 | 12 | 0 | 8 | 4 | PASS |

Inspection resolves automatically; PASS continues to downstream completion;
FAIL rejects and is never counted good; `total − good − reject == units_on_line`
in every sampled point.
→ [05-quality-and-count-proof.md](../evidence/DDAY-B2/05-quality-and-count-proof.md)

### Controls

START/PAUSE/RESUME/STOP/RESET all verified, with PAUSE freezing time, positions
and counts, RESUME continuing from the preserved state, STOP being a controlled
stop with no `FAULT`/`DOWNTIME`, and RESET returning to a zeroed, empty, known
initial state.
→ [06-control-proof.md](../evidence/DDAY-B2/06-control-proof.md)

### Determinism

Independent instances and a reset-replay produce identical trace SHA-256 digests
(`6d968db7…`) and identical facts. Step-driven, seeded, no wall-clock.
→ [07-determinism-proof.md](../evidence/DDAY-B2/07-determinism-proof.md)

### Tests

| Suite | Collected | Passed | Failed | Result |
|---|---|---|---|---|
| B2 acceptance (T01–T12) | 17 | 17 | 0 | PASS |
| Legacy regression (T13) | 575 | 575 | 0 | PASS |
| Full suite | 1664 | 1664 | 0 | PASS |

Baseline before B2 was 1647 passed; the delta is exactly the 17 new tests. No
pre-existing test was modified, skipped or removed.
→ [08-assy-regression.md](../evidence/DDAY-B2/08-assy-regression.md),
[09-test-results.md](../evidence/DDAY-B2/09-test-results.md)

### Smoke

`python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py` → exit 0.
Drives the real runtime: START → progression → Inspection → good/reject →
downstream completion, plus PAUSE/RESUME/STOP/RESET and deterministic replay.

### Scope and leakage

Complete changed-file set is inside the allowlist; no forbidden path touched.
Domain-isolation scan over the configuration, raw facts, trace, contracts, unit
identities and quality records found **0** occurrences of the legacy domain
tokens. The legacy demo-snapshot path publishes no Bottled Water state.
→ [10-scope-and-leakage-audit.md](../evidence/DDAY-B2/10-scope-and-leakage-audit.md)

---

## Acceptance Matrix

| ID | Criterion | Result | Evidence |
|---|---|---|---|
| A01 | Existing discrete foundation reused | PASS | evidence 02, 03 |
| A02 | No new engine/foundation | PASS | evidence 10 §E |
| A03 | Exact 8-station route | PASS | evidence 04 |
| A04 | Automatic unit progression | PASS | evidence 04, 09 (T02) |
| A05 | Deterministic replay | PASS | evidence 07 (T03) |
| A06 | PASS and FAIL/reject flows | PASS | evidence 05 (T04, T05) |
| A07 | Count invariant | PASS | evidence 05 (T06) |
| A08 | START/PAUSE/RESUME/STOP/RESET | PASS | evidence 06 (T07–T11) |
| A09 | No outward legacy/APxx leakage | PASS | evidence 10 §B (T12) |
| A10 | Legacy regression green | PASS | evidence 08 |
| A11 | No OEE/KPI implementation | PASS | evidence 10 §C |
| A12 | No B3/B4/B5/B6/B7 work | PASS | evidence 10 §F |
| A13 | All edits inside allowlist | PASS | evidence 10 §A |
| A14 | Required remote + exact-head CI evidence | see gateway section below | traces/DDAY-B2/evidence.json |

---

## Remote / exact-head invariant

Required: `remote branch HEAD = PR #101 head SHA = CI head SHA = reported review SHA`.

| Field | Value |
|---|---|
| Reported review SHA | HEAD of `sa/dday-track-b-20261003` after the evidence commit |
| Remote branch HEAD | verified by `verify_remote_state.py` (gate P08) |
| PR #101 head SHA | verified (gate P09) |
| CI head SHA / conclusion | verified by `verify_exact_head_ci.py` (gate P10) |
| Machine record | `.ai-harness/traces/DDAY-B2/evidence.json` |

The PM reports the invariant only from that machine record; hand-transcribed CI
values are not used as evidence.

---

## Deferred gaps (classified, not delivered)

| Gap | Slice |
|---|---|
| Dedicated Bottled Water 2D skin; generic outward snapshot schema | **B3** |
| Water Treatment / Utilities / Warehouse runtime; full-factory overview | **B4** |
| Capper deterministic degradation (NORMAL → DEGRADING → WARNING → INTERMITTENT_STOP → RECOVERY) and the `FAULT`/`DOWNTIME` operating states | **B5** |
| PlantOS local integration proof (MQTT JSON payloads, stable ID resolution, historian) | **B6** |
| VPS co-located deployment and integrated D-Day verification | **B7** |
| API/UI wiring for the Bottled Water workspace (`api.py` seam not needed for B2) | B3 or later |
| `UNKNOWN` operating state | not produced by B2; belongs with the fault/downtime slices |

---

## Issues

| Type | Details |
|---|---|
| Tool failures | none required for the acceptance items |
| Unknown evidence | none |
| Contradictions | none |
| Process note | The harness defines `expected_base_sha` against `origin/main`, whereas the SA-issued B2 baseline is the branch head. Both are recorded truthfully in the contract; no governance fact was changed. |

---

## Derived Status

| Field | Value |
|---|---|
| Derived status | produced by `.ai-harness/scripts/derive_status.py`; see `.ai-harness/traces/DDAY-B2/evidence.json` |
| Requested gate | `ready_for_sa_review` |
| Requested human decision | SA review of the exact head diff, tests and evidence |
| Merge authorization | **not granted** |
| Next-slice authorization | **not granted** |
