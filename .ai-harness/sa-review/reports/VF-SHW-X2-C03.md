# VF-SHW-X2-C03 — Physical Conservation vs Accounting Reconciliation (correction)

**Machine-derived status: `READY FOR SA REVIEW`** · **Verdict: `INVENTED_WATER_FAILS_PHYSICAL_VALIDITY`**

| Field | Value |
| --- | --- |
| Gate | VF-SHW-X2-C03 (narrow completion of C02-3; Issue #94 SA comment `5645448466`) |
| Gate type | **CORRECTION** — oracle + bounded-discharge + loss-audit correction; no config/contract/architecture/topology/control expansion, no C2/T107/UI/PIM/ASSY, no merge |
| Branch / PR | `feature/vf-shw-x2-c01` · PR **#96** (Issue #94 stays OPEN) |
| Required base | `c3e7893adeead308cce72ac2a76ba24b497d6bdb` (`c3e7893`, C02 head) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`, untouched) |
| Task contract | `.ai-harness/tasks/VF-SHW-X2-C03.json` |
| Harness preflight | PASSED |
| `x2_whole_plant_runtime` group | **84 passed** (was 75; +9 C03 tests) |
| Full suite | **2799 passed** (was 2790) |
| Evidence verdicts | 01…11 unchanged + **`INVENTED_WATER_FAILS_PHYSICAL_VALIDITY`** (new `12-physical-validity.json`) |

---

## 0. SA finding addressed

> `ScopeParticipant._bound_volume` records negative-volume clamping as `_shortfall_m3` … `balance_report` subtracts that amount from `residual` and defines `conserved` solely as `abs(residual)<=tolerance`. SA counterexample: initial water 0; input 0; output 1 m³ → `conserved true`. *A diagnostic correction term must not certify invented water as physically conserved.*

Reproduced at this head before the fix (exact methods): `_bound_volume(-1, 10)` → volume 0, `shortfall 1`, report `residual 0.0`, **`conserved true`**. ✅ confirmed.

| Requirement | Status |
| --- | --- |
| 1. Created water stays visible but can never certify conservation; accounting reconciliation clearly separated | **CLOSED** (§1) |
| 2. Real discharges bounded by available water; no unavailable water emitted and repaired by a clamp | **CLOSED** (§2) |
| 3. Counterexample test + dry/near-empty filter forced backwash; created water within a justified rounding tolerance on every accepted scenario | **CLOSED** (§3) |
| 4. LINE2 `process_loss` proven = declared law + modelled capacity spill; one negative mutation check | **CLOSED** (§4) |
| 5. Evidence verdicts must fail on physical invalidity (a reconciled residual alone cannot PASS) | **CLOSED** (§5) |
| 6. Re-run focused X2, baseline, full suite; regenerate evidence | **DONE** (§6) |

---

## 1. Physical conservation ≠ accounting reconciliation

`balance_report()["plant_water"]` now reports two **different claims**:

| Field | Meaning |
| --- | --- |
| `conserved` / `physical_valid` | the balance closes **without any compensation term**, created water is within the rounding tolerance and the process-loss audit holds |
| `accounting_reconciled` | the same balance **after subtracting the created-water diagnostic** — diagnosis only, explicitly labelled *"NOT a physical-conservation claim"* |
| `shortfall_m3` / `created_water_diagnostic_m3` | created water, read **live** from the scopes (a clamp performed outside the window loop is visible) |
| `created_water_within_rounding` | `shortfall <= CREATED_WATER_TOLERANCE_M3` (1e-9, float rounding only) |
| `process_loss_declared_law_plus_spill` / `process_loss_audit_failures` | the LINE2 loss audit (§4) |

The residual is now
`(water_inside) − plant_in + plant_out + process_loss + overflow` — **the `− shortfall` term is gone**, so invented water breaks the physical claim.

**Counterexample (machine-derived, `12-physical-validity.json`)**

| Basis | Verdict |
| --- | --- |
| C02 oracle formula `abs(residual − created) <= tolerance` | **true** (this is the defect: it certified 1 m³ of invented water) |
| C03 oracle formula `abs(residual) <= tolerance AND created <= rounding` | **false** |
| live model check after a 1 m³ clamp | `created_water_within_rounding=false`, `physical_valid=false`, `conserved=false` |

---

## 2. Discharges are bounded by available water

New shared helper `ScopeParticipant._available_outflow_rate(dt_s, inflow_m3h)` = `held/dt + inflow`.

| Scope | Discharge | Before | After |
| --- | --- | --- | --- |
| T106 filter | backwash wash water (5 m³/h, 2.5 in SETTLE) | fixed flow → could exceed the filter's water → clamp → **created water** | `min(requested, available)` + alarm `wash_water_limited_by_available_volume` |
| T108 | transfer withdrawal | `min(pump_rate, max(0, held/dt))` (already bounded) | unchanged, now documented as the rule |
| T100 / T105 / T110 / T201 / T101 / T104 | withdrawal, sludge, return, processing, pass-through | already bounded by available water | verified by a new bounded-discharge proof test |

No invalid state is repaired by a clamp: the emitted flow is limited and the limitation is **alarmed**
(explicit diagnostics). The clamp remains only as a float-noise guard and its output is a diagnostic (§1).

---

## 3. Tests (requirement 3)

| Test | Proof |
| --- | --- |
| `test_invented_water_is_never_certified_as_conserved` | the SA counterexample: created water 1.0 m³ visible, `created_water_within_rounding=false`, `conserved=false`, `physical_valid=false`, residual not compensated |
| `test_accepted_scenarios_keep_created_water_within_rounding` | 7 accepted scenarios (default, stopped/zero inflow, backwash, dry-filter backwash, empty T108, tiny LINE2 capacity, overflowing T106): `shortfall <= 1e-9`, `physical_valid=true`, audit failures 0 |
| `test_dry_filter_forced_backwash_cannot_invent_water` | real zero-volume filter with a forced backwash through the **real window path** (`t106_dp_initial_kpa=85`, `t106_initial_volume_m3=0`): 6 backwash/settle windows, wash discharge bounded by held+inflow, `wash_water_limited_by_available_volume` raised, created water ≤ 1e-9, `physical_valid=true` |
| `test_accounting_reconciliation_never_certifies_physical_conservation` | a deliberate pre-C03 mutation (unbounded discharge) creates water: `accounting_reconciled=true` **while** `conserved=false` — the two claims are demonstrably separate |
| `test_withdrawals_are_bounded_by_available_water` | 3 extreme scenarios × 20 windows: every storage discharge ≤ held + delivered inflow, volumes never negative |
| `test_the_audit_finds_no_other_deleting_tank` | every storage scope: `shortfall < 1e-9` (was `>= 0`) |

---

## 4. LINE2 process loss = declared law + modelled spill

Declared law (frozen contract): `delivery = max(0, min(feed × (1 − loss_fraction), capacity))`.

New `audit_line2_process_loss(feed, delivered, loss_fraction, capacity)` returns the declared loss
(`feed × loss_fraction`), the capacity spill (`max(0, feed×(1−fraction) − capacity)`), the expected delivery
and the observed loss, plus the two checks `delivery_matches_declared_law` and
`loss_equals_declared_plus_spill`.

- The participant now computes its delivery **from the declared law** and records the step-time
  `step_feed_m3h`, `declared_loss_m3h`, `capacity_spill_m3h`, `observed_loss_m3h`, `process_loss_audit_ok`.
- The model ledger uses `declared_loss + capacity_spill` (not the raw difference), so an arbitrary dropped
  delivery can no longer be relabelled as process loss; audit failures are counted and invalidate
  `physical_valid`.
- Evidence proves: admissible case (100 → 99, 1 % loss) `valid=true`; **negative mutation** (100 → 50) `valid=false`
  with both checks false; capacity-spill case (100 → 10 with capacity 10) `valid=true`, spill 89, observed loss 90.
- Scenario proof: with `line2_capacity_m3h=1` the spill binds in 10 of 11 windows and
  `process_loss_declared_law_plus_spill` stays `true`.

---

## 5. Evidence verdicts propagate physical validity (requirement 5)

- `05-physical-oracles.json` now requires `physical_valid`, `created_water_within_rounding` and
  `process_loss_declared_law_plus_spill` — a reconciled residual alone can no longer yield
  `PHYSICAL_ORACLES_SATISFIED`.
- `10-water-ledger.json` requires physical validity on every scenario (and reports created water, physics vs
  accounting per scenario).
- New `12-physical-validity.json` → **`INVENTED_WATER_FAILS_PHYSICAL_VALIDITY`** (counterexample rejected,
  dry-filter backwash creates no water, bounded-discharge rule, declared-loss audit + negative mutation).

---

## 6. Regression and change surface

| Check | Result |
| --- | --- |
| Harness preflight | PASSED |
| `x2_whole_plant_runtime` | **84 passed** (75 → 84) |
| Full suite | **2799 passed** (2790 → 2799) |
| Evidence (12 artefacts) | all green, incl. the new C03 verdict |
| Canonical baseline | recorded at the pushed head (see the PR comment) |

Changed: `src/virtual_factory/shwtp/whole_plant.py`, `tests/test_vnext_x2_whole_plant_runtime.py`,
`.ai-harness/regression/vnext_baseline_manifest.json`,
`.ai-harness/sa-review/{CURRENT.md, reports/VF-SHW-X2-C03.md, evidence/VF-SHW-X2/generate_evidence.py}` and the
regenerated/new evidence artefacts, `.ai-harness/tasks/VF-SHW-X2-C03.json`.

**Untouched:** `configs/**`, `contracts.py`, `x2_controls.py`, `session.py`, `structural.py`, `connectivity.py`,
`expansion.py`, `runcontrol/**`, `composition/**`, `ui/**`, ASSY, PIM, `docs/`, `deploy/`, `examples/`,
`simulators/`.

---

**VF-SHW-X2-C03 — READY FOR SA REVIEW · `INVENTED_WATER_FAILS_PHYSICAL_VALIDITY`**

**STOP — X3/X4/X5 must not begin. Issue #94 stays OPEN. Merge requires explicit SA authorization for the exact PR head SHA.**
