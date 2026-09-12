# VF-vNEXT-G4-C02 · Evidence 10 — C02 corrections: full authority triangle

SA review of exact head `fbeea8567b976185bb1b70204e4fd9738c484369` found two
remaining same-class authority gaps. Fixed; no STOP condition; no G5+.

## C02-1 — Transfer time must belong to the producer's coordination interval

`Coordinator.run_window` now captures the authoritative pre-advance time
(`before`) for each emitting participant and requires every transfer returned by
that participant to satisfy:

    before <= transfer.simulation_time_s <= target_time_s

- equality at either boundary allowed; no epsilon/tolerance invented;
- no global timestep — each participant keeps its own lower bound;
- a stale transfer (time < before) fails the window before commit.

## C02-2 — Registered structural identity coherent at execution time

Before advancing each participant, `run_window` re-reads
`participant.scope_path` through the contract; it must still be a
`StructuralPath` and exactly equal the structural identity under which the
participant was registered. Drift to another scope / foreign workspace /
nonexistent path / container-only path / invalid type fails closed before that
participant advances. No silent re-key/re-register during a window.

## Final authority-triangle self-audit

- `registered scope key ↔ current participant.scope_path ↔ transfer.source.owner_scope`
  — all three must agree (register validates the key; run_window re-verifies the
  reported scope_path; transfer.source must equal the emitting scope).
- `participant pre-window time ↔ transfer.simulation_time_s ↔ target boundary`
  — lower bound and upper bound both enforced.
- `active window_id ↔ transfer.window_id` — enforced (C01).
- workspace / graph / binding / port authorities — enforced (C01/C02).

No value is fabricated or re-keyed to make authorities agree.

## Tests added

- `test_stale_transfer_below_producer_interval_fails_closed` (participant at 5.0
  → 10.0 emitting time 1.0 → fail);
- `test_transfer_inside_producer_interval_is_accepted` (time 7.0 inside
  [5.0, 10.0] → completed);
- `test_post_registration_scope_drift_fails_closed` (A→B drift → fail before
  advance);
- `test_post_registration_invalid_scope_type_fails_closed` (string scope_path →
  fail).

## Regression

New G4 tests 53 passed; G1 32; G2 36; G3 328; core 21; discrete 279; ASSY 354;
continuous 61; full suite **1846 passed** (0 failures).
