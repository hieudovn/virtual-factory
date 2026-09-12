# VF-vNEXT-G12A-C01 — Endpoint identity consistency fix — Evidence

Correction: SA comment `5560719582` (base `9ddf2d2c42e89a53b098206d6db893c3f2408853`).

## Blocker addressed

`ReferenceEndpoint` previously froze semantic identity as `(authority, entity_id)`
(via `.key`) but dataclass equality/hash still included `entity_kind`. This made
`inbound()` / `outbound()` (dataclass `==`) disagree with the graph's frozen
identity rule and let conflicting `entity_kind` metadata for one external
identity collapse silently in `nodes()`.

## Fix (smallest planning/test-only correction)

- `entity_kind` is now `field(default=None, compare=False, hash=False)`:
  equality and hash use ONLY `(authority, entity_id)`. Endpoint identity remains
  exactly `(authority, entity_id)`; `entity_kind` is descriptive metadata.
- `ReferenceConnectivityGraph.__init__` now runs
  `_check_endpoint_metadata_consistency(...)`: fail closed when the same
  endpoint identity appears with conflicting `entity_kind` metadata (including
  missing vs known — a missing kind and a known kind are treated as a
  disagreement). Behavior is deterministic: any disagreement fails closed.
- `inbound()` / `outbound()` / `has_edge()` / duplicate-logical-relation checks
  now all follow the frozen identity rule (`entity_kind` excluded).

## Strengthened regression (`tests/test_vnext_g12a_reference_graph.py`)

Added `TestEndpointIdentityConsistency`:
- equality/hash ignore `entity_kind`;
- same identity + same kind allowed;
- conflicting `entity_kind` (Unit vs ProcessConnection) fails closed;
- missing vs known `entity_kind` fails closed;
- `outbound()` matches by frozen identity regardless of the query endpoint's
  `entity_kind`.

G12A tests now 31 (was 26). Full suite 2058 passed.

## Unchanged

Endpoint identity `(authority, entity_id)`, SH-WTP materialization (none), G4,
runtime projection (none), semantic taxonomy (none), runtime authorization, G12B
(not started).
