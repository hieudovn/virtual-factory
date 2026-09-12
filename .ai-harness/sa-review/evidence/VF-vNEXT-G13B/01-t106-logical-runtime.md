# VF-vNEXT-G13B — SH-WTP T106 Standalone Synthetic Logical Runtime — Evidence

Gate: `VF-vNEXT-G13B` · Second authorized SH-WTP executable candidate (T106 LogicalOnly pass-through; no T108 change).

## 1. Target

- Canonical: `UNIT-SHW-L1-T106` (locked read-only PIM semantic reference).
- VF StructuralPath: `shwtp/line1/l1_t106` (the only runnable target of this seam).
- Behavior: standalone synthetic LogicalOnly zero-storage pass-through.

## 2. Implementation

`src/virtual_factory/shwtp/logical_runtime.py`:

- `T106Config(dt_s)` — explicit; `dt_s > 0`; no hidden behavior defaults.
- `T106LogicalRuntime(config, run_context, semantic_contract_*)` — isolated attempt;
  validates `RunContextV2` workspace == `shwtp` and `scope_path` == exact
  `shwtp/line1/l1_t106` (workspace/container/T108/T110 targets rejected); canonical
  reference locked to `UNIT-SHW-L1-T106` (no caller override).
- `step(inflow_m3_s)` — deterministic one-`dt_s` step; `output_flow = inflow`; time
  advances exactly `dt_s`; fail-closed on negative/non-finite inflow.
- `reset()` — in-context restore to initial logical state; `state`/`snapshot()` —
  detached immutable `T106State(time_s, last_input_flow_m3_s, last_output_flow_m3_s,
  provenance)`.

## 3. Provenance (G2 vocabulary)

Every step record AND detached snapshot carries `ProvenanceV2` built via
`to_provenance_v2` with `origin_kind=OriginKind.SIMULATION`,
`data_status=DataStatus.SYNTHETIC`, `fidelity=Fidelity.LOGICAL_ONLY`. No
measured/site/SiteVerified/SourceMapped/ParameterizedReady/CalibratedReady claim.
Optional G9 semantic contract pins threaded only when supplied (never fabricated).

## 4. Isolation / boundaries honored

- No modification of T108 `runtime.py` (equations/provenance untouched).
- No import of composition/runcontrol/equipment; G12A/B reference graph inert; no
  `FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO` projection; no BoundaryPort/G4/coordinator.
- Only exact `shwtp/line1/l1_t106` runs; `shwtp` / `shwtp/line1` / T108 / T110 are NOT
  executable here. No T106 -> T108 wiring.
- Admission JSON preserved: `review_status=COMPLETE`,
  `authorization_mode=CANDIDATE_SCOPED`, T106=SYNTHETIC_REFERENCE_ALLOWED, T108 accepted
  first-order, T110 blocked, NOT_AUTHORIZED unchanged.

## 5. Test evidence

- `tests/test_vnext_g13b_t106.py` — 19 tests PASS.
- G13 T108 tests still 28 PASS (unchanged).
- Full suite: 2140 passed (2121 prior + 19 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G13B.md`.

## 6. Unchanged

PIM; T108 runtime; G1/G2/G7/G9/G4; G12A/B; ASSY/continuous/UI; runtime authority; no G14.
