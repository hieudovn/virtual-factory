# VF-vNEXT-G17A — Post-G16 Platform Workstream Independence Review

Gate: `VF-vNEXT-G17A`
Base (required): `732decd68a02af6f0ee1de1e830631747a99d060` (G16 accepted head)
External PIM evidence: `d10049801a1eb022a7fa2e83badabefb92fb7412`
Verdict: `T108-DIST-EVIDENCE — STILL_INSUFFICIENT`
Status: READY FOR SA REVIEW

## Scope

Planning/review only — no runtime implementation. Separates VF work that
depends on unresolved plant semantic authority from platform capability work
that can proceed independently.

## Implemented (additive, isolated)

- `configs/vnext/shwtp/shwtp_workstream_independence_review.json` —
  machine-readable workstream classification matrix (23 records), dependency
  matrix, topology distinction, recommended next gate, deferred/blocked list,
  architecture invariants, no-runtime-authorization statement.
- `configs/vnext/shwtp/WORKSTREAM-INDEPENDENCE-REVIEW.md` — human-readable note.
- `tests/test_vnext_g17a_workstream_review.py` (24 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G17A gate context +
  `g17a_workstream_review` group.

## Classification

- `CAN_PROCEED_INDEPENDENTLY` (16): multi-participant federation (>2), lifecycle
  hardening, deterministic replay, diagnostics generalization, evaluation-trace
  generalization, scenario input handling, orchestration-policy seam, runtime
  inspection, topology visualization, run status/health, online charts, boundary
  monitoring, failure propagation, attempt isolation, heterogeneous archetypes,
  coupling-policy extension seam.
- `SHOULD_WAIT_FOR_RUNTIME_EXPANSION` (2): multi-scope runtime UI shell,
  alarms/events for simulation runtime.
- `BLOCKED_BY_PIM_EVIDENCE` (5): whole-plant SH-WTP, DIST-P108, T110, Line 2,
  chemical/electrical/automation runtime.

## Topology distinction (SA clarification)

- `PIM_AUTHORITATIVE_TOPOLOGY` — still BLOCKED for T108->DIST-P108.
- `VF_SCENARIO_ASSUMED_TOPOLOGY` — future bounded synthetic-reference gate only;
  explicit/versioned/provenanced/reversible; never promoted to site truth.

## Recommended next gate (exactly one)

`VF-vNEXT-G18 — Generic scenario-topology overlay (VF_SCENARIO_ASSUMED_TOPOLOGY)`
capability, model Pro. First illustrative use-case: T108 -> DIST-P108 as an
explicit synthetic scenario assumption. Satisfies all seven selection criteria
(independent of T108->DIST-P108 authority; reduces whole-plant federation risk;
no SH-WTP runtime broadening; no plant truth required; CompositionGraph !=
execution order; coupling policy stays orchestration policy; no G4 redesign).
G18 NOT started in G17A.

## Frozen boundaries preserved

G4 Coordinator/ExecutableParticipant/BoundaryTransfer; G7 run control; G14A
projection (2 ports / 1 binding); G14B explicit_lagged + identity locking; G15
evaluator; G16 readiness artifact; T106/T108 equations/provenance; PIM unchanged.
No DIST-P108/T110/Line2/chemical/electrical/automation runtime; no new
ports/bindings/participants; no Gauss-Seidel/iterative/multirate policy; no G4
redesign.

## Authority unchanged

`vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`;
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## Regression

- G17A: 24 passed.
- Full suite: 2300 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, full_suite, checks_compile,
  checks_static_lint_type, checks_changed_files, checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G17A/01-workstream-independence-review.md`
