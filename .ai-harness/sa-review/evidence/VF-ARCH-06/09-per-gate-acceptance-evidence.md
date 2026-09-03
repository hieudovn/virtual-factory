# VF-ARCH-06 · Evidence 09 — Decision I: Per-gate acceptance evidence

## 1. Decision statement

**Each future gate has a minimum acceptance-evidence class defined below. No
tests are implemented here — this is an expectation contract only.**

## 2. Shared evidence classes (definitions)

| Class | Meaning |
|---|---|
| `files` | exact changed-file scope (allowlist, no out-of-scope edits) |
| `unit` | unit tests for new/changed units |
| `integration` | cross-module integration tests |
| `regression` | existing tests must still pass |
| `determinism` | deterministic replay / provenance checks (same seed+inputs → byte-identical) |
| `assy-oracle` | ARCH-05 ASSY regression oracle (route/quality/genealogy/timing/LINE_OUT, incl. C01 functional-semantics oracle) |
| `cont-baseline` | continuous/compressor/process-dynamics/balance/pid baseline tests |
| `bind-failclosed` | semantic-binding fail-closed tests (missing ref/hash, SHA mismatch, unmapped/ambiguous) |
| `ui-projection` | UI context/capability projection tests (capability state drives visibility; no name hard-coding) |
| `no-dup-path` | proof that no duplicate runtime path was introduced |

## 3. Per-gate minimum evidence

| Gate | Minimum acceptance evidence |
|---|---|
| G1 Workspace/Scope Foundation | `files` (workspace/scope structural classes + `configs/workspaces/` only); `unit` + `integration` (container vs executable, federated child); `regression` (ASSY oracle + cont-baseline unaffected) |
| G2 Runtime Context + Provenance v2 | `files`; `unit` provenance envelope; `determinism`; `regression` (ASSY oracle + cont-baseline) |
| G3 Observation/Event/Alarm alignment | `files`; `unit`/`integration` (projection never mutates truth; Alarm ⊂ Event); `regression` (ASSY oracle + cont-baseline) |
| G4 Composition Graph + Coordinator + Typed Ports | `files`; `integration` (inter-scope boundary, no cross-scope mutation); `regression` (ASSY oracle + cont-baseline); `no-dup-path` |
| G5 TIPA/ASSY federation | `files`; `assy-oracle` (full ARCH-05 oracle); `cont-baseline`; `no-dup-path` (single `AssyLineRuntime`) |
| G6 Shared hierarchical UI primitives | `files` (no framework migration); `ui-projection`; `regression` (ASSY UX preserved) |
| G7 Hierarchical Scenario/Run Control | `files`; `integration` (ARCH-02 command levels: create/start/stop vs pause/resume/step; reset in-context); `regression` (ASSY oracle + cont-baseline) |
| G8 VF Platform vNext Regression Baseline | `files`; full `regression` suite (ASSY oracle + cont-baseline + all prior gate tests); `determinism`; `no-dup-path` |
| G9 Semantic Binding vNext | `files`; `bind-failclosed`; `integration` (version/hash pinning, `mapped` exactly-one target); `regression` (ASSY oracle + cont-baseline) |
| G10 Resume SH WTP runtime | `files`; `unit`+`integration` SH WTP domain models hosted behind the scope execution boundary (continuous shared-core precedent); fidelity `logical_only` asserted (`data_status=synthetic`); `regression` (ASSY oracle + cont-baseline); `no-dup-path`; legacy mini-engine deprecation gated on this gate's proof |

## 4. ASSY regression protection (explicit)

Every gate G1–G10 lists `assy-oracle` or its equivalent. No shared-infrastructure
change is accepted if the ARCH-05 ASSY oracle (route, quality, genealogy,
timing, LINE_OUT, and the C01 functional semantics) regresses.

## 5. No implementation here

These are expectation contracts, not tests. Nothing is written.

**Decision I is explicit.**
