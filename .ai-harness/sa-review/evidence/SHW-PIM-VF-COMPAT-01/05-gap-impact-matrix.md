# 05 — Gap Impact Matrix (GAP-SHW-001 … GAP-SHW-012)

Classification vocabulary (Issue #35 §E):

- `compatible_with_gap` — does not prevent semantic compatibility / logical planning.
- `blocks_binding` — prevents a required semantic mapping or contract guarantee.
- `blocks_runtime` — semantic compatibility may pass, but runtime implementation/execution must remain blocked.
- `out_of_scope_for_v0.1` — irrelevant to v0.1 compatibility.

VF does **not** close PIM gaps. Classification is for VF-side compatibility only.

| Gap | Severity | Status | Category | Classification | Rationale |
|---|---|---|---|---|---|
| GAP-SHW-001 | HIGH | OPEN | SourceTags | **blocks_runtime** | No PLC/SCADA tag export → no SourceMapped evidence. Canonical identity is unaffected (compat passes), but source-mapped/site-verified runtime truth must stay blocked. |
| GAP-SHW-002 | HIGH | OPEN | ControlLogic | **blocks_runtime** | No PLC logic / interlock matrix → control/permissive runtime execution must stay blocked. Not a canonical-identity gap. |
| GAP-SHW-003 | MEDIUM | ACCEPTED_FOR_V0_1 | DynamicTwin | **compatible_with_gap** | Hydraulic parameters missing → LogicalOnly/FirstOrderReady only; does not block logical planning. |
| GAP-SHW-004 | MEDIUM | ACCEPTED_FOR_V0_1 | QualityModel | **compatible_with_gap** | Quality history missing → quality model deferred; accepted for v0.1. |
| GAP-SHW-005 | MEDIUM | ACCEPTED_FOR_V0_1 | Electrical | **out_of_scope_for_v0.1** | Electrical detail not required for the first process slice. |
| GAP-SHW-006 | LOW | ACCEPTED_FOR_V0_1 | relationship | **compatible_with_gap** | `DISCHARGES_TO`/`CONNECTED_TO` unconstrained (REL-006); accepted and linked. |
| GAP-SHW-007 | LOW | OPEN | AlarmTaxonomy | **compatible_with_gap** | Alarm taxonomy not finalized; alarms carried as Signal entities. |
| GAP-SHW-008 | LOW | OPEN | KPI | **out_of_scope_for_v0.1** | KPI category not available; planning-only. |
| GAP-SHW-009 | LOW | OPEN | Procedure | **compatible_with_gap** | Procedure steps deferred to semantic metadata; reference-only. |
| GAP-SHW-010 | MEDIUM | OPEN | VFReadiness | **compatible_with_gap** | Required model parameters missing → readiness stays LogicalOnly/FirstOrderReady; blocks parameterized runtime only. |
| GAP-SHW-011 | LOW | OPEN | VFReadiness | **compatible_with_gap** | Object-class mapping is draft; must be validated against a real VF library before use. |
| GAP-SHW-012 | LOW | OPEN | VFReadiness | **out_of_scope_for_v0.1** | Calibration out of scope; CalibratedReady never claimed. |

## 5.1 Summary

- **blocks_binding**: NONE — no gap prevents the exact-one canonical binding
  structure; canonical identity is complete and unambiguous for the first slice.
- **blocks_runtime**: GAP-SHW-001, GAP-SHW-002 (the two HIGH OPEN gaps).
- **compatible_with_gap**: GAP-SHW-003, 004, 006, 007, 009, 010, 011.
- **out_of_scope_for_v0.1**: GAP-SHW-005, 008, 012.

Net effect: semantic compatibility is not blocked by any gap; runtime/execution
must remain fail-closed on the two HIGH gaps (plus the general `NOT_AUTHORIZED`
status).
