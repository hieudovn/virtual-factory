# VF-vNEXT-G18-C01 — from_dict fail-closed provenance/reversibility — Evidence

Gate: `VF-vNEXT-G18-C01` · Correction gate on G18 head
`45e931a1db0f4333239037b0041763d4ce522e06`.

## Defect corrected

`AssumedTopologyEdge.from_dict()` previously defaulted `source_kind`, `status`,
and `reversible` to valid assumed values when the keys were ABSENT from the
input dict. A malformed/truncated serialized edge could therefore silently
reconstruct as a valid assumption without carrying explicit provenance.

## Fix

`from_dict()` now checks that `source_kind`, `status`, and `reversible` are
PRESENT in the input dict; omission raises `ScenarioTopologyOverlayError`
(fail closed). Allowed values are unchanged:

- `source_kind = "vf_scenario_assumption"`
- `status = "assumed/synthetic"`
- `reversible = True`

## Tests (added)

- `test_missing_required_field_fails_closed` — parametrized over
  `source_kind`, `status`, `reversible`: popping each from a valid
  `to_dict()` payload and reconstructing must raise.
- `test_valid_edge_round_trip_still_passes` — a full `to_dict()` payload
  reconstructs to an equal edge (round-trip preserved).

## Regression

- `tests/test_vnext_g18_scenario_overlay.py` — 33 tests PASS (29 prior + 4 new).
- Complete canonical vNext baseline (see report `VF-vNEXT-G18-C01.md`).
