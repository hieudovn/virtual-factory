# VF-vNEXT-G23 — Multi-Workspace Runtime Selection

Gate: `VF-vNEXT-G23`
Base (required): `1c076525c62ab5c12e98fe970e035b4921cb62a0` (G22 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Additive generic Workspace runtime registry/selector seam over the accepted G22
sessions for TIPA (ASSY) and shwtp (G21/G22 slice). Backend/platform selection
only; prepares a future G24 workspace selector/UI (not in this gate).

## Implemented (additive, isolated)

- `src/virtual_factory/runcontrol/registry.py` — `WorkspaceRuntimeRegistry`,
  `WorkspaceRuntimeInfo`, `WorkspaceRegistryError` (domain-agnostic; runcontrol
  never references SH-WTP — SH-WTP factory wiring is by the caller).
- `tests/test_vnext_g23_registry.py` (15 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G23 gate context +
  `g23_workspace_registry` group.

## Required semantics proven

- deterministic enumeration (TIPA + shwtp, sorted);
- select TIPA / select shwtp return the correct independent RuntimeSession;
- two Workspace sessions isolated (no shared state/run_id/clock/scenario);
- switching does not mutate the inactive session;
- fresh independent session per explicit select;
- unknown/ambiguous/identity-mismatch Workspace fails closed;
- registration order does not affect enumeration/selection;
- no cross-workspace runtime coupling;
- registry is orchestration metadata only;
- architecture open for future Workspaces.

## Frozen boundaries preserved

G22 session semantics; G21/G20/G19/G18/G14/G15; TIPA ASSY; runcontrol G7
boundary. No UI, no gateway routing, no MES/PIM change, no G4 redesign, no
domain semantics change, no T110/Line2.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G23: 15 passed.
- Full suite: 2428 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, g19, g20, g21, g22, g23, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G23/01-workspace-registry.md`
