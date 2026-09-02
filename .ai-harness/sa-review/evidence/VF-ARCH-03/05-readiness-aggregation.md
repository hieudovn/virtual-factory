# 05 — Workspace / Scope Health & Readiness Aggregation (Issue #42 §G)

## 5.1 Aggregation, not a second source of truth

Workspace/scope Health/Readiness **aggregates** lower-level states; it is **not**
a separate competing evaluator and **not** a source of truth. The inputs are:

1. **Capability states** (platform / execution-domain / workspace-feature) —
   evidence 04.
2. **Semantic binding compatibility/readiness** — PH00 `compatibility.status`
   (compatible / review_required / incompatible) + `semantic_binding.mode`.
3. **Runtime initialization/readiness** — scope runtime lifecycle readiness
   (ARCH-02 validate/readiness precondition), `runtime.engine`, fidelity ceiling.
4. **Child scope readiness** — aggregated from participating child scopes.

## 5.2 Aggregation rules (deterministic, categorical — no arbitrary scores)

1. **Required vs optional:** required capabilities/inputs contribute as blockers;
   optional ones contribute as warnings/degradation, not blockers.
2. **Child scope readiness:** a parent scope's readiness is a deterministic
   function of its participating child scopes' readiness (per ARCH-02
   parent/child run contract).
3. **Semantic binding:** with `semantic_binding.mode: required`, a missing/
   mismatched/incompatible pin makes readiness fail-closed (`review_required`
   / not ready).
4. **Runtime init:** a scope that cannot initialize/validate is `not_ready`
   (or `error/degraded` if it initializes but faults).
5. **Degraded-continue vs fail-closed** is declared at contract level (ARCH-02
   failure policy); it does not imply a hidden health score.
6. **Container-only scope readiness:** a container-only scope has no runtime
   readiness of its own; its readiness is the aggregation of its child scopes
   (and/or `not_applicable` when it has no executable children).
7. **`not_applicable` effect:** capabilities/scopes marked `not_applicable` are
   excluded from blocking aggregation (they are irrelevant, not failures).
8. **`restricted` vs `not_ready`:** `restricted` is usable-within-limits and does
   not block (it may degrade); `not_ready` is a prerequisite gap and does block
   where the capability is required.

**Anti-drift:** no arbitrary health score hides exact blockers. The aggregation
surface is always the explicit categorical state of lower-level inputs;
`not_ready`/missing capabilities remain visible.

## 5.3 No scoring algorithm

Repo evidence does not justify a numeric scoring algorithm. ARCH-03 freezes
**deterministic categorical aggregation** over the states above; any numeric
score (if ever introduced) is a later implementation decision, not this gate.
