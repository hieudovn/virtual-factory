# SA REVIEW INBOX

Task: VF-ARCH-01-C01
Status: READY FOR SA REVIEW (C01: structural-contract contradictions + overclaims corrected)
Parent: Issue #39 VF-vNEXT-ARCH

Gate type:
Architecture / design gate — documentation & evidence only (no production
implementation). C01 correction gate for Issue #40.

Canonical baseline:
main @ f5261c8ca18cd4e01779c0274b55270ba028b4e5

Frozen structural model (C01-consistent):
VF Platform -> Workspace -> Simulation Scope -> Simulation Object
- containment hierarchy = tree; connectivity/dependency = graph (independent).
- Simulation Scope = structural/addressable boundary; may be EXECUTABLE
  (runtime/execution boundary) or CONTAINER-ONLY (groups child scopes/objects).
  executability = capability, NOT a type default.
- standalone/federated contract applies to executable-capable scopes only.
- Workspace = deployment/identity/config/composition boundary; NO single-engine
  implication; legacy runtime.engine = compatibility/default/profile field
  (ARCH-02 decides runtime-composition semantics).
- runtime state isolated per scope (executable scopes).

Identity invariants:
- workspace_id / scope_id / scope path / object identity = VF structural
  identity, SEPARATE from outputs.namespace and PIM canonical ids.
- child scope id unique within parent boundary; object id unique within owning
  scope; identity independent of UI labels.

Archetype vs execution:
- continuous / batch / discrete = archetype labels (hybrid allowed), NOT
  mandatory engines; mechanisms composable (core tick, discrete event,
  assembly state-machine).

Reference mappings:
- TIPA (verified, lossless): TIPA Workspace -> ASSY Scope -> ASSY-SL01..06
  child Scopes -> AP/WIP/carrier Objects. AssyLineRuntime NOT redesigned.
- SH WTP (conceptual, no invented topology): SH-WTP Workspace -> area/unit
  Scopes -> equipment Objects. No special-case architecture.

C01 corrections applied:
- Simulation Scope executability semantics made consistent (no more
  "every scope has execution/runtime boundary" contradiction).
- Workspace definition no longer implies a single engine.
- AssyDemoComposition downgraded to reusable composition pattern/precedent;
  vNext TIPA->ASSY federation remains an implementation target.
- Migration dispositions expressed as candidate directions; final disposition
  deferred to later gates.

Non-decisions deferred to ARCH-02+: clock sync, port payloads, coordinator
scheduling, observation/event schema, provenance impl, capability registry,
UI impl, semantic binding, SH WTP runtime, ASSY refactor, frontend migration.

Production code changed: NO
ARCH-02 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-01.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-01/ (6 files: 01…06; 02/03/04/06
C01-refined)



