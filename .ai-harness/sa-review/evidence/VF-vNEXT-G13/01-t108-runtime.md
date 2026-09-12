# VF-vNEXT-G13 — SH-WTP T108 Standalone Synthetic First-Order Runtime — Evidence

Gate: `VF-vNEXT-G13` · First authorized SH-WTP executable slice (T108 only; no T106/T110/G4).

## 1. Target

- Canonical: `UNIT-SHW-L1-T108` (read-only PIM semantic reference).
- VF StructuralPath: `shwtp/line1/l1_t108` (the only runnable target of this seam).
- Behavior: standalone synthetic/reference first-order tank accumulator.

## 2. Implementation

`src/virtual_factory/shwtp/runtime.py`:

- `T108Config(capacity_m3, tank_area_m2, initial_volume_m3, dt_s)` — all behavior-affecting
  values explicit (no hidden defaults), validated fail-closed.
- `T108TankRuntime(config, run_context, canonical_id=..., semantic_contract_*)` — isolated
  attempt; validates `RunContextV2` workspace == `shwtp` and `scope_path` == exact
  `shwtp/line1/l1_t108` (workspace/container targets rejected).
- `step(inflow_m3_s, requested_outflow_m3_s)` — one deterministic `dt_s` with explicit
  overflow and empty-tank saturation; fail-closed mass-balance guard.
- `reset()` — in-context restore to initial; `state`/`snapshot()` — detached immutable
  `T108State(time_s, volume_m3, level_m)`.
- `T108Step` — immutable record carrying start state, inputs, applied outflow, overflow,
  end state, and truthful provenance.

Step semantics (as frozen): `available = V + Qin*dt`; `applied = min(Qout, available/dt)`;
`pre_overflow = available - applied*dt`; `overflow = max(0, pre_overflow - capacity)`;
`V_next = pre_overflow - overflow`; `level_next = V_next / area`.

## 3. Provenance (G2 vocabulary)

Every step record carries `ProvenanceV2` built via `to_provenance_v2` with
`origin_kind=OriginKind.SIMULATION`, `data_status=DataStatus.SYNTHETIC`,
`fidelity=Fidelity.FIRST_ORDER`. No measured/site/SiteVerified/SourceMapped/
ParameterizedReady/CalibratedReady claim. Optional G9 semantic contract pins are threaded
through only when supplied (never fabricated).

## 4. Isolation / boundaries honored

- No modification of `equipment.process_dynamics.py` or the legacy continuous engine.
- No import of composition/runcontrol/equipment; G12A/B reference graph stays inert; no
  `FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO` projection; no BoundaryPort/G4/coordinator.
- Only exact `shwtp/line1/l1_t108` runs; `shwtp` / `shwtp/line1` are NOT executable here.
- Admission JSON preserved: `review_status=COMPLETE`, `authorization_mode=CANDIDATE_SCOPED`,
  `first_authorized_slice=[T108]`, `blocked_candidates=[T110]`, NOT_AUTHORIZED unchanged.

## 5. Test evidence

- `tests/test_vnext_g13_t108.py` — 24 tests PASS.
- Full suite: 2117 passed (2093 prior + 24 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G13.md`.

## 6. Unchanged

PIM; G1/G2/G7/G9/G4; T106 unimplemented; T110 blocked; ASSY/continuous/UI; runtime
authorization; no G14.
