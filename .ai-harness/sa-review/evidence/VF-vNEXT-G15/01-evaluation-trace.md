# VF-vNEXT-G15 — SH-WTP Federated Evaluation Trace & Diagnostics — Evidence

Gate: `VF-vNEXT-G15` · Deterministic evaluation/diagnostic layer over the accepted G14B federation.

## 1. Frozen runtime under evaluation

`T106 (LogicalOnly) -> REL-SHW-F01 -> T108 (FirstOrder)` via accepted
`ShwtpFederation` (explicit_lagged, one F01 binding, one shared communication
step, G14B-C01 identity locking). No runtime/coupling/plant semantics introduced.

## 2. Evaluation trace row (one immutable row per COMPLETED window)

Captured from actual accepted T106/T108 runtime step records + the federation's
post-boundary committed inflow:

`window_id`, `window_index`, `start_time_s`, `end_time_s`,
`communication_step_s`, `run_id`, `coupling_policy`, `t106_input_flow_m3_s`,
`t106_output_staged_m3_s`, `t108_inflow_used_m3_s`,
`t108_committed_next_m3_s`, `t108_requested_outflow_m3_s`,
`t108_applied_outflow_m3_s`, `t108_start_volume_m3`, `t108_end_volume_m3`,
`t108_end_level_m`, `t108_overflow_m3`, `mass_balance_residual_m3`,
provenance/fidelity/status refs (`simulation/synthetic/logical_only` for T106;
`simulation/synthetic/first_order` for T108; status `completed`).

## 3. Mass-balance diagnostic (exact, no invented tolerance)

`residual = V_end - (V_start + Qin_used*dt - Qout_applied*dt - overflow)`.

`t108_mass_balance_residual` mirrors the accepted G13 runtime arithmetic
exactly, so the residual is deterministically `0.0`; a non-zero residual fails
closed. No `math.isclose` / rel_tol / abs_tol is introduced.

## 4. Lag diagnostic (visible, machine-checkable)

- Window 1: `t108_inflow_used` = explicit `initial_t108_inflow_m3_s`; T106
  output is staged but NOT used same-window.
- Boundary 1: `t108_committed_next` = T106 output (available for next window).
- Window 2: `t108_inflow_used` = previous window's `t106_output_staged`.
- `lag_windows = 1` exposed as evaluation metadata only — never a
  `CompositionGraph`/binding/port property.

## 5. Bounded runner

`ShwtpEvaluator(config, window_count >= 1)` — fresh federation attempt per
instance; sequential `window-1..window-N`; records only completed windows; any
failed outcome fails closed (no retry/rollback/skip/hide). No scheduler/profile
engine; constant G14B scenario values only.

## 6. Deterministic summary

run_id, completed window_count, start/end time, communication step, coupling
policy, `lag_windows`, initial/final + min/max T108 volume, initial/final T108
level, total T106 staged volume, total T108 inflow-used volume, total applied
outflow volume, total overflow volume, max absolute mass-balance residual — all
derived exactly from trace rows.

## 7. Evaluation cases (test-only values, never plant defaults)

- balanced: inflow ≈ outflow → tank stable (volume constant, residual 0).
- fill: inflow > demand → volume rises monotonically.
- drain: inflow < demand → volume falls monotonically, never negative.
- overflow: inflow pushes past capacity → explicit overflow; mass accounted
  (residual 0, volume pinned at capacity).

## 8. Test evidence

- `tests/test_vnext_g15_evaluation.py` — 30 tests PASS.
- G14B-C01/G14B (63), G14A (20), G13B (19), G13 (28) remain green; full suite
  2253 passed.
- Complete canonical vNext baseline PASS (see report `VF-vNEXT-G15.md`).

## 9. Preserved / unchanged

T106/T108 equations + provenance; G4 Coordinator/ExecutableParticipant/transfer;
G14A projection; explicit_lagged + identity locking; G7; PIM. No T110, no
F02-F07, no scheduler, no UI/alarms/KPIs, no tolerance policy, no plant-wide
execution.
`vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`.
