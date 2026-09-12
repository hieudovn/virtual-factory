# 05 — Archetype / Execution Mapping & Reference Mappings

## 5.1 Archetype vs execution mechanism (Issue #40 §F)

Frozen:

1. **Primary archetypes:** `continuous`, `batch`, `discrete`.
2. **Hybrid composition allowed:** a scope/workspace may combine archetypes.
3. **Archetype ≠ mandatory engine.** An archetype is a declarative
   classification, not a requirement to instantiate a separate engine per
   archetype.
4. **Execution mechanisms (composable, already present in repo):**
   - continuous dynamics — `core/` tick solver (`SimulationEngine`,
     `RuntimeAssembly`, `PlantGraph`);
   - discrete-event — `discrete/` kernel (`DiscreteSimulationEngine`,
     `FutureEventScheduler`, `DiscreteRunController/Service`);
   - state-machine / procedure — `assembly/` station contracts + operation
     execution, `AssemblyRuntimeState` lifecycle.
5. **A scope/workspace may use multiple mechanisms** where justified (e.g. an
   ASSY scope uses discrete-event line indexing + station lifecycle; a
   continuous scope uses tick solver + state logic).

Mapping of the three "archetypes" in the Issue #40 owner intent
(Continuous / Batch / Discrete) to mechanisms:

| Archetype | Dominant mechanism (existing) | Notes |
|---|---|---|
| continuous | `core/` tick solver | compressor / continuous MVP / SH WTP (logical) |
| discrete | `discrete/` event kernel (+ `assembly/` runtime) | ASSY line indexing, generic discrete demo |
| batch | state-machine / procedure over continuous or discrete primitives | no separate batch engine; composed from existing mechanisms |

## 5.2 Reference mapping — TIPA (verified, no invention)

```
Workspace:            TIPA
└─ Scope:             ASSY
   ├─ Scope:          ASSY-SL01 (hydraulic)
   ├─ Scope:          ASSY-SL02 (hydraulic)
   ├─ Scope:          ASSY-SL03 (hydraulic)
   ├─ Scope:          ASSY-SL04 (thermal)
   ├─ Scope:          ASSY-SL05 (thermal)
   └─ Scope:          ASSY-SL06 (thermal)
      └─ Objects (per sub-line scope): AP01..AP06 stations, SSO2/RSO2 sources,
         shared buffer, carriers, WIP, final-quality gate, finished/rework sinks
```

Repo evidence: `sub_line_identity.py` (TIPA → ASSY → 6 sub-lines),
`demo_composition.py` (6 per-sub-line contexts over `AssyLineRuntime`),
`tipa.py` + `line_runtime.py` (AP01..06, WIP, carrier objects).

Mapping is **lossless** — no flattening, no rename of `ASSY-SLxx`, no rewrite of
`AssyLineRuntime`. `ASSY-SLxx` are child scopes, not "six lines" and not
workspaces.

## 5.3 Reference mapping — SH WTP (conceptual; no invented topology)

```
Workspace:            SH-WTP
├─ Scope (illustrative): AREA-SHW-LINE1  (or a unit scope, e.g. UNIT-SHW-L1-T106)
│  └─ Objects (illustrative): equipment/signal objects for that area/unit
├─ Scope (illustrative): AREA-SHW-CHEMICAL
└─ … (other areas/units as nested scopes)
```

Rules applied:

- SH WTP maps to the **same structural model** with **no special-case
  architecture**: Workspace → (nested) process-area/unit Scopes → equipment
  Objects.
- Only **generic/illustrative scope examples** are used where plant truth is
  not yet authoritative; they are labeled as such. No unverified SH WTP
  physical topology is invented here (the authoritative topology remains
  PIM-owned, `SHW-PIM-VF-EXPORT-v0.1`).
- SH WTP scope identity is VF structural identity, distinct from PIM canonical
  ids (`AREA-SHW-*`, `UNIT-SHW-*`) which VF consumes read-only.

## 5.4 Anti-risks checked (Issue #40 "critical risks")

- Confusing Workspace with Scope → prevented (definitions §02; TIPA=Workspace, ASSY=Scope).
- Flattening plant hierarchy into workspaces → prevented (scopes nest under ONE workspace).
- Coupling scope identity to UI routes/labels → prevented (identity stable, UI is presentation selector).
- Coupling scope identity to PIM canonical identity → prevented (separate axes).
- Forcing every scope to own an engine → prevented (container scopes allowed).
- Second ASSY runtime/composition engine → prevented (reuse `AssyLineRuntime` only).
- Standalone vs federated divergence → prevented (same domain runtime).
- Graph connectivity as containment → prevented (hierarchy vs graph axes).
- ASSY-only design failing Continuous/Batch → prevented (archetypes are labels over shared mechanisms).
