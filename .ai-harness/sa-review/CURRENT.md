# SA REVIEW INBOX

Task: VF-ARCH-01
Status: READY FOR SA REVIEW (platform structural model frozen)
Parent: Issue #39 VF-vNEXT-ARCH

Gate type:
Architecture / design gate — documentation & evidence only (no production
implementation)

Canonical baseline:
main @ f5261c8ca18cd4e01779c0274b55270ba028b4e5

Frozen structural model:
VF Platform -> Workspace -> Simulation Scope -> Simulation Object
- containment hierarchy = tree (management/navigation/addressing);
- connectivity/dependency = graph (independent of containment);
- scope may be standalone or federated with identical domain semantics;
- runtime state isolated per scope (cross-scope via future declared contracts/ports).

Identity invariants:
- workspace_id / scope_id / scope path / object identity are VF structural
  identity, SEPARATE from outputs.namespace and PIM canonical ids.
- child scope id unique within its parent boundary; object id unique within its
  owning scope; identity independent of UI labels.

Archetype vs execution:
- continuous / batch / discrete = archetype labels (hybrid allowed), NOT
  mandatory separate engines.
- execution mechanisms composable: core/ tick solver, discrete/ event kernel,
  assembly/ state-machine/station contracts.

Reference mappings:
- TIPA (verified, lossless): TIPA Workspace -> ASSY Scope -> ASSY-SL01..06
  child Scopes -> AP/WIP/carrier Objects. AssyLineRuntime NOT redesigned.
- SH WTP (conceptual, no invented topology): SH-WTP Workspace -> area/unit
  Scopes -> equipment Objects. No special-case architecture.

Repo-first evidence: no production Workspace/Scope/workspace_id in src/ (only
PH00 proposal) => no competing abstraction. AssyDemoComposition already
demonstrates standalone+federated over one AssyLineRuntime.

Non-decisions deferred to ARCH-02+: clock sync, port payloads, coordinator
scheduling, observation/event schema, provenance impl, capability registry,
UI impl, semantic binding, SH WTP runtime, ASSY refactor, frontend migration.

Production code changed: NO
ARCH-02 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-01.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-01/ (6 files: 01…06)



