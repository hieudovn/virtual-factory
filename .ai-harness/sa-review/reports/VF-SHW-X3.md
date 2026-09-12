# VF-SHW-X3 - Physical Bounds + Deep Scope A Two-PI Runtime

- **Issue**: https://github.com/hieudovn/virtual-factory/issues/98 (design freeze: Issue #97 + SA
  clarification `5645547152`; SA continuation comment on #98, 2026-09-12)
- **Branch**: `feature/vf-shw-x3`
- **Base**: `92fbabe7b0023785f86058c6d9d6fce3f9c5c861` (accepted X2-C03 head, PR #96) - branched from this
  exact commit, never from `main`
- **Gate type**: IMPLEMENTATION (no new topology, no second simulation engine, no merge)

## 0. Head and verification pin

| | |
|---|---|
| Implementation commit (all source, config, tests, contract, manifest, CURRENT) | `e3c2846d0a40d786dad8b398039f4eb6d92897a6` |
| Evidence/acceptance commit (evidence artefacts + report + the `x3.*` rules; no source change) | `c105ec8b143b9abff04a1bc46ee7d6e1e5b89eb0` |
| Docs/status pin commit(s) (markdown only, code-identical) | the `feature/vf-shw-x3` branch head; the exact reviewed SHA is the PR #99 head reported to the SA |
| Pull request | #99 (`feature/vf-shw-x3` → `main`, base `main`, not merged) |

Machine-derived verification **at the implementation head**, with a clean tree:

```
canonical baseline : overall PASS, 46 groups, failed_groups []
  x3_whole_plant_runtime : PASS  (64 passed)
  x2_whole_plant_runtime : PASS  (85 passed)
  full_suite             : PASS  (2864 passed)
  checks_changed_files   : PASS  (FILE VALIDATION PASSED (31 file(s)))
  checks_preflight       : PASS  (PRECHECK PASSED)
focused                : tests/test_vnext_x3_*.py 64 passed (23/16/13/12)
CI                     : VF-DM CI run 34701098691 = SUCCESS at that head
```

The commits after it add evidence artefacts, the machine-checkable acceptance block and documentation only —
**no source, config or test file is touched after the baseline run**, so the reviewed code content is exactly
the implementation commit. The canonical baseline is re-run on the final branch head (that run is the one
reported in the PR comment for #99), and the contract's acceptance criteria are verified by
`.ai-harness/scripts/evaluate_acceptance.py` (7/7 PASS) rather than by this prose.

## 1. Execution provenance (SA section 1)

The X3 profile/model/control/budget modules and the bounded `whole_plant.py` hooks were authored **before**
this task's local contract and preflight existed (the SA continuation comment authorizes resuming that
checkpoint). The contract `.ai-harness/tasks/VF-SHW-X3.json` therefore carries an explicit
`execution_ordering_disclosure`: the preflight recorded here is a **post-edit** gate check, not a passed
pre-implementation preflight. Nothing is backdated. The carried checkpoint was committed as
`M6-SHW-X3: checkpoint of the authorized X3 work carried from 92fbabe` so the harness could gate a clean
tree, and preflight then PASSED on that clean tree.

## 2. What X3 materializes (D1-D9)

| D | Requirement | Implementation |
|---|---|---|
| D1 | 16 admitted scopes, exactly two C2 loops, C1 arbitration, deferred loops unavailable | `x3_whole_plant.py` (16 participants), `x3_controls.py` (2 PI + 9 C1 + explicit `arbitration` reason), `shwtp_x3_profile_v1.json.deferred_loops` |
| D2 | deterministic global 1-second windows, one attempt identity, no same-window feed-through | `tick_s = 1.0`, session still bound to the active attempt context, `explicit_lagged` commits |
| D3 | profile validation + invalid-state rejection before stepping | `x3_profile.py`, `WholePlantX3Runtime._reject_invalid_state` |
| D4 | conservative pre-transfer allocation, reservations are capacity tokens | `physical_budget.py` (source water, receiver headroom/conduit, edge + trunk + element throughput, bounded queue) |
| D5 | the PIs drive REAL actuators through the declared elements | valve = `vf-shw-edge-t105-t106` throughput; pump feasibility limits the `t108-dist` request |
| D6 | pump head/power feasibility, OFF = zero, energy with units, unmodelled energy unavailable | `PumpModel`, `X3EnergyLedger`, `energy.unavailable` |
| D7 | PI sign/anti-windup/bumpless/manual/interlock/arbitration | `PIController` (conditional integration + back-calculation + external-override integral hold) |
| D8 | closed independent water ledger, no created water, acceptance numbers | full-run identity from tick zero (section 3) |
| D9 | deferred items unavailable, never silently claimed | pressure/RAW/T100/chlorine explicitly listed as deferred; energy gaps declared |

## 3. Conservation (SA section 2): the interval balance is only a supplement

The authoritative identity is evaluated **from tick zero**:

```
R(t) = [storage_flow_delta(t) + created_water(t) + in_transit(t)]
       - cumulative_in + cumulative_out - declared_physical_losses
```

- `storage_flow_delta` is derived from the flows each participant actually **integrated** (plus explicit
  overflow / created water), not from the float state variable, so the identity is not polluted by a
  state/flow bookkeeping difference.
- `in_transit` is the pending-slug inventory of the current tick; the pass-through conduits start **empty**,
  so no initial inventory is inferred from a later residual.
- `created_water` (`shortfall_m3`) is always a physical failure beyond the 1e-9 rounding tolerance and is
  **never** used as a reconciliation term.
- The storage **integration gap** (`state delta - flow delta - created + overflow`) is an independent
  physical claim: a duplicated/missing initialisation stock, or a hidden clamp, fails even when the
  flow-based residual still closes. `physical_valid` = full-run residual **and** integration gap **and**
  created water **and** the loss audit.
- `mark_balance_baseline()` / `window_residual_m3` remain available as a **supplement only**
  (`full_run_authoritative = true`); `08-verdict`/`02-water-identity` show a mutation injected *after* a
  marked baseline still failing the physical claim.

Measured (evidence `02`): 2400 ticks, **0 invalid ticks**, worst residual **2.0e-12 m³** (tick 432),
created water **0.0 m³**, integration gap **≤5e-12 m³**.

Two real defects were found and fixed by this work (they were *not* visible in the accepted X2 evidence):

1. **A pass-through conduit could destroy water.** The allocation capped a conduit's *emission* by its
   *new* inbound water, so a header that still held a parcel from the previous tick lost the difference
   (measured: the DIST discharge collapsed 28.7 → 2.9 m³/h at tick 65 and the plant residual jumped
   -7.1e-3 m³). The emission is now bounded by the conduit's declared element capacity and by the shared
   reservation taken at its **entry**, never by the newly received water.
2. **The distribution loss was mis-converted.** `0.0006 bar per (m3/h)^2` must convert to
   `0.0006 * 1e5 * 3600^2 / (rho*g) = 79266.06 s^2/m^5`; the checkpoint value `7.776e8` pinned the DIST
   pump at 0.66 m³/h. The conversion is now proven by dimensional arithmetic in the test
   (`test_dimensional_conversion_of_the_distribution_loss`) and in evidence `05`.

## 4. Reservations (SA section 3)

- **Resource identity/units**: an edge/trunk/element reservation is a **flow capacity** token in m³/s,
  published to the processors in m³/h (`budget_m3h_by_scope_port`); a receiver reservation is a **volume
  headroom** expressed as an equivalent one-tick rate. A reservation is never water, never a source/sink.
- **Acquire/release**: a conduit's capacity components (each edge rating and each control element's
  declared throughput) are reserved **once**, when water **enters** the conduit, and released by the
  forward emission on the next tick. A series hop is **never charged twice** (proved numerically: the same
  parcel charges `t102-t103` and `t103-t104` equally); parallel branches from the **same header** share the
  trunk within one tick (`shared_trunk` limiting factor, the trunk fully saturated).
