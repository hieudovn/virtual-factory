# 03 — Run Lifecycle & Parent/Child Run Relationship (Issue #41 §B, §C)

## 3.1 Common platform run lifecycle (frozen at contract level)

The lifecycle is defined over **runs**; `pause`/`resume`/`step` are
scope-execution actions, `create`/`start`/`stop` are orchestration commands.

```text
        ┌─────────────┐
        │  validate/  │  readiness precondition (config + semantic pins + compatibility)
        │  readiness  │
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │   create /  │  allocate run identity + run context (workspace-level orchestration)
        │  initialize │
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │   start /   │  begin execution (child scopes enter their own run state)
        │     run     │
        └──────┬──────┘
               ▼
        ┌─────────────┐      ┌──────────────┐
        │   step(s)   │◄────►│ pause / resume │  scope-level execution actions
        └──────┬──────┘      └──────────────┘
               ▼
        ┌─────────────┐
        │ stop / end  │  terminal success/failure/abort
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │    reset /  │  discard run state; return to validated/config baseline
        │   restart   │  (replay = deterministic re-execution, NOT reset)
        └─────────────┘
```

### Lifecycle operation classification

| Operation | Level | Notes |
|---|---|---|
| validate/readiness | Workspace orchestration | Config, semantic-source pins, compatibility (PH00), boundary bindings. |
| create/initialize | Workspace orchestration | Creates run context; child scopes initialize their runtimes. |
| start/run | Workspace orchestration | Begins coordinated advancement. |
| step | Scope execution | One advancement of an executable scope (tick / event / dwell-index). |
| pause / resume | Scope execution | Suspends/resumes a scope's advancement. |
| stop / end | Workspace orchestration | Terminal; policy-driven (success / failure / abort). |
| reset state | Workspace orchestration | Return the current executable runtime/composition to its defined initial/baseline state (explicit whether it remains inside an unstarted/current run context). |
| restart / new attempt | Workspace orchestration | After a run has produced execution history/results, a restart/new attempt requires a **distinct run identity or versioned child attempt identity**; provenance histories must remain distinguishable. |
| replay | Contract-level | A new deterministic execution derived from pinned prior inputs — **not** a mutation of the historical run record (distinct from reset/snapshot restore; storage deferred). |
| failure/degraded/abort | Boundary | Policy at contract level; implementation deferred. |

No persistence/history warehouse is designed here.

## 3.2 Parent/child run relationship

1. **One workspace run owns/contains child run contexts.** A workspace run has a
   `run_id`; each participating executable scope has a child run context with a
   **child run identity** (`scope_id` + `run_id` scoped), independently
   addressable while participating.
2. **Child join/leave/start/stop** follow the parent lifecycle. Participation,
   isolation, degraded operation, quarantine, fail-fast, and fail-continue are
   **declared run/composition policies**. A failed/degraded/excluded scope may
   stop advancing its domain runtime while still receiving/emitting required
   status/coordination/physical/information boundary data per declared policy.
   No universal rule says a faulted scope receives zero boundary exchanges;
   `AssyDemoComposition` fault-exclusion remains demo evidence only, not
   platform failure semantics.
3. **Container-only scopes** participate structurally (grouping) but have no run
   context of their own and no simulation runtime state.
4. **Failure propagation policy** is declared at contract level: a child failure
   is surfaced to the coordinator; the run's terminal state (fail-fast vs
   degraded-continue) is a declared policy, not an implementation here.
5. **Independent addressability while federated:** a child run context remains
   inspectable (snapshot/status) during a parent run, without being independently
   executable outside the parent's declared interface.

## 3.3 Conformance with existing repo evidence

- `discrete/` already encodes a compatible lifecycle
  (`CREATED → READY → RUNNING/PAUSED → COMPLETED/STOPPED/FAILED`) with a
  service façade owning one run — a precedent for the platform lifecycle, not a
  replacement for it.
- `AssyDemoComposition.reset()/step_all()/snapshot()` demonstrate create/step/
  inspect over six isolated executable child contexts; `demo_step_number` is a
  presentation clock, not a synchronization guarantee.
