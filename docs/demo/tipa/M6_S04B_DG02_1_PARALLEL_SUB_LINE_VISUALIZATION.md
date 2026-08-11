# M6-S04B-DG02.1 — Parallel ASSY Sub-Line Visualization Addendum

> **Status**: Design architecture — documentation only.  
> **Terminology corrected by DG02.2 (11-Aug-2026)**: "multi-line" deprecated for TIPA ASSY.  
>   Correct term: **parallel ASSY sub-lines**.  
> **Parent**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` (canonical UI/UX authority)  
> **Date**: 2026-08-11

---

## 1. Purpose

This addendum captures the clarified TIPA parallel sub-line topology and its implications for UI/UX architecture. The canonical design guide defines the general production hierarchy principles (Section 20). This document applies those principles specifically to TIPA.

**No runtime implementation. No UI changes. No M6-S05.**

---

## 2. TIPA Production Hierarchy

```
TIPA Plant
│
├── SSO2 Line (upstream)
│   └── produces stator-side semi-finished material
│
├── RSO2 Line (upstream)
│   └── produces rotor semi-finished material
│
└── ASSY Line / Assembly Line (primary demo scope)
    │
    ├── ASSY-SL01 ─┐
    ├── ASSY-SL02  ├─ Hydraulic SSO2 Input Variant
    ├── ASSY-SL03 ─┘
    │
    ├── ASSY-SL04 ─┐
    ├── ASSY-SL05  ├─ Thermal SSO2 Input Variant
    └── ASSY-SL06 ─┘
```

**ASSY is ONE Production Line** containing **6 parallel ASSY Sub-lines**.

Each ASSY Sub-line executes the complete ASSY flow and outputs a complete finished motor.

### Common ASSY Process Template (per sub-line)

```
SSO2 Input (Hydraulic or Thermal variant)
    ↓
PRE-ASSY → AP01 → AP02 → AP03 → AP04 → AP05
→ AP06 → AP07 → AP08 → AP09 → AP10 → AP11
→ Finished Motor

RSO2 → AP04 JOIN
```

### Variant Difference

| Aspect | Hydraulic | Thermal |
|--------|-----------|---------|
| SSO2 input | Hydraulic Press variant | Thermal Press variant |
| Primary difference | Test/profile behavior | Test/profile behavior |
| Downstream ASSY | Common template | Common template |

Future differences SHOULD be modeled through configuration/variant specialization.

---

## 3. Architecture: Process Definition vs Variant vs Sub-Line Instance

```
┌─────────────────────────────────┐
│ ASSY Process Definition         │  ← Common template
│ (stations, routing, quality)    │
└────────────┬────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌─────────┐    ┌─────────┐
│Hydraulic│    │ Thermal │        ← SSO2 Input Variants
│ Variant │    │ Variant │           (test profile, config)
└────┬─────┘    └────┬────┘
     │               │
  ┌──┴──┐         ┌──┴──┐
  │SL01 │         │SL04 │
  │SL02 │         │SL05 │        ← Sub-Line Runtime Instances
  │SL03 │         │SL06 │           (independent state)
  └─────┘         └─────┘
```

**DO NOT**: create 6 separate hard-coded implementations.

**PREFER**: `ProcessDefinition + VariantConfiguration + SubLineInstance + RuntimeState`.

---

## 4. UI/UX Visualization Architecture

### 4.1 Hierarchy

```
TIPA / Production Overview
  ↓
ASSY Line Overview (6 sub-lines)
  ↓
Selected ASSY Sub-line Detail (full shopfloor)
  ↓
Station / WIP / Event Detail (inspector)
```

This follows the canonical UI/UX guide's physical-first + progressive-disclosure principles.

### 4.2 ASSY Line Overview

High-level view showing all 6 ASSY Sub-lines:

```
┌────────────────────────────────────────────┐
│ ASSY LINE                                  │
│                                            │
│ HYDRAULIC SSO2 INPUT VARIANT               │
│ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │SL01  │ │SL02  │ │SL03  │               │
│ │Operat│ │Operat│ │ HOLD │               │
│ └──────┘ └──────┘ └──────┘               │
│                                            │
│ THERMAL SSO2 INPUT VARIANT                 │
│ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │SL04  │ │SL05  │ │SL06  │               │
│ │Operat│ │Ready │ │Operat│               │
│ └──────┘ └──────┘ └──────┘               │
└────────────────────────────────────────────┘
```

Actual UI SHOULD use industrial SVG/visual objects. Each sub-line shows: variant group, high-level state, WIP summary, quality/hold status.

### 4.3 Sub-Line Detail (Drill-Down)

Selecting a sub-line drills into the detailed Industrial Operations Cockpit:

```
ASSY LINE / ASSY-SL03
SSO2 INPUT VARIANT: HYDRAULIC

