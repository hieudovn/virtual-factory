# VF-vNEXT-G13-C01 — T108 identity/provenance closure — Evidence

Correction: Issue #62 (base `34b87516288d9e4c805a683e5b208a49e99dc0cd`).

## Gaps closed

### A. Canonical identity/reference integrity
`T108TankRuntime(..., canonical_id=...)` previously allowed a caller to override the
canonical semantic reference. Correction: the `canonical_id` constructor parameter was
removed; `self._canonical_id` is locked to `SHWTP_T108_CANONICAL_ID`
(`UNIT-SHW-L1-T108`). It is read-only metadata, never VF runtime identity, and can no
longer be relabeled.

### B. Snapshot provenance visibility
`T108State` previously carried only `time_s` / `volume_m3` / `level_m`. Correction:
`T108State` now carries an immutable `ProvenanceV2` built via the reused G2
`to_provenance_v2` seam with `OriginKind.SIMULATION`, `DataStatus.SYNTHETIC`,
`Fidelity.FIRST_ORDER`, `simulation_time_s` = current time, `step` = current step index.
Optional semantic contract pins are preserved only when actually supplied (never
fabricated). `state` / `snapshot()` remain detached and immutable.

## Boundaries preserved

- Exact executable path only `shwtp/line1/l1_t108`; no T106/T110 runtime; T110 blocked.
- No G4 / BoundaryPort / CompositionBinding / coordinator; no G12A/B relation projection.
- No PIM / legacy engine / G2 provenance semantics / G1 identity / G7 lifecycle change.
- No site-faithful/measured/SourceMapped/SiteVerified/ParameterizedReady/CalibratedReady.
- `vf_runtime_authorization = NOT_AUTHORIZED`; `site_authorized_execution = NOT_AUTHORIZED`.

## Focused regression tests (`tests/test_vnext_g13_t108.py`)

Added `TestC01Corrections`:
- `test_canonical_reference_locked_to_t108` — no `canonical_id` override parameter;
  every emitted step record carries exactly `UNIT-SHW-L1-T108`.
- `test_snapshot_carries_truthful_provenance` — snapshot provenance is
  simulation/synthetic/first_order with T108 scope path and no site/measurement labels.
- `test_snapshot_provenance_tracks_time_and_step`.
- `test_snapshot_provenance_immutable_and_detached`.

G13 tests now 28 (was 24). Full suite 2121 passed.

## Unchanged

No runtime expansion, no G4/PIM/T106/T110/G14.
