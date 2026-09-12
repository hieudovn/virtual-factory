# VF-vNEXT-G10 — SH-WTP Runtime Readiness & Scope Freeze — Evidence

Gate: `VF-vNEXT-G10` · Planning-only (no runtime, no physics, no control, no PIM write).

## 1. Pinned PIM evidence (repo-first)

| Fact | Value |
| --- | --- |
| PIM repository | `hieudovn/plant-intelligence-model` |
| PIM base SHA | `ec7f1266d4a19e5201b689874a2a7a75a022fc5c` |
| Export package | `SHW-PIM-VF-EXPORT-v0.1` `v0.1` (`SHW-PH03-v0.1`) |
| Semantic model identity SHA | `f23f3c4614f50a1a2e3805f7e887433feb934915` |
| Export artifact hash SHA | `ea3361a4aca9d25927a4a76c792f3af184e1aabb` |
| Model fixture | `examples/song-hong-wtp/model_fixture/model.yaml` (105 entities / 121 relationships / 4 contracts) |
| Seed skeleton | `examples/song-hong-wtp/seed/plant_wide_skeleton_ph03.yaml` (review_artifact) |
| First VF-readiness slice | `examples/song-hong-wtp/seed/first_vf_readiness_slice_t106_t108_t110.yaml` (T106/T108/T110) |
| Gap register | `gap_register.yaml` — `GAP-SHW-001..012` |
| Runtime authorization | `NOT_AUTHORIZED` |
| Compatibility (PIM request) | `candidate_for_review` |
| Compatibility (VF decision, frozen G9) | `compatible_with_constraints` |

Skeleton-derived topology (no invented names): plant `PLANT-SHW`; areas
`AREA-SHW-RAW-WATER`, `-LINE1`, `-LINE2`, `-CHEMICAL`, `-SLUDGE`, `-ELECTRICAL`,
`-AUTOMATION`; units per area as documented in
`plant_wide_skeleton_ph03.yaml` (DocumentConfirmed / PatternInferred /
IndustryExpected); plant-level units `UNIT-SHW-DIST-P108`, `UNIT-SHW-WASH-T110`;
`major_flow_spine` includes cross-area sludge and chemical-dosing lines.

## 2. Scope / readiness inventory

See `configs/vnext/shwtp/shwtp_readiness_scope.json` `inventory` (29 entries).
Key classifications:

- Container only: `PLANT-SHW` + all `AREA-SHW-*` process areas.
- Reference only: electrical/automation areas + MCC/PLC + PatternInferred Line 2 units + chemical dosing.
- Executable candidates (first slice only): `UNIT-SHW-L1-T106` (OSF filtration, ceiling `LogicalOnly`), `UNIT-SHW-L1-T108` (clean water tank, ceiling `FirstOrderReady`), `UNIT-SHW-WASH-T110` (wash water recovery, ceiling `FirstOrderReady`).
- Object only (skeleton, DocumentConfirmed, not in slice): raw intake, T100, T101..T105, T107, T109, sludge T201, dist P108.

## 3. Fidelity freeze

- `FirstOrderReady` only for T108/T110 (simple tanks).
- `ParameterizedReady` / `CalibratedReady` — BLOCKED (GAP-SHW-003/-004/-012).

## 4. Boundary contracts v0

`UNIT-SHW-L1-T108`, `UNIT-SHW-WASH-T110`, `UNIT-SHW-L1-T106` — every field tagged
`PIM-supported` | `VF synthetic assumption` | `unknown/blocking`.

## 5. G11 admission plan

Structural construction `AUTHORIZED_IN_G11`; synthetic/reference execution
`PENDING_LATER_PIM_REVIEW`; site-authorized execution `NOT_AUTHORIZED`.
Prohibited until site evidence: control/interlock (GAP-002), hydraulic params
(GAP-003), quality truth (GAP-004), electrical mapping (GAP-005), sludge
modelling (GAP-010), calibration (GAP-012). No A→B→C flattening; cross-area
relations are many-to-many; containment is a structural tree distinct from
connectivity.

## 6. Test evidence

- `tests/test_vnext_g10_plan.py` — 17 invariant tests PASS.
- Canonical baseline (post-commit, clean tree): see report `VF-vNEXT-G10.md`.

## 7. No production runtime / no G11 construction

G10 changed files are confined to `configs/vnext/`, `tests/`,
`.ai-harness/tasks/`, `.ai-harness/sa-review/`, and the baseline manifest. No
`src/` change. No SH-WTP runtime, physics, or control implementation.
