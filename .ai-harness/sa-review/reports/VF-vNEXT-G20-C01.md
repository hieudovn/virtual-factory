# VF-vNEXT-G20-C01 — from_dict authority

Gate: `VF-vNEXT-G20-C01`
Base (required): `4bf44d31e63b936902460c9beec67cfc7fea6026` (G20 head)
Status: READY FOR SA REVIEW

## Correction

`GatewayBindingTable.from_dict()` must not trust the serialized
`known_scope_paths` field as validation authority. Reconstruction with bindings
must receive the authoritative known scope set from the caller / actual
Workspace, or fail closed. The serialized field stays as inspection metadata
only.

## Changed

- `src/virtual_factory/integration/binding.py` — `from_dict` now takes
  `known_scope_paths` as an explicit authoritative parameter and ignores the
  serialized field for validation.
- `tests/test_vnext_g20_gateway_binding.py` — added 3 authority tests; updated
  round-trip to pass the authoritative set.

## Regression

- G20 tests: 25 passed (22 prior + 3 new).
- Full suite: 2377 passed.
- Complete canonical vNext baseline PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G20-C01/01-from-dict-authority.md`
