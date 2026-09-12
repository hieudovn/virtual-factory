# VF-vNEXT-G19 — Generic Multi-Participant Federation Proof (>2)

Gate: `VF-vNEXT-G19`
Base (required): `44d026f4d081296c31d418806ac5e96575a2d8e4` (G18-C01 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Additive reusable synthetic harness + tests proving the existing G4
Coordinator / ExecutableParticipant / BoundaryTransfer mechanism coordinates
3+ synthetic participants exchanging detached boundary values over 2+ bindings
in one deterministic window — no plant semantics.

## Implemented (additive, isolated)

- `src/virtual_factory/federation/generic.py` — `SyntheticParticipant`,
  `SyntheticFederation`, `build_synthetic_federation` (linear chain, 3+
  participants, N-1 bindings, explicit_lagged applied at orchestration level).
- `tests/test_vnext_g19_multi_participant.py` (19 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G19 gate context +
  `g19_multi_participant` group.

## Required invariants proven

- G4 semantics reused (no G4 file changed);
- CompositionGraph != execution order;
- coupling policy remains orchestration policy (`explicit_lagged` only in
  harness, never on graph/ports/bindings/transfers);
- deterministic participant/transfer ordering (registration-order independent);
- detached immutable transfers;
- identity/workspace mismatch fails closed;
- failed window never reported completed;
- 3+ participants exchange values over >=2 bindings in one window;
- identical inputs => identical results;
- no same-window feed-through (explicit_lagged).

## Frozen boundaries preserved

G4 composition/coordinator; G14A projection; G14B explicit_lagged; G15
evaluator; G18 overlay; reference connectivity graph; T106/T108 runtimes; PIM
pins. No new coupling policy. No DIST-P108/T110/Line2/chemical/electrical/
automation runtime. No SH-WTP authority broadening. No UI.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G19: 19 passed.
- Full suite: 2352 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, g19, full_suite, checks_compile,
  checks_static_lint_type, checks_changed_files, checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G19/01-multi-participant-proof.md`
