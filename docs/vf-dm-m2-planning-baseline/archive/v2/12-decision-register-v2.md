# 12-v2 — Decision Register (Corrected)

**Date:** 2026-08-05  
**Replaces:** `12-decision-register.md`

| ID | Question | PM Recommendation | SA Disposition |
|----|----------|-------------------|----------------|
| D-001 | SVG for MVP? | SVG | **Approved** |
| D-002 | Full snapshot vs delta? | Full for MVP, delta at M6 | **Approved with adaptive publication** |
| D-003 | Shared FastAPI process? | Yes, separate service ownership | **Approved** |
| D-004 | Step one event? | Yes, core engine | **Approved for core** |
| D-005 | Live injection vs pause? | Live acceptance, safe-point application | **Modified: safe-point, no epsilon** |
| D-006 | Handler mutation model? | Direct with fail-stop rules, no scheduler access | **Conditional: no scheduler, fail-stop** |
| D-007 | In-memory vs persistence? | In-memory for MVP | **Approved** |
| D-008 | TIPA layout location? | JS file + server YAML | **Approved** |
| D-009 | Contract location? | Python models + YAML | **Approved** |
| D-010 | Command concurrency? | Sequential FIFO | **Approved with server sequence** |
| D-011 | Authentication? | None + --unsafe-demo flag | **Approved** |
| D-012 | Operator modeling? | Anonymous role | **Approved** |
| D-013 | KPI set? | 6 provisional metrics | **Approved as provisional** |
| D-014 | CI timing? | M2-S01 | **Approved** |
| D-015 | UI extraction scope? | Incremental, small utilities only | **Approved** |
| D-016 | Continuous renderer? | **Unchanged. No renames.** | **Modified: protect, do not rename** |
| D-017 | Vanilla JS? | Yes for MVP | **Approved** |
| D-018 | Branch strategy? | Per-slice feature branches | **Approved** |
| D-019 | One active run? | Yes for M2–M5 | **Approved** |
| D-020 | REST=commands, WS=snapshots? | Yes for MVP | **Approved** |
| D-021 | Separate /discrete page? | Yes | **Approved** |
| D-022 | M2: 7 slices? | Yes (C-013) | **Approved** |
| D-023 | Transport in M4? | Yes, not M2 | **Approved** |

**All 23 decisions resolved.**
