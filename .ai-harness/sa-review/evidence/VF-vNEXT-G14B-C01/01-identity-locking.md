# VF-vNEXT-G14B-C01 — SH-WTP Federation Identity Locking — Evidence

Gate: `VF-vNEXT-G14B-C01` · SA correction 5592283850 (Issue #65).

## 1. Problem (before C01)

`ShwtpT106Participant` / `ShwtpT108Participant` accepted `run_id` and
`workspace_id` independently from the wrapped runtime's immutable `RunContextV2`
and never cross-checked them. A caller could construct a runtime with
`run_id = r1` and an adapter with `run_id = r2`, so T106 would emit a
`BoundaryTransfer(run_id=r2)` while the produced step provenance stayed on `r1`
— split authority between domain provenance and federation exchange identity.

## 2. Frozen correction (C01)

- Both adapters now cross-check the explicit adapter identity against the wrapped
  runtime's `RunContextV2` at construction and fail closed on any mismatch:
  - `runtime.run_context.workspace_id == workspace_id == "shwtp"`;
  - `runtime.run_context.run_id == run_id`;
  - `runtime.scope_path` and `runtime.run_context.scope_path` equal the exact
    T106/T108 path.
- The adapter then stores the runtime's own immutable `run_id` / `workspace_id`
  values as the single authority for transfer identity.
- The RunContext is never mutated, runtime identity never rewritten, and no new
  run identity is derived after construction.

## 3. Identity chain (now single authority)

- T106: `runtime.run_context.run_id == adapter run_id == emitted
  BoundaryTransfer.run_id == step provenance run_id`.
- T108: `runtime.run_context.run_id == adapter run_id == federation run_id ==
  T108 step provenance run_id`.
- Workspace: `"shwtp"` throughout.

## 4. Implementation

`src/virtual_factory/shwtp/federation.py`:

- New `_validate_runtime_identity(...)` helper (fail-closed identity cross-check).
- `ShwtpT106Participant.__init__` and `ShwtpT108Participant.__init__` call the
  helper before storing state, then lock `_run_id` / `_workspace_id` to
  `runtime.run_context` values.
- No other behavior changed: explicit_lagged lag semantics, F01-only transfer,
  T106/T108 participant roles, and the existing G4 integration are untouched.

## 5. Test evidence

- `tests/test_vnext_g14b_federation.py` — 63 tests PASS (55 G14B + 8 new
  identity-locking regressions):
  - T106 adapter run-id mismatch fails closed;
  - T108 adapter run-id mismatch fails closed;
  - T106/T108 adapter workspace mismatch fails closed;
  - valid matching context PASS;
  - transfer run_id == T106 step provenance run_id == runtime RunContext run_id;
  - T108 provenance run_id == federation run_id;
  - RunContext not mutated across execution.
- G14B focused tests green; complete canonical vNext baseline PASS
  (see report `VF-vNEXT-G14B-C01.md`).

## 6. Preserved

- explicit_lagged + one-window lag; F01 only; T106 + T108 only; no T110; no
  F02-F07; no G4 change; no T106/T108 equation change; no F01 projection change;
  no policy expansion; no RunContext contract change; no G15.
