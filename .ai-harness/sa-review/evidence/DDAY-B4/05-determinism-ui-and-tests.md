# DDAY-B4 — 05. Determinism, B3 observer-only and tests

Source of truth: [`machine-evidence.json`](machine-evidence.json) →
`determinism`, `b3_observer`, `tests_b4`, `tests_regression`, `tests_full`.

## 1. Deterministic replay (§14.7)

The same configuration, the same seed and the same control sequence produce the
same state trace. Digests are SHA-256 over the canonical JSON of the whole
factory projection:

```
sequence: initial → START+250 s → PAUSE+40 s → RESUME+250 s → STOP+120 s → RESET

run #1  001f6302…  cd6afb6f…  f0992cbd…  7dfbce99…  23e999dd…  001f6302…
run #2  001f6302…  cd6afb6f…  f0992cbd…  7dfbce99…  23e999dd…  001f6302…

identical_control_sequences : true
reset_returns_initial_state : true     (last digest == fresh-instance digest)
step_size_irrelevant        : true     (20 x step(20 s) == 400 x step(1 s))
```

No wall-clock value can enter the simulation: the projection is a pure function of
simulated state (`test_b4_07c` takes two snapshots 0.25 s apart with no stepping
in between and asserts identical digests).

Two identical fresh instances produce the same digest from t = 0, which is what
makes `RESET` a genuine return to the deterministic initial state (tank at its
configured initial fill, zero counters, empty recent-event window).

## 2. B3 target-line UI — observer-only (§2, §10)

| Proof | Value |
| --- | --- |
| Skin POSTs | `/start`, `/pause`, `/resume`, `/stop`, `/reset` — nothing else |
| `skin_posts_advance` | **false** (`/advance` no longer appears in the skin) |
| Skin polls | `bwGet('/state')` |
| Operator buttons | exactly `bw-btn-start|pause|resume|stop|reset` |
| Refresh control | relabelled "display only — the server clock drives production" |
| Page still serves | true, with the same routes as B3 |
| Skin and factory share one runtime | **true** — after a debug advance, `target_line.counts.total == 1` and `factory.simulation_time_s == state.simulation_time_s == 20` |

The `/advance` endpoint **remains** (Issue #105 §2 explicitly allows a manual or
debug seam), but it is no longer the normal D-Day operating path and it is not a
visible operator action. It is documented as such in the endpoint docstring and
asserted by `test_b4_20`.

B3 skin assets, the frozen 8-station route and the B3 operator semantics are
unchanged, so the B3 contract is still satisfied. Two B3 assertions and the two
B3 offline harnesses were adjusted **only** to reflect the authorized change of
the production clock (see §4).

## 3. Test results

| Scope | Command | Result |
| --- | --- | --- |
| B4 slice | `pytest tests/test_dday_b4_bottled_water_factory.py` | **27 passed** (exit 0) |
| Regression subset | `pytest tests/test_api.py tests/test_assy_demo.py tests/test_demo_composition.py tests/test_demo_overview.py tests/test_dday_b2_bottled_water_line.py tests/test_dday_b3_bottled_water_ui.py tests/test_runtime_service.py` | 163/164 then **164/164 on rerun** (pre-existing flake, see §5) |
| Full suite | `pytest -q` | **1716 passed, 0 failed** (exit 0) |

Suite progression across the programme: 1647 (pre-B2) → 1664 (B2) →
1666 (B2-C01) → 1689 (B3) → **1716 (B4)**.

JUnit records: [`junit-b4.xml`](junit-b4.xml),
[`junit-b4-regression.xml`](junit-b4-regression.xml),
[`junit-b4-regression-rerun.xml`](junit-b4-regression-rerun.xml),
[`junit-b4-full.xml`](junit-b4-full.xml).

Requirement → test map (Issue #105 §14):

| # | Requirement | Test |
| --- | --- | --- |
| 1 | START progresses server-side without browser `/advance` | `test_b4_01`, `SMOKE-BW-FACTORY` §1 |
| 2 | Closing / not opening the B3 page does not stop simulation | `test_b4_02`, `test_b4_02b`, `SMOKE-BW-FACTORY` §1 |
| 3 | PAUSE freezes target line and aggregate factory progression | `test_b4_03` |
| 4 | RESUME continues from preserved state | `test_b4_04` |
| 5 | STOP halts progression without becoming FAULT | `test_b4_05` |
| 6 | RESET returns deterministic initial state | `test_b4_06` |
| 7 | Same config/seed + control sequence ⇒ deterministic trace | `test_b4_07`, `test_b4_07b`, `test_b4_07c` |
| 8 | B1 hierarchy appears exactly; one parent per asset | `test_b4_08` |
| 9 | Unique source IDs; no duplicate Blower | `test_b4_09` |
| 10 | Every exposed fact maps to a valid hierarchy node | `test_b4_10` |
| 11 | Water balance coherent; tank bounded | `test_b4_11`, `test_b4_11b` |
| 12 | Water/material consumption follows production counts | `test_b4_12`, `test_b4_12b` |
| 13 | Utilities respond coherently to production load | `test_b4_13` |
| 14 | Cumulative energy monotonic, derived from power/time | `test_b4_14`, `test_b4_14b` |
| 15 | Warehouse/FG follows completed good production | `test_b4_15` |
| 16 | No calculated KPI fields | `test_b4_16` |
| 17 | No TIPA/APxx semantic leakage | `test_b4_17` |
| 18 | B3 target-line UI still works as observer/control surface | `test_b4_18`, `test_b4_19b`, `SMOKE-BW-UI` |
| 19 | B2/B3/legacy ASSY regression green | `test_b4_19`, regression subset, `SMOKE-BW` |
| 20 | Full suite passes (pre-existing flake excepted) | full suite above |
| 21 | Exact-head invariant | machine task gate + PR/CI check |

## 4. Deliberate, disclosed adaptations of earlier artefacts

The B4 authorization changes the **production clock authority** of the shipping
app. Deterministic, offline harnesses that drove production themselves must
therefore opt out of the autonomous clock; this is a required adaptation, not a
weakening of any earlier assertion:

| Artefact | Change | Why |
| --- | --- | --- |
| `tests/test_dday_b3_bottled_water_ui.py` | added `factory_autorun=False` to the two app constructions; strengthened two assertions to require **no** `/advance` from the skin; added `/bottled-water-demo/factory` to the BW route set | keep the B3 contract deterministic and assert the B4 observer-only behaviour |
| `.ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py` | added `factory_autorun=False` | the B3 smoke drives production through the debug seam |
| `.ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py` | added `factory_autorun=False` | the B3 evidence is captured through the debug seam |

No assertion was removed or relaxed; two were made stricter.

## 5. Pre-existing flaky test (out of scope)

`tests/test_demo_composition.py::TestReset` asserts that the `id()` values
collected before and after `reset()` are disjoint. `id()` is a memory address and
CPython may reuse addresses once the old objects become unreachable, so the
assertion is not guaranteed. It failed once in the B4 regression subset run and
passed on rerun (164/164); the full suite was green.

* Disclosed in DDAY-B3 for `test_reset_creates_fresh_configs`.
* Observed in DDAY-B4 for `test_reset_creates_fresh_runtimes`.
* Root cause demonstrated deterministically in
  [`flaky_reset_disclosure.py`](flaky_reset_disclosure.py) /
  [`flaky-reset-disclosure.txt`](flaky-reset-disclosure.txt).

Issue #105 §13 places unrelated flaky-test cleanup outside B4, so it is disclosed
rather than fixed.
