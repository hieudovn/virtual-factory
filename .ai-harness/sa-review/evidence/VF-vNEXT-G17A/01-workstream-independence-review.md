# VF-vNEXT-G17A — Post-G16 Platform Workstream Independence Review — Evidence

Gate: `VF-vNEXT-G17A` · Planning/review only. No runtime implementation.

## 1. Proven baseline under review

- VF base (required by Issue #68): `732decd68a02af6f0ee1de1e830631747a99d060`
  (accepted G16 head on `feature/vf-vnext-g16`).
- External PIM evidence reference: `d10049801a1eb022a7fa2e83badabefb92fb7412`.
- PIM verdict: `T108-DIST-EVIDENCE — STILL_INSUFFICIENT` →
  `UNIT-SHW-L1-T108 -> UNIT-SHW-DIST-P108` remains BLOCKED.

## 2. Repo state actually inspected

- `src/virtual_factory/composition/{graph,ports,transfer,participant,coordinator}.py`
  — G4 generic composition: CompositionGraph (separate from containment, cycles
  allowed), typed BoundaryPort, immutable detached BoundaryTransfer,
  mechanism-neutral ExecutableParticipant, deterministic fail-closed Coordinator.
- `src/virtual_factory/runcontrol/{targets,lifecycle,assy_bridge,continuous_bridge}.py`
  — G7 hierarchical run control: target resolution, RunLifecycleService
  (CREATED/RUNNING/PAUSED/STOPPED/FAILED), replay pins scenario_id + fresh run_id.
- `src/virtual_factory/federation/*` — G5 TIPA ASSY federation (6 sub-line
  participants, no cross-scope value exchange).
- `src/virtual_factory/shwtp/projection.py` — G14A F01 (2 ports + 1 binding, inert).
- `src/virtual_factory/shwtp/federation.py` — G14B explicit_lagged (2 participants,
  orchestration policy NOT on CompositionGraph).
- `src/virtual_factory/shwtp/evaluation.py` — G15 SH-WTP-specific evaluation trace.
- `configs/vnext/shwtp/shwtp_expansion_readiness.json` — G16 readiness (29 units;
  DIST-P108 NEXT_SLICE_CANDIDATE, now blocked).
- `src/virtual_factory/ui/{api.py,hierarchy.py,runtime_service.py}` + `static/` —
  continuous dashboard (charts), assy-demo, G6 hierarchy UI, G7 `/vnext/runs`,
  `/health`, `run_control_context.js`. No CompositionGraph visualization, no
  generic federation inspection surface.
- `src/virtual_factory/provenance/*` — G2 RunContextV2 immutable identity; G7
  replay over TIPA/continuous (federated replay not yet proven).

## 3. Workstream classification (23 records)

- CAN_PROCEED_INDEPENDENTLY (16): WS-01..WS-10, WS-13..WS-18.
- SHOULD_WAIT_FOR_RUNTIME_EXPANSION (2): WS-11 (multi-scope UI shell),
  WS-12 (alarms/events for simulation runtime).
- BLOCKED_BY_PIM_EVIDENCE (5): WS-19 (whole-plant), WS-20 (DIST-P108),
  WS-21 (T110), WS-22 (Line 2), WS-23 (chemical/electrical/automation).

Each record carries readiness, dependencies, plant-truth-required flag,
architecture-risk-if-done-now, rationale, priority, and future model (Flash/Pro).

## 4. Topology distinction (SA clarification applied)

- `PIM_AUTHORITATIVE_TOPOLOGY` — still BLOCKED for T108->DIST-P108; never
  fabricated, never inferred from names/descriptions/aggregates.
- `VF_SCENARIO_ASSUMED_TOPOLOGY` — may be considered for a future bounded
  synthetic-reference gate; explicit/versioned/provenanced/reversible; never
  promoted to site truth; never back-propagated into PIM/KG authority.

## 5. Recommended next gate (exactly one)

`VF-vNEXT-G18 — Generic scenario-topology overlay (VF_SCENARIO_ASSUMED_TOPOLOGY)`
capability, model Pro. First illustrative use-case: T108 -> DIST-P108 as an
explicit synthetic scenario assumption (NOT PIM-derived truth).

All seven selection criteria satisfied; five preservation constraints recorded.
G18 is NOT started in G17A.

## 6. Authority unchanged

`vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`;
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## 7. No runtime change proof (tests)

`tests/test_vnext_g17a_workstream_review.py` asserts:
- external PIM blocker reference + verdict + base exact;
- 23 workstreams, full records, exact classification counts (16/5/2);
- topology distinction + five scenario-assumption constraints;
- exactly one recommended next gate, all seven criteria satisfied;
- frozen G4/G7/G14A/G14B/G15 constants and structures unchanged:
  - `SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"`;
  - G14A F01 projection still 2 ports + 1 binding;
  - `SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"` etc.;
  - G4 Coordinator/BoundaryTransfer/CompositionGraph importable; RunState frozen;
  - ShwtpEvaluator / ShwtpFederationConfig importable; SH-WTP workspace builds.
