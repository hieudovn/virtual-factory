# DG06-01-C02 — SA Review Report

> **Status**: READY FOR SA REVIEW  
> **Gate**: DG06-01-C02 — Public-Snapshot WIP Visual Boundary Correction  
> **Baseline**: `5ca429f` (DG06-01-C01)  
> **Current head**: `e3b723a`  
> **Date**: 2026-08-12  

---

## 1. Purpose

Correct the WIP visual-state evolution contract (Section 8-A of DG06) to align with **public post-index snapshot semantics**. The C01 version had station boundaries one processing step too early at several stations (AP04, AP05, AP06, AP09).

---

## 2. Root Cause

The ASSY runtime flow is:

1. WIP is physically at a station during dwell
2. Station processing **completes** during dwell
3. Line **indexes**
4. Public post-step snapshot shows WIP at the **NEXT** position

Therefore the visual token at a given `positions[]` entry represents the WIP state **upon arrival**, not after the current station's operation completes.

C01 incorrectly showed the operation result at the station where the operation occurs (e.g., MTR JOINED at AP04). C02 corrects this: the operation result becomes visible only after index to the next position.

---

## 3. Key Corrections

| Position | C01 (wrong) | C02 (correct) | Reason |
|----------|------------|---------------|--------|
| AP04 | MTR JOINED | **STATOR ASSY** | JOIN child created but not visible until index to AP05 |
| AP05 | MTR PRE-TEST | **MTR JOINED** | AP04 JOIN completed → visible at AP05 |
| AP06 | TESTED MTR | **MTR PRE-TEST** | AP05 mechanical done → visible at AP06; test not yet passed |
| AP07 | TESTED MTR | **TESTED MTR** | ✓ (unchanged) |
| AP09 | PACKED GOODS | **TESTED MTR** | Boxing occurs at AP09; not visible until index to AP10 |
| AP10 | PACKED GOODS | **PACKED GOODS** | AP09 boxing completed → visible at AP10 |

---

## 4. Final Canonical Mapping

| Position | Token | Operation that produced this state |
|----------|-------|-----------------------------------|
| PRE-ASSY | STATOR ASSY | Upstream SSO2 feed |
| AP01 | STATOR ASSY | — |
| AP02 | STATOR ASSY | — |
| AP03 | STATOR ASSY | — |
| AP04 | STATOR ASSY | JOIN occurs; child not yet downstream |
| AP05 | MTR JOINED | AP04 JOIN completed + indexed |
| AP06 | MTR PRE-TEST | AP05 mechanical completed + indexed |
| AP07 | TESTED MTR | AP06 successful test + indexed |
| AP08 | TESTED MTR | AP06 test was successful |
| AP09 | TESTED MTR | Boxing occurs here |
| AP10 | PACKED GOODS | AP09 boxing completed + indexed |
| AP11 | PACKED GOODS | AP10 packaging completed + indexed |
| OUT | No token | Unless positions[] has occupant |

---

## 5. Manufacturing vs Visual Distinction

| Station | Manufacturing operation | Visual token visible at |
|---------|------------------------|------------------------|
| AP04 | JOIN | AP05 (after index) |
| AP05 | Mechanical completion | AP06 (after index) |
| AP06 | Electrical TEST | AP07 (after pass + index) |
| AP09 | Boxing | AP10 (after index) |

---

## 6. Exception Semantics (New)

### AP06 FAIL / HOLD / RETEST_PENDING
- Base visual: `MTR PRE-TEST` (motor not yet successfully tested)
- Quality overlay: FAIL (red) or HOLD (amber)
- Never show as `TESTED MTR` until retest passes + index to AP07

### AP08 NG / REINSPECT_PENDING
- Base visual: `TESTED MTR` (AP06 test was successful)
- Quality overlay: NG (red) or HOLD (amber)
- Base category unchanged — reinspect is quality overlay only

### FAILED_FINAL
- Base visual follows position rules (PRE-TEST at AP06, TESTED at AP08)
- Terminal state: FAIL overlay + "FAILED_FINAL" context
- Inspector preserves all attempt records

---

## 7. New Invariants Added

- **Invariant #5**: No transient pre-index state. Public snapshot is post-index. Effects of station operations become visible only after the WIP indexes to the next position.
- RSO2 documented as branch component feed only (ROTOR token at branch input point, never fabricated as main-conveyor occupancy)

---

## 8. Changed Files

```
docs/ui/M6_S04B_DG06_PHYSICAL_LAYER_REALISM_AND_BRIGHT_UI.md   (+79 / -22)
```

---

## 9. Scope Confirmation

```
Production code modified: NONE
I09-P01 implementation started: NO
I07 started: NO
I08 started: NO
M6-S05 started: NO
```

---

> **DG06-01-C02 is READY FOR SA REVIEW at `e3b723a`.**
