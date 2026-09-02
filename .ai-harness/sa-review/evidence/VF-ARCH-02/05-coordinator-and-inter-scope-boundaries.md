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

| Category | Producer → Consumer | Direction | Read/write authority |
|---|---|---|---|
| Material / physical flow | source scope → sink scope | directed | producer writes at exchange; consumer reads only |
| Utility / energy flow | source scope → sink scope | directed | producer writes; consumer reads only |
| Information / observation flow | producing scope → observing scope | directed (aligned with Runtime State → Observation → projections) | producer publishes; consumer subscribes read-only |
| Coordination / event flow | coordinator ↔ scopes | bidirectional (lifecycle/coordination only) | coordinator commands; scopes report status |

Boundary contract rules:

1. Producer/consumer ownership is declared per boundary; no implicit coupling.
2. Directionality is explicit per category.
3. Read/write authority: cross-scope mutation is forbidden; only boundary
   exchange is a data/flow path.
4. Boundary validation expectations: bindings are validated at readiness
   (missing/incompatible binding → run invalid, fail-closed).
5. Time/sync metadata (conceptual): a boundary exchange carries the coordination
   point / source scope time reference (details deferred).
6. **Identity:** a port/boundary references **structural scope/object identity**
   (`scope_id`/object id), never PIM canonical semantic identity, and is not
   coupled to UI routes/labels. PIM canonical ids remain semantic-side, consumed
   read-only elsewhere.
7. Failure behavior: missing/incompatible binding → declared failure (not silent
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
