# VF-vNEXT-G21 — SH-WTP Functional Simulation Expansion

Gate: `VF-vNEXT-G21`
Base (required): `65a2581ef825a79f8f088c0bc7672b249e96c942` (G20-C01 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Expand SH-WTP from the T106→T108 proof into a bounded runnable multi-scope
simulation slice spanning treatment and distribution. Additive plant-slice
module + tests; no plant physics fabricated.

## Selected slice (5 executable scopes)

`RAW-INTAKE → T100 → T106 → T108 → DIST-P108`

- RAW-INTAKE (logical_only, scenario_assumed) — synthetic raw-water source.
- T100 (logical_only, scenario_assumed) — receiving junction.
- T106 (logical_only, accepted) — filter, reuses T106LogicalRuntime.
- T108 (first_order, accepted) — clean-water tank, reuses T108TankRuntime.
- DIST-P108 (logical_only, scenario_assumed) — distribution sink.

Only T106→T108 is PIM-authoritative (REL-SHW-F01). The other three links are
G18 `VF_SCENARIO_ASSUMED_TOPOLOGY` (explicit/versioned/reversible). T110 is not
used.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/expansion.py` — `PlantSliceScope`, 5 participant
  adapters, `build_shwtp_plant_slice`.
- `tests/test_vnext_g21_shwtp_expansion.py` (21 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G21 gate context +
  `g21_shwtp_expansion` group.

## Frozen boundaries preserved

TIPA ASSY behavior; G20/G19/G18/G14/G15; reference connectivity graph; T106/T108
standalone runtimes; PIM pins. No gateway routing, no MQTT/Kafka/REST, no T110
runtime, no whole-plant/site-faithful claim, no G4 redesign.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G21: 21 passed.
- Full suite: 2398 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, g19, g20, g21, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G21/01-shwtp-expansion.md`
