# 06 — Migration Impact, Frozen Decisions & Non-decisions

## 6.1 Migration impact of existing ASSY-specific abstractions (Issue #40 §H)

> C01: ARCH-01 freezes **structural semantics and migration direction only**.
> The dispositions below are **candidate directions**, not final implementation
> design. Final disposition (reuse / adapt / generalize / retain) is confirmed
> in later implementation/migration gates.

| Existing abstraction | Candidate disposition (direction) | Rationale |
|---|---|---|
| `AssyProductionLineIdentity` / `AssySubLineIdentity` (`sub_line_identity.py`) | **Likely adapter/wrapper target** for the generic Scope identity contract (semantics already match Workspace→Scope→child Scope). No rename of `ASSY-SLxx`. | Already encodes the required hierarchy. |
| `AssyDemoComposition` + `AssyDemoContext` (`demo_composition.py`) | **Reference pattern / strong precedent** for standalone+federated scope composition (not a completed vNext federation). | Composes 6 isolated contexts over one runtime; composition coordinates without rewriting child semantics. |
| `AssyLineRuntime` (`line_runtime.py`) | **Reuse target — NOT redesigned** (frozen intent). Implementation disposition deferred to a later migration gate. | Frozen: single source of simulation truth. |
| `StationContract` / `Capabilities` (`station_contracts.py`) | **Candidate for reuse** (later generalization into scope-object capability contracts is deferred). | Already capability-driven. |
| `build_tipa_topology()` (`tipa.py`) | **Retained as legacy/reference** single-line topology; not the vNext structural authority. | Hard-coded; superseded by composition + per-sub-line runtime. |
| `PlantConfig` + `PlantGraph` + `RuntimeAssembly` (`core/`) | **Candidate for reuse** (continuous archetype); scope/workspace identity extension deferred to later gates. | Generic, config-driven. |
| `discrete/` kernel | **Candidate for reuse** (discrete archetype). | Domain-neutral. |
| `simulators/wtp` (VF-1), `simulators/vf2` (VF-2) | **Retained as legacy/reference** (PH00 B7); not extended. | Out-of-platform. |

No refactor or implementation is performed in this gate.

## 6.2 Frozen decisions

1. Structural model: **Platform → Workspace → Simulation Scope → Simulation Object**.
2. Containment hierarchy is a **tree** (management/navigation/addressing).
3. Connectivity/dependency is a **graph**, independent of containment.
4. `workspace_id`, `scope_id`, hierarchical scope path, and object identity are
   VF structural identity — **distinct** from `outputs.namespace` and from PIM
   canonical ids.
5. An **executable-capable scope** may be run **standalone or federated** with
   identical domain semantics; federation only adds host/composition context.
   Container-only scopes are not subject to this contract.
6. Runtime state is **isolated per executable scope**; container-only scopes
   have no simulation runtime state of their own. Cross-scope interaction is
   only through future declared contracts/ports (not implemented here).
7. Archetypes `continuous`/`batch`/`discrete` are **labels**, not mandatory
   engines; execution mechanisms (tick solver, discrete-event, state-machine)
   are composable.
8. TIPA = Workspace; ASSY = Scope; ASSY-SL01..06 = child Scopes; AP/WIP/carrier
   = Objects. (Verified, lossless.)
9. SH WTP = Workspace; areas/units = nested Scopes; equipment = Objects.
   (Conceptual; no invented topology.)
10. `AssyLineRuntime` is **not redesigned**.

## 6.3 Explicit non-decisions (deferred to ARCH-02+)

The following are **deliberately not decided** in this gate:

1. Clock / synchronization algorithm across scopes.
2. Typed boundary port payloads.
3. Coordinator scheduling across scopes.
4. Observation / event schema.
5. Provenance implementation.
6. Capability registry schema.
7. UI component implementation.
8. Semantic loader / binding.
9. SH WTP runtime / domain models.
10. ASSY runtime refactor.
11. Frontend framework migration.

## 6.4 STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| ASSY semantics cannot map without breaking domain behavior | **NOT triggered** — lossless mapping (§05); `AssyLineRuntime` reused. |
| Competing generic hierarchy abstraction already in repo | **NOT triggered** — no production Workspace/Scope/`workspace_id` in `src/` (grep empty; only PH00 proposal). |
| Scope identity not separable from PIM canonical id / output namespace | **NOT triggered** — three distinct axes (§03). |
| Standalone/federated reuse requires domain-runtime rewrite | **NOT triggered** — a reusable composition pattern exists (`AssyDemoComposition` over one `AssyLineRuntime`); no rewrite required. Full vNext federation remains an implementation target. |
| Structural decision requires ARCH-02 runtime sync/port semantics | **NOT triggered** — only structural boundary frozen; ports/sync explicitly deferred. |

**Conclusion: no STOP condition triggered.**
