# VF-vNEXT-G4-C03 · Evidence 11 — C03 correction: identity coherent across advance_to()

SA review of exact head `6ebf70947a9912ad1b0b76df179a8ccedf82b635` found one
residual identity-authority gap of the same class. Fixed; no STOP condition;
no G5+; no scope expansion.

## C03 — Participant scope identity must remain coherent across advance_to()

`Coordinator.run_window` previously re-read `participant.scope_path` only BEFORE
calling `advance_to(target)` (C02-2). A broken/mutable participant could:

1. register as scope A;
2. report A at the pre-advance C02-2 check;
3. mutate its own `scope_path` to B (or an invalid type) DURING `advance_to()`;
4. return no transfers (or transfers still claiming source A);
5. land correctly at the target time;
6. and the coordinator would still complete the window while reporting/ordering
   that participant under registered key A.

Fix: after a successful `advance_to(target)` and before any of its outputs are
accepted/staged, `run_window` re-reads `participant.scope_path` a SECOND time
through the participant contract. It must still be a `StructuralPath` exactly
equal to the registered key; drift/invalid type during `advance_to()` fails the
window before any boundary commit. No re-key/re-register; no continuous polling;
no concurrency semantics — a deterministic pre/post contract around the call.

The two checks share one helper `_scope_identity_failure(participant, key)`
(reason string or `None`), used on BOTH sides of the call so that no authority
conflict can be silently re-keyed/re-registered away.

## Final bounded authority-matrix review (C03 close-out)

- registered scope ↔ pre-advance scope_path ↔ **post-advance scope_path** ↔
  transfer.source.owner_scope — all present authorities must agree (C02-2 pre,
  C03 post, C01-1 source-ownership). 
- before-time ↔ transfer.simulation_time_s ↔ target ↔ post-advance time — C02-1
  lower bound + C01-2 upper bound + C01-5 exact boundary landing.
- active window_id ↔ transfer.window_id — C01-2 (loop + pre-commit validation).
- graph/workspace/binding/port authority — C01-3 graph-level multi-producer,
  C01-4 endpoint resolution in G1 Workspace, registry/binding/port checks.

No further same-class defect found; matrix closes.

## Tests added (mandatory adversarial + positive)

- `test_scope_drift_during_advance_fails_closed` — registered A, reports A
  pre-advance, mutates to B DURING advance_to(), emits nothing, lands at the
  boundary → window fails ("changed during advance_to" + "drifted"), no commit;
- `test_scope_invalid_type_during_advance_fails_closed` — mutates to a
  non-StructuralPath DURING advance_to() → window fails, no commit;
- `test_coherent_identity_across_advance_is_accepted` — coherent participant
  (identity stable before and after) remains accepted and the exchange completes.

All C01/C02 tests preserved and passing.

## Regression

New G4 tests 56 passed; G1 32; G2 36; G3 328; core 21; discrete 279; ASSY 354;
continuous 61; full suite **1849 passed** (0 failures). Compile PASS; no
configured ruff/mypy/black.
