# VF-vNEXT-G4 · Evidence 01 — Repo-first discovery + changed files

## 1. Issue scope (Issue #49)

Composition Graph + Coordinator + Typed Boundary Ports. Coordinator is a
composition service, not a domain engine. Containment stays a tree; composition/
connectivity is a separate graph that may contain cycles. Exchange only through
declared typed boundary ports via detached/immutable staged transfers; no direct
cross-scope state mutation; deterministic ordering independent of declaration/
registration order; container-only scopes own no runtime participant; no
fabricated PIM canonical identity; no false rollback claims; no AssyLineRuntime
rewrite; no G5+.

## 2. Repo-first classification (accepted G3 head)

| Seam | Class | Decision |
|---|---|---|
| G1 `workspace/` (StructuralPath, SimulationScope, ScopeMode, Workspace.resolve_scope) | REUSE | graph endpoints resolve through G1 identity; container-only guard via ScopeMode |
| G2 `provenance/` (RunContextV2/ProvenanceV2) | REFERENCE | transfer carries workspace/run id where available; no second run/provenance model |
| G3 Observation/Event/Alarm | UNCHANGED | downstream facts; coordinator never turns telemetry into authority |
| `core/ports.py` (configured model Port) | LEGACY-REFERENCE | distinct meaning from cross-scope boundary ports; NOT collapsed |
| `core/plant_graph.py` (intra-plant graph) | LEGACY-REFERENCE | distinct composition-level seam used; not replaced |
| `core/engine_contract.py` (SimulationEngineProtocol) | LEGACY-REFERENCE | current runtime usage; NOT a universal timestep/cardinality contract |
| `assembly/demo_composition.py` (six isolated runtimes + demo-step policy) | LEGACY-REFERENCE | strong isolation precedent; demo policy, not plant truth |
| `discrete/clock.py` (local scheduler-owned time) | LEGACY-REFERENCE | proves per-scope cadence independence |

## 3. Reuse / adapt / new / defer

- NEW generic: `src/virtual_factory/composition/` (ports, graph, transfer,
  participant, coordinator) — distinct composition-level seam.
- REUSE (read-only): G1 `workspace` identity/model; G2 identity context.
- DEFER: G5 ASSY federation, G6 UI, G7 run-control, G8, G9 binding, G10 SH-WTP,
  material/energy schemas, numerical solver, historian.

## 4. Changed files (15)

Production (6): `src/virtual_factory/composition/{__init__,ports,graph,transfer,
participant,coordinator}.py` (new).

Tests (4): `tests/test_composition_{ports,graph,transfer,coordinator}.py` (new).

Harness (5): `.ai-harness/tasks/VF-vNEXT-G4.json`, `.ai-harness/sa-review/
CURRENT.md`, `.ai-harness/sa-review/reports/VF-vNEXT-G4.md`,
`.ai-harness/sa-review/evidence/VF-vNEXT-G4/` (01…08).

No forbidden file changed (workspace, provenance, observation, telemetry,
discrete, assembly, core, ui, integration, protocols, equipment untouched).
