# VF-vNEXT-G14A — SH-WTP T106→T108 Runtime Projection Contract (F01)

Gate: `VF-vNEXT-G14A`
Base (required): `2cea59f8fbb7ce974d4b9404469c085d98cdeca6`
Status: READY FOR SA REVIEW

## Scope

Explicit, evidence-traceable, **INERT** runtime projection for exactly one PIM
relationship, `REL-SHW-F01` (`FLOWS_TO`, `DocumentConfirmed`):

```
PROC-SHW-L1-T106-OUT-FLOW --FLOWS_TO--> PROC-SHW-L1-T108-IN-FLOW
shwtp/line1/l1_t106#out_flow  -->  shwtp/line1/l1_t108#in_flow
```

No execution, no value transfer, no coordinator/run-control orchestration. G14A
authorizes only this synthetic/reference projection contract for a future bounded
gate (G14B).

## Why F01 only (no auto-projection)

Justified by: PIM F01 DocumentConfirmed; G12C T106 filtered-water output-flow fact;
G12C T108 filtered-water input-flow fact; G13B T106 `output_flow_m3_s`; G13 T108
`inflow_m3_s`; identical volumetric-flow unit semantics. No generic
`FLOWS_TO => material binding` rule exists.

## Implemented (additive, isolated)

- `src/virtual_factory/shwtp/projection.py` (+ `__init__.py` exports):
  - frozen pins `SHWTP_F01_*` (projection/relation/endpoints/unit/descriptor/binding ids);
  - `_f01_relation()` cross-checks the accepted G12B connectivity slice and fails closed;
  - `t106_out_port()` OUT/MATERIAL/m3/s/volumetric_flow, `t108_in_port()` IN/MATERIAL/m3/s/volumetric_flow;
  - `f01_binding()` single `CompositionBinding`; `check_port_compatibility` enforced;
  - `ProjectionRecord` (frozen) + `ShwtpF01Projection.serialize()` deterministic;
  - VF-local PortRefs only (never PIM canonical ids).
- `tests/test_vnext_g14a_projection.py` (20 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G14A gate context + `g14a_f01_projection` group.

## Frozen boundaries preserved

- Only F01; F02–F07 not projected; T110 absent/blocked.
- T106 (G13B 19 green) and T108 (G13 28 green) standalone behavior, equations, and
  provenance unchanged; no runtime mutation on construct/inspect.
- G1/G2/G4/G7/G9, G10-G13B, G12A/B reference graph, PIM unchanged.
- `vf_runtime_authorization = NOT_AUTHORIZED`; `site_authorized_execution = NOT_AUTHORIZED`;
  no workspace/container execution, no plant-wide runtime, no G14B.

## Regression

- G14A: 20 passed.
- Full suite: 2160 passed (2140 prior + 20 new).
- Complete canonical vNext baseline (g1..g13b + g14a + full_suite + compile/static/
  changed-files/preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G14A/01-f01-projection-contract.md`
