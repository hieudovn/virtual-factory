# SA REVIEW INBOX

Task: VF-ARCH-06-C01
Status: READY FOR SA REVIEW (C01: executable scope = execution/runtime boundary, not 1 scope = 1 engine)
Parent: Issue #39 VF-vNEXT-ARCH (prerequisite: ARCH-05 #44 CLOSED as completed)

Gate type:
Architecture / design / roadmap gate — documentation & evidence only (no
production implementation)

Architecture baseline:
ARCH-01 @ feature/vf-arch-01 41903e186e96a05726483e4a17b9ac2d9cd56655
ARCH-02 @ feature/vf-arch-02 40454487acb4d5667872168a88c8b742c29cb975
ARCH-03 @ feature/vf-arch-03 392401bdfaf1ee2acf4ebcd204dbcfa419359e4c
ARCH-04 @ feature/vf-arch-04 d5c155b636481017a25596ace5e09062b88bc450
ARCH-05 @ feature/vf-arch-05 8fafa11904b66c25662db88ee8d924f64bdb29e7
Production baseline: canonical main @ f5261c8 (unchanged; not merged)

Frozen decisions:
- SH WTP = Workspace -> process-area/unit Scopes -> equipment/instrument Objects
  (illustrative scope names only; no site truth; fidelity ceiling logical_only).
- Continuous/Batch/Discrete = archetypes, not one-engine-per-workspace;
  runtime.engine: continuous_process (B3).
- Shared core owns execution/composition framework; SH-WTP physics is a future
  domain model, not platform architecture. An executable Simulation Scope owns
  an execution/runtime boundary (one or more execution mechanisms per scope
  contract — continuous/state-machine/discrete/hybrid); SimulationEngine /
  runtime.engine: continuous_process are the current continuous
  implementation/profile precedent (PH00 descriptor), NOT a universal
  1 scope = 1 engine rule; engine cardinality/type is an implementation/profile
  concern.
- PIM = semantic authority; version/hash-pinned, fail-closed
  (semantic_binding.mode: required); VF read-only.
- Legacy WTP mini-engines (simulators/wtp, simulators/vf2) = reference/legacy ->
  future deprecation; not the target runtime (B7).
- Observation/Event/Capability/Readiness + Continuous UI map to ARCH-03/ARCH-04
  without fabricated truth (data_status=synthetic; Live Series != Historian).
- Ordered implementation roadmap G1..G10; one-gate-at-a-time; per-gate
  acceptance evidence; ASSY regression oracle + continuous/compressor baseline
  on EVERY gate.

Roadmap:
G1 Workspace/Scope Foundation; G2 Runtime Context + Provenance v2;
G3 Observation/Event/Alarm alignment; G4 Composition Graph + Coordinator +
Typed Ports; G5 TIPA/ASSY federation; G6 Shared hierarchical UI primitives;
G7 Hierarchical Scenario/Run Control; G8 VF Platform vNext Regression Baseline;
G9 Semantic Binding vNext; G10 Resume SH WTP runtime.

Architecture closure:
No unresolved platform-level architecture gap remains after ARCH-01..06.
Umbrella #39 may close after SA accepts ARCH-06; the implementation program
(G1..G10) becomes the next phase.

C01 corrections applied:
- Removed universal '1 executable scope = 1 SimulationEngine' assumption.
- Executable scope owns an execution/runtime boundary; may use one or more
  execution mechanisms per scope contract (continuous/state-machine/discrete/
  hybrid).
- SimulationEngine / runtime.engine: continuous_process = current continuous
  implementation/profile precedent (PH00 descriptor), NOT universal
  engine-cardinality rule.
- Consistency sweep removed residual 'engine at scope level' / 'exactly one
  engine per executable scope' wording across evidence 02/03/09/10 + report.
- G1-G10 roadmap, legacy WTP disposition, fidelity constraints, closure
  conclusion unchanged.

STOP conditions: none triggered.

Production code changed: NO
Implementation started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-06.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-06/ (10 files: 01…10)





