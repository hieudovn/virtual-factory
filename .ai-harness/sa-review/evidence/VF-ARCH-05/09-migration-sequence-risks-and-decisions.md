# VF-ARCH-05 · Evidence 09 — Decisions I, J: migration sequence, risks/rollback, STOP assessment, non-decisions

## 1. Decision I — Migration sequence/dependencies (architecture-level, NOT implemented)

Frozen sequence for later implementation:

```
1. Generic host/context seam
   (scope identity + run boundary around an executable scope; no domain change)
2. ASSY wrapper / composition
   (AssyDemoComposition → generic composition seam; same AssyLineRuntime underneath)
3. Hierarchy exposure
   (TIPA → ASSY → ASSY-SL01..06 structural paths; context strip / breadcrumb)
4. UI / context integration
   (Frame A/B content re-hosted in ARCH-04 shell; interaction model unchanged)
5. Regression proof
   (run the frozen invariants of evidence 06 as the acceptance oracle)
```

Dependencies:
- Step 1 depends on ARCH-01/ARCH-02 contracts (already frozen).
- Step 2 depends on `AssyLineRuntime` reuse boundary (evidence 03) — no rewrite.
- Step 3 depends on identity mapping (evidence 04).
- Step 4 depends on ARCH-04 UI preservation (evidence 07).
- Step 5 depends on regression invariants (evidence 06).

Each step is a separate future authorization slice; none is implemented here.

## 2. Decision J — Compatibility and rollback risk

| Risk | Mitigation (frozen expectation) |
|---|---|
| Second runtime path (standalone vs federated fork) | one `AssyLineRuntime`, wrap-only (evidence 03, 05) |
| Standalone/federated divergence | parent adds services only; domain authority non-overlapping (evidence 05) |
| ID alteration (wip_id/run_id/event ids) | local ids preserved; structural path is additive metadata (evidence 04) |
| Deterministic evidence breakage | timing/idempotency keys byte-identical for same seed+inputs (evidence 06 §4) |
| UX loss | Frame A/B + inspector + domain extensions unchanged until migration (evidence 07) |
| Promoting ASSY capabilities into platform registry without proof | capability promotion deferred; provider authority preserved (evidence 08) |
| Treating `AssyDemoComposition` as completed federation | classified as reference precedent, not completed (evidence 01) |
| Flattening sub-lines / retyping ASSY | lossless ARCH-01 mapping frozen (evidence 02, 04) |
| Parent mutating child domain state | forbidden; ARCH-02 boundaries (evidence 05) |
| Route/quality/genealogy semantic drift | frozen invariants + regression proof (evidence 06) |
| Premature implementation | all implementation non-decisions deferred (this section) |

Fail-safe expectation: any later migration slice that cannot pass the frozen
regression invariants must STOP and return to SA rather than silently normalize
a behavior change.

## 3. STOP-condition assessment

| STOP condition | Assessment |
|---|---|
| Standalone + federated cannot preserve same `AssyLineRuntime` semantics | **Not triggered** — single runtime class already serves both (evidence 01/03) |
| Mapping requires flattening/retyping accepted hierarchy | **Not triggered** — lossless TIPA→ASSY→SL01..06→Objects (evidence 02/04) |
| Preserving invariants requires domain-runtime rewrite | **Not triggered** — invariants are already encoded in `AssyLineRuntime` (evidence 06) |
| Accepted tests/evidence materially conflict with frozen target and need Owner/SA decision | **Not triggered** — discrepancies (buffer literals, legacy tipa.py, mes_adapter) are reporting differences, not material conflicts; reported verbatim (evidence 06 §3) |
| Migration requires reopening ARCH-01..04 decisions | **Not triggered** — consumed as-is |
| Implementation required to answer an architecture question safely | **Not triggered** — answers are conceptual; implementation deferred |

**Conclusion: no STOP condition triggered.**

## 4. Frozen decisions (summary)

1. Target hierarchy lossless with ARCH-01; no retype/flatten.
2. Standalone + federated use the same `AssyLineRuntime`.
3. `AssyLineRuntime` reuse boundary: wrap/adapt around a frozen core; no fork, no rewrite.
4. Identity maps structurally; distinct from PIM semantic id and `outputs.namespace`.
5. Parent may add composition/run/context/boundary services; never alters domain authority.
6. Regression invariants (evidence 06) are the migration acceptance oracle, with discrepancies reported verbatim.
7. ASSY UX preserved unchanged until migration (ARCH-04 boundary).
8. ASSY projections map to ARCH-03 contracts; no duplicate store; capability promotion deferred.
9. Migration sequence frozen (5 steps); each step a future slice.
10. Fail-safe: a slice failing the invariants STOPs for SA.

## 5. Explicit non-decisions (deferred to implementation)

1. Implementing TIPA Workspace or ASSY federation.
2. Rewriting `AssyLineRuntime`.
3. Refactoring accepted domain logic.
4. Implementing generic Workspace/Scope classes.
5. Implementing coordinator/ports.
6. Changing frontend components.
7. Creating fake simulations for other TIPA production lines.
8. Changing PIM semantic contracts.
9. Implementing provenance-v2.
10. Starting SH WTP runtime work.
11. Selecting a new frontend framework.

## 6. Critical risks challenged (resolution)

| Risk | Resolution |
|---|---|
| `AssyDemoComposition` as proof federation is complete | classified reference precedent only |
| Duplicating `AssyLineRuntime` into two paths | forbidden; single class |
| Flattening ASSY-SL01..06 into objects | forbidden; sub-lines stay Scopes |
| Retyping ASSY as Workspace | forbidden; ASSY stays child Scope |
| Parent mutating child domain state | forbidden |
| Route/quality/genealogy semantic change | frozen invariants |
| Losing deterministic timestamps/idempotency | frozen + regression proof |
| Replacing accepted ASSY UX unnecessarily | preserved |
| Promoting ASSY capability semantics without proof | deferred |
| Implementing migration prematurely | deferred |

**Decisions I and J are explicit; STOP assessment clean.**
