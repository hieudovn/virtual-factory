# M6-S04B-DG02.1 — Multi-Line / Repeated-Process Visualization Addendum

> **Status**: Design architecture — documentation only.  
> **Parent**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` (canonical UI/UX authority)  
> **Date**: 2026-08-11

---

## 1. Purpose

This addendum captures the clarified TIPA multi-process topology and its implications for UI/UX architecture. The canonical design guide defines the general multi-line principles (Section 20). This document applies those principles specifically to TIPA.

**No runtime implementation. No UI changes. No M6-S05.**

---

## 2. TIPA Production Topology

TIPA simulation is NOT a single production process. It consists of **6 parallel process/line instances**, all based on a common ASSY process template.

```
TIPA Motor Production Area
│
├── Hydraulic Group (SSO2 variant: Hydraulic Press)
│   ├── Line/Process 01
│   ├── Line/Process 02
│   └── Line/Process 03
│
└── Thermal Group (SSO2 variant: Thermal Press)
    ├── Line/Process 04
    ├── Line/Process 05
    └── Line/Process 06
```

### Common Process Template

Each instance follows the same ASSY process:

```
SSO2 Variant (Hydraulic or Thermal)
    ↓
PRE-ASSY → AP01 → AP02 → AP03 → AP04 → AP05
→ AP06 → AP07 → AP08 → AP09 → AP10 → AP11
→ Finished Product

RSO2 → AP04 JOIN
```

### Variant Difference

| Aspect | Hydraulic | Thermal |
|--------|-----------|---------|
| SSO2 upstream | Hydraulic Press | Thermal Press |
| Primary difference | Test/profile behavior | Test/profile behavior |
| Downstream ASSY | Common template | Common template |

Future differences between variants SHOULD be modeled through configuration/variant specialization, not duplicated implementations.

---

## 3. Architecture: Process Definition vs Variant vs Instance

Three distinct concepts:

```
┌─────────────────────────────────┐
│ Process Definition              │  ← Common ASSY template
│ (stations, routing, quality)    │
└────────────┬────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌─────────┐    ┌─────────┐
│Hydraulic│    │ Thermal │        ← Process Variants
│ Variant │    │ Variant │           (test profile, config)
└────┬─────┘    └────┬────┘
     │               │
  ┌──┴──┐         ┌──┴──┐
  │ L01 │         │ L04 │
  │ L02 │         │ L05 │        ← Runtime Instances
  │ L03 │         │ L06 │           (independent state)
  └─────┘         └─────┘
```

**DO NOT**: create 6 separate hard-coded process implementations with duplicated logic.

**PREFER**: `ProcessTemplate` + `VariantConfiguration` + `LineInstance` + `RuntimeState`.

---

## 4. UI/UX Visualization Architecture

### 4.1 Hierarchy

```
TIPA Plant
  ↓
Production Area Overview (all 6 lines)
  ↓
Selected Line Detail (full shopfloor)
  ↓
Station / WIP / Event Detail (inspector)
```

This follows the canonical UI/UX guide's physical-first + progressive-disclosure principles.

### 4.2 Production Area Overview

A high-level view showing all 6 process/line instances.

Example conceptual layout:

```
┌────────────────────────────────────────────┐
│ TIPA MOTOR PRODUCTION AREA                 │
│                                            │
│ HYDRAULIC GROUP                            │
│ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │ L01  │ │ L02  │ │ L03  │               │
│ │Operat│ │Operat│ │ HOLD │               │
│ └──────┘ └──────┘ └──────┘               │
│                                            │
│ THERMAL GROUP                              │
│ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │ L04  │ │ L05  │ │ L06  │               │
│ │Operat│ │Ready │ │Operat│               │
│ └──────┘ └──────┘ └──────┘               │
└────────────────────────────────────────────┘
```

Actual UI SHOULD use industrial SVG/visual objects, not text rows. Each line shows: group membership, high-level state, WIP/load summary, quality/hold status.

### 4.3 Line Detail (Drill-Down)

Selecting a line instance drills into the full shopfloor visualization as defined by the canonical guide:

```
Line 03 — Hydraulic
SSO2(H) → PRE → AP01 → AP02 → ... → AP11 → Finished
```

Supports: indexed conveyor, pallet/WIP movement, AP04 join, AP06 quality, AP08 visual, AP11 release, event rail, WIP/station inspector, measurements, genealogy.

### 4.4 Variant Visualization

Hydraulic vs Thermal MUST be visually distinguishable without consuming semantic state colors.

Use: variant label, icon, neutral badge, grouping, subtitle.

```
LINE 03                    LINE 05
SSO2 VARIANT: HYDRAULIC    SSO2 VARIANT: THERMAL
```

Semantic colors remain reserved: PASS (green), HOLD (amber), FAIL (red), RELEASED (cyan).

---

## 5. Identity / Context Implications

Multi-line support implies context must distinguish:

```
plant_id
area_id
line_id / process_instance_id
station_id
wip_id
```

A bare `AP06` is not globally sufficient once 6 parallel lines exist. This affects M6-S05 observation/MES projection.

**Not implemented in this task.**

---

## 6. Observation / MES Implications (Future)

When M6-S05 begins:

- Observation context MUST identify the originating line/process instance.
- MES projection MUST NOT assume a single AP06/AP11 for the whole factory.

Conceptually:

```
Plant → Line 03 → AP06 → MTR-xxxx → QualityRecord
```

---

## 7. Runtime Architecture Direction (Future)

```
PlantRuntime
├── LineRuntime 01 (Hydraulic)
├── LineRuntime 02 (Hydraulic)
├── LineRuntime 03 (Hydraulic)
├── LineRuntime 04 (Thermal)
├── LineRuntime 05 (Thermal)
└── LineRuntime 06 (Thermal)
```

Each instance maintains independent: line state, conveyor state, dwell/index, WIP, genealogy, quality, events. All reuse common definitions/configurations.

**Not implemented in this task.**

---

## 8. Demo Story

```
Production Area Overview
    → Viewer sees 6 parallel process instances
    → One line shows exception (HOLD)
    → Select that line
    → Inspect station/WIP/test
    → Retest PASS
    → Line resumes
    → Return to Production Area Overview
```

Supports both BOD understanding and IT/engineering drill-down.

---

## 9. DG03 Figma Impact

Future DG03 design work MUST include:

| Frame | Content |
|-------|---------|
| Frame A | Production Area Overview — all 6 lines with high-level status |
| Frame B | Selected Line Detail — one line in full Industrial Operations Cockpit |
| Frame C | Exception Drilldown — one line HOLD → area highlight → line detail → retest |

Do NOT create 6 full-detail mockups.

---

## 10. Non-Goals (Explicit)

- ❌ Implement 6 runtime instances
- ❌ Refactor simulation engine
- ❌ Create duplicated process code
- ❌ Implement test-profile logic
- ❌ Implement multi-line API or UI
- ❌ Create Figma production screens
- ❌ Start M6-S05
- ❌ Change closed S02/S03/S04 behavior
- ❌ Redefine canonical UI style

**This task is documentation/design architecture only.**

---

## 11. References

- **Canonical UI/UX Guide**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` (Section 20: Multi-Line / Repeated-Process Visualization)
- **TIPA Baseline**: `docs/demo/tipa/TIPA_ASSY_DEMO_BASELINE_v0.9.md`
- **TIPA Progress**: `docs/demo/TIPA_DEMO_PROGRESS.md`
