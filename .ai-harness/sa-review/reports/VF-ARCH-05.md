# VF-ARCH-05 — Freeze TIPA/ASSY migration architecture and regression invariants

> **C01 revision (Issue #44 SA review):** the regression oracle is now
> **semantic, not token-based**. The conceptual labels `SSO2_BUFFER`,
> `RSO2_BUFFER`, `FINISHED` are confirmed NOT to be literal conveyor-position
> tokens, and the discrepancy reporting is kept; the oracle is expanded to
> preserve the evidence-backed functional semantics behind those labels: (1)
> SSO2 feed/queue/buffering before entry at PRE-ASSY; (2) RSO2 buffering/
> availability feeding AP04 JOIN; (3) terminal `FINISHED` semantics as
> lifecycle/output (`RELEASED` / MES `LINE_OUT` GOOD/REJECT as applicable), not
> as a conveyor position. Rows lacking a direct test are recorded explicitly as
> future regression proof obligations. No other ARCH-05 decision changed.

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-05` (GitHub Issue #44) |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Prerequisite | ARCH-04 / Issue #43 CLOSED by SA as `completed` |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design gate — documentation & evidence only (no production migration implementation) |
| Architecture baseline | ARCH-01 @ `41903e18…` + ARCH-02 @ `40454487…` + ARCH-03 @ `392401bd…` + ARCH-04 @ `d5c155b6…` |
| Production baseline | canonical `main` lineage (`f5261c8…`; unchanged) |
| Production code changed | **NO** (only `.ai-harness/`) |
| ARCH-06 started | **NO** |

## 1. Objective

Freeze the migration architecture that moves accepted ASSY behavior into the
vNext hierarchical/federated model — `TIPA Workspace → ASSY Simulation Scope →
ASSY-SL01..06 child Simulation Scopes → station/AP/WIP/carrier Simulation
Objects` — without rewriting `AssyLineRuntime`, losing accepted UX/runtime
behavior, or creating two runtime paths between standalone and federated hosts.

## 2. Repo-first discovery (evidence 01)

Single domain runtime `AssyLineRuntime` (`assembly/line_runtime.py`) already
serves both the standalone host (`tests/demo_assy.py`) and the six-sub-line host
(`AssyDemoComposition` wrapping six `AssyDemoContext`, each with one
`AssyLineRuntime`). Authoritative route = `conveyor.py::ConveyorConfig.positions`
(12 positions). `sub_line_identity.py` encodes TIPA→ASSY→ASSY-SL01..06.
`tipa.py::build_tipa_topology()` is legacy M3-S03 single-line (superseded). No
generic Workspace/Scope class exists in `src/`.

## 3. Frozen decisions (evidence 02–09)

| Decision | Frozen contract |
|---|---|
| **A — Inventory** | ASSY pieces classified: reuse as-is / wrap-host / adapt composition / generalize later / legacy-demo-only / must-not-rewrite. |
| **B — Hosting model** | TIPA=Workspace, ASSY=child Scope, ASSY-SL01..06=child Scopes (executable, each owns one `AssyLineRuntime`), Objects=station/AP/WIP/carrier. No retype/flatten. |
| **C — Reuse boundary** | `AssyLineRuntime` domain behavior frozen; migration wraps/adapts around it; never forks or rewrites. |
| **D — Identity migration** | lossless structural path `TIPA/ASSY/ASSY-SLnn/<object>`; local ids preserved; distinct from PIM semantic id and `outputs.namespace`. |
| **E — Standalone vs federated** | equivalent domain semantics; parent adds composition/run/context/boundary services only; authority non-overlapping. |
| **F — Regression invariants** | 12 invariants with exact repo evidence + discrepancies reported verbatim, PLUS a functional-semantics oracle (SSO2 feed before PRE-ASSY; RSO2 buffering before AP04 JOIN; terminal FINISHED → RELEASED / LINE_OUT GOOD/REJECT) that is semantic, not token-based. |
| **G — UI preservation** | Frame A/B + inspector + domain extensions unchanged until migration; no frontend implementation. |
| **H — Observation/Event/Capability** | projections map to ARCH-03 contracts; no duplicate store; capability promotion deferred. |
| **I — Migration sequence** | 5 frozen steps (host seam → ASSY wrapper → hierarchy exposure → UI integration → regression proof); not implemented. |
| **J — Risks/rollback** | fail-safe: any slice failing the frozen invariants STOPs for SA. |

## 4. Regression invariants (evidence 06)

Route (12 positions, PRE-ASSY first), AP04 both-parent genealogy, AP06 retest,
AP08 reinspect, AP11 final-QC, `failed_final` terminal+idempotent, `LINE_OUT`
good/reject, quality/checklist/measurement (`DEMO_SYNTHETIC`), deterministic
timing + idempotency keys, six sub-lines, continuous/compressor functionality,
demo behavior preserved unless demo-only.

**Functional-semantics oracle (semantic, not token-based):** the conceptual
labels `SSO2_BUFFER`, `RSO2_BUFFER`, `FINISHED` are NOT literal conveyor-position
tokens (discrepancy reporting kept). The oracle additionally preserves the
functional semantics they stand for: (1) SSO2 feed/queue/buffering before entry
at PRE-ASSY; (2) RSO2 buffering/availability feeding AP04 JOIN; (3) terminal
`FINISHED` = lifecycle/output mapping (`RELEASED` for good; MES `LINE_OUT`
GOOD/REJECT as applicable), never as a conveyor position. Sub-behaviors without
a direct test are explicitly recorded as **future regression proof obligations**
in evidence 06 §3. A migration that preserves the 12 positions but breaks
SSO2/RSO2 feed/buffer behavior or terminal release/output semantics is a
regression.

**Reported discrepancies (verbatim, not normalized):** buffer literals
`SSO2_BUFFER`/`RSO2_BUFFER` are not code tokens; `FINISHED` = `WipLifecycle.RELEASED`
(not a position); `tipa.py` is legacy single-line; `mes_adapter.py` holds no
determinism/idempotency logic; AP06 retest-in-place ≠ legacy AP04 rework.

## 5. STOP-condition assessment (evidence 09 §3)

None triggered: single runtime serves both hosts; hierarchy lossless; invariants
already encoded in `AssyLineRuntime`; discrepancies are reporting differences,
not material conflicts; no ARCH-01..04 reopening; no implementation required to
answer safely.

## 6. Non-decisions (deferred)

No TIPA Workspace/ASSY federation implementation; no `AssyLineRuntime` rewrite;
no generic Workspace/Scope classes; no coordinator/ports; no frontend changes;
no fake TIPA lines; no PIM changes; no provenance-v2; no SH WTP runtime; no
framework migration.

## 6.1 C01 corrections applied

1. **Regression oracle semantic (C01-1):** the regression oracle in evidence 06
   now preserves the evidence-backed functional semantics behind the conceptual
   labels `SSO2_BUFFER`, `RSO2_BUFFER`, `FINISHED`, in addition to the 12
   conveyor positions: SSO2 feed/queue/buffering before entry at PRE-ASSY (§3.1),
   RSO2 buffering/availability feeding AP04 JOIN (§3.2), and terminal `FINISHED`
   = lifecycle/output (`RELEASED` / `LINE_OUT` GOOD/REJECT) (§3.3).
2. **Token discrepancy reporting kept:** `SSO2_BUFFER`/`RSO2_BUFFER`/`FINISHED`
   remain explicitly non-literal, non-conveyor-position labels; no code tokens
   were invented (§3.4 / §4).
3. **Future regression proof obligations recorded:** sub-behaviors without a
   direct test today (SSO2 feed-queue drain ordering; `rso2_buffer_size` count
   semantics) are marked explicitly as future regression proof obligations in
   evidence 06 §3, not fabricated as evidence.

## 7. Acceptance

| Criterion | Result |
|---|---|
| Target hierarchy lossless, consistent with ARCH-01 | PASS (02, 04) |
| Standalone/federated hosting explicit | PASS (02, 05) |
| AssyLineRuntime reuse boundary explicit | PASS (03) |
| Parent/child authority non-overlapping | PASS (05) |
| ASSY regression invariants documented with repo evidence | PASS (06) |
| UI preservation boundary explicit | PASS (07) |
| ARCH-03 observation/event/capability contracts respected | PASS (08) |
| Migration risks and dependencies explicit | PASS (09) |
| No production code changes | PASS (only `.ai-harness/`) |
| No implementation started | PASS (non-decisions deferred) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-05/` — 9 files (01…09).

## 9. Final status

```text
VF-ARCH-05-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. ARCH-06 is NOT started; all
implementation non-decisions remain deferred.
