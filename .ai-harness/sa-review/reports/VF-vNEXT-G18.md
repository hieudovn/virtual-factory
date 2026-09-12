# VF-vNEXT-G18 — Scenario-Assumed Topology Overlay

Gate: `VF-vNEXT-G18`
Base (required): `ae1dbd3575df11f5aad68762cd5c7f47620f55d8` (G17A accepted head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Additive implementation of the smallest generic `VF_SCENARIO_ASSUMED_TOPOLOGY`
overlay mechanism, so VF can carry bounded, explicit, versioned,
provenance-bearing topology assumptions without modifying or impersonating
`PIM_AUTHORITATIVE_TOPOLOGY`. T108->DIST-P108 is used only as the first bounded
fixture; no plant truth is claimed.

## Implemented (additive, isolated)

- `src/virtual_factory/connectivity/scenario_overlay.py` — generic
  `AssumedTopologyEdge` + `ScenarioTopologyOverlay` with fail-closed invariants,
  deterministic serialization, immutable `remove`/`replace`.
- `src/virtual_factory/shwtp/overlay.py` — SH-WTP T108->DIST-P108 assumed
  topology fixture (VF-local identity, never PIM canonical ids).
- `tests/test_vnext_g18_scenario_overlay.py` (29 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G18 gate context +
  `g18_scenario_overlay` group.

## Required semantics

- assumption id/version explicit;
- source = VF scenario/design assumption (never PIM/site);
- provenance/status synthetic/assumed;
- reversible/replaceable;
- no back-propagation into PIM/KG;
- authoritative vs assumed distinguishable (distinct schema);
- fail closed on malformed/ambiguous overlay;
- deterministic serialization;
- overlay unordered (no execution order);
- coupling policy remains G14B orchestration policy (untouched).

## Frozen boundaries preserved

G4 composition/coordinator; G14A projection (2 ports / 1 binding); G14B
explicit_lagged; G15 evaluator; G17A review artifact; reference connectivity
graph (G12A/B); T106/T108 runtimes; PIM pins unchanged. No new coupling policy.
No T110/Line2/chemical/electrical/automation runtime. No runtime/site
authorization broadened.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G18: 29 passed.
- Full suite: 2329 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, full_suite, checks_compile,
  checks_static_lint_type, checks_changed_files, checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G18/01-scenario-overlay.md`
