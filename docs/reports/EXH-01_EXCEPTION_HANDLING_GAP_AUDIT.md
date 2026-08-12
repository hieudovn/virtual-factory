# EXH-01 — Exception Handling Gap Audit

> **Baseline**: `67ade9c`  
> **Scope**: Assembly (ASSY) Indexed Line  

---

## 1. Findings by Severity

### CRITICAL — Must Fix Before Physical Freeze

| # | Finding | File | Impact |
|---|---------|------|--------|
| C1 | **LINE-IN/LINE-OUT labels describe off-line repair workflow not supported by runtime** | `assy_demo.js:753-765` | UI is semantically misleading: shows "QC HOLD → REPAIR" and "REPAIR → RETURN" but runtime has no LINE_OUT/LINE_IN mechanism |
| C2 | **No explicit FAILED_FINAL handling in step loop** | `demo_composition.py:136-138` | Indexing is implicitly blocked by station-not-complete; but controller should explicitly detect and surface FAILED_FINAL |

### HIGH — Should Fix Before MES/Production

| # | Finding | File | Impact |
|---|---------|------|--------|
| H1 | `QualityStatus.HOLD` declared but never used | `quality_records.py:29` | Confusing for developers; code inspection expected HOLD to be set somewhere |
| H2 | `QualityRecord.disposition` uses `str` not `QualityDisposition` enum | `quality_records.py:91` | Type inconsistency with `quality.py` |
| H3 | `MESAdapter` is contract-only, never connected to runtime | `mes_adapter.py:118-168` | No MES event emission from ASSY runtime |
| H4 | No bridge from `LineEvent` → `MESEvent` | `mes_adapter.py` | Assembly runtime events are internal-only |
| H5 | SCRAP disposition has no route in TIPA topology | `tipa.py:77` | Only PASS and REWORK edges exist |

### MEDIUM — Clarify But Does Not Block

| # | Finding | File | Impact |
|---|---------|------|--------|
| M1 | Dual lifecycle model: `WipStatus` + `WipLifecycle` | `line_runtime.py:55-61`, `wip.py:15-22` | Two different lifecycle representations |
| M2 | `_HOLD_STATUSES` excludes `QualityStatus.HOLD` | `demo_snapshot.py:335-338` | Technically correct but confusing |
| M3 | `_map_event_type()` missing HOLD/FAILED_FINAL mappings | `mes_adapter.py:171-182` | Can't emit HOLD events to MES |

### DEFER — Enhancement, Not Required for Demo

| # | Finding | File | Impact |
|---|---------|------|--------|
| D1 | No off-line repair routing in runtime | `line_runtime.py` | Requires significant runtime redesign |
| D2 | No SCRAP implementation in ASSY runtime | `line_runtime.py:487-494` | Defined in enums but unreachable |
| D3 | Equipment fault YAMLs unrelated to assembly quality | `configs/faults/*.yaml` | Different domain |

---

## 2. Recommendation Matrix

| Gap | Severity | Demo Impact | Architecture Impact | Fix Now? | Proposed Slice |
|-----|----------|-------------|---------------------|----------|----------------|
| C1 — LINE-IN/OUT labels | CRITICAL | UI is misleading | Low (label change) | **YES** | EXH-01-C01: Relabel to "QC HOLD" / "QC CLEAR" or add "CONCEPTUAL" marker |
| C2 — FAILED_FINAL explicit | CRITICAL | Controller ignores terminal state | Low (add check) | **YES** | EXH-01-C01: Add FAILED_FINAL detection in step loop |
| H1 — QualityStatus.HOLD dead code | HIGH | None | Low (deprecate) | Before MES | EXH-02: Deprecate or alias |
| H2 — disposition string vs enum | HIGH | None | Medium (refactor) | Before MES | EXH-02: Unify type |
| H5 — SCRAP no route | HIGH | None | Medium (add edge) | Before MES | EXH-03: Add SCRAP sink |
| H3/H4 — MES integration | HIGH | None | Large (new adapter) | Before MES | EXH-04: Wire LineEvent→MESEvent |
| M1-M3 — Clarifications | MEDIUM | None | Low | Any time | EXH-02 |
| D1-D3 — Deferred | DEFER | None | Large | Later | M7+ |

---

## 3. Current State: What IS Implemented

| Capability | Status |
|-----------|--------|
| Same-station quality check (AP03, AP06, AP08, AP11) | ✅ |
| FAIL → RETEST_PENDING | ✅ |
| NG → REINSPECT_PENDING | ✅ |
| Max attempts → FAILED_FINAL | ✅ |
| HOLD blocks conveyor indexing | ✅ |
| Quality history per WIP | ✅ |
| Scenario switching (HAPPY_PATH, AP06_FAIL_RETEST, AP08_NG_REINSPECT, FAILED_FINAL) | ✅ |
| Snapshot projection includes holds | ✅ |
| Overview shows exception sub-lines | ✅ |

## 4. Current State: What is NOT Implemented

| Capability | Status |
|-----------|--------|
| Off-line repair routing (LINE_OUT) | ❌ |
| Off-line return routing (LINE_IN) | ❌ |
| REWORK treatment (changing WIP state) | ❌ |
| SCRAP disposition execution | ❌ |
| MES event emission | ❌ |
| Runtime LINE_OUT/LINE_IN events | ❌ |

---

> **EXH-01 Gap Audit — COMPLETE**  
> **Recommended immediate action**: EXH-01-C01 — relabel LINE-IN/OUT to match current runtime truth