- **Queue bound**: `queue.max_queued_volume_m3` is enforced (exceeding it raises `X3BudgetError`).
- **Cancellation/trip**: a trip or a stop removes the request, so the reservation is released on the
  following tick - measured on the live allocation (every hop returns to its full component capacity once
  no parcel moves), with no hidden water loss and no deadlock. In-flight (queued) water is physical
  inventory: it survives a stop/reset without loss or duplication.
- **Downstream bottleneck**: the entry is limited by the narrow hop, so a narrow serial pipe throttles the
  chain **without** the upstream pushing water in and losing it (runtime proof: the chain settles at the
  narrow rating, the ledger stays valid and created water is 0).
- **Full receiver**: a full terminal receiver blocks its series chain; the water stays in the upstream
  storage (explicitly asserted) instead of being forced in and dropped.

## 5. Control and energy

- **Exactly two active C2 loops**; pressure/RAW/T100/chlorine are declared deferred and never evaluated
  (verified against the `deferred_loops` declaration, not asserted by name).
- **Actual actuator response** (measured setpoint sweep in evidence `04`, `setpoint_sweep`): the flow SP
  0.006 → 0.009 m³/s moves the measured inlet flow **0.00600 → 0.00900 m³/s** and the valve
  **48.00 → 72.00 %**; the level SP 2.3 → 2.7 m moves the measured T108 level **2.2305 → 2.6269 m** with the
  pump **58.21 → 67.09 %**. Both level variants settle inside the documented 0.10 m off-nominal band and the
  water identity stays valid in every variant.
