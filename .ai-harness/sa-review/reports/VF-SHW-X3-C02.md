# VF-SHW-X3-C02 — correction of the SA energy finding (C02-1) and of the independent-oracle gap (C02-2)

Correction gate inside **Issue #98 / PR #99**, authorized by the SA review comment `5649199324` at the reviewed head
`1d8de908648a1718819247772b5ae58722e87260` (branch `feature/vf-shw-x3`, no competing implementation gate).
Correction contract `.ai-harness/tasks/VF-SHW-X3-C02.json` was created **before** the C02 edits and the harness
preflight PASSED (`PRECHECK PASSED`) on the clean reviewed head.

**SA decisions carried into this correction:** the C01-1 control correction is accepted (counterexample resolved, C1
release adjustment accepted, blanket `tests/` forbidden entry removal accepted). **The energy result 4.207016 MJ was
NOT accepted** because the realized point applied `Hreq` instead of the frozen D6 pump head, and because the
"independent" recomputation called the production helper and therefore repeated the same wrong formula.

## 1. C02-1 — the realized point now applies the frozen D6 pump law (throttle dissipation included)

`physical_budget.PumpModel.realized_point` evaluates the realized flow against the SAME frozen head/power equations
as the capacity statement: `P_pump = rho*g*Q_actual*H(n, Q_actual)`, `P_useful = rho*g*Q_actual*Hreq`,
`P_throttle = P_pump - P_useful` and `P_elec = P_pump/eta_total + no_load_w`, so the energy that is later
dissipated through the throttle is part of the electricity instead of being reported only as a head. The three
powers are exported separately, the identity `P_pump = P_useful + P_throttle` is enforced in the realized
feasibility verdict on every positive flow (a violation is reported `power_split_inconsistent` and can never reach
a success verdict), the declared OFF/idle simplification is unchanged, and **no pump curve parameter was touched**.

**The SA's exact-source counterexample is reproduced (evidence `10-energy-from-actual-flow.json`).** Frozen DIST
parameters at 80 %, `Q = 0.008 m3/s`:

| quantity | SA expectation | this head |
|---|---|---|
| head `H(n,Q)` | 26.0928 m | **26.092800 m** (`matches_sa_numbers = true`) |
| requirement `Hreq` | 5.07302784 m | **5.07302784 m** |
| pump hydraulic `rho*g*Q*H` | 2047.762944 W | **2047.762944 W** |
| useful system power `rho*g*Q*Hreq` | 398.131224883 W | **398.131224883 W** |
| throttle dissipation | 1649.631719117 W | **1649.631719117 W** |
| frozen electric law | 3325.375634286 W | **3325.375634286 W** |

The previously reported value for the same point was 968.758892690 W (the rejected law).

**Full run at this head (1200 ticks, evidence `10`).**

| Check | Result |
|---|---|
| total electricity | **8.805505 MJ** = idle **0.102650 MJ** + pumped **8.702855 MJ** |
| per pump | DIST **4.139123 MJ**, raw intake **3.063771 MJ**, T108 transfer **1.602611 MJ** |
| pump hydraulic energy | **5.242170 MJ** = useful **2.118870 MJ** + throttle **3.123300 MJ** (identity residual `max_power_balance_error_w = 0.0`) |
| throttle share charged | `total_electric_j > useful_hydraulic_j` holds and `throttle_dissipated_j > 0` — the dissipated share is real |
| realized feasibility | 1200 ticks observed, **0 infeasible**, `all_realized_points_feasible = true` |
| per-tick export | commanded speed, achieved Q (m3/s, m3/h), capacity Q, H, Hreq, throttle head, **P_pump, P_useful, P_throttle**, power-balance error, P_elec, energy delta, off/idle/energized, feasibility and reason |
| scenarios | startup **0.378608 MJ**, zero available water **0.026935 MJ** (downstream chain **0.0 m3**), full receiver **0.630960 MJ**, narrowed downstream **3.005768 MJ** — all water-valid, all realized points feasible |

## 2. C02-2 — the energy oracle no longer reuses the implementation

The recomputation was rebuilt as a genuinely independent oracle in **two** places (the X3 test module and the
evidence generator), each with its own copy of the physics:

* **inputs:** only the committed PHYSICAL pump discharge records published by the runtime
  (`pump_discharge_records()` → tick, pump, binding, committed discharge m3, tick duration, commanded speed).
  Water and command only - the record carries **no power, efficiency or energy statement**;
