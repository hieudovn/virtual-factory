# VF-vNEXT-G3-C01 · Evidence 08 — C01 corrections

SA review of exact head `910317f4bd66877aeda6ae264f7ed9cc1860845f` required two
fail-closed semantic corrections. Both applied; no STOP condition triggered; no
G4+ scope.

## C01-1 — Observation/Event run-context identity coherence

Applied:

- `observation/alignment.py carry_structural_context()` now enforces, fail
  closed:
  - `context.run_id` (when present) MUST equal `ObservationEnvelope.run_id`;
  - `context.provenance.run_id` (when provenance present) MUST equal
    `envelope.run_id` (so if both are present all three agree);
  - a pre-existing reserved `vf.*` context key may only be repeated with the
    SAME value; a conflicting value raises `ObservationContextError` (never
    silently overwritten).
- `telemetry/event_fact.py EventFact.__post_init__()` now enforces provenance
  coherence: when both explicit event fields and `ProvenanceV2` are present,
  `provenance.run_id == run_id` (when run_id present) and
  `provenance.scope_path == scope_path` (when both scope paths present).
  Optional fields need not exist; no two present authorities may contradict.

Tests added:

- `test_observation_alignment.py::test_context_run_id_mismatch_fails_closed`
- `test_observation_alignment.py::test_provenance_run_id_mismatch_fails_closed`
- `test_observation_alignment.py::test_all_run_authorities_agree_when_context_and_provenance_present`
- `test_observation_alignment.py::test_reserved_key_conflict_fails_closed_not_silently_overwritten`
- `test_observation_alignment.py::test_reserved_key_same_value_is_allowed`
- `test_event_fact.py::test_provenance_run_id_mismatch_fails_closed`
- `test_event_fact.py::test_provenance_scope_path_mismatch_fails_closed`
- `test_event_fact.py::test_event_and_provenance_authorities_agree_when_both_present`

## C01-2 — Alarm initial-active history

Applied in `telemetry/alarm_manager.py evaluate()` (smallest correct contract):

- first observed INACTIVE → baseline, no Event;
- first observed ACTIVE → emits an `assert` `AlarmEventFact` at that observation
  time (so a later clear is never an orphan);
- first ACTIVE then CLEAR → history `[assert, clear]`;
- stable active/inactive → no duplicate transition facts;
- existing `SignalValue`, thresholds and `AlarmState` semantics preserved.

Tests added / reworked:

- `test_alarm_event_facts.py::test_first_observed_inactive_emits_no_fact`
- `test_alarm_event_facts.py::test_first_observed_active_emits_assert_fact`
- `test_alarm_event_facts.py::test_first_active_then_clear_is_assert_then_clear_not_orphan`

## Regression (all green)

- New G3 tests 44 passed; observation M5 244; telemetry/alarm/event 27; G2
  provenance 36; G1 workspace 32; ASSY oracle 354 (clean re-run); continuous 61;
  full suite **1759 passed** (0 failures).

## Preserved (unchanged)

- `evaluate()` signature/return/`industrial_event` output; `AlarmState`;
  `EventStore` append-only typed semantics; non-fabrication of G1/G2/PIM
  identity; no G4+ implementation.
