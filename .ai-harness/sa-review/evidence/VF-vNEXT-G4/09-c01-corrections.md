# VF-vNEXT-G4-C01 · Evidence 09 — C01 authority corrections + adversarial self-audit

SA review of exact head `a044efebf23dc678cb43b049187f0e46bbdee24d` found five
authority gaps in the coordinator/graph contract. All fixed; no STOP condition;
no G5+.

## C01-1 — Producer ownership fail-closed

`Coordinator.run_window` now requires every transfer staged by participant scope
X to have `transfer.source.owner_scope == X`. The emitting participant is the
authoritative producer; a source-scope mismatch fails the window before commit.

## C01-2 — Coordination window authority

- Every staged transfer must carry exactly the active `window_id` (checked both
  in the advance loop and in `_validate_transfers`).
- `BoundaryTransfer.simulation_time_s` must be finite (rejects NaN/Inf at
  construction) and must not exceed the authorized target boundary (checked in
  `_validate_transfers`; equal-time not required — an event may occur inside the
  window before the boundary).
- `Coordinator.run_window` rejects NaN/Inf `target_time_s`.

## C01-3 — Multi-producer ambiguity is a declared-graph error

`CompositionGraph.__init__` now rejects implicit many-to-one input at build time:
a target input may have at most one distinct source port across DECLARED
bindings (not merely emitted transfers). Fan-out from one output remains
allowed. The staged-transfer multi-producer check is retained as defense-in-depth.

## C01-4 — Graph endpoint scope resolution via G1 authority

`Coordinator._validate_graph_bindings` now resolves every binding endpoint's
`owner_scope` in the G1 `Workspace` before participant advance; a bound endpoint
naming a nonexistent structural scope fails the window pre-advance.

## C01-5 — Participant time contract verified by the coordinator

`run_window` now verifies, per participant, before and after advance:
`current_time_s` numeric/finite/non-negative; before advance, local time ahead of
the boundary fails without calling `advance_to`; after a successful
`advance_to(target)`, the participant must report exactly `target` (exact
equality — no invented tolerance policy); already-at-boundary remains a valid
no-op.

## Adversarial self-audit (5 matrices re-run against broken participants)

Added `BadParticipant` and focused tests:

- emitted-transfer source scope vs emitting participant → fail (`test_emitting_participant_is_authoritative_producer`);
- active window_id vs transfer.window_id → fail (`test_transfer_window_id_must_match_active_window`);
- transfer time finite / within boundary → fail (`test_transfer_time_must_not_exceed_boundary`, `test_coordinator_rejects_nonfinite_target_time`);
- participant current_time before/after advance → fail (`test_participant_must_reach_boundary_after_advance`);
- declared graph multi-producer even when a producer is silent → fail at graph build (`test_declared_multi_producer_input_rejected_at_graph_build`);
- nonexistent bound endpoint scope → fail pre-advance (`test_nonexistent_bound_endpoint_scope_fails_before_advance`).

No same-class defect found beyond the five corrections; no new architecture
decision required. Cycles, no-DAG, no-domain-engine, no-direct-mutation, no
universal dt/scheduler, no-false-rollback, no-G5+, no-AssyLineRuntime-rewrite all
preserved.

## Regression

New G4 tests 49 passed; G1 32; G2 36; G3 328; core 21; discrete 279; ASSY 354;
continuous 61; full suite **1842 passed** (0 failures).
