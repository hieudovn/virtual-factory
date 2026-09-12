# VF-vNEXT-G14B — SH-WTP T106→T108 Explicit Lagged Federation

Gate: `VF-vNEXT-G14B`
Base (required): `22a69e0cf61958d256fb2f61ce38ae0f3e207dca`
Status: READY FOR SA REVIEW

## Scope

Execute exactly the already-authorized federation:

```
T106 (LogicalOnly) --REL-SHW-F01 / G14A projection--> T108 (FirstOrder)
```

using the existing G4 `Coordinator` / `ExecutableParticipant` / `BoundaryTransfer`
semantics with a deterministic **explicit one-window-lag** coupling policy
(`explicit_lagged`, Jacobi-style). Exactly two participants
(`shwtp/line1/l1_t106`, `shwtp/line1/l1_t108`) and exactly one F01 binding
(`BIND-SHW-F01-T106-OUT-T108-IN`). No T110, no F02–F07, no plant-wide execution.

## Coupling policy seam

- `coupling_policy = "explicit_lagged"` is exposed/enforced only in the SH-WTP
  federation layer — NOT on `CompositionGraph`/`BoundaryPort`/`CompositionBinding`.
- Unsupported policy values fail closed at config construction.
- Frozen separation `CompositionGraph != execution order`; future policies may be
  introduced above the unchanged graph.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/federation.py` (+ `__init__.py` exports):
  - `ShwtpFederationConfig` (explicit scenario values; no hidden defaults):
    `communication_step_s > 0`, `initial_t108_inflow_m3_s >= 0`,
    `t106_inflow_m3_s >= 0`, `t108_requested_outflow_m3_s >= 0`, T108 tank
    config, `coupling_policy` (only `explicit_lagged`), `run_id`.
  - `ShwtpT106Participant`: wraps T106; stages exactly one detached
    `BoundaryTransfer` per window on the F01 binding with payload key
    `volumetric_flow_m3_s`; rejects unexpected inbound transfers.
  - `ShwtpT108Participant`: wraps T108; `advance_to` uses ONLY the committed
    (previous-boundary) inflow + explicit requested outflow (never reads T106
    state); `commit_transfers` validates the exact F01 transfer and stores the
    flow for the NEXT window (no same-window retroactive step).
  - `ShwtpFederation`: builds the accepted G1 Workspace + G14A projection graph,
    registers the two adapters with the existing G4 `Coordinator`, and provides
    the smallest window-preparation seam before `Coordinator.run_window(...)`.
    Deterministic window sequence; stale/wrong/future/duplicate window fails
    closed; deterministic `serialize()`.
- `tests/test_vnext_g14b_federation.py` (55 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G14B gate context +
  `g14b_federation` group.

## Lag semantics proven

Before window 1 T108 uses explicit `initial_t108_inflow_m3_s`; window 1 T108 does
NOT use Q106[1]; boundary 1 commits Q106[1]; window 2 T108 uses exactly Q106[1];
no same-window feed-through or retroactive step.

## Frozen boundaries preserved

- T106 (G13B 19 green) and T108 (G13 28 green) domain equations, canonical ids,
  and provenance unchanged (`simulation/synthetic/logical_only` and
  `simulation/synthetic/first_order`).
- G14A projection (20 green) unchanged; G4 `Coordinator`/participant/transfer
  semantics unchanged (no G4 file modified).
- G1/G2/G7/G9, G10–G14A, PIM unchanged.
- `vf_runtime_authorization = NOT_AUTHORIZED`;
  `site_authorized_execution = NOT_AUTHORIZED`; no workspace/container execution.

## Regression

- G14B: 55 passed.
- G14A 20, G13B 19, G13 28 green.
- Full suite: 2215 passed (2160 prior + 55 new).
- Complete canonical vNext baseline (g1..g13b + g14a + g14b + full_suite +
  compile/static/changed-files/preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G14B/01-explicit-lagged-federation.md`