* **parameters:** read from `configs/vnext/shwtp/shwtp_x3_profile_v1.json` by the oracle itself (constants + pumps):
  `h0_m`, `k_s2_m5`, `h_static_m`, `r_s2_m5`, `eta_total`, `no_load_w`, `rho`, `g`;
* **no production call:** the oracle never calls `realized_point`, `power_split_w`, `hydraulic_power_w`,
  `electric_power_w`, `energy_step_j`, never touches `pump_models`, `energy_trace`, `energy_report` or
  `energy_components_j`, and never consumes an exported power field. A source-token scan asserts this
  (`oracle.independent_of_production_helpers = true`, with the checked tokens listed as
  `oracle.forbidden_tokens_checked`), and a test applies the same scan to the test oracle.

**Result:** the oracle reproduces the ledger **per pump** exactly (DIST 4139123.001819 J, raw 3063771.102483 J, T108
1602610.981859 J; `independent_recomputation_matches = true`, per-pump agreement ≤ 1e-6 J), and **both** substitution
mutations fail acceptance:

| mutation (evaluated with the same independent parameter path) | per-pump difference vs the ledger | detected |
|---|---|---|
| capacity/rated flow substituted for the achieved flow | DIST **2.203330 MJ**, raw **0.911438 MJ**, T108 **2592.48 J** | yes |
| `Hreq` substituted for the frozen pump head `H(n,Q)` (the C01-2 error) | DIST **2.243509 MJ**, raw **1.912850 MJ**, T108 **0.442131 MJ** | yes |

The Hreq-law mutation integrates exactly **4.207016 MJ** - the figure the SA rejected - against the accepted
**8.805505 MJ** on the frozen law, so the defect cannot reappear unnoticed.

## 3. C02-3 — factual reporting corrections

1. **The amendment commit changed four files, not one.** `109e3f2 -> 4426b74` changes the task contract, the C01
   report, `.ai-harness/sa-review/CURRENT.md` and the new evidence artefact
   `evidence/VF-SHW-X3/12-baseline-failed-run.json`. The previous claim that no evidence/report file was touched is
   **false and is corrected** in the C01 report (section 5) and in `CURRENT.md`. **No runtime or test change** is
   part of that commit.
2. **The protective releases are not all 0 pp.** Of the six epilogues, the four **trip/interlock** releases step
   **0.00 pp** (preloaded from the actual stopped value) while the two **C1-override** releases ramp at the declared
   limits: **10.0 pp** (flow loop / valve, 10 pp/s) and **5.0 pp** (level loop / pump, 5 pp/s). Both are inside the
   slew but they are ramps, not zero steps; the blanket wording is corrected in the C01 report and `CURRENT.md`.
3. **PR #99's description** presented the rejected `c3f4b23` numbers (11.821 MJ, 2864 tests) as current; they are now
   marked historical/superseded and point at this correction.

## 4. Regression retained

* **C01-1 control:** unchanged (the control layer is not in this contract's allowlist and `x3_controls.py` is
  explicitly forbidden); the actuator-tracking evidence `11` is regenerated unchanged and the counterexample,
  epilogues (with the corrected release-step wording), the 5400-tick runtime continuity scan and the one-attempt
  step/saturation/recovery assertions stay green.
* **C01-2 semantics:** energy is still integrated only from the achieved pumped throughput (the capacity point stays
  an allocation/envelope statement) with the declared idle-loss rule; the previously reported 4.207016 MJ is now
  identified as the Hreq-only law and therefore superseded.
* **Water identity:** unchanged - full-run closure from tick zero, 0 invalid ticks, created water 0.0 m3; the four
  energy scenarios stay water-valid.
* **Tests at this head:** `tests/test_vnext_x3_physical_bounds.py` 35, `tests/test_vnext_x3_two_pi_control.py` 26,
  `tests/test_vnext_x3_reservations.py` 16, `tests/test_vnext_x3_session_wiring.py` 12 → **89 passed, 0 failed**.
* **Evidence:** sections `01..11` all PASS with the new verdict `ENERGY_FROM_ACHIEVED_FLOW_ON_THE_FROZEN_PUMP_LAW`,
  overall `SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED`, and the harness accepts **11/11** criteria of the C02
  contract (X3C02-1, X3C02-2 + the X3C01-1/X3C01-2 and X3-1..X3-7 regression re-assertions) with `failed: []`.

## 5. Gate

The canonical 46-group baseline (including `full_suite`) and VF-DM CI are run at the exact pushed head of this
correction; their machine-derived numbers are recorded in the C02 verification comment on PR #99.

**STOP** — X4/X5 must NOT begin; no merge and no Issue #98 closure without the SA's explicit authorization for the
exact PR head SHA.
