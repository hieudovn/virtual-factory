# VF-vNEXT-G20-C01 — from_dict authority — Evidence

Gate: `VF-vNEXT-G20-C01` · Correction gate on G20 head
`4bf44d31e63b936902460c9beec67cfc7fea6026`.

## Defect corrected

`GatewayBindingTable.from_dict()` previously reconstructed
`known_scope_paths` from the serialized dict itself, so a tampered serialized
scope list could authorize an unknown scope.

## Fix

- `from_dict(data, *, known_scope_paths=None)` now requires the caller to pass
  the authoritative `known_scope_paths` set (derived from the actual G1
  Workspace) whenever the reconstruction has bindings; otherwise it fails
  closed.
- The serialized `known_scope_paths` field remains in `serialize()` output as
  inspection metadata only and is never read as validation authority.

## Tests (added)

- `test_tampered_scope_list_does_not_authorize_unknown_scope` — tampering the
  serialized metadata does not authorize a bound scope outside the authoritative
  set; a correct authoritative set reconstructs fine (tampered field ignored).
- `test_reconstruction_requires_authoritative_scope_set` — reconstruction with
  bindings fails closed when no (or a wrong) authoritative set is supplied.
- `test_deterministic_trusted_round_trip` — round-trip with the authoritative set
  reproduces an equal serialized table.

## Regression

- `tests/test_vnext_g20_gateway_binding.py` — 25 tests PASS (22 prior + 3 new).
- Complete canonical vNext baseline (see report `VF-vNEXT-G20-C01.md`).
