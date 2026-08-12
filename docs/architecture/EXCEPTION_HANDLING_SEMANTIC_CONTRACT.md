# Exception Handling — Canonical Semantic Contract

> **Status**: DESIGN AUTHORITY — Locked for EXH-01-C01  
> **Baseline**: `53a481c` (corrected from `67ade9c`)  
> **Scope**: Assembly (ASSY) Indexed Line Demo  

---

## 1. Six-Layer Taxonomy

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
| **HOLD** (generic) | Reserved for future generic containment — NOT equivalent to RETEST_PENDING | Declared but unused in current demo |

### 1.3 Routing / Transfer
*Where the WIP goes for exception handling.*

| Term | Definition | Current Demo Support |
|------|-----------|---------------------|
| **STAY_AT_STATION** | WIP remains at current station for retest/reinspect | ✅ Fully implemented |
| **LINE_OUT** | WIP physically leaves the main conveyor for off-line handling | ❌ NOT IMPLEMENTED (contextual UI concept only) |
| **LINE_IN** | WIP physically returns to main conveyor after off-line handling | ❌ NOT IMPLEMENTED (contextual UI concept only) |

**Critical rule**: LINE OUT / LINE IN are routing concepts inside Exception Handling. They are NOT line start/end markers. Do NOT hardcode LINE OUT to AP06 or LINE IN to AP08.

### 1.4 Treatment
*What is done to the WIP during exception handling.*

| Term | Definition | Current Demo Support |
|------|-----------|---------------------|
| **INSPECTION_ONLY** | Visual/measurement inspection without modification | ⚠️ Implicit in retest/reinspect |
| **REWORK** | Active correction/repair of the WIP | ❌ NOT IMPLEMENTED |

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
| **FAILED_FINAL** | Terminal hold; WIP cannot proceed | ✅ Blocks indexing; runtime owns this state |
| **SCRAP** | WIP scrapped and removed from line | ❌ Defined in enums but NOT IMPLEMENTED in authoritative ASSY runtime |

---

## 2. Canonical Exception Flow

### 2.1 Current Demo Implementation (Same-Station Retest/Reinspect — FROZEN)

```
DETECT FAIL/NG at quality station
      │
      ▼
SET RETEST_PENDING / REINSPECT_PENDING
      │
      ▼
CONVEYOR BLOCKS (station not complete; runtime owns blocking logic)
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
                                              (runtime emits QUALITY_FAILED_FINAL,
                                               then QUALITY_WAITING_DISPOSITION)
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

## 3. Authoritative Ownership

| Concern | Owner |
|---------|-------|
| Exception state and blocking behavior | **Runtime** (`AssyLineRuntime`) |
| Exception observability/display | **Snapshot / UI** |
| Exception orchestration | **NOT Controller** — controller orchestrates scenario selection only |

> **Rule**: Controller does NOT own quality business logic. Runtime owns state. Snapshot exposes it.

---

## 4. Compatibility Constraints

### Preserved Contracts

| Contract | Status |
|----------|--------|
| `positions[]` as sole main-line occupancy truth | ✅ FROZEN |
| `positions[]` must NOT be used for off-line WIP tracking | ✅ FROZEN |
| Off-line WIP must use additive contracts (e.g., `exception_cases[]`, `offline_wips[]`) | ✅ RULE |
| `DemoSnapshot` structure | ✅ PRESERVED |
| `QualityRecord` history per WIP | ✅ PRESERVED |
| `is_quality_hold` → blocks indexing | ✅ PRESERVED |

---

## 5. Future Type Architecture (EXH-DOM-01, NOT IMPLEMENTED)

Current `QualityDisposition` enum mixes detection result, treatment, and terminal disposition. Future target:

```text
QualityResult:      PASS | FAIL | NG
TreatmentType:      NONE | INSPECTION_ONLY | ADJUSTMENT | REWORK | REPAIR
FinalDisposition:   RESUME | RELEASE | SCRAP | FAILED_FINAL
```

Do NOT implement now. Documented as target for EXH-DOM-01.

---

## 6. Future ExceptionCase Model (EXH-CASE-01, NOT IMPLEMENTED)

```
WIP
 ├── manufacturing lifecycle
 ├── physical location/occupancy (positions[])
 ├── quality history
 └── 0..N ExceptionCase
      ├── exception_id
      ├── detected_at_station
      ├── trigger_type / trigger_result
      ├── containment_status
      ├── handling_mode (ON_LINE / OFF_LINE)
      ├── line_out_occurred / line_in_occurred
      ├── treatment_type
      ├── verification_type
      └── final_disposition
```

ExceptionCase is orthogonal to WIP lifecycle. One WIP may have multiple exception cases.

---

## 7. UI Labeling Rules

| UI Element | Canonical Meaning | Rule |
|-----------|-------------------|------|
| **LINE OUT** | WIP leaves main line for off-line handling | May appear as contextual/conceptual architecture; mark as CONCEPTUAL if runtime does not support |
| **LINE IN** | WIP returns to main line after off-line handling | Same rule as LINE OUT |
| **QC HOLD** | Active quality hold | Shown on station with held_reason from runtime |
| **OFF-LINE HANDLING** | Conceptual zone for exception handling | Contextual only; no active WIP unless runtime supports |
| **ASSY INPUT / OUTPUT** | Line start/end boundaries | Do NOT reuse LINE IN/OUT for these |

---

## 8. Frozen Demo Truth (August 2026)

### AP06 (TEST)
FAIL → RETEST_PENDING → WIP stays at AP06 → retest at same station → PASS: CLEAR → continue → max attempts: FAILED_FINAL

### AP08 (VISION)
NG → REINSPECT_PENDING → WIP stays at AP08 → reinspect at same station → PASS: CLEAR → continue → max attempts: FAILED_FINAL

**No actual LINE OUT, LINE IN, REWORK, or SCRAP in authoritative August runtime.**

---

> **This contract is frozen for EXH-01-C01.**  
> **DOCS ONLY — zero production code changes.**
  

