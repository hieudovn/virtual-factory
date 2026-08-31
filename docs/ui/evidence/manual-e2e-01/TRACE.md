# MANUAL-E2E-01 — Authoritative Truth Trace

- Mode: MANUAL | Scenario: HAPPY_PATH | Sub-line: ASSY-SL01
- Source WIP: SSO2-0001 (carrier PAL-001) → child MTR-0001

| Seq | Sim time | Station | WIP | Op state before | Operator action | Operation result | Quality result | Quality status | Routing | Eligible after |
|---:|---:|---|---|---|---|---|---|---|---|---|
| 1 | 10s | PRE-ASSY | SSO2-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 2 | 20s | AP01 | SSO2-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 3 | 30s | AP02 | SSO2-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 4 | 40s | AP03 | SSO2-0001 | AWAITING_COMPLETION | CONFIRM_AND_COMPLETE | CONFIRMED |  | clear | CONTINUE | yes |
| 5 | 50s | AP04 | SSO2-0001 | AWAITING_COMPLETION | JOIN_COMPLETE | JOIN_COMPLETE |  | clear | CONTINUE | yes |
| 6 | 60s | AP05 | MTR-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 7 | 70s | AP06 | MTR-0001 | AWAITING_DECISION | CONFIRM + PASS | TEST_COMPLETE | PASS | clear | CONTINUE | yes |
| 8 | 80s | AP07 | MTR-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 9 | 90s | AP08 | MTR-0001 | AWAITING_DECISION | CONFIRM + PASS | INSPECTION_COMPLETE | PASS | clear | CONTINUE | yes |
| 10 | 100s | AP09 | MTR-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 11 | 110s | AP10 | MTR-0001 | AWAITING_COMPLETION | DONE | DONE |  | clear | CONTINUE | yes |
| 12 | 120s | AP11 | MTR-0001 | AWAITING_DECISION | CONFIRM + PASS | CONFIRMED | PASS | clear | CONTINUE | no |
| 13 | 130s | AP11 | MTR-0001 | AWAITING_COMPLETION | RELEASE | RELEASED | PASS | clear | CONTINUE | yes |

## AP04 genealogy handoff
- `MTR-0001` ← `SSO2-0001` + `RSO2-0001` @ AP04 (t=50s)

## Quality records (exactly once)
- AP06 #1 TEST: PASS
- AP08 #1 VISUAL_INSPECTION: PASS
- AP11 #1 FINAL_QC: PASS

## Final state: RELEASED