# 02 — Terminology & Definitions (mutually exclusive)

Precise, non-overlapping definitions with explicit anti-definitions
(Issue #40 §A).

## 2.1 Definitions

| Term | Definition | Anti-definition (what it is NOT) |
|---|---|---|
| **Platform** | The Virtual Factory product: shared kernels (`core/`, `discrete/`), reusable domain models (`equipment/`, `control/`, `instrumentation/`, `telemetry/`, `protocols/`, `observation/`), gateway/integration layers, and the workspace/scope structural contract. A single runtime product that hosts many workspaces. | NOT a workspace. NOT a plant. NOT a simulation. NOT an engine. NOT a PIM semantic authority. |
| **Workspace** | A top-level, independently addressable deployment/identity container that groups related simulation scopes and carries the workspace manifest (identity, engine selection, config references, scenarios, output namespace, semantic sources). Examples: `TIPA`, `SH-WTP`, compressor-benchmark, continuous-mvp. | NOT a plant (a plant is semantic/physical; a workspace is a VF runtime grouping). NOT a simulation scope (a scope executes; a workspace is the top-level grouping). NOT a canonical semantic ID. NOT a UI route. |
| **Simulation Scope** | A structurally addressable unit of simulation within a workspace that has an execution/runtime boundary and may itself contain child scopes and/or objects. It is the unit of standalone or federated execution and of runtime-state isolation. Examples: `ASSY` (child scope of TIPA), `ASSY-SL01..06` (child scopes of ASSY), a process area/unit in SH WTP. | NOT a workspace (it is nested under one). NOT a physical object. NOT a station. NOT a scenario. NOT a UI view. |
| **Simulation Object** | A leaf runtime entity that participates in simulation: equipment, station, WIP, carrier, sensor, controller, actuator, source, buffer, gate, sink. An object belongs to exactly one scope (containment) but may have many graph relationships. | NOT a scope (it cannot contain child scopes). NOT a workspace. NOT a process area. |
| **Archetype** | A classification of the dominant simulation semantics of a scope/workspace: `continuous`, `batch`, `discrete` (hybrid allowed). A declarative label, not an engine. | NOT an engine. NOT a scheduler. NOT an execution mechanism. NOT a fidelity level. |
| **Execution paradigm / mechanism** | The actual computation used to advance a scope: continuous dynamics (tick solver), state-machine/procedure, discrete-event scheduling — possibly multiple within one scope. | NOT an archetype label. NOT a mandatory per-archetype engine. |
| **Composition relation** | A containment/parenting relationship: a scope contains child scopes and/or objects; a workspace contains scopes. Forms the management/navigation tree. One parent per child. | NOT a process/material flow. NOT a dependency. NOT a port connection. |
| **Connectivity / dependency relation** | A graph relationship between objects/scopes representing process, material, energy, information, utility, dependency, or coordination links. Many per node; independent of containment. | NOT containment. NOT navigation parent/child. NOT a rename. |

## 2.2 Identity terms (non-overlapping)

| Term | Meaning | Boundary |
|---|---|---|
| `workspace_id` | Stable logical VF workspace identity (e.g. `TIPA`, `SH-WTP`). | Globally unique within the platform; never derived from plant id; never a PIM semantic id. |
| `scope_id` | Stable identity of a simulation scope (e.g. `ASSY`, `ASSY-SL01`). | Unique within its parent workspace/scope boundary; stable independent of UI labels. |
| Hierarchical scope path | Deterministic `parent/…/child` path of scope ids from the workspace root. | Navigation/addressing only; not a canonical semantic id; not a runtime state key. |
| Local object/runtime identity | Object id and runtime-local state keys, unique within the owning scope. | Scoped to the owning scope; not globally unique; never renamed to canonical ids. |
| `outputs.namespace` | Protocol/path-safe token deterministically bound to `workspace_id` (PH00 §06). | Distinct from `workspace_id` and from scope path (string equality not required). |
| PIM canonical identity | PIM-owned semantic ids (`PLANT-SHW`, `AREA-SHW-*`, `SIG-SHW-*`, …). | Owned by PIM; VF consumes read-only; VF structural identity must not replace it. |

## 2.3 Sufficiency check

These definitions cover the Issue #40 §A list (Platform, Workspace, Simulation
Scope, Simulation Object, Archetype, Execution paradigm, Composition relation,
Connectivity/dependency relation) with mutually exclusive semantics and
explicit anti-definitions. No term is a synonym for another.
