# 07 — PH00 `runtime.engine` Reconciliation, STOP Assessment & Decisions (Issue #41 §K)

## 7.1 PH00 `runtime.engine` reconciliation (frozen B3 vs vNext)

PH00 §06 froze `runtime.engine: continuous_process` as a workspace-manifest field
selecting an engine discriminator (B3), with `resolve_engine_kind` defaulting to
`continuous_process` for legacy configs.

Reconciliation (no schema change):

1. **Backward-compatibility meaning preserved.** `runtime.engine` retains its
   PH00 meaning: a workspace-level **compatibility/default/profile** execution
   descriptor. Existing configs keep defaulting to `continuous_process`.
2. **Not proof of one-engine-per-workspace.** The field is a default/profile for
   legacy single-engine workspaces, not an architectural claim that a workspace
   must use one engine (ARCH-01/C01).
3. **Interpretation for vNext:** pending later schema implementation, it is
   treated as the **default/primary execution descriptor** of a workspace, while
   per-scope execution mechanism may differ in hybrid composition (evidence 06).
4. **No silent break of PH00 contract.** This gate does not change the field, its
   default, or `resolve_engine_kind` behavior.

> If a concrete schema change were required, this gate would STOP FOR SA rather
> than invent it. None is required here.

## 7.2 STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| Safe composition requires rewriting `AssyLineRuntime` domain semantics | NOT triggered — composition wraps, does not rewrite. |
| Continuous/Discrete hybrid cannot be represented without one forced global engine | NOT triggered — mixed cadences + boundary exchange (§04/§06). |
| Existing accepted runtime contracts conflict materially (breaking decision) | NOT triggered — `core/` and `discrete/` are separate, composable seams; no conflict. |
| PH00 `runtime.engine` cannot be reconciled without schema-breaking change | NOT triggered — reconciled as default/profile (§7.1). |
| Deterministic composition requires site/domain-specific numerical behavior | NOT triggered — deterministic ordering is mechanism-agnostic (§04). |
| Typed boundary semantics cannot be separated from PIM canonical semantic ownership | NOT triggered — structural identity is the runtime key; PIM canonical identity stays semantic and is only optionally carried as read-only binding metadata (§05.3). |
| Requires deciding ARCH-03 Observation/Event/Capability semantics prematurely | NOT triggered — all deferred (§7.4). |

**Conclusion: no STOP condition triggered.**

## 7.3 Frozen decisions (ARCH-02)

1. Coordinator = composition service; **not** a domain engine; anti-responsibilities fixed (§05).
2. Common platform run lifecycle: validate → create → start → step/pause/resume → stop → reset (replay distinct) (§03).
3. One workspace run owns/contains child run contexts; child run identity = scope-scoped; container-only scopes have no run context (§03).
4. Synchronized composition does **not** require identical timestep/scheduler; three cadences already coexist (§04).
5. Deterministic ordering: declared stable key; explicit inputs/version/seed; no dict/set/hash/time-of-day ordering (§04).
6. Boundary exchange is the **only** cross-scope data path; direct cross-scope mutation forbidden (§05).
7. Inter-scope boundary categories: material, utility/energy, information/observation, coordination/event — ownership semantics only (§05).
8. Hybrid archetypes compose without a shared engine (§06).
9. ASSY maps as six executable sub-line scopes over the existing `AssyLineRuntime`; demo policy is not plant truth (§06).
10. PH00 `runtime.engine` = compatibility/default/profile descriptor; not one-engine-per-workspace (§7.1).

## 7.4 Explicit non-decisions (deferred to ARCH-03+ / implementation gates)

1. Production coordinator classes.
2. Final port payload/schema classes.
3. Observation/Event/Alarm schema (ARCH-03).
4. Capability registry / readiness model (ARCH-03).
5. UI components/navigation (ARCH-04).
6. TIPA/ASSY migration implementation (ARCH-05+).
7. SH WTP runtime/domain models.
8. Semantic loader/binding.
9. Provenance implementation details.
10. Historian/result warehouse.
11. Snapshot/checkpoint restore/branching implementation.
12. Frontend framework migration.
13. Real plant-control authority.
