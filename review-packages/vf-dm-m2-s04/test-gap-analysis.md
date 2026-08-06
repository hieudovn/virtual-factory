# M2-S04 Test Gap Analysis

## Overview

Prior to C01 corrections, 613 tests passed but four defects were present:

1. **C01-01**: Manual step from PAUSED returned without processing events
2. **C01-02**: allowed_actions used alphabetical ordering instead of documented contract
3. **C01-03**: Accepted command results were discarded (assigned to `_`)
4. **C01-04**: Controller accessed private engine state (`_engine._run_context`)

## Identified gaps in pre-C01 tests

### GAP-01: Manual step from PAUSED — "no exception" treated as success

**Test**: `TestManualMode::test_step_from_paused_in_manual` (test_discrete_run_controller.py:351)

**Previous assertion**: Checked only `snap.status == "paused"` after stepping.

**Why it failed to detect the defect**: The test called `step_once()`, the method returned without error, status was "paused". But the `step_once()` method was returning early because status was "paused" — it never actually called `engine.step_event()`. The test only checked the final status, not whether an event was actually processed.

**New assertion added**: `test_manual_paused_step_processes_one_event` — verifies `processed_events` increases by 1, `last_event_id` changes, `trace_total_entries` increases by 1, `pending_events` decreases.

---

### GAP-02: allowed_actions — alphabetic order accepted as correct

**Test**: `TestAllowedActions::test_result_is_tuple` (test_discrete_run_controller.py:203)

**Previous assertion**: `assert actions == tuple(sorted(actions))` — explicitly verified alphabetical sorting.

**Why it failed to detect the defect**: The test codified the wrong behavior. The documented contract requires `("step_event", "auto_run", "stop")` for READY/HYBRID. Alphabetical sorting gives `("auto_run", "step_event", "stop")`.

**New assertion added**: 13 parameterized tests in `TestExactAllowedActions` verifying every row of the matrix with exact order.

---

### GAP-03: Command result observability — internal creation without caller access

**Tests**: `TestPauseDuringDispatch::test_pause_during_dispatch_commits_event_then_pauses`, `TestMultipleCommands::test_commands_apply_fifo`, all other safe-point tests.

**Previous assertion**: Tests verified `snap.status`, `snap.processed_events` etc. but never verified that command results are observable by the caller.

**Why it failed to detect the defect**: `_apply_commands()` returned results, but in `step_once()` and `run_cycle()` the results were discarded (not stored in any outbox). Results were also discarded via `_ = drained` in terminal drain paths. Tests only checked engine state, not command result retrieval.

**New assertion added**: 
- `test_accepted_pause_one_applied_result` — drain produces exactly 1 applied result
- `test_accepted_stop_one_applied_result` — drain produces 1 applied result for stop
- `test_accepted_command_invalidated_by_earlier_one_rejected` — 2 commands, one applied, one rejected
- `test_terminal_drain_explicit_rejected_result` — drained commands produce rejection results
- `test_fifo_result_ordering` — results ordered by command_sequence
- `test_drain_returns_tuple` — drain returns immutable tuple
- `test_second_drain_empty` — second drain returns ()
- `test_no_accepted_command_without_result` — all 3 commands produce results

---

### GAP-04: Terminal drain — results discarded

**Tests**: `TestAutomaticMode::test_run_cycle_drains_on_terminal`, `TestMultipleCommands::test_terminal_queue_drained`

**Previous assertion**: Checked `snap.status` after terminal, but did not verify that drained commands produced observable results.

**Why it failed to detect the defect**: `_ = drained` silently discarded the results.

**New assertion**: `test_terminal_drain_explicit_rejected_result` verifies drained commands produce rejection results in the outbox.

---

### GAP-05: Pause safe-point — event counters not checked

**Test**: `TestPauseDuringDispatch::test_pause_applies_before_next_event`

**Previous assertion**: Checked `snap.status == "paused"` and `snap.processed_events == 0`.

**Why it failed to detect the defect**: The test only checked that `processed_events == 0`, but the pre-C01 code was returning early due to PAUSED status check, not due to the pause command's safe-point semantics. The same outcome (0 events processed, PAUSED status) would occur whether the pause was applied at safe-point or the method simply detected PAUSED after safe-point.

**New assertion**: `test_pause_command_blocks_event` — explicitly verifies pause was applied at safe-point (snapshot_sequence increased by exactly 1 for transition), and the pending event remains pending.

---

## Summary of new C01 tests

| Test Class | Tests | Covers |
|------------|-------|--------|
| `TestManualStepFromPaused` | 2 | C01-01 MANUAL + HYBRID paused stepping |
| `TestPauseCommandBlocksNextEvent` | 3 | C01-01 pause safe-point blocks event |
| `TestExactAllowedActions` | 13 | C01-02 every row of matrix |
| `TestCommandResultObservability` | 8 | C01-03 outbox, drain, ordering |
| `TestEngineRunId` | 3 | C01-04 run_id encapsulation |
| **Total** | **29** | |
