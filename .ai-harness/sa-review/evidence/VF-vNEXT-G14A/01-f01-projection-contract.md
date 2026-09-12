# VF-vNEXT-G14A — SH-WTP T106→T108 Runtime Projection Contract — Evidence

Gate: `VF-vNEXT-G14A` · Explicit inert runtime projection for exactly REL-SHW-F01 (no execution).

## 1. Projection decision (frozen)

| Field | Value |
| --- | --- |
| Projection id | `PROJ-SHW-F01-T106-T108` |
| PIM relation | `REL-SHW-F01` (`FLOWS_TO`, `DocumentConfirmed`) |
| PIM source | `PROC-SHW-L1-T106-OUT-FLOW` |
| PIM target | `PROC-SHW-L1-T108-IN-FLOW` |
| VF source | `shwtp/line1/l1_t106` (T106 OUT, MATERIAL, m3/s, volumetric_flow) |
| VF target | `shwtp/line1/l1_t108` (T108 IN, MATERIAL, m3/s, volumetric_flow) |
| Binding | `BIND-SHW-F01-T106-OUT-T108-IN` |

Port ids are VF-local (`out_flow` / `in_flow`), never PIM canonical ids.

## 2. Why F01 only (no auto-projection)

Permitted by the conjunction of: PIM F01 DocumentConfirmed; G12C T106 filtered-water
output-flow fact; G12C T108 filtered-water input-flow fact; G13B T106
`output_flow_m3_s`; G13 T108 `inflow_m3_s`; identical volumetric-flow unit semantics.
No generic `FLOWS_TO => material binding` rule exists.

## 3. Implementation

`src/virtual_factory/shwtp/projection.py`:

- Cross-checks the accepted G12B connectivity slice for `REL-SHW-F01` and fails closed
  if relation_type / source / target / evidence differ from the pinned values.
- Builds exactly two `BoundaryPort`s and exactly one `CompositionBinding`, validates
  via `check_port_compatibility` (OUT→IN, MATERIAL match, m3/s match, descriptor match),
  then builds an inert `CompositionGraph` (workspace `shwtp`, 1 binding).
- `ProjectionRecord` carries projection id, relation id, exact PIM endpoints, exact VF
  paths, exact PortRefs, direction/category/unit/descriptor, evidence status, PIM
  authority/main SHA, authorization scope, and site/runtime disclaimer.
- `ShwtpF01Projection.serialize()` produces a deterministic inspection of
  record + ports + bindings.

No execution: no coordinator advance, no T106→T108 value transfer, no shared clock, no
run-control orchestration, no Workspace/container run.

## 4. Boundaries preserved

- Only F01; F02/F03/F04/F05/F06/F07 not projected; T110 absent.
- T106/T108 standalone behavior, equations, and provenance unchanged (G13B 19 + G13 28
  green).
- G4 semantics, G7, G12A/B reference graph, PIM unchanged.
- `vf_runtime_authorization = NOT_AUTHORIZED`; `site_authorized_execution = NOT_AUTHORIZED`.

## 5. Test evidence

- `tests/test_vnext_g14a_projection.py` — 20 tests PASS.
- Full suite: 2160 passed (2140 prior + 20 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G14A.md`.

## 6. Unchanged

PIM; T106/T108; G1/G2/G4/G7/G9; G10-G13B; ASSY/continuous/UI; runtime authority; no G14B.
