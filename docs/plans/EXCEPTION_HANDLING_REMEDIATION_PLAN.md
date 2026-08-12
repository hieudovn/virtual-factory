# EXH-01-C01 — Exception Handling Remediation Plan (Corrected)

> **Baseline**: `53a481c`  
> **Corrected from**: EXH-01 (`67ade9c`)  

---

## 1. Corrected Remediation Gates

### EXH-01-C01 — Contract Correction (CURRENT — DOCS ONLY)
- Update semantic contract, gap audit, remediation plan per SA corrections
- Reclassify severity per corrected definitions
- Freeze authoritative runtime truth
- Zero production code changes

### EXH-UI-01 — Demo-safe Exception UI Alignment (Before Physical Freeze)
- LINE OUT / LINE IN may remain visible as contextual exception-handling concept
- Mark as CONCEPTUAL or OFF-LINE HANDLING
- Do NOT hardcode LINE OUT to AP06 or LINE IN to AP08
- Do NOT claim runtime movement that does not exist
- Do NOT place active WIP in off-line zone unless runtime supports it
- Production code: `assy_demo.js` labels only

### EXH-OBS-01 — Exception Observability (Optional, Pre-Demo)
- Additive snapshot/UI clarity for FAILED_FINAL
- Exception summary in overview/snapshot
- No controller business logic added
- Runtime already owns blocking + event emission correctly

### EXH-DOM-01 — Domain Model Cleanup (Post-Demo, Before MES)
- Split DetectionResult / TreatmentType / FinalDisposition into orthogonal types
- Resolve QualityStatus.HOLD semantics (deprecate or add orthogonal containment)
- Document WipStatus vs WipLifecycle distinction
- Do NOT alias HOLD to RETEST_PENDING

### EXH-CASE-01 — ExceptionCase Foundation (Post-Demo)
- Additive ExceptionCase model (orthogonal to WIP lifecycle)
- Exception lifecycle events
- 0..N ExceptionCases per WIP

### EXH-MES-01 — MES/CDM Exception Projection (After ExceptionCase)
- Wire LineEvent → MESEvent bridge
- Implement missing event type mappings
- Target authoritative ASSY runtime, not legacy topology

### EXH-SCRAP-01 — Scrap / Terminal Disposition (Before Productization)
- Design against authoritative `AssyLineRuntime`
- Define removal from conveyor/carrier
- Preserve WIP identity/history
- Define terminal snapshot/event semantics
- Do NOT implement via legacy `tipa.py` topology

### EXH-ROUTE-01 — Physical Off-Line Routing (Post-Demo, After Plant Validation)
- Implement LINE_OUT / LINE_IN in authoritative runtime
- Additive `exception_cases[]` / `offline_wips[]` contracts
- Do NOT use `positions[]` for off-line WIP
- No fixed station-to-station repair route until plant routing validates

---

## 2. Authoritative Ownership

| Concern | Owner | Rule |
|---------|-------|------|
| Exception state + blocking | Runtime | `AssyLineRuntime` owns FAILED_FINAL, HOLD, retest/reinspect |
| Exception display | Snapshot/UI | Additive fields for observability |
| Exception orchestration | NOT Controller | Controller orchestrates scenario selection only; never quality business logic |

---

## 3. Frozen `positions[]` Contract

> `positions[]` is the sole source of truth for current MAIN-LINE physical conveyor/station occupancy.

Off-line WIP must use additive contracts (e.g., `exception_cases[]`, `offline_wips[]`). Do not fabricate station occupancy for off-line WIP. Do not break the existing contract.

---

## 4. Demo Scope — What Ships in August

| Feature | Status |
|---------|--------|
| Same-station quality check + retest/reinspect | ✅ IN |
| FAILED_FINAL (runtime-owned, snapshot-visible) | ✅ IN |
| Scenario switching | ✅ IN |
| Quality history in popup | ✅ IN |
| Hold visualization on stations | ✅ IN |
| LINE OUT / LINE IN as contextual concept (EXH-UI-01) | ✅ IN (corrected labels) |
| LINE OUT / LINE IN as runtime routing | ❌ OUT |
| REWORK treatment | ❌ OUT |
| SCRAP execution | ❌ OUT |
| MES event emission | ❌ OUT |

---

> **EXH-01-C01 Remediation Plan — CORRECTED**  
> **Production code changed: NO**
