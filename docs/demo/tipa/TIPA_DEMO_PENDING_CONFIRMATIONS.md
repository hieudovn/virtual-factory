# TIPA Demo — Pending Confirmations

> **Status**: M6-S01. Items awaiting TIPA clarification.
> Development proceeds with provisional values where marked.

---

| ID | Item | Provisional Demo Behavior | Impact if Changed | Change Type |
|----|------|--------------------------|-------------------|-------------|
| PTC-01 | SSO2 thermal/shrink vs hydraulic press | Configurable `sso2_operation_type`; default "shrink_fit" | Low | CONFIG_ONLY |
| PTC-02 | SSO2 output WIP name + serial convention | `SSO2-{seq:04d}`; internal naming only | Medium | CONFIG_ONLY |
| PTC-03 | RSO2 detailed operations + release criteria | Generic "rotor_assembly" operation; release after cycle time | Low | CONFIG_ONLY |
| PTC-04 | RSO2 output WIP name + identity convention | `RSO2-{seq:04d}`; internal naming only | Medium | CONFIG_ONLY |
| PTC-05 | Exact AP04 component list | Configurable list: `[]` (empty placeholder; all items TBD by TIPA) | Low | CONFIG_ONLY |
| PTC-06 | AP04 join sequence + production identity semantics | Generic join: parent_A + parent_B + components → child; genealogy via `assembly_join` | Medium | SMALL_LOGIC_CHANGE |
| PTC-07 | AP06 FAIL / repair / retest routing | HOLD → RETEST (max 2) → PASS or HOLD | Medium | CONFIG_ONLY |
| PTC-08 | AP08 NG / reinspection routing | HOLD → REINSPECT (max 1) | Low | CONFIG_ONLY |
| PTC-09 | AP11 sampling + failed-lot/unit disposition | 100% inspection for demo | Low | CONFIG_ONLY |
| PTC-10 | Conveyor lane allocation / blocking / index | Single lane, indexed movement, downstream blocking | Medium | SMALL_LOGIC_CHANGE |
| PTC-11 | Actual station cycle times | Configurable `demo_cycle_time_s` per station; default 3s | Low | CONFIG_ONLY |
| PTC-12 | Product/model routing variants | Single motor model for demo | High | POTENTIAL_STRUCTURAL_CHANGE |

---

## Change Impact Summary

| Impact Type | Count | Items |
|-------------|-------|-------|
| CONFIG_ONLY | 9 | PTC-01,02,03,04,05,07,08,09,11 |
| SMALL_LOGIC_CHANGE | 2 | PTC-06,10 |
| POTENTIAL_STRUCTURAL_CHANGE | 1 | PTC-12 |

**Assessment**: 11/12 pending items can be resolved without structural code change.
Multiple product variants (PTC-12) would require broader routing changes; deferred post-demo.

---

## Items NOT Blocking Development

All 12 items have provisional demo values. No PTC item blocks M6-S02 implementation.
Development proceeds with configurable defaults for all pending items.
