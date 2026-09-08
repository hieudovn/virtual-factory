# VF-vNEXT-G14B-C01 — SH-WTP Federation Identity Locking

Gate: `VF-vNEXT-G14B-C01`
Base (required): `3e69e257a578c220594df92e136017ba0f846249`
SA comment: `5592283850`
Status: READY FOR SA REVIEW

## Scope

Lock the SH-WTP federation participant adapters' federation identity to the
wrapped runtimes' immutable `RunContextV2`, closing the split-authority seam
identified in SA review of G14B.

## Fix

- `ShwtpT106Participant` and `ShwtpT108Participant` constructors now fail closed
  when `runtime.run_context.workspace_id != workspace_id`,
  `runtime.run_context.run_id != run_id`, or the runtime scope path is not the
  exact T106/T108 path.
- Enforced invariant: `runtime.run_context.workspace_id == adapter workspace_id
  == "shwtp"` and `runtime.run_context.run_id == adapter run_id`.
- The adapter stores the runtime's own immutable `run_id` / `workspace_id` values
  as the single transfer identity authority — never mutating the RunContext,
  never rewriting runtime identity, and never deriving a new run id after
  construction.

## Identity chain (single authority)

- T106: `runtime.run_context.run_id == adapter run_id == BoundaryTransfer.run_id
  == step provenance run_id`.
- T108: `runtime.run_context.run_id == adapter run_id == federation run_id ==
  T108 step provenance run_id`.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/federation.py`: added `_validate_runtime_identity`
  helper; both participant constructors cross-check + lock identity.
- `tests/test_vnext_g14b_federation.py`: 8 new identity-locking regressions
  (63 tests total).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G14B-C01 gate context.

## Frozen boundaries preserved

- explicit_lagged + one-window lag; F01 only; T106 + T108 only; no T110; no
  F02-F07; no G4 change; no T106/T108 equation change; no F01 projection change;
  no policy expansion; no RunContext/G2 identity contract change; no G15.

## Regression

- G14B focused: 63 passed.
- Full suite: 2223 passed (2215 prior + 8 new).
- Complete canonical vNext baseline (g1..g13b + g14a + g14b + full_suite +
  compile/static/changed-files/preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G14B-C01/01-identity-locking.md`
