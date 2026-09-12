# 02 — Runtime Ownership Model (Issue #41 §A)

Non-overlapping ownership with explicit may/may-not-mutate. Inherits ARCH-01
(executable vs container-only scope; runtime state isolated per executable scope).

| Component | Owns | May mutate | May NOT mutate |
|---|---|---|---|
| **Workspace host / composition context** | Workspace identity, config refs, scenario refs, `outputs.namespace`, semantic-source pins, composition of child scopes | Workspace-level lifecycle/composition commands; child scope lifecycle commands (via declared interfaces only) | Child scope internal runtime state; domain semantics; PIM semantics |
| **Executable Simulation Scope runtime** | Its own runtime/execution boundary and domain state | Its own state via its domain runtime | Other scopes' state; workspace identity; PIM canonical ids |
| **Container-only scope** | Structural/configuration/composition state (grouping of child scopes/objects) | Its structural/composition membership | Simulation runtime state (it owns none); child domain state |
| **Coordinator / composition service** | Run/composition context, lifecycle coordination, synchronization/exchange boundaries, ordering, failure propagation, outcome collection | Lifecycle commands, sequencing of declared exchanges, run-level status | Domain state (AP/WIP/quality, pump/tank physics, recipe/phase rules, control logic); PIM semantics; monitoring/dashboard state |
| **Domain engine / runtime** | Domain physics/business semantics of one scope | Its own runtime state | Other scopes; composition/coordination state |
| **Run context** | The identity/state of one run (run_id, participation, phase) | Run lifecycle phase, participation metadata | Domain state; PIM semantics |
| **Scenario context** | Scenario definitions/actions bound to a run | Applies its declared actions at its authorized points | Domain truth beyond declared actions; PIM semantics |

## 2.1 Ownership invariants

1. Coordinator owns **composition**, not **domain**. It is **not** a second
   domain engine.
2. An executable scope owns its **own domain state** exclusively; the parent and
   coordinator access it only through declared lifecycle/runtime interfaces.
3. Container-only scopes own **no simulation runtime state** (ARCH-01/C02).
4. PIM remains semantic authority; runtime composition does **not** invent
   canonical semantic identity.
5. Monitoring/dashboard/telemetry state is **not** owned by the coordinator.

## 2.2 Non-overlap check

The seven components have disjoint ownership axes: workspace (identity/config),
executable scope (domain runtime), container-only scope (structural grouping),
coordinator (composition), domain engine (domain physics), run context
(run identity), scenario context (scenario actions). No component is a synonym
or a superset of another.
