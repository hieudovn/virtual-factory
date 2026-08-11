# M6-S04B-DG03 — Visual Design / Figma Gate

> **Status**: Visual design gate — ready for SA review.  
> **Design tool**: SVG/HTML mockups (Figma-ready specification).  
> **Date**: 2026-08-11  
> **Design Authority**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` v1.1

---

## 1. Summary

DG03 defines the visual design system for the TIPA Virtual Factory demo, suitable for BOD, IT Manager, and engineering audiences on 1920×1080 projector/display.

The design follows the canonical **Industrial Operations Cockpit** style: clean, engineering-oriented, dark control-room feel, projector-friendly, high clarity, low visual noise.

---

## 2. Design Tool & Artifacts

**Tool**: SVG/HTML mockups (exportable to Figma for interactive prototyping).

Visual artifacts in `docs/demo/tipa/ui/`:

| File | Frame | Description |
|------|-------|-------------|
| `frame_a_assy_overview.html` | Frame A | ASSY Line Overview — 6 sub-lines |
| `frame_b_subline_detail.html` | Frame B | Selected Sub-line Detail with AP06 HOLD |

Open `.html` files in browser to view at full 1920×1080 resolution.

---

## 3. Visual Foundation

### Style
- **Industrial Operations Cockpit**: dark neutral background (#0d1117), blue-gray headers, muted surfaces
- No cyberpunk, no neon, no glassmorphism, no gaming UI

### Palette

| Role | Color | Usage |
|------|-------|-------|
| Background | #0d1117 / #161b22 | Main canvas |
| Header | #1a2332 → #0f1a2e | Top bar |
| Surface | #0f1a2e | Cards, panels |
| Border | #1e3a5f | Subtle separators |
| Hydraulic group | #1a2740 | Variant grouping tint |
| Thermal group | #221a30 | Variant grouping tint |
| PASS / active | #4ecca3 | Green-teal |
| FAIL / NG | #e94560 | Red |
| HOLD / warning | #ffc107 | Amber |
| RELEASED | #17a2b8 | Cyan |
| Text primary | #e0e0e0 | Main labels |
| Text secondary | #888 | Metadata |
| Text muted | #555 / #666 | Less important |

### Typography
- System sans-serif (Segoe UI / system-ui)
- Title: 20–22px, station ID: 11–12px, labels: 9–10px
- Monospace for timestamps, IDs, measurements

### Spacing
8px-based: 4/8/12/16/24/32px

---

## 4. Component Library

```
VFOperationsShell
├── GlobalStatusBar
├── AssyLineOverview
│   ├── VariantGroupHeader
│   └── SubLineSummary
├── ShopfloorScene
│   ├── ConveyorLane
│   ├── StationNode
│   ├── CarrierToken
│   ├── WipToken / ProductToken
│   ├── FeederIndicator
│   ├── JoinIndicator
│   └── LineOutput
├── InspectorDrawer
│   ├── OverviewSection
│   ├── GenealogyView
│   ├── QualityHistory
│   ├── MeasurementView
│   └── EventHistory
├── EventRail
├── ControlBar
└── LegendBar
```

---

## 5. Frame A — ASSY Line Overview

**File**: `frame_a_assy_overview.html`

Shows ONE ASSY Line containing 6 parallel ASSY Sub-lines:

- **Hydraulic SSO2 Input Variant**: ASSY-SL01 (OPERATING), SL02 (OPERATING), SL03 (QUALITY HOLD — highlighted red)
- **Thermal SSO2 Input Variant**: ASSY-SL04 (OPERATING), SL05 (OPERATING), SL06 (READY)

Each sub-line card shows:
- Sub-line ID + state badge
- Simplified flow indicator (colored dots along track)
- WIP count, output count, dwell number
- Feeder hint (SSO2(H) or SSO2(T))
- Output hint (MOTOR)

Exception sub-line (SL03) highlighted with red border + glow.

Bottom: production summary bar + demo controls.

---

## 6. Frame B — Selected ASSY Sub-line Detail

**File**: `frame_b_subline_detail.html`

Shows ASSY-SL03 in full shopfloor detail with AP06 QUALITY HOLD:

- Header: "ASSY LINE / ASSY-SL03 — SSO2 INPUT VARIANT: HYDRAULIC"
- 12 station nodes (PRE-ASSY → AP11) along conveyor track
- AP04 highlighted gold (JOIN with RSO2 feeder)
- AP06 highlighted red (FAIL #1 + HOLD badge)
- AP11 cyan (RELEASED motor output)
- Right-side inspector showing WIP MTR-0015 details: overview, genealogy, quality history (FAIL attempt 1), synthetic measurements, recent events
- Bottom: controls + legend

---

## 7. Frame C — Exception Drilldown (Documented)

The exception story is visible in Frame B:

```
ASSY-SL03 → AP06 QUALITY HOLD
→ MTR-0015 FAIL #1, RETEST PENDING
→ Inspector shows: genealogy, measurements, event history
→ RETEST → PASS → READY → INDEX resumes
```

---

## 8. Motion Vocabulary

All motion follows canonical vocabulary. SVG mockups are static; animation behavior described below:

| Motion | Visual Behavior | Duration |
|--------|----------------|----------|
| INDEX_SHIFT | All occupied carriers shift one station simultaneously | ~500ms |
| LINE_IN | WIP slides in from feeder | ~300ms |
| LINE_OUT | Motor exits to output area | ~300ms |
| JOIN | Both inputs converge at AP04, child created | ~600ms |
| WORK_PULSE | Station border subtle glow during active processing | continuous while active |
| HOLD_PULSE | Blocking station red pulse 1.5s cycle | while held |
| DATA_PULSE | Brief connection line from station to event rail | ~200ms |

---

## 9. Information Hierarchy

| Level | Content | Location |
|-------|---------|----------|
| L0 Ambient | Station ID, operation label, WIP/carrier, state, quality badge | Shopfloor canvas |
| L1 Peek | Operation detail, attempt, latest result, short measurements | Hover tooltip |
| L2 Inspector | Full genealogy, quality history, measurements, events, timestamps | Right drawer |

---

## 10. Viewport Evidence

- **1920×1080**: Primary — all frames designed at this resolution
- **1366×768**: Shopfloor canvas compresses horizontally; inspector reduces width; station labels remain readable at 9px+

---

## 11. Manufacturing Truth Check

- ✅ ASSY represented as ONE production line (not six)
- ✅ Six parallel paths called ASSY Sub-lines (ASSY-SL01..SL06)
- ✅ No unconfirmed conveyor independence asserted
- ✅ No MES/data semantics invented
- ✅ DEMO/SYNTHETIC DATA label visible in inspector
- ✅ Current runtime is ONE sub-line flow; design shows intended 6-sub-line experience
- ✅ Variant distinction uses labels + grouping, not semantic colors

---

## 12. Technical Feasibility

The design maps directly to the existing architecture:

```
SVG shopfloor canvas + HTML/CSS overlays
  ↕
AssyDemoSnapshot (JSON from /assy-demo/snapshot)
  ↕
DemoController / AssyLineRuntime
```

No new framework required. Existing FastAPI + vanilla JS approach sufficient for implementation.

---

## 13. Open Visual Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Exact transition animation timing (400ms vs 650ms) | TBD during implementation |
| 2 | 1366×768 inspector layout compaction | TBD |
| 3 | Sub-line overview card: horizontal vs vertical flow indicator | Current design acceptable |

No frozen architecture conflicts found.

---

## 14. Scope Check

- ✅ No production UI implementation
- ✅ No runtime changes
- ✅ No multi-sub-line runtime implementation
- ✅ No MES / M6-S05
- ✅ Canonical UI/UX guide complied with
- ✅ DG02.1 terminology used throughout

---

> **M6-S04B-DG03 Visual Design Gate is READY FOR SA REVIEW.**
