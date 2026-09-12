# VF-vNEXT-G3-C03 · Evidence 10 — Self-audit: full reserved vf.* state validation matrix

## 0. C03 correction applied

SA review of exact head `9f4770ab489ceffbc56b9eb34a9b1eb682497d9e` required
validation of the ENTIRE pre-existing reserved `vf.*` state before merge. In
`observation/alignment.py`, `carry_structural_context()` was rewritten so that
an incoming optional omission is never treated as permission to retain stale
contradictory reserved authority:

- existing `vf.workspace_id` must equal the incoming workspace;
- existing `vf.run_id` must equal `envelope.run_id` (even when incoming run_id is
  omitted);
- existing `vf.scope_path` must be a valid canonical path rooted in the same
  workspace and agree with every other present scope authority (existing /
  incoming context / incoming provenance);
- existing `vf.provenance` must be structurally compatible with the frozen
  workspace/run/scope/time authorities and, when an incoming provenance is also
  present, must be the SAME serialized provenance (no silent overwrite of a
  differing authority);
- coherent pre-existing reserved state remains accepted; `context=None` returns
  the same envelope unchanged (legacy).

## 1. Three authority sources

SA appended self-audit requirement before READY: after the C03 fix, sweep the
whole observation context seam for variants of the same class and prove (in
tests) that any two simultaneously-present authorities which differ fail closed.

## 1a. Three authority sources

| Source | workspace | run_id | scope_path | simulation_time_s | provenance |
|---|---|---|---|---|---|
| `ObservationEnvelope` field | — | `run_id` (always) | — | `simulation_time_s` (always) | — |
| pre-existing reserved `vf.*` | `vf.workspace_id` | `vf.run_id` | `vf.scope_path` | (inside `vf.provenance.simulation_time_s`) | `vf.provenance` |
| incoming context/provenance | `context.workspace_id` (required) | `context.run_id` | `context.scope_path` | `context.provenance.simulation_time_s` | `context.provenance` |

## 2. Matrix (per field: absent / present-same / present-conflict)

Every cell below is enforced fail-closed in `observation/alignment.py`
(`ObservationStructuralContext.__post_init__`, `carry_structural_context`,
`_validate_existing_provenance`, `_parse_scope_path`). No value is fabricated.

### workspace_id
| present authorities | outcome | guard |
|---|---|---|
| existing vf.workspace_id only | == context.workspace_id required | `KEY_WORKSPACE_ID in existing` equal check |
| existing vf.workspace_id + incoming context | must be equal (same/conflict) | conflict → `_conflict` |
| existing vf.provenance.workspace_id | must equal context.workspace_id | `_validate_existing_provenance` |
| scope_path root (existing/context/prov) | must equal context.workspace_id | scope-root check |
| incoming provenance.workspace_id | must equal context.workspace_id | context `__post_init__` |
| all present | all equal or fail | above |

### run_id
| present authorities | outcome | guard |
|---|---|---|
| envelope.run_id (always) | authoritative | anchor |
| existing vf.run_id | must equal envelope.run_id even when incoming omits run_id | `KEY_RUN_ID in existing` check |
| incoming context.run_id | must equal envelope.run_id | incoming run check |
| incoming/context provenance.run_id | must equal envelope.run_id | incoming prov run check |
| existing vf.provenance.run_id | must equal envelope.run_id | `_validate_existing_provenance` |
| all present | all equal or fail | above |

### scope_path
| present authorities | outcome | guard |
|---|---|---|
| existing vf.scope_path | must be a valid canonical path rooted in context.workspace_id | `_parse_scope_path` + root check |
| incoming context.scope_path | must equal any present scope | distinct-scope check |
| incoming provenance.scope_path | must equal any present scope | distinct-scope check |
| existing vf.provenance.scope_path | must equal any present scope authority + root | `_validate_existing_provenance` |
| all present | all equal or fail (even when incoming omits its own scope) | distinct-scope check |

### simulation_time_s
| present authorities | outcome | guard |
|---|---|---|
| envelope.simulation_time_s (always) | authoritative | anchor |
| incoming provenance.simulation_time_s | must equal envelope time | incoming prov time check |
| existing vf.provenance.simulation_time_s | must equal envelope time | `_validate_existing_provenance` |
| all present | all equal or fail | above |

### provenance (whole authority)
| present authorities | outcome | guard |
|---|---|---|
| existing vf.provenance only | validated against workspace/run/scope/time | `_validate_existing_provenance` |
| incoming provenance only | validated against envelope/workspace/scope | incoming checks |
| BOTH existing vf.provenance and incoming provenance | must be EQUAL dicts, else fail (no silent overwrite) | equality guard in carry |

### optional omission rule
Incoming optional omission is NOT permission to retain stale contradictory
reserved authority: existing reserved keys are validated against the envelope /
incoming workspace regardless of whether the incoming optional field is
provided. Coherent existing reserved state remains accepted.

### legacy
`context=None` → same envelope returned unchanged (C03 validation applies only
when the carry/merge seam is invoked explicitly).

## 3. Tests added (test_observation_alignment.py, C03 block)

workspace: `test_existing_vf_workspace_must_match_incoming_workspace`,
`test_existing_vf_provenance_workspace_conflict_fails_closed`.
run_id: `test_existing_vf_run_id_conflicts_when_incoming_omits_run`,
`test_existing_vf_run_id_coherent_when_incoming_omits_run_is_accepted`,
`test_existing_vf_provenance_run_id_conflict_fails_closed`.
scope_path: `test_existing_vf_scope_path_conflicts_via_incoming_provenance_scope`,
`test_existing_vf_scope_path_must_be_rooted_in_workspace`,
`test_existing_vf_scope_path_must_be_valid_structural_path`,
`test_existing_vf_scope_path_coherent_is_accepted_when_incoming_omits_scope`,
`test_existing_vf_provenance_scope_conflict_fails_closed`.
simulation_time_s: `test_existing_vf_provenance_time_conflict_fails_closed`,
`test_existing_vf_provenance_time_coherent_is_accepted`.
provenance: `test_existing_vf_provenance_must_equal_incoming_provenance_when_both_present`.
coherent/legacy: `test_coherent_full_existing_reserved_state_is_accepted`,
`test_coherent_existing_provenance_retained_when_incoming_omits`,
`test_legacy_context_none_returns_same_envelope_even_with_reserved_state`.

## 4. Self-audit conclusion

- No defect of the "two present authorities differ" class remains: any
  simultaneously-present conflicting authority for workspace / run_id /
  scope_path / simulation_time_s / provenance fails closed.
- No value is fabricated to make authorities agree.
- No architecture/schema redesign was required (ObservationEnvelope and G2
  ProvenanceV2 untouched); scope stays G3.
