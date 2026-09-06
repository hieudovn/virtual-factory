# VF-vNEXT-G7-C01 · Evidence 08 — Active-attempt authority + attempt-bound execution

SA review of exact head `8b168f927c85de9148259faea1e1f7c8d07ebe78`
(comment `5557354313`) found two lifecycle-authority defects. Fixed in
`src/virtual_factory/runcontrol/lifecycle.py` (+ tests). No G8+, no new
synchronization policy, no `AssyLineRuntime` change.

## C01-A — Single mutable active attempt (per service/workspace authority)
- `_require_active(run_id)` now gates EVERY mutation (start/step/pause/resume/
  stop/reset): the run must equal `active_run_id` AND pass the state guard. A
  known but superseded/historical run id fails closed even though it still
  exists in `_runs`.
- `create_run()` fails closed when the current active run is nonterminal
  (`created/running/paused`) — it can no longer silently supersede a mutable
  attempt.
- `restart()`/`replay()` remain the only paths that create the next active
  attempt, and both now require a TERMINAL source run (restart already did;
  replay now also requires terminal). This preserves exactly one mutable active
  attempt; concurrent mutable attempts are impossible.
- `status`/`has_run`/`current` remain READ-only for any run — historical records
  stay readable.

## C01-B — Attempt-bound execution state
- Removed the single global `_bridge` cache. `RunRecord` now carries an
  attempt-local `bridge` field; `_bridge_for(record)` lazily builds the bridge
  ONCE per run attempt (the API bridge factory constructs a fresh
  `TipaAssyFederation` per attempt).
- `restart`/`replay` therefore start from a FRESH domain execution context at
  initial time/state — they do NOT continue the prior runtime's time/WIP/domain
  state; the prior run's runtime state is never mutated/reused.
- `reset` uses the SAME attempt bridge (`_bridge_for(record)`) → same `run_id`
  and same runtime objects, returning them to their accepted reset baseline. It
  is not turned into restart/replay.
- No cross-workspace execution: target resolution still fails closed for foreign
  workspace paths (`TargetResolutionError`).

## Mandatory adversarial tests (evidence 07)
1. create A (nonterminal) then create B → `RunLifecycleError`.
2. A terminal → B active → mutate A (known superseded id) → fail closed.
3. API mutation with a known historical/superseded run id → 409 conflict.
4. run A advances ASSY to 120, stops, restart B → distinct `run_id` +
   `source_run_id=A`, fresh context (first B step lands at 120, not 240).
5. replay from eligible terminal run → fresh execution context; source run's
   runtime state untouched (next boundary still 240).
6. reset on active nonterminal run keeps same `run_id` and same runtime object
   identity, returning time to 0.
7. prior run records remain readable/immutable lifecycle history (`status(A)`
   unchanged after B active).
8. full G7/G6/G5/G4/G1-G3/ASSY/continuous/full regressions green.

## Regression (re-run)
New G7 tests 37 passed (was 30; +7 C01); UI/API + S04B gating 134; G6 31;
G5 26; G4 56; G1 32; G2 36; G3 328; ASSY oracle 354; continuous 61; full suite
**1943 passed** (0 failures). Compile PASS.
