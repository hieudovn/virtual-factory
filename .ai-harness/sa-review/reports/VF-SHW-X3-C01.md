# VF-SHW-X3-C01 - Correction of the two blocking SA findings

- **Issue**: #98 (SA review comment `5646905334`), correction authorized inside the same issue / **PR #99**
- **Branch**: `feature/vf-shw-x3` (continued, no competing implementation gate)
- **Technical base (reviewed head)**: `c3f4b231bb83bbd48f2c8a66f7dda13efd7ef290`
- **Correction contract**: `.ai-harness/tasks/VF-SHW-X3-C01.json` (created BEFORE the edits; harness
  preflight `PRECHECK PASSED` on the clean tree at contract commit `579f0c2`)
- **Gate type**: CORRECTION - no new engine, topology, loop or fidelity scope; frozen X1/X2 behaviour,
  runcontrol, composition, PIM and ASSY remain protected

The SA reviewed `c3f4b23`, reproduced both defects with isolated runs of the exact PI/PumpModel source and
rejected the gate. Both findings are accepted as valid; this correction fixes them and makes the defects
unable to stay green.

## 1. C01-1 - the final physical actuator is now the controller's tracked actuator

**Defect (SA reproduction).** `PIController` returned `applied_mv = 0` on a forced stop / interlock without
writing the value into its own applied-MV tracking; C1 arbitration stamped the returned status
(`_with_actual_actuator`) without tracking the value either, and `external_override` was derived from the
PREVIOUS tick's ownership. So after `90 % -> stop 0 %`, the next unforced scan re-applied the pre-stop 90 %:
a **90 pp step in one second** against the declared 10 pp/s valve limit, and a stale pre-stop command was
returned after a C1 override. The existing backwash test waited 900 ticks and never looked at the release
discontinuity.

**Fix (in `x3_controls.py`).**

- `X3ControlLayer.evaluate` decides protective ownership **before** the PI scans (trip > C1
  backwash/permissive > interlock > PI, exactly the accepted priority) and passes the owner and its value
  into the scan.
- `PIController._protective_status(...)` writes the actuator **exactly once**: the value the plant really
  receives is committed to `_applied_mv` (the slew base and the release anchor), the integral is held from
  the FIRST protected scan, and `protection` / `integral_held` / `committed_actual_mv` / `pi_output_mv` /
  `applied_by` are reported separately (requested-vs-applied provenance preserved).
- The first unprotected scan after a protective episode **preloads from that actual stopped value**
  (`released_from_<protection>_bumpless`) and then ramps under the normal slew limit, so ordinary
  reopening/re-starting obeys valve 10 pp/s and pump 5 pp/s; only the protective action itself bypasses
  the slew.
- `PIController.commit_actual(mv)` is called once per tick by the arbiter with the FINAL realized command:
  the controller tracks reality and the back-calculation is reconciled against that final command (the sum
  equals `Kb*(u_final - u_raw)*dt`), never against a pre-arbitration copy.
- New explicit arbitration labels: `f106_inlet_interlock_protective_stop`,
  `t108_pump_interlock_protective_stop` (the interlock paths of both loops are now visible instead of being
  reported as `pi_flow_output`).
- `PIController.set_setpoint(sp)` (validated against `sp_admissible`, fail closed) allows a feasible step and
  an unreachable -> reachable recovery to be proven **inside one ongoing attempt** with the controller state
  retained.

**Measured (evidence `11-actuator-tracking.json`, generator-derived, head of this correction).**

