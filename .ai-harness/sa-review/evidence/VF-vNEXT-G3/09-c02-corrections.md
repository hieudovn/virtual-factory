# VF-vNEXT-G3-C02 · Evidence 09 — C02 corrections

SA review of exact head `f2beb14193880f8676d4c70b844a906c969721bc` required one
remaining fail-closed coherence gap to be closed. Narrow G3 correction only; no
redesign of `ObservationEnvelope`, G2 `ProvenanceV2`, `EventStore`, alarm
semantics, or protocols; no G4+.

## C02-1 — Full scope/provenance/time coherence when both authorities present

Observation alignment (`observation/alignment.py`):

- `ObservationStructuralContext.__post_init__`: when both `context.scope_path`
  and `context.provenance.scope_path` are present they MUST be equal, else
  `ObservationContextError`.
- `carry_structural_context()`: when `context.provenance.simulation_time_s` is
  present it MUST equal `ObservationEnvelope.simulation_time_s`, else
  `ObservationContextError`.
- Workspace/run coherence and legacy no-context behavior preserved; absent
  provenance fields are never fabricated.

EventFact (`telemetry/event_fact.py`):

- `scope_path` itself carries authoritative workspace identity: with
  `provenance` present, `provenance.workspace_id` MUST equal
  `scope_path.workspace_id` even when explicit `EventFact.workspace_id` is
  omitted (an explicit `workspace_id` never contradicts its own scope path).
- when both event and provenance `scope_path` are present they MUST be equal.
- when `provenance.simulation_time_s` is present it MUST equal
  `EventFact.simulation_time_s`.
- C01 run/workspace checks retained; optional provenance fields not mandatory;
  no missing identity fabricated.

## C02-2 — Reserved-key presence check

`_reserved_key_check()` now uses KEY PRESENCE (`key in current`), not `get()`
semantics: a present reserved `vf.*` key whose value is `None` is still a
pre-existing key and cannot be silently overwritten by a non-None value; any
existing value differing from the new value fails closed; same-value repeats are
allowed.

## Required tests added (positive/negative)

- `test_observation_alignment.py::test_scope_vs_provenance_scope_mismatch_fails_closed`
- `test_observation_alignment.py::test_provenance_simulation_time_mismatch_fails_closed`
- `test_observation_alignment.py::test_all_scope_run_time_authorities_agree`
- `test_observation_alignment.py::test_reserved_key_present_none_conflicts_with_new_value`
- `test_event_fact.py::test_scope_path_is_workspace_authority_without_explicit_workspace`
- `test_event_fact.py::test_scope_path_workspace_authority_agrees_with_provenance`
- `test_event_fact.py::test_provenance_simulation_time_mismatch_fails_closed`
- `test_event_fact.py::test_event_and_provenance_authorities_agree_when_both_present`
  (extended: also asserts agreeing `simulation_time_s`)

## Regression (all green)

- New G3 tests 51 passed; observation M5 244; telemetry/alarm/event 27; G2
  provenance 36; G1 workspace 32; ASSY oracle 354; continuous 61; full suite
  **1766 passed** (0 failures).
