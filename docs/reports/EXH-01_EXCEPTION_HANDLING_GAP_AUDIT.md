# EXH-01-C01 — Exception Handling Gap Audit (Corrected)

> **Baseline**: `53a481c`  
> **Corrected from**: EXH-01 (`67ade9c`)  
> **Scope**: Assembly (ASSY) Indexed Line  

---

## 1. Severity Definitions

| Level | Criteria |
|-------|----------|
| **CRITICAL** | Demo/runtime tells a materially false manufacturing story OR violates an authoritative invariant |
| **HIGH** | Architecture likely to cause incorrect future implementation/integration |
| **MEDIUM** | Observability, naming, dead semantic code, maintainability |
| **DEFER** | Requires real plant routing/business rules not yet known |

---

## 2. Findings by Corrected Severity

### CRITICAL — Must Fix Before Physical Freeze

| # | Finding | File | Impact |
|---|---------|------|--------|
| C1 | **LINE-IN/OUT labels imply fixed AP06→AP08 off-line repair route not supported by runtime** | `assy_demo.js:753-765` | UI is semantically misleading |

### HIGH — Should Fix Before MES/Production

| # | Finding | File |
|---|---------|------|
| H1 | `QualityStatus.HOLD` declared but never used — generic containment vs specific RETEST_PENDING | `quality_records.py:29` |
| H2 | `QualityDisposition` mixes result, treatment, and terminal disposition (PASS/FAIL/REWORK/SCRAP, no NG) | `quality.py:12` |
| H3 | MES adapter (`MESAdapter`) is contract-only, never connected to runtime | `mes_adapter.py:118` |
| H4 | No bridge from `LineEvent` → `MESEvent` | `mes_adapter.py` |
| H5 | `tipa.py` is legacy M3 topology — not authoritative for August ASSY demo; SCRAP edge would target wrong module | `tipa.py:77` |

### MEDIUM — Clarify But Does Not Block

| # | Finding | File |
|---|---------|------|
| M1 | No explicit FAILED_FINAL surfacing in demo controller — runtime owns blocking correctly but snapshot/UI may not surface it clearly | `demo_composition.py:136` |
| M2 | Dual lifecycle model: `WipStatus` + `WipLifecycle` | `line_runtime.py:55` |
| M3 | `_map_event_type()` missing HOLD/FAILED_FINAL entries | `mes_adapter.py:171` |

### DEFER — Enhancement, Not Required for Demo

| # | Finding |
|---|---------|
| D1 | No off-line repair routing in authoritative runtime (LINE_OUT/LINE_IN) |
| D2 | No SCRAP execution in authoritative ASSY runtime |
| D3 | No ExceptionCase model / exception lifecycle events |

---

## 3. Corrected Recommendation Matrix

| Gap | Severity | Demo Impact | Fix Now? | Proposed Slice |
|-----|----------|-------------|----------|----------------|
| C1 — LINE-IN/OUT labels | CRITICAL | UI misleading | YES | EXH-UI-01: relabel as CONCEPTUAL or remove fixed AP06/AP08 mapping |
| M1 — FAILED_FINAL surfacing | MEDIUM | Observability | Optional | EXH-OBS-01: snapshot/UI clarity |
| H1 — HOLD semantics | HIGH | None | Before MES | EXH-DOM-01 |
| H2 — Disposition enum mixing | HIGH | None | Before MES | EXH-DOM-01 |
| H5 — Legacy topology vs authoritative | HIGH | None | Before SCRAP | EXH-SCRAP-01 (target authoritative runtime) |
| H3/H4 — MES integration | HIGH | None | Before MES | EXH-MES-01 |
| D1-D3 — Deferred | DEFER | None | Post-demo | EXH-CASE-01, EXH-ROUTE-01 |

---

## 4. Frozen Demo Truth

| Capability | Status |
|-----------|--------|
| Same-station quality check + retest/reinspect | ✅ |
| FAIL → RETEST_PENDING, NG → REINSPECT_PENDING | ✅ |
| Max attempts → FAILED_FINAL (runtime-owned) | ✅ |
| HOLD blocks conveyor indexing | ✅ |
| Runtime emits QUALITY_FAILED_FINAL, QUALITY_WAITING_DISPOSITION | ✅ |
| Controller does NOT own quality business logic | ✅ |
| LINE OUT / LINE IN off-line routing | ❌ NOT IMPLEMENTED |
| REWORK treatment | ❌ NOT IMPLEMENTED |
| SCRAP execution | ❌ NOT IMPLEMENTED |

---

> **EXH-01-C01 Gap Audit — CORRECTED**  
> **Production code changed: NO**
  
> **Scope**: Assembly (ASSY) Indexed Line  

