# SA REVIEW INBOX

Task: VF-vNEXT-G6
Status: READY FOR SA REVIEW (Shared Hierarchical UI Primitives)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate after G5)
Prerequisite: Issue #50 accepted as completed; G1–G5 contracts authoritative

Gate type:
Accelerated implementation gate — Implement Shared Hierarchical UI Primitives (G6), per Issue #51

Architecture baseline:
ARCH-01..06 accepted; G1–G5 contracts authoritative
Required base (branch point): d1419cec3bd87d283ee9dcb03c412479a794359d (accepted G5-C01 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive, inside src/virtual_factory/ui/):
- hierarchy.py: pure read-only projection/serialization of the G1
  Workspace/Scope tree (workspace_to_dict / simulation_scope_to_dict) +
  path-qualified selection context (structural_context / root_only_context);
  canonical StructuralPath preserved; no second model; no runtime mutation.
- api.py (additive): read-only GET endpoints /api/ui/hierarchy,
  /api/ui/context, /api/ui/context/continuous (no run-control semantics).
- static/hierarchy.js: shared, domain-agnostic primitives
  (renderNavigator + renderBreadcrumb); container vs executable from G1
  capability booleans; path-qualified selection; expand/collapse.
- static/assy_context.js: additive ASSY seam — renders the canonical hierarchy
  and binds executable ASSY-SLxx selection to the EXISTING Frame A single-click
  selection path (never resets/reconstructs a runtime).
- static/continuous_context.js: additive continuous seam — truthful ROOT-ONLY
  context (workspace id, empty hierarchy; no invented plant structure).
- index.html / assy_demo.html: additive context mounts + script tags.
  styles.css / assy_demo.css: additive styles. app.js and assy_demo.js are NOT
  modified (ASSY/continuous domain rendering preserved).

Frozen invariants preserved:
- Hierarchy derived from G1 StructuralPath only; canonical paths preserved;
  bare local ids are display labels only.
- Inspector = object-centric; Monitoring = scope-centric; object selection is
  never fabricated; container-only never implies execution
  (executable_controls_implied=False).
- ASSY UI and continuous dashboard not rewritten; no framework migration;
  no PIM identity fabrication; no runtime mutation through the model.
- No G7 run-control/replay/orchestration; no G8+/G9/G10.

Inspector / Monitoring + capability (evidence 05):
- Object context only when an object is actually selected and resolvable in the
  selected scope; scope context never fabricates an object; changing scope
  never silently changes structural ownership.

Compatibility / no redesign (evidence 04):
- Existing dashboard routes/APIs, ASSY routes/behavior, static references all
  preserved; app.js / assy_demo.js untouched; UI/API + S04B gating tests green.

STOP-condition assessment: none triggered (no new UX/navigation model; truthful
continuous root-only context; ASSY additively adapted not rewritten; G1 intact;
no new lifecycle semantics; no G7/G8+; no framework migration).

Test / regression results (evidence 07):
- New G6 tests: 26 passed.
- Existing UI/API + S04B gating tests: 134 passed.
- G5 federation tests: 26 passed.
- G4 composition tests: 56 passed.
- G1 workspace: 32 passed.
- G2 provenance: 36 passed.
- G3 Observation/Event/Alarm (+ M5 + alarm_manager): 328 passed.
- Complete ASSY regression oracle: 354 passed.
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1901 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Deferred (NOT implemented): G7 run-control/UI/API/replay policy, G8+, G9
semantic binding, G10 SH-WTP runtime, any ASSY/continuous UI rewrite, any
frontend framework migration.

STOP conditions: none triggered.

G7 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G6.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G6/ (7 files: 01 repo-first discovery +
scope; 02 shared context model + projection; 03 navigator + breadcrumb
primitives; 04 ASSY + continuous integration; 05 inspector/monitoring +
capability; 06 stop assessment; 07 tests + regression results)






