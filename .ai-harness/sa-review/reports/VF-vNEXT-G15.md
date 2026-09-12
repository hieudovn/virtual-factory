# VF-vNEXT-G15 — SH-WTP Federated Evaluation Trace & Diagnostics

Gate: `VF-vNEXT-G15`
Base (required): `75521720ae6330160c16075084a36a07ecaa6521`
Status: READY FOR SA REVIEW

## Scope

Deterministic evaluation/diagnostic layer over the accepted G14B federation
(T106 → REL-SHW-F01 → T108, `explicit_lagged`) — evaluation only, no new
runtime/coupling/plant semantics.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/evaluation.py` (+ `__init__.py` exports):
  - `ShwtpEvaluationRow` — one immutable/detached row per completed window with
    all required identity, T106/T108 flow/volume/level/outflow/overflow,
    mass-balance residual, and provenance/fidelity/status fields.
  - `t108_mass_balance_residual(step)` — exact accepted-model residual
    (`V_end - (V_start + Qin_used*dt - Qout_applied*dt - overflow)`); exactly
    `0.0`, no invented tolerance; non-zero fails closed.
  - `ShwtpEvaluator(config, window_count >= 1)` — bounded sequential runner over
    `ShwtpFederation`; records only completed windows; failed outcomes fail
    closed (no retry/rollback/skip/hide); fresh attempt per instance.
  - `ShwtpEvaluationSummary` — deterministic immutable summary derived only from
    trace rows (run_id, window_count, start/end time, communication step,
    coupling policy, `lag_windows=1`, initial/final + min/max volume,
    initial/final level, total staged/inflow-used/applied-outflow/overflow
    volumes, max absolute mass-balance residual).
- `tests/test_vnext_g15_evaluation.py` (30 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G15 gate context +
  `g15_evaluation` group.

## Lag visibility

`lag_windows = 1` (evaluation metadata only, never on `CompositionGraph`).
Window 1 uses explicit `initial_t108_inflow_m3_s`; boundary 1 commits T106
output for the next window; window 2 uses exactly the previous window's T106
output. Verified machine-checkable.

## Frozen boundaries preserved

- T106 (G13B 19 green) and T108 (G13 28 green) equations/provenance unchanged.
- G4 Coordinator/ExecutableParticipant/transfer unchanged; G14A projection (20
  green) unchanged; G14B-C01 identity locking (63 green) unchanged; explicit_lagged
  semantics unchanged; PIM/G7 unchanged.
- No T110/F02-F07; no scheduler/profile engine; no tolerance policy; no UI/KPIs;
  no plant-wide execution.
- `vf_runtime_authorization = NOT_AUTHORIZED`;
  `site_authorized_execution = NOT_AUTHORIZED`.

## Regression

- G15: 30 passed.
- Full suite: 2253 passed (2223 prior + 30 new).
- Complete canonical vNext baseline (g1..g13b + g14a + g14b + g15 + full_suite +
  compile/static/changed-files/preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G15/01-evaluation-trace.md`
