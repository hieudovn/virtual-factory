# VF-vNEXT-G3-C04 · Evidence 11 — Provenance lifecycle self-audit

SA review of exact head `c234dbb4b51979e40b2a3affa6d1c1a3876d160d` found two
defects in `vf.provenance` handling and required a full lifecycle self-audit:

`ProvenanceV2 -> serialized reserved vf.provenance -> ObservationEnvelope.context
-> read/to_dict consumer`

## Defect 1 (fixed) — pre-existing vf.provenance only partially validated

Previously `vf.provenance` was checked only for mapping type + workspace/run/
scope/time consistency, so an envelope could retain an invalid G2 truth label
(e.g. `origin_kind="measured"`, unsupported `data_status`/`fidelity`, invalid
step/time).

Fix in `observation/alignment.py` (G3-local; no competing/weaker validator):

- `_coerce_existing_provenance()` accepts the canonical JSON-string form or a
  plain serialized mapping (anything else fails closed).
- `_rehydrate_provenance()` reconstructs a G2 `ProvenanceV2` from the serialized
  dict, reusing the G2 enums/invariants EXACTLY: `OriginKind(...)`,
  `DataStatus(...)`, `Fidelity(...)`, `ProvenanceV2.__post_init__`
  (`origin_kind` must be simulation; time/step non-negative; required fields
  present). The serialized field set must be EXACTLY the `ProvenanceV2` field
  set and `prov.to_dict() == data` (faithful round-trip). Any malformed/missing
  required field, unknown/extra key, or invalid frozen truth label fails closed.
- Optional fields are preserved as-is; nothing is fabricated.

## Defect 2 (fixed) — nested-mutable provenance in Observation context

Previously `carry_structural_context()` stored `context.provenance.to_dict()` as
a nested dict inside `ObservationEnvelope.context`, whose top-level mapping is a
`MappingProxyType` but whose nested objects are NOT deep-frozen — so a completed
Observation's provenance could be mutated after validation.

Fix (smallest G3-local solution; `ObservationEnvelope` NOT redesigned):

- The reserved `vf.provenance` value is now an immutable **canonical JSON string**
  (`json.dumps(prov.to_dict(), sort_keys=True, separators=(",",":"))`).
- A `str` leaf cannot be item-mutated; the top-level context is read-only, so
  mutation through the resulting Observation is impossible.
- Serialization stays deterministic and plain-data compatible: the exact G2
  serialized dict is preserved (JSON-encoded); `json.dumps(envelope.to_dict())`
  round-trips.
- Pre-existing provenance (legacy dict or canonical string) is validated and
  normalized to the canonical string on merge.

## Lifecycle self-audit proofs (test_observation_alignment.py C04 block)

| Invariant | Proof |
|---|---|
| validity not weakened across serialization | `test_valid_provenance_survives_serialization_boundary` (string fed back revalidates identically); `_rehydrate_provenance` faithful round-trip check |
| no post-validation mutation | `test_carried_provenance_is_immutable_canonical_json`, `test_no_provenance_mutation_through_context_read` (TypeError on nested/top-level mutation; to_dict stable) |
| invalid origin_kind / data_status / fidelity / step / time fail closed | `test_existing_provenance_invalid_origin_kind_fails_closed`, `..._invalid_data_status_fails_closed`, `..._invalid_fidelity_fails_closed`, `..._invalid_step_time_fails_closed` |
| malformed/missing/unknown fields fail closed | `..._missing_required_field_fails_closed`, `..._extra_unknown_key_fails_closed`, `..._non_mapping_fails_closed` |
| C01–C03 coherence intact | full regression: workspace/run/scope/time matrix tests retained and green |
| deterministic plain-data serialization | `test_carried_provenance_serialization_is_plain_data_and_deterministic` |
| no PIM canonical / evidence fabricated | existing tests retained (`no canonical_signal_id` / `evidence` in parsed provenance) |
| legacy `context=None` unchanged | `test_legacy_context_none_returns_same_envelope_even_with_reserved_state` |
| no G4+ / no ObservationEnvelope / ProvenanceV2 redesign | scope guard; only `observation/alignment.py` + tests changed |

## Regression (all green)

New G3 tests 78 passed; observation M5 244; telemetry/alarm/event 27; G2
provenance 36; G1 workspace 32; ASSY oracle 354 (clean re-run; one run surfaced
the documented pre-existing `test_demo_composition` id()-flake); continuous 61;
full suite **1793 passed** (0 failures).
