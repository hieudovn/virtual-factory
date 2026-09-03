# VF-ARCH-05 · Evidence 05 — Decision E: Standalone vs federated contract + parent/child authority matrix

## 1. Decision statement

**Standalone and federated ASSY expose equivalent domain semantics because both
use the same `AssyLineRuntime`. The parent host may add composition/run/context/
boundary services; it may not alter domain authority.**

## 2. Equivalence contract

| Axis | Standalone host | Federated host | Equivalence |
|---|---|---|---|
| Domain runtime | `AssyLineRuntime` (direct) | `AssyLineRuntime` (one per sub-line scope) | identical class |
| Route / quality / genealogy / timing | unchanged | unchanged | identical |
| Determinism / idempotency | unchanged | unchanged | identical |
| Structural identity | expressed as metadata path `TIPA/ASSY/ASSY-SLnn` | materialized as scope tree | same path |
| Run control | thin host (demo/UI) | ARCH-02 coordinator (create/start/stop; pause/resume/step at scope) | command semantics preserved (ARCH-04 C01-3) |
| MES/observation projection | unchanged | unchanged | identical facts |

## 3. What the parent may add

- composition / run orchestration (ARCH-02 create/start/stop);
- coordinated advancement across executable sub-line scopes (coordinator role);
- boundary services (inter-scope flow per ARCH-02, graph/connectivity);
- context/navigation surface (ARCH-04 shell).

## 4. What the parent may NOT alter

- domain runtime state directly (no cross-scope mutation);
- route order, AP04 join parents, AP06/AP08/AP11 quality semantics;
- genealogy records or quality status transitions;
- deterministic timing stream or idempotency keys;
- MES/event/observation fact schemas;
- `WipLifecycle` terminal semantics.

## 5. Parent/child authority matrix (non-overlapping)

| Capability | Workspace (TIPA) | Scope (ASSY) | Scope (ASSY-SLnn) | Object |
|---|---|---|---|---|
| composition / run identity | owns | — | — | — |
| coordinated advancement | orchestrates | coordinates | executes `step`/`dwell` | — |
| domain truth (route/quality/genealogy/timing) | — | — | **owns** (via `AssyLineRuntime`) | participates |
| child runtime state isolation | — | — | owns its own state | — |
| structural identity | TIPA | ASSY | ASSY-SLnn | station/AP/WIP/carrier |
| MES/observation facts | projects only | projects only | emits | participates |

"Owns" is exclusive; no row's authority is duplicated by another row. The parent
host mutates nothing in the child's domain state.

## 6. Conclusion

- Two runtime paths: **prevented** — one `AssyLineRuntime`, wrapped differently.
- Divergence standalone/federated: **prevented** — parent adds only services,
  never domain changes.

**Decision E is explicit; authority is non-overlapping.**
