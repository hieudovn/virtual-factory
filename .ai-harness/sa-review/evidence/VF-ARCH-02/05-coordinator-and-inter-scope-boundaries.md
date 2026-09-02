# 05 — Coordinator Responsibilities & Inter-scope Boundaries (Issue #41 §F, §G, §H)

## 5.1 Composition Coordinator — responsibilities

The coordinator owns **composition**, never domain:

- Resolve the executable scopes participating in a run.
- Maintain the composition/run context (run identity, participation, phase).
- Coordinate lifecycle commands across child scopes.
- Establish synchronization/exchange boundaries.
- Sequence declared inter-scope exchanges at coordination points.
- Commit/collect execution outcomes at coordination points.
- Propagate failures/status per declared policy.
- Preserve deterministic ordering (evidence 04).

## 5.2 Coordinator — explicit anti-responsibilities (never owns)

| Not owned | Why |
|---|---|
| AP/WIP/quality semantics | Domain runtime (`AssyLineRuntime` + station contracts) |
| Pump/tank physics | Equipment models (`equipment/*`) |
| Recipe/phase business rules | Scenario/domain layer |
| Domain control logic | Controllers/actuators (`control/`, `instrumentation/`) |
| PIM semantics | PIM (canonical identity/vocabulary authority) |
| Monitoring/dashboard state | Telemetry/observation layer (target data-flow: Runtime State → Observation → projections) |

**Frozen:** the coordinator is **not** a God Engine and **not** a second domain
engine. It does not compute domain truth.

## 5.3 Typed inter-scope boundary contract (categories + ownership, not schemas)

| Category | Producer ↔ Consumer | Direction | Read/write authority (C01) |
|---|---|---|---|
| Material / physical flow | source scope ↔ sink scope | directional, **or** bidirectional/coupled, **or** resolved at a coordination boundary (per declared contract) | producer publishes/exposes output; consumer consumes boundary input and updates **its own** state via its own runtime semantics |
| Utility / energy flow | source scope ↔ sink scope | directional, **or** bidirectional/coupled (per declared contract) | same authority semantics as material flow |
| Information / observation flow | producing scope → observing scope | directed (aligned with Runtime State → Observation → projections) | publish/subscribe/read-only where appropriate |
| Coordination / event flow | coordinator ↔ scopes | bidirectional (lifecycle/coordination only) | coordinator commands; scopes report status |

Boundary contract rules (C01):

1. **No direct cross-scope mutation:** one scope may never directly mutate
   another scope's internal runtime state.
2. **Publish/consume:** a producing scope publishes/exposes an output through a
   declared boundary; the consuming scope consumes that boundary input and uses
   it to update **its own** runtime/domain state through its own runtime
   semantics.
3. **Coordinator is transport, not authority:** the coordinator/boundary
   infrastructure transfers, validates, and exchanges values; it does **not**
   become domain-state authority.
4. **Coupling shape is per-contract:** physical/material/utility coupling may be
   directional, bidirectional/coupled, or resolved at a coordination boundary
   depending on the declared contract — not forced into a simple
   source→sink producer/consumer model.
5. Boundary validation expectations: bindings are validated at readiness
   (missing/incompatible binding → run invalid, fail-closed).
6. Time/sync metadata (conceptual): a boundary exchange carries the coordination
   point / source scope time reference (details deferred).
7. **Identity (C01-2):** VF **structural identity** (`workspace_id`/`scope_id`/
   object or runtime identity) is authoritative for VF runtime
   addressing/routing/ownership. A boundary/port **MAY carry read-only PIM
   semantic binding metadata** where needed for validation, traceability,
   provenance, compatibility, or integration — but PIM canonical identity must
   **not** become the VF runtime routing key unless a later explicit contract
   says so. Structural identity and PIM semantic identity remain **distinct
   axes**; PIM canonical identity is never replaced or invented by VF.
   Boundaries are not coupled to UI routes/labels.
8. Failure behavior: missing/incompatible binding → declared failure (not silent
   skip).

> `core/ports.py` `Port` (physical/measurement/signal/command/publication) is
> **evidence**, not an assumed-sufficient vNext payload. Final payload/schema
> classes are deferred to implementation gates.

## 5.4 Isolation & mutation invariants (frozen)

1. One executable scope may **not** mutate another scope's internal state directly.
2. Parent/coordinator may **not** reach into child domain state except through
   declared lifecycle/runtime interfaces.
3. **Boundary exchange is the only cross-scope data/flow path.**
4. Container-only scopes have **no simulation runtime state** to mutate.
5. UI/API clients must **not** bypass composition boundaries (no out-of-band
   state mutation).