| Check | Result |
|---|---|
| SA counterexample: normal command | 90.00 % |
| forced stop applied / **tracked** value | 0.00 % / **0.00 %** |
| release step vs valve limit (10 pp/s) | **0.000 pp** (within the limit) |
| protective epilogues (trip, interlock, C1 override x flow, level = 6) | all: protection recognised, tracked value 0.00 %, integral held on the first protected scan AND with a changed PV, every ramp step within the slew, actuator taken back |
| release step of the 4 trip/interlock epilogues | **0.00 pp** (preloaded from the actual stopped value) |
| release step of the 2 C1-override epilogues | **10.0 pp** (flow loop / valve, exactly at the 10 pp/s limit) and **5.0 pp** (level loop / pump, exactly at the 5 pp/s limit) - a bounded ramp at the slew limit, NOT a 0 pp release (wording corrected per SA finding C02-3) |
| runtime continuity over 5400 ticks (whole backwash episode) | tracked == realized on every tick; **0** tracking/slew violations; owners: `pi_flow_output` 5010 ticks, `c1_backwash_closes_inlet` 390 ticks, pump `pi_level_output` 5400 ticks |
| one ongoing attempt: 0.006 -> 0.0125 (unreachable) -> 0.008 | feasible step tracked (err 0.0 at tick 2400), unreachable saturates with `output_saturated` (measured 0.0100 < 0.0125, tick 4200), recovery inside 5 % (err 0.0 at tick 6000) with the controller state retained |
| live setpoint projection | `control_rows()` now reports the setpoint in force (from the PI status), so a runtime step is visible in every projection |

**Design decision recorded (C1 override release).** A forced stop / interlock pins the output at its protective value, so the
release preloads the integral from that actual stopped value (bumpless and slew limited). A C1 override instead only
borrowed the actuator while the integral was HELD at the pre-override working point: on release the request resumes there
and the SLEW governs the applied value, so the plant is restored in ~7 s with the valve stepping 0 -> 10 pp in the first
second (measured: release at tick 3746 with the valve at 10.0 pp, flow recovered to the SP by tick 5700, level error
0.0366 m inside the declared 0.05 m band). Preloading the integral in this case re-integrated from the closed position and
degraded the level band (`final_level_error_m` 0.0658 m > 0.05 m), which would have been a real control regression.

## 2. C01-2 - energy is integrated from the ACHIEVED pumped throughput

**Defect (SA reproduction).** `_requested_edge_flows` built `_pump_points` from
`operating_point(speed, q_rated)` BEFORE allocation and `_update_energy` integrated those same points, so the
DIST pump integrated its achievable envelope point (48.096 m3/h, 5285.377 W) for every second regardless of
startup inventory, upstream delivery or downstream throttling: a capacity statement reported as an actual
operating point.

**Fix.**

- `physical_budget.PumpModel.operating_point` is now documented and used as the **CAPACITY** statement
  (allocation + declared envelope) only.
- New `PumpModel.realized_point(speed_pct, actual_flow_m3_s)` evaluates the operating point of the water that
  was ACTUALLY moved, against the same frozen curve/system laws, and reports head and motor feasibility on
  that point.
- `PumpOperatingPoint` gained `energized`; `off` now means "not energized" (exactly zero flow and zero
  energy) and `idle` means "energized but no water moved". The declared rule is written into the evidence:
  an OFF pump integrates exactly zero; an energized no-flow pump integrates only `no_load_w` with **no**
  useful hydraulic power; a pumped point integrates `P_hyd(Hreq)/eta + no_load_w` where the useful power uses
  the head actually delivered to the water and the excess available head stays a recorded
  `throttle_head_m` dissipation.
- `x3_whole_plant.py` reads the committed physical transfer of each pump's **discharge binding**
  (`PUMP_DISCHARGE_BINDINGS`) after the tick executes, so the realized flow already reflects a limited
  startup inventory, an empty source, a full receiver or a narrowed downstream capacity. `_update_energy`
  integrates the realized points and exports a per-tick row (actual Q, speed, capacity Q, H, Hreq, throttle
  head, P_hyd, P_elec, energy delta, energized/idle/off, reason, feasibility) through
  `energy_trace()`/`energy_report()`.
- `energy_report()` states the basis (`realized_actual_pumped_throughput`), the idle-loss rule, the realized
  feasibility counters, the idle vs pumped energy split and the allocation capacity points separately.
- No X3 pressure/head projection exists beyond the energy report (the DIST pressure PI stays explicitly
  deferred), and every head value that is published now comes from the achieved point.

**Measured (evidence `10-energy-from-actual-flow.json`).**

