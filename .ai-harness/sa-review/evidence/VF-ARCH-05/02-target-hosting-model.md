# VF-ARCH-05 · Evidence 02 — Decision B: Target hosting model

## 1. Decision statement

**The frozen target hierarchy is lossless with ARCH-01 and is NOT retyped by
the current standalone demo:**

```
TIPA = Workspace
 └─ ASSY = child Simulation Scope
     ├─ ASSY-SL01 = child Simulation Scope (hydraulic)
     ├─ ASSY-SL02 = child Simulation Scope (hydraulic)
     ├─ ASSY-SL03 = child Simulation Scope (hydraulic)
     ├─ ASSY-SL04 = child Simulation Scope (thermal)
     ├─ ASSY-SL05 = child Simulation Scope (thermal)
     └─ ASSY-SL06 = child Simulation Scope (thermal)
         └─ station / AP / WIP / carrier = Simulation Objects
```

ASSY is **not** retyped as Workspace; sub-lines are **not** downgraded to
Objects. The current standalone demo is a **presentation/run precedent**, not a
structural re-typing (ARCH-04 C01-1).

## 2. Standalone hosting (dev / demo / test / product-module)

- One `AssyLineRuntime` is created directly from a sub-line config and driven by
  a thin host (today: `tests/demo_assy.py::run_tipa_demo()`; UI `/assy-demo/*`).
- The host supplies **run/context only** — it never changes domain semantics.
- The standalone sub-line still carries its **structural identity**
  (`TIPA → ASSY → ASSY-SLnn`) even when no parent Workspace runtime is
  materialized; the path is expressed as identity metadata, not as a runtime
  parent object.

## 3. Federated hosting (TIPA → ASSY)

- The TIPA Workspace hosts ASSY as a **child Simulation Scope**; ASSY hosts
  ASSY-SL01..06 as **child Simulation Scopes**.
- Each sub-line scope owns **one `AssyLineRuntime`** — the same class used
  standalone. No second/federated engine class is introduced.
- The parent/federated host supplies **composition / run context / boundary
  services** only (per ARCH-02); it never mutates a child runtime's domain state
  directly.
- Child runtime state remains **isolated**; inter-scope interaction follows
  ARCH-02 boundaries (coordinator relations, not shared mutable truth).

## 4. Parent / container vs executable roles

| Node | Role | Execution semantics |
|---|---|---|
| TIPA | Workspace (container/composition) | composition-level only; no ASSY domain runtime |
| ASSY | child Simulation Scope (container over sub-lines) | composition/coordination of sub-lines; domain truth lives in sub-lines |
| ASSY-SL01..06 | child Simulation Scopes (**executable**) | each owns one `AssyLineRuntime` — the only domain runtime |
| station/AP/WIP/carrier | Simulation Objects | leaf runtime entities inside a sub-line scope |

Container vs executable follows ARCH-01: a container-only scope has structural/
composition readiness and `not_applicable` execution readiness — it must never
be presented as if it had an executable runtime.

## 5. Composition coordinator relation (ARCH-02)

- The future TIPA/ASSY host plays the ARCH-02 **composition coordinator** role:
  create/start/stop orchestration + coordinated advancement across executable
  sub-line scopes.
- `AssyDemoComposition.step_all()` (COMMON_DEMO_CLOCK) is the **demo precedent**
  for "coordinate N independent executable scopes on a common advance" — not the
  finished coordinator and not plant synchronization truth.
- The parent does **not** take over ASSY domain authority (routing, genealogy,
  quality, timing stay inside `AssyLineRuntime`).

## 6. Consistency check

- Lossless with ARCH-01 (TIPA=Workspace, ASSY=child Scope, SL=child Scopes,
  Objects): **yes**.
- No retyping/flattening: **yes**.
- Standalone and federated use identical domain runtime: **yes** (evidence 01, 03).
- No fake sibling TIPA lines: unknown/not-configured siblings are represented
  explicitly as `not_ready` / `not_configured` only where justified — never as
  fabricated simulations.

**Decision B is explicit.**
