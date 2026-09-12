# VF-vNEXT-G22 — Scenario / Run / Replay Integration

Gate: `VF-vNEXT-G22`
Base (required): `028fdd8aadcee05483b7c5b3bbcf9815a680685f` (G21 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Additive generic runtime-session/lifecycle seam over the G7 run-lifecycle
authority, usable for both TIPA ASSY and the SH-WTP G21 slice. No UI, no
transport.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/bridge.py` — `ShwtpExecutionBridge`.
- `src/virtual_factory/shwtp/session.py` — `build_shwtp_session`.
- `src/virtual_factory/runcontrol/session.py` — `RuntimeSession`,
  `SessionIdentity`, `build_tipa_session` (domain-agnostic; runcontrol never
  references SH-WTP).
- `tests/test_vnext_g22_session.py` (15 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G22 gate context +
  `g22_session_replay` group.

## Required semantics proven

- explicit workspace/run/attempt/scenario identity;
- reset vs new-attempt vs replay distinct and tested;
- fresh attempt/replay rebuilds fresh runtime state (no hidden carry-over);
- deterministic replay reproduces equivalent outcome/trace;
- TIPA and SH-WTP isolated;
- identity mismatch (workspace/run/scenario) fails closed;
- SH-WTP assumed topology/fidelity metadata survives replay unchanged;
- orchestration-only session (domain runtime owns truth).

## Frozen boundaries preserved

TIPA ASSY semantics; T106/T108 equations; G21/G20/G19/G18/G14/G15; reference
connectivity graph; PIM pins. No UI, no gateway routing, no MES/PIM change, no
G4 redesign, no T110/Line2 physics.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G22: 15 passed.
- Full suite: 2413 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, g19, g20, g21, g22, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G22/01-session-replay.md`