| Check | Result |
|---|---|
| total energy at the corrected head | **4.207016 MJ** = idle **0.102650 MJ** + pumped **4.104366 MJ** |
| per pump | DIST 1.895614 MJ, raw intake 1.150922 MJ, T108 transfer 1.160480 MJ |
| ledger vs independent recomputation from the per-tick actual rows | **matches per pump** (<= 1e-6 J) |
| capacity-flow substitution | **detected**: it would differ by 1.763154 MJ (DIST), 0.273185 MJ (raw) and 0.001721 MJ (T108) |
| realized feasibility | 1200 ticks observed, **0 infeasible**, all realized points feasible |
| OFF/idle contract | OFF rows integrate exactly 0 J; idle rows have 0 hydraulic power and exactly the declared `no_load_w` |
| scenario matrix | startup 0.166018 MJ, zero available water (downstream chain pumped **0.0 m3**) 0.025259 MJ, full receiver 0.265514 MJ, narrowed downstream 1.433434 MJ - all four keep the water identity valid and every realized point feasible |
| worked examples (last tick) | DIST 7.057 m3/h at 80 % (H 26.093 m, Hreq 0.305 m, throttle 25.788 m, 408.37 W); raw intake 33.750 m3/h at 75 % (461 W hydraulic / 1009 W electric); T108 transfer energized at 46.46 % with **no lift head** -> 0 m3/h, 0 W hydraulic, 250 W declared idle (`energized_zero_flow_no_lift_head`) |
| per-tick export | `energy_trace()` exposes commanded speed, achieved Q (m3/s and m3/h), capacity Q, H, Hreq, throttle head, P_hyd, P_elec, energy delta, energized/idle/off, reason and feasibility for every tick; the artefact carries a 4-tick sample |

## 3. Mandatory regression repairs (SA section "Mandatory regression/evidence repairs")

1. **Command continuity at every protection entry and release, both loops** -
   `tests/test_vnext_x3_two_pi_control.py::TestC01ActuatorTrackingAndReleaseSlew` (6 parametrised epilogues +
   MANUAL/changed-PV + runtime continuity for the valve and the pump + the LAYER trip/release test) asserts
   the tracked value, the first-tick integral hold and the slew-limited release.
2. **Steps and recovery inside one ongoing attempt** -
   `TestC01SetpointStepsInsideOneAttempt::test_feasible_step_unreachable_then_recovery_on_one_attempt`
   uses `set_setpoint` on ONE model with fresh window ids and retains the controller state.
3. **Per-tick actual export + independent recomputation + capacity mutation** -
   `tests/test_vnext_x3_physical_bounds.py::TestC01EnergyFromAchievedFlow` (6 tests) plus evidence section
   `10`; the capacity-Q substitution is rejected.
4. **Regenerated evidence and acceptance rules** - evidence sections `10` and `11` are new, `04` gained the
   tracking/recovery facts, and the acceptance block now carries `x3c01.actuator_tracking` and
   `x3c01.energy_from_actual_flow` next to the re-asserted `x3.*` regression rules, so neither defect can
   remain green.

## 4. Tests and gate

| Check (measured at the correction head) | Result |
|---|---|
| `tests/test_vnext_x3_physical_bounds.py` | **30 passed** (was 23; +7 realized-energy tests) |
| `tests/test_vnext_x3_two_pi_control.py` | **26 passed** (was 13; +13 tracking/continuity/step tests) |
| `tests/test_vnext_x3_reservations.py` | 16 passed (unchanged) |
| `tests/test_vnext_x3_session_wiring.py` | 12 passed (unchanged) |
| `tests/test_vnext_x2_whole_plant_runtime.py` | 85 passed (unchanged; no migration needed) |
| Focused X3 total | **84 passed, 0 failed** |
| Evidence `01..11` | all nine section verdicts PASS, overall `SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED` |
| Contract acceptance | **9/9 PASS** (`X3C01-1`, `X3C01-2` + the `X3-1..X3-7` regression re-assertions, evaluated by the harness on `08-verdict.json`) |
| Water identity (regression) | 0 invalid ticks, worst residual 2e-12 m3, created water 0.0 m3, storage integration gap -5e-12 m3 |
| Canonical baseline (46 groups) at the contract-correction head `4426b74` | **overall PASS, 46/46 groups, `failed_groups = []`**: `x3_whole_plant_runtime` 84 passed (113.75 s), `x2_whole_plant_runtime` 85, `x1_whole_plant_contracts` 46, `full_suite` **2884 passed** (171.00 s), `checks_compile` / `checks_static_lint_type` PASS, `checks_changed_files` `FILE VALIDATION PASSED (17 file(s))`, `checks_preflight` `PRECHECK PASSED` |

