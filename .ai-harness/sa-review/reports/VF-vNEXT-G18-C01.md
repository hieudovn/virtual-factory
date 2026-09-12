# VF-vNEXT-G18-C01 — from_dict fail-closed provenance/reversibility

Gate: `VF-vNEXT-G18-C01`
Base (required): `45e931a1db0f4333239037b0041763d4ce522e06` (G18 head)
Status: READY FOR SA REVIEW

## Correction

`AssumedTopologyEdge.from_dict()` must fail closed when `source_kind`,
`status`, or `reversible` are omitted from the input dict (previously they
silently defaulted to assumed values). Allowed values are unchanged:
`vf_scenario_assumption` / `assumed/synthetic` / `reversible=True`.

## Changed

- `src/virtual_factory/connectivity/scenario_overlay.py` — `from_dict` now
  requires the three provenance/reversibility keys to be present; omission
  raises `ScenarioTopologyOverlayError`.
- `tests/test_vnext_g18_scenario_overlay.py` — added parametrized omission
  fail-closed tests + explicit edge round-trip test.

## Regression

- G18 tests: 33 passed (29 prior + 4 new).
- Full suite: 2333 passed.
- Complete canonical vNext baseline PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G18-C01/01-from-dict-fail-closed.md`
