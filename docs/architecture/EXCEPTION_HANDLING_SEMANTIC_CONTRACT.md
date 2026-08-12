# Exception Handling — Canonical Semantic Contract

> **Status**: DESIGN AUTHORITY — Locked for EXH-01  
> **Baseline**: `67ade9c`  
> **Scope**: Assembly (ASSY) Indexed Line Demo  

---

## 1. Taxonomy

### 1.1 Detection Result
*What was observed at a quality station.*

| Term | Definition | Examples |
|------|-----------|----------|
| **PASS** | All measurements/checks within spec | `PASS` |
| **FAIL** | One or more measurements out of spec — retestable | `FAIL` |
| **NG** | Visual/surface defect detected — reinspectable | `NG` |

### 1.2 Containment State
*What the line does with the WIP after detection.*

| Term | Definition | Implementation |
|------|-----------|----------------|
| **CLEAR** | No quality issue; WIP may proceed | QualityStatus.CLEAR |
| **RETEST_PENDING** | FAIL at TEST station; retest required | QualityStatus.RETEST_PENDING |
| **REINSPECT_PENDING** | NG at VISION station; reinspect required | QualityStatus.REINSPECT_PENDING |
| **FAILED_FINAL** | Max attempts exhausted; terminal hold | QualityStatus.FAILED_FINAL |

### 1.3 Exception Routing Actions
*Where the WIP goes for handling.*

| Term | Definition | Current Demo Support |
|------|-----------|---------------------|
| **STAY_AT_STATION** | WIP remains at current station for retest/reinspect | ✅ Fully implemented |
| **LINE_OUT** | WIP physically leaves the main conveyor for off-line handling | ❌ NOT IMPLEMENTED (UI label only) |
| **LINE_IN** | WIP physically returns to main conveyor after off-line handling | ❌ NOT IMPLEMENTED (UI label only) |
| **RETURN_TO_STATION** | WIP returns to a specific station (not necessarily the detection station) | ❌ NOT IMPLEMENTED |

### 1.4 Treatment
*What is done to the WIP during exception handling.*

| Term | Definition | Current Demo Support |
|------|-----------|---------------------|
| **INSPECTION_ONLY** | Visual/measurement inspection without modification | ⚠️ Implicit in retest/reinspect |
| **REWORK** | Active correction of the WIP | ❌ NOT IMPLEMENTED (M3 topology has REWORK edge but ASSY runtime never uses it) |
| **NO_ACTION** | Re-test without treatment | ✅ Implicit in current retest |

### 1.5 Verification
*How the exception is confirmed resolved.*

| Term | Definition | Implementation |
|------|-----------|---------------|
| **RETEST** | Re-run the same test at the same station (AP06) | ✅ `RETEST_PENDING → CLEAR on PASS` |
| **REINSPECT** | Re-run visual inspection at the same station (AP08) | ✅ `REINSPECT_PENDING → CLEAR on PASS` |

### 1.6 Final Disposition
*Ultimate outcome of the exception case.*

| Term | Definition | Implementation |
|------|-----------|----------------|
| **RESUME** | WIP continues normal production | ✅ CLEAR state after retest PASS |
| **RELEASE** | WIP exits the line (at AP11) | ✅ `WipLifecycle.RELEASED` |
| **FAILED_FINAL** | Terminal hold; WIP cannot proceed | ✅ Blocks indexing, requires operator intervention |
| **SCRAP** | WIP scrapped and removed from line | ❌ Defined in enums but NOT IMPLEMENTED in ASSY runtime |

---

## 2. Canonical Exception Flow

### 2.1 Current Demo Implementation (Same-Station Retest)

```
DETECT FAIL/NG at quality station
      │
      ▼
SET RETEST_PENDING / REINSPECT_PENDING
      │
      ▼
CONVEYOR BLOCKS (station not complete)
      │
      ▼
DWELL timer resets to 0.0
      │
      ▼
RE-TEST / RE-INSPECT at same station
      │
      ├── PASS ──► CLEAR → WIP proceeds
      │
      └── FAIL/NG (max attempts reached) ──► FAILED_FINAL → terminal hold
```

### 2.2 Future Target (Off-Line Handling — NOT IMPLEMENTED)

```
DETECT FAIL/NG at quality station
      │
      ▼
HOLD + LINE_OUT
      │
      ▼
OFF-LINE INSPECTION / DIAGNOSIS
      │
      ├── NO REWORK NEEDED ──► RE-VERIFY
      │                              │
      └── REWORK REQUIRED ──► REWORK ──► RE-VERIFY
                                            │
                                    LINE_IN + RETEST/REINSPECT
                                            │
                                    ├── PASS ──► RESUME
                                    └── FAIL ──► FAILED_FINAL / SCRAP
```

---

## 3. Compatibility Constraints

### Preserved Contracts

| Contract | Status |
|----------|--------|
| `positions[]` as sole occupancy truth | ✅ PRESERVED |
| `DemoSnapshot` structure | ✅ PRESERVED |
| `QualityRecord` history per WIP | ✅ PRESERVED |
| `is_quality_hold` → blocks indexing | ✅ PRESERVED |
| MES adapter boundary | ✅ PRESERVED (contract, not implementation) |
| Scenario definitions (HAPPY_PATH, AP06_FAIL_RETEST_PASS, AP08_NG_REINSPECT_PASS, FAILED_FINAL) | ✅ PRESERVED |

### Semantic Debt — To Be Addressed Before MES/Production

| Issue | Impact |
|-------|--------|
| `QualityStatus.HOLD` declared but never used | Confusing enum — should be deprecated or aliased |
| `QualityRecord.disposition` uses `str` not `QualityDisposition` enum | Type inconsistency with `quality.py` |
| Dual `WipStatus` / `WipLifecycle` models | Two different lifecycle representations for same entity |
| `_HOLD_STATUSES` excludes `QualityStatus.HOLD` | Consistent with dead code but confusing for readers |
| No SCRAP implementation in ASSY runtime | Defined everywhere, used nowhere |

---

## 4. UI Labeling Rules

| UI Element | Canonical Meaning | Current UI |
|-----------|-------------------|------------|
| **LINE IN** | WIP returns to main line from off-line handling | At AP06: "QC HOLD → REPAIR" |
| **LINE OUT** | WIP leaves main line for off-line handling | At AP08: "REPAIR → RETURN" |
| **ASSY INPUT** | Line start / entry point | Not yet implemented |
| **ASSY OUTPUT** | Line end / discharge point | Not yet implemented |
| **HOLD AREA** | Contextual rework/hold zone | "REWORK / HOLD AREA" |
| **QC HOLD** | Active quality hold on WIP | Shown on station with held_reason |

**Rule**: LINE IN/OUT labels describe exception routing. Do NOT reuse for line start/end.

---

> **This contract is frozen for the August demo scope.**  
> Off-line routing (LINE_OUT/LINE_IN) is declared as NOT IMPLEMENTED.  
> UI labels are contextual/conceptual and backed by same-station retest/reinspect only.