The first baseline run at the code head `109e3f2` failed one harness group and is disclosed in section 5; the
re-run above is the gate result for the corrected contract. The final commit of this correction only pins these
machine-derived numbers into markdown (this report and `CURRENT.md`) and changes no source, test, config or
evidence file, so the same canonical 46-group baseline is re-run at that pinned head; its exact SHA and result are
recorded in the C01 verification comment on PR #99.

## 5. Harness contract correction disclosed to the SA (not a scope change)

**The first full baseline run at head `109e3f2` FAILED, and it is reported as a FAILED run.**
Machine-derived result: `overall = FAIL`, `failed_groups = ["checks_changed_files"]`, 45 of 46 groups PASS -
including `x3_whole_plant_runtime`, `x2_whole_plant_runtime`, `x1_whole_plant_contracts`, `full_suite`
(2884 passed) and `checks_preflight` (`PRECHECK PASSED`) - with exactly one group,
`checks_changed_files`, FAILED:

```
FILE VALIDATION FAILED:
  - Forbidden path changed: tests/test_vnext_x3_physical_bounds.py (matches 'tests/')
  - Forbidden path changed: tests/test_vnext_x3_two_pi_control.py (matches 'tests/')
```

The raw run is `.ai-harness/traces/vnext_baseline_x3c01_h1.json` (log
`.ai-harness/traces/vnext_baseline_x3c01_h1.log`); because `.ai-harness/traces/` is git-ignored, the run is
preserved in the committed artefact `evidence/VF-SHW-X3/12-baseline-failed-run.json` (per-group status,
exit codes, the failing group verbatim and the critical-group verdicts) so the failure stays verifiable.

The cause is a defect in this correction's own contract, not in the correction: `forbidden_paths` carried the
whole-directory entry `tests/` while `allowed_paths` explicitly allowlisted the four existing X3 test modules -
including the two `tests/test_vnext_x3_two_pi_control.py` / `tests/test_vnext_x3_physical_bounds.py` modules that
the SA's mandatory repairs 1 and 3 require editing. `.ai-harness/scripts/verify_changed_files.py` evaluates the
forbidden list unconditionally and independently of the allowlist, so the contract failed on files it explicitly
permitted. The accepted X3 contract records the opposite rule verbatim ("tests/ is deliberately not a
whole-directory forbidden entry").

**Correction applied:** the single entry `"tests/"` was removed from `forbidden_paths` (recorded in the new
`allowlist_correction` block of `.ai-harness/tasks/VF-SHW-X3-C01.json`). **No runtime or test change is part of
that commit**; it changes four files - the task contract, this report (section 5), `.ai-harness/sa-review/CURRENT.md`
and the new evidence artefact `evidence/VF-SHW-X3/12-baseline-failed-run.json` - and every other forbidden entry
(frozen X1 configs, `contracts.py`, `x2_controls.py`, `whole_plant.py`, `session.py`, `workspace_monitor.py`,
`runcontrol/`, `composition/`, `assembly/`, `pim/`, `core/`, `docs/`, `deploy/`, `examples/`, `simulators/`,
`main`) is untouched. (The earlier wording of this section claimed that no evidence or report file is touched by
the amendment commit; that was factually wrong and is corrected here per SA finding C02-3.)

**Independent proof that this is not a scope widening:** recomputing the changed-file verdict against the
ORIGINAL contract gives 16 changed paths, `outside_allowlist = []`, and the two files above as the ONLY forbidden
hits - both caused solely by the blanket prefix. The allowlist is exhaustive, so the permitted set after the
amendment is identical to the original intent; re-running the verifier reports
`FILE VALIDATION PASSED (16 file(s))`.

Because the amendment changes the tree, the full 46-group baseline is re-run at the new head; only that re-run is
reported as the gate result for the corrected head. The SA retains the decision on accepting this contract
correction.
