# VF-vNEXT-G11 — SH-WTP Structural Workspace Construction — Evidence

Gate: `VF-vNEXT-G11` · Structural construction ONLY (no runtime/connectivity/PIM write).

## 1. Construction source

- Immediate VF-side contract: `configs/vnext/shwtp/shwtp_readiness_scope.json` (frozen G10 plan).
- Generic foundation reused: `virtual_factory.workspace` (`Workspace`/`SimulationScope`/`SimulationObject`,
  `ScopeMode`, `build_workspace`, `StructuralPath`). No parallel SH-WTP structural framework.
- New module: `src/virtual_factory/shwtp/structural.py` + `__init__.py` (builder + metadata + serialization).

## 2. Structure materialized (deterministic)

- Workspace root `shwtp` (VF local id), display "SH-WTP Water Treatment Plant"; plant canonical reference
  `PLANT-SHW` held as root reference metadata (role `container_only`).
- 8 top-level scopes (under the workspace root): 7 container Areas + plant-level `dist_p108`
  (`UNIT-SHW-DIST-P108`).
- 20 unit scopes nested under their Area. Total scope nodes = 28 = G10 inventory entries minus PLANT root.
- Containment layout derived from the pinned PIM skeleton `plant_wide_skeleton_ph03.yaml`
  (`units_by_area` / `plant_level_units`); `UNIT-SHW-WASH-T110` homed under `AREA-SHW-LINE1` for the
  slice scope (as G10 notes). No Area/Unit invented; no object leaves invented below units.

Areas under root: raw_water, line1, line2, chemical, sludge, electrical, automation.
Unit children per area: raw_water {raw_intake, t100}; line1 {l1_t101..l1_t109, wash_t110};
line2 {l2_t101, l2_t105, l2_t106, l2_t108}; chemical {chem_dosing}; sludge {sludge_t201};
electrical {elec_mcc}; automation {auto_plc}; plus top-level dist_p108.

## 3. VF local identity vs PIM canonical (never renamed)

- VF local scope id = deterministic lowercase alias (prefix stripped, `-` -> `_`), e.g.
  `UNIT-SHW-L1-T108` -> `l1_t108`; never equal to the canonical id.
- Each node carries read-only reference metadata: `canonical_id`, `pim_reference`, `inventory_id`.

## 4. Roles / readiness / authorization

- Role -> G1 ScopeMode: `container_only`/`object_only`/`reference_only` -> `CONTAINER_ONLY`;
  `executable_candidate` (T106/T108/T110 only) -> `EXECUTABLE_CAPABLE` (classification only).
- Metadata preserved verbatim from G10 per node: role, fidelity ceiling, evidence status/confidence,
  gaps, G10 note. Fidelity `FirstOrderReady` only on T108/T110; T106 `LogicalOnly`; no
  `ParameterizedReady`/`CalibratedReady`.
- `vf_runtime_authorization = NOT_AUTHORIZED`; `structural_construction = AUTHORIZED_IN_G11`;
  `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`; `site_authorized_execution = NOT_AUTHORIZED`.

## 5. No fake runtime / no connectivity

- Generic G1 model only: no engine/bridge/solver/behavior/advance on any node.
- `virtual_factory.shwtp` imports no runcontrol/composition/semantic/equipment/control modules.
- `virtual_factory.runcontrol` has no reference to `shwtp` (no G7 participant, no admission override).
- No connectivity/composition graph materialized; containment is a structural tree only.

## 6. Inspection / serialization

- `build_shwtp_workspace(plan_path=...)` -> `ShwtpWorkspace` (`workspace`, `meta_by_path`,
  `iter_scope_metas`, `plant_meta`, deterministic `serialize()` returning a machine-readable dict:
  workspace, plant reference, authorization, ordered nodes with path/scope_id/mode/role/fidelity/
  evidence/gaps/canonical ref/runtime authorization).

## 7. Test evidence

- `tests/test_vnext_g11_shwtp.py` — 22 structural invariant tests PASS.
- Full suite: 2027 passed (2005 prior + 22 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G11.md`.

## 8. Unchanged

PIM; runtime authorization; G1 architecture; TIPA/continuous run-control/UI; fidelity ceilings;
inventory roles; no G12 work started.
