# EXH-01 — Exception Handling Remediation Plan

> **Baseline**: `67ade9c`  
> **Scope**: Sequential remediation gates for August demo  

---

## 1. Remediation Gates

### EXH-01-C01: UI Label Correction (IMMEDIATE — Before Physical Freeze)

**Problem**: LINE-IN/LINE-OUT labels describe off-line repair not supported by runtime.

**Action**:
- Relabel "LINE IN: QC HOLD → REPAIR" → "QC HOLD" (with "retest pending" subtitle)
- Relabel "LINE OUT: REPAIR → RETURN" → "QC CLEAR" (with "reinspect pending" subtitle)
- Add `(CONCEPTUAL)` marker if keeping LINE IN/OUT naming
- Add FAILED_FINAL explicit detection in demo_controller step loop

**Files**: `assy_demo.js` only  
**Risk**: None — label change only  
**Test impact**: No runtime changes  

### EXH-02: Domain Model Cleanup (Before MES)

**Problems**: `QualityStatus.HOLD` dead code, `str` vs enum inconsistency, dual lifecycle models.

**Actions**:
1. Deprecate `QualityStatus.HOLD` or alias to RETEST_PENDING
2. Unify `QualityRecord.disposition` to use `QualityDisposition` enum
3. Document `WipStatus` vs `WipLifecycle` distinction
4. Add missing `_map_event_type()` entries for HOLD/FAILED_FINAL

**Files**: `quality_records.py`, `demo_snapshot.py`, `mes_adapter.py`  
**Risk**: Low — internal refactoring  
**Test impact**: Update enum references in tests  

### EXH-03: SCRAP Sink (Before MES)

**Problem**: SCRAP defined everywhere but no route exists in TIPA topology.

**Actions**:
1. Add SCRAP sink node in TIPA topology
2. Add SCRAP edge from final-quality gate
3. Implement `_execute_quality_station()` SCRAP disposition for FAILED_FINAL with SCRAP override

**Files**: `tipa.py`, `handlers.py`, `line_runtime.py`  
**Risk**: Medium — new topology edge  
**Test impact**: New scenario: FAILED_FINAL → SCRAP  

### EXH-04: MES Integration (Before Production)

**Problem**: No bridge from `LineEvent` to `MESEvent`.

**Actions**:
1. Create `AssyLineMESAdapter` that converts `LineEvent` → `MESEvent`
2. Wire adapter into `DemoController` as optional output
3. Implement event types: QUALITY_RESULT, QUALITY_HOLD, RETEST, REINSPECT, FAILED_FINAL

**Files**: New file `assy_mes_adapter.py`, `demo_controller.py`  
**Risk**: Medium — new module  
**Test impact**: New integration tests  

### EXH-05: Off-Line Routing (Post-Demo)

**Problem**: LINE_OUT/LINE_IN not implemented in runtime.

**Actions**:
1. Design `ExceptionCase` model
2. Add off-line WIP state to `WipStatus`
3. Implement `line_out()`, `line_in()` on `AssyLineRuntime`
4. Update `positions[]` contract for off-line tracking

**Files**: `line_runtime.py`, `demo_snapshot.py`, new `exception_case.py`  
**Risk**: High — core runtime change  
**Test impact**: Significant — all quality scenarios affected  

---

## 2. Demo Scope — What Ships in August

| Feature | Status |
|---------|--------|
| Same-station quality check + retest/reinspect | ✅ IN |
| FAILED_FINAL detection | ✅ IN (already working, add explicit controller check) |
| Scenario switching | ✅ IN |
| Quality history in popup | ✅ IN |
| Hold visualization on stations | ✅ IN |
| QC HOLD / QC CLEAR labels (corrected) | ✅ IN (EXH-01-C01) |
| LINE OUT / LINE IN (off-line routing) | ❌ OUT (EXH-05, post-demo) |
| REWORK treatment | ❌ OUT |
| SCRAP execution | ❌ OUT (EXH-03, before MES) |
| MES event emission | ❌ OUT (EXH-04, before MES) |

---

## 3. Current UI → Runtime Truth Map

| UI Shows | Runtime Actually Does | Match? |
|----------|----------------------|--------|
| AP06 "QC HOLD → REPAIR" | RETEST_PENDING: same-station retest | ⚠️ MISLEADING |
| AP08 "REPAIR → RETURN" | REINSPECT_PENDING: same-station reinspect | ⚠️ MISLEADING |
| "REWORK / HOLD AREA" | Contextual only — no WIP goes there | ✅ MATCH (labeled as contextual) |
| Is_quality_hold flag | Correctly derived from RETEST_PENDING/REINSPECT_PENDING/FAILED_FINAL | ✅ MATCH |
| Held_reason text | Correctly shows "FAIL (attempt X)" | ✅ MATCH |

---

> **EXH-01 Remediation Plan — COMPLETE**  
> **Next step**: SA authorize EXH-01-C01 for immediate UI label correction