- **Feasible tracking at the nominal operating point**: flow error **0.0000 %** of SP and level error
  **≤0.03 m** (declared acceptance 5 % / 0.05 m, after the documented settling horizon of 1800 s which
  covers the cold-start chain fill: 60 s intake rest timer + 300 s T101 residence + 300 s T104 residence +
  the filter lag). An off-nominal level setpoint settles inside a documented 0.10 m band; the tuning is
  declared synthetic and is *not* claimed as site tuning.
- **Disturbance**: a tank started 0.3 m off-setpoint returns inside the declared band.
- **Unreachable SP**: the valve pins at 100 %, `saturated = true`, reason `output_saturated`, alarm
  `setpoint_unreachable_or_output_saturated`, the PV is reported **below** the SP (never "met"), and the
  integral is held (anti-windup). A reachable SP in the same profile recovers to within 5 %.
- **Interlock/backwash**: at the frozen DP threshold the C1 sequence takes the valve; the arbitration record
  carries `c1_backwash_closes_inlet` (the PI's own detail carries the generic `c1_arbitration` override flag
  with `external_override = true`) while the PI's own output stays visible as `pi_output_mv`, the measured
  flow is exactly 0 with `applied_mv = 0`, the integral is **held**
  (`external_c1_override_integral_held`) and on release the loop recovers to within 5 %
  (`valve_applied_by` returns to `pi_flow_output`).
- **AUTO/MANUAL**: manual → auto is bumpless (the requested output does not jump beyond the slew); the
  error signs are explicit and tested.
- **Slew**: the valve/pump ramp limits are enforced every tick.
- **Energy**: `P_elec = P_hyd/eta_total + no_load` with explicit units; the envelope walk (0-100 % speed
  in 10 % steps, all three pumps) keeps head ≥ the system curve and power ≤ motor rating; OFF is exactly
  zero flow and zero energy; unmodelled drives are declared unavailable, never fabricated.

## 6. Mutations (SA required evidence)