SSO2(H) → PRE → AP01 → AP02 → ... → AP11 → Finished Motor
```

Supports: indexed conveyor, pallet/WIP movement, AP04 join, AP06 quality, AP08 visual, AP11 release, event rail, WIP/station inspector, measurements, genealogy.

### 4.4 Variant Visualization

Hydraulic vs Thermal MUST be visually distinguishable without consuming semantic state colors.

Use: variant label, icon, neutral badge, grouping, subtitle.

```
ASSY-SL03                          ASSY-SL05
SSO2 INPUT: HYDRAULIC              SSO2 INPUT: THERMAL
```

Semantic colors remain reserved: PASS (green), HOLD (amber), FAIL (red), RELEASED (cyan).

---

## 5. Identity / Context Hierarchy

```
plant_id
line_id          (SSO2 | RSO2 | ASSY)
sub_line_id      (ASSY-SL01..SL06)
station_id       (AP06)
wip_id           (MTR-xxxx)
```

A bare `AP06` is not globally sufficient with 6 parallel sub-lines. This affects M6-S05.

**Not implemented in this task.**

---

## 6. Observation / MES Implications (Future)

- Observation context MUST identify the originating sub-line instance.
- MES projection MUST NOT assume a single AP06/AP11.

```
TIPA → ASSY → ASSY-SL03 → AP06 → MTR-xxxx → QualityRecord
```

---

## 7. Runtime Architecture Direction (Future)

```
PlantRuntime
├── SSO2LineRuntime
├── RSO2LineRuntime
└── ASSYLineRuntime
    ├── SubLineRuntime ASSY-SL01 (Hydraulic)
    ├── SubLineRuntime ASSY-SL02 (Hydraulic)
    ├── SubLineRuntime ASSY-SL03 (Hydraulic)
    ├── SubLineRuntime ASSY-SL04 (Thermal)
    ├── SubLineRuntime ASSY-SL05 (Thermal)
    └── SubLineRuntime ASSY-SL06 (Thermal)
```

Each sub-line requires its own sub-line-scoped identity, WIP, genealogy, quality, and event context.

Conveyor/index/control ownership and synchronization boundaries across sub-lines remain TBD (see Section 8). Shared coordination MAY be introduced later only if confirmed by plant reality.

**Do NOT** invent an `ASSYLineCoordinator` now.

Distinguish:
- **logically separate execution context** (required — identity, WIP, genealogy, quality, events per sub-line);
- **physically/control-independent conveyor/runtime** (TBD — may or may not be independent).

**Not implemented in this task.**

---

## 8. Open Physical Question

The following remains TBD until confirmed by TIPA:

- Whether each ASSY Sub-line has a fully independent indexed conveyor.
- Whether shared transport/control/synchronization exists across sub-lines.

Do NOT invent an `ASSYLineCoordinator` without evidence.

---

## 9. Demo Story

```
ASSY Line Overview
    → Viewer sees 6 parallel ASSY Sub-lines
    → One sub-line shows exception (HOLD)
    → Select that sub-line
    → Inspect station/WIP/test
    → Retest PASS
    → Sub-line resumes
    → Return to ASSY Line Overview
```

Supports both BOD understanding and IT/engineering drill-down.

---

## 10. DG03 Figma Impact

| Frame | Content |
|-------|---------|
| Frame A | ASSY Line Overview — all 6 sub-lines with high-level status |
| Frame B | Selected ASSY Sub-line Detail — full Industrial Operations Cockpit |
| Frame C | Exception Drilldown — one sub-line HOLD → detail → retest |

Do NOT create 6 full-detail mockups. Do NOT describe as 6 production lines.

---

## 11. Non-Goals

- ❌ Implement 6 sub-line runtimes
- ❌ Refactor simulation engine
- ❌ Create duplicated process code
- ❌ Implement multi-sub-line UI
- ❌ Create Figma
- ❌ Start M6-S05
- ❌ Change closed S02/S03/S04
- ❌ Redefine canonical UI style
- ❌ Invent physical coordination behavior

---

## 12. References

- **Canonical UI/UX Guide**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` (Section 20)
- **TIPA Baseline**: `docs/demo/tipa/TIPA_ASSY_DEMO_BASELINE_v0.9.md`
- **TIPA Progress**: `docs/demo/TIPA_DEMO_PROGRESS.md`
