# 05 — Gap Impact Matrix (GAP-SHW-001 … GAP-SHW-012)

Classification vocabulary (Issue #35 §E):

- `compatible_with_gap` — does not prevent semantic compatibility / logical planning.
- `blocks_binding` — prevents a required semantic mapping or contract guarantee.
- `blocks_runtime` — semantic compatibility may pass, but runtime implementation/execution must remain blocked.
- `out_of_scope_for_v0.1` — irrelevant to v0.1 compatibility.

> C01 refinement (Issue #36): the coarse `blocks_runtime` class is refined with
> **scope-precise sublabels** so it never over-reads as "all VF runtime/
> simulation is blocked". The four Issue #35 §E classes are preserved; the
> sublabels qualify exactly which execution scope is blocked and which is not.
>
> Runtime scopes distinguished (matching the frozen SH WTP roadmap/fidelity
> model):
> - **S1 — synthetic LogicalOnly simulation**: simulation-owned state +
>   simulation-owned control/scenario logic; provenance clearly synthetic; no
>   plant/source truth claimed.
> - **S2 — source-mapped / site-integrated runtime**: binding to real source
>   tags and any `SourceMapped`/`SiteVerified` operational-truth claim.
> - **S3 — site-faithful control/interlock behavior**: faithful reproduction of
>   actual plant control logic / interlock permissives.
> - **S4 — FirstOrder/parameterized execution**: physics/parameter-driven
>   execution for affected models (and `CalibratedReady` where claimed).

VF does **not** close PIM gaps. Classification is for VF-side compatibility only.

| Gap | Sev | Status | Category | Class (Issue #35) | C01 scope refinement (blocks / does NOT block) |
|---|---|---|---|---|---|
| GAP-SHW-001 | HIGH | OPEN | SourceTags | `blocks_runtime` → **S2** | Blocks **S2 source-mapped/site-integrated binding** and any `SourceMapped`/`SiteVerified` source-truth claim. Does **NOT** block **S1 synthetic LogicalOnly simulation** with synthetic/runtime-local state (no plant truth claimed). |
| GAP-SHW-002 | HIGH | OPEN | ControlLogic | `blocks_runtime` → **S3** | Blocks **S3 site-faithful control/interlock behavior**. Does **NOT** block a **simulation-owned logical controller/scenario model** in S1, clearly labeled non-site-authoritative. |
| GAP-SHW-003 | MED | ACCEPTED_FOR_V0_1 | DynamicTwin | `compatible_with_gap` | Hydraulic parameters missing → blocks S4 parameterized fidelity; S1 LogicalOnly / S4-FirstOrder planning feasible. |
| GAP-SHW-004 | MED | ACCEPTED_FOR_V0_1 | QualityModel | `compatible_with_gap` | Quality model deferred; accepted for v0.1. |
| GAP-SHW-005 | MED | ACCEPTED_FOR_V0_1 | Electrical | `out_of_scope_for_v0.1` | Electrical detail not required for the first process slice. |
| GAP-SHW-006 | LOW | ACCEPTED_FOR_V0_1 | relationship | `compatible_with_gap` | `DISCHARGES_TO`/`CONNECTED_TO` unconstrained (REL-006); accepted and linked. |
| GAP-SHW-007 | LOW | OPEN | AlarmTaxonomy | `compatible_with_gap` | Alarm taxonomy not finalized; alarms carried as Signal entities. |
| GAP-SHW-008 | LOW | OPEN | KPI | `out_of_scope_for_v0.1` | KPI category not available; planning-only. |
| GAP-SHW-009 | LOW | OPEN | Procedure | `compatible_with_gap` | Procedure steps deferred to semantic metadata; reference-only. |
| GAP-SHW-010 | MED | OPEN | VFReadiness | `compatible_with_gap` → **S4** | Missing required physical/model parameters may block **S4 FirstOrder/parameterized execution for affected models**; **S1 LogicalOnly composition may remain feasible**. |
| GAP-SHW-011 | LOW | OPEN | VFReadiness | `compatible_with_gap` | Object-class mapping is draft; must be validated against a real VF library before use. |
| GAP-SHW-012 | LOW | OPEN | VFReadiness | `out_of_scope_for_v0.1` | Calibration out of scope; `CalibratedReady` never claimed. |

## 5.1 Summary

- **blocks_binding**: NONE — no gap prevents the exact-one canonical binding
  structure; canonical identity is complete and unambiguous for the first slice
  (unchanged, evidence-supported).
- **blocks_runtime (scope-precise)**:
  - GAP-SHW-001 → blocks **S2** (source-mapped/site-integrated runtime + source-truth claims);
  - GAP-SHW-002 → blocks **S3** (site-faithful control/interlock behavior).
  - Neither blocks **S1 synthetic LogicalOnly simulation**.
- **compatible_with_gap**: GAP-SHW-003, 004, 006, 007, 009, 010, 011.
  - GAP-SHW-010 additionally scopes **S4**: FirstOrder/parameterized execution of
    affected models is blocked while physical parameters are missing; LogicalOnly
    composition remains feasible.
- **out_of_scope_for_v0.1**: GAP-SHW-005, 008, 012.

## 5.2 Net effect (C01)

- Semantic compatibility and binding are **not** blocked by any gap
  (0 `blocks_binding`).
- **Synthetic LogicalOnly simulation** (S1) is not semantically blocked by
  GAP-001/002/010 — provided provenance is clearly synthetic and no plant/source
  truth is claimed. Whether S1 may actually be run is a **separate governance
  decision** (current state: `NOT_AUTHORIZED` for this gate), not a semantic
  impossibility caused by these gaps.
- **Source-faithful / plant-integrated runtime** (S2/S3) and **parameterized /
  first-order execution with real parameters** (S4) remain fail-closed while the
  corresponding plant evidence is missing.