| Mutation | Expected | Result |
|---|---|---|
| state water injected after a marked baseline | fail | `physical_valid = false`, integration gap > tolerance |
| created water (shortfall) | fail | `created_water_within_rounding = false`, `physical_valid = false` |
| full receiver over-fill attempt | safe | volume ≤ capacity, created water 0, no chain loss |
| mis-converted / impossible head (DIST loss) | detected | achievable flow < plant demand |
| motor overload | bounded | power ≤ rating, flow limited by the curve |
| narrow serial pipe | safe | throughput bounded, ledger valid, created water 0 |

## 7. Canonical wiring

- `whole_plant_x3` is the **canonical default** (`SHWTP_DEFAULT_MODEL`) at 1-second windows with the two
  PI loops; `whole_plant_x2` (60 s, **zero** C2) and `g21_slice` (5 scopes) stay explicitly constructible
  through `model=` selectors and the compatibility factories, with their scenario ids preserved.
- Identity: the model, its participants and every transfer carry the **active attempt's** run id
  (`run_id_source = attempt_context`); reset preserves it, new attempt/replay re-issue it, an ambient
  `run_id=` kwarg fails closed.
- Trajectories: two independent sessions and a reset+replay are byte-identical on the monitor projection.
- The read-only `workspace_monitor` projection is model-agnostic (it uses the model's own `monitor_rows()`
  and the new declared `model_label`) and stays read-only (selecting does not advance the tick).
- Migrations: the canonical-default assertions in `test_vnext_x2_whole_plant_runtime.py`,
  `test_vnext_g23_registry.py`, `test_vnext_g24_workspace_ui.py` and `test_vnext_g25_acceptance.py` now
  expect the X3 canonical profile, while explicit X2/G21 coverage is retained (and extended).

## 8. Test and regression results

| Check | Result |
|---|---|
| `tests/test_vnext_x3_physical_bounds.py` | 23 passed |
| `tests/test_vnext_x3_reservations.py` | 16 passed |
| `tests/test_vnext_x3_two_pi_control.py` | 13 passed |
| `tests/test_vnext_x3_session_wiring.py` | 12 passed |
| Full suite | **2864 passed, 0 failed** (X2-C03 head: 2799) |
| Canonical baseline | 46/46 groups PASS (`x3_whole_plant_runtime` inserted before `full_suite`) |
| Acceptance rules X3-1..X3-7 | **7/7 PASS** (`evaluate_acceptance.py`, `phase=final`, rules `x3.*` in `08-verdict.json`) |

Evidence artefacts: `.ai-harness/sa-review/evidence/VF-SHW-X3/01..09`
(`generate_evidence.py` regenerates every number from the committed model; `09-summary.md` is the readable
digest). The generator also emits the machine-checkable `x3.*` acceptance block into `08-verdict.json` and
runs the harness acceptance evaluation over the task contract, writing the X3-1..X3-7 results back into the
same artefact — so the contract's acceptance criteria are verified by the repository's own evaluator, not by
prose.

## 9. Deviations, risks and residual uncertainty

- **Ordering deviation** (section 1) - disclosed, not hidden.
- **Synthetic tuning**: the level loop is deliberately not tuned to an unverified site; the nominal
  acceptance bands hold, an off-nominal level setpoint settles inside a documented 0.10 m band.
- **Pipeline holding**: the pass-through conduits hold exactly one tick of committed water; this is
  explicit inventory in the report and is *not* an identity term (the pending-slug transit already carries
  it), so a reader cannot mistake it for a compensation term.
- **`h0 = 35 m` on the T108 transfer pump** is a synthetic choice (chosen so the shut-off head exceeds the
  8 m static lift at the bias speed, which is what gives the level loop authority in both directions); it
  is validated over the operating envelope, not only at the PI equilibrium.
- No change to any frozen X1 config, to the accepted X2 behaviour, to runcontrol/composition/ASSY/PIM, to
  the process graph or to any scope authority. No merge. No X4/X5.
