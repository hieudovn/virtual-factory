# SH-WTP Runtime Readiness & Scope Freeze (VF-vNEXT-G10)

Planning / reference only. This document and `shwtp_readiness_scope.json` are the
deterministic G10 scope freeze. No SH-WTP runtime, physics, or control implementation.

## 1. Pinned PIM evidence (repo-first)

| Pin | Value |
| --- | --- |
| PIM repository | `hieudovn/plant-intelligence-model` |
| PIM base SHA | `ec7f1266d4a19e5201b689874a2a7a75a022fc5c` |
| Export package | `SHW-PIM-VF-EXPORT-v0.1` `v0.1` |
| Source model | `SHW-PH03-v0.1` |
| Semantic model identity SHA | `f23f3c4614f50a1a2e3805f7e887433feb934915` |
| Export artifact hash SHA | `ea3361a4aca9d25927a4a76c792f3af184e1aabb` |
| Model fixture | `model.yaml` (105 entities / 121 relationships / 4 contracts) |
| Seed skeleton | `plant_wide_skeleton_ph03.yaml` (seed_status: review_artifact) |
| First VF-readiness slice | `first_vf_readiness_slice_t106_t108_t110.yaml` (T106/T108/T110) |

- PIM owns canonical IDs, state vocabulary, and evidence policy.
- `vf_runtime_authorization: NOT_AUTHORIZED`; `compatibility_status_requested: candidate_for_review`.
- VF-side frozen compatibility decision: `compatible_with_constraints`.

## 2. Scope / readiness inventory (summary)

- **Container only** (never executable): `PLANT-SHW` and every `AREA-SHW-*`.
- **Executable candidates** (first slice only):
  - `UNIT-SHW-L1-T108` clean water tank → ceiling `FirstOrderReady`
  - `UNIT-SHW-WASH-T110` wash water recovery → ceiling `FirstOrderReady`
  - `UNIT-SHW-L1-T106` OSF filtration → ceiling `LogicalOnly`
- **Object only** (skeleton, DocumentConfirmed, not in slice): T100, T101..T105, T107, T109, raw intake, sludge T201, dist P108.
- **Reference only** (PatternInferred / IndustryExpected): Line 2 units, chemical dosing, electrical MCC, automation PLC.

## 3. Fidelity freeze

- `StructuralOnly` / `LogicalOnly` — allowed for structural planning.
- `FirstOrderReady` — only T108 / T110 (simple tanks with level/flow); later gate, after PIM re-review.
- `ParameterizedReady`, `CalibratedReady` — **BLOCKED** (GAP-SHW-003/-004/-012).

## 4. Boundary contracts v0

Each field tagged `PIM-supported` | `VF synthetic assumption` | `unknown/blocking`.
See `shwtp_readiness_scope.json` `boundary_contracts_v0` for T106/T108/T110.

## 5. G11 admission plan

- Authorized in G11 (structural construction only): SH-WTP Workspace, containment scopes,
  StructuralPath, canonical PIM reference binding, container_only / object_only / reference_only
  materialization per inventory, and executable_candidate classification only for
  T106 / T108 / T110 (roles and fidelity ceilings frozen).
- Not authorized in G11: executable behavior for T106 / T108 / T110. Their synthetic/reference
  black-box behavior is `allowed_later` / `PENDING_LATER_PIM_REVIEW`.
- Three distinct concepts: structural construction = `AUTHORIZED_IN_G11`;
  synthetic/reference execution = `PENDING_LATER_PIM_REVIEW`; site-authorized execution = `NOT_AUTHORIZED`.
- Prohibited until site evidence: control/interlock (GAP-002), hydraulic params (GAP-003),
  quality truth (GAP-004), electrical mapping (GAP-005), sludge modelling (GAP-010), calibration (GAP-012).
- Do not flatten SH-WTP into a single A→B→C chain; cross-area relations are many-to-many.

## 6. Relation classes

material_flow, chemical_flow, sludge_waste_flow, utility_energy_flow,
control_information_flow, dependency_constraint. Containment is a structural tree and is
distinct from connectivity.
