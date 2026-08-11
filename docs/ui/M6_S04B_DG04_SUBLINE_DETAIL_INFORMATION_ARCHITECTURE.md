# M6-S04B-DG04 — Sub-line Detail Information Architecture

> **Status**: DESIGN-ONLY. Frame B information architecture + semantic zoom design.  
> **Baseline**: I04 evidence head `e97b78f`. DG03 CLOSED at `cf20843`.  
> **Design Authority**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` v1.1  
> **Purpose**: Freeze Frame B UX, navigation, layers, and I05 acceptance criteria.  
> **Rule**: Design only. No implementation. No backend changes. No M6-S05.

---

## 1. UX Goals

```
Overview   = detect   (Frame A — 6 Sub-lines simultaneously)
Detail     = understand (Frame B — 1 Sub-line as primary physical workspace)
Inspector  = investigate (Frame C — WIP / Station / Genealogy / Quality drill-down)
```

Frame B must answer within seconds:
1. Which Sub-line? What state?
2. Where are WIPs physically positioned?
3. Which carrier holds which WIP?
4. Which station is active / ready / held?
5. What happened at AP04? AP06? AP08? AP11?
6. Which WIP/station should I click for deeper investigation?

---

## 2. Navigation Hierarchy

```
LEVEL 0 — Frame A: ASSY Line Overview
        6 Sub-lines, aggregate data, live overview
             │
             │ click lane → select
             │ Open Detail / double-click → semantic zoom
             ▼
LEVEL 1 — Frame B: ASSY Sub-line Detail
        1 Sub-line, full physical canvas, actual positions
             │
             │ click station → select station
             │ click WIP/carrier → select WIP context
             ▼
LEVEL 2 — Frame C: Context Inspector
        WIP / Station / Genealogy / Quality / Events drill-down
```

**Rule**: Mouse-wheel zoom is NOT the primary navigation. Semantic zoom (level change) drives hierarchy. Geometric zoom is a secondary canvas tool.

---

## 3. Screen Anatomy

```
┌──────────────────────────────────────────────────────────┐
│ ← Back to Overview │ TIPA / ASSY / ASSY-SL03              │
│ HYDRAULIC │ STOP/WORK │ t=480s │ DWELL 8 │ ● LIVE      │  Header
├──────────────────────────────────────────────────────────┤
│                                                           │
│  SSO2 → PRE → AP01–AP03 → ╔AP04╗ → AP05 → ╔AP06╗        │
│                             ║JOIN║          ║TEST║       │  Physical
│                          RSO2 → ╝       → AP07 → ╔AP08╗  │  Canvas
│                                                   ║VISN║  │  ~65%
│  → AP09–AP10 → ╔AP11╗ → OUT                             │
│                 ║FINAL║                                   │
│                                                           │
│  [carriers + WIP tokens at actual occupied positions]     │
│                                                           │
├──────────────────────────────────────┬───────────────────┤
│ ═══════════════════════════════════ │ Inspector         │
│ 12:04 AP04 MTR-0008 CREATED        │ (collapsed /      │  Event Strip
│ 12:06 AP06 FAIL #1                  │  reserved)        │  + Inspector
│ 12:06 HOLD ⏸                       │                   │  ~35%
├──────────────────────────────────────┴───────────────────┤
│ ← Back │ Reset │ Step │ Auto │ Speed │ Scenario          │  Controls
│ [-][100%][+] [Fit]                                       │  Zoom
└──────────────────────────────────────────────────────────┘
```

**Key decisions**:
- Physical canvas is dominant (~65% vertical)
- Right panel reserved for Inspector (collapsed by default, expands on selection)
- Compact event strip at bottom-left of canvas area
- Controls at fixed bottom bar
- Zoom controls integrated into bottom bar
- Header compact but carries full identity + state

---

## 4. Data-to-Visual Mapping

Source: `GET /assy-demo/sub-line/{sub_line_id}` → `AssyDemoSnapshot`

### Available Detail Fields

| API Field | UI Use |
|-----------|--------|
| `plant_id` | Header breadcrumb |
| `production_line_id` | Header breadcrumb |
| `sub_line_id` | Header title |
| `variant` | Subtle variant badge |
| `simulation_time_s` | Header: `t=480s` |
| `line_state` | Header status badge |
| `dwell_number` | Header: `DWELL 8` |
| `scenario` | Header context |
| `positions[].position_id` | Station node label |
| `positions[].station_label` | Station tooltip/hover |
| `positions[].wip_id` | WIP token on station |
| `positions[].wip_type` | Token color: SSO2 green / MTR amber |
| `positions[].carrier_id` | Pallet label: `PAL-003` |
| `positions[].manufacturing_status` | WIP lifecycle indicator |
| `positions[].quality_status` | Quality state badge |
| `positions[].latest_quality_result` | PASS/FAIL/NG badge |
| `positions[].attempt_number` | Attempt counter |
| `positions[].is_occupied` | Station fill state |
| `positions[].is_quality_hold` | Red station border |
| `positions[].held_reason` | Hover text |
| `genealogy[]` | AP04 panel / Inspector |
| `recent_quality_events[]` | Event strip + Inspector |
| `production` | Compact summary |

### DATA GAPs (documented, not blocking)

| Gap | Impact |
|-----|--------|
| No per-station elapsed time in snapshot | Cannot show "60% complete" progress bars without runtime change |
| No RSO2 WIP identity at AP04 position | JOIN parent display limited to genealogy records |
| Quality events are flat list | Need client-side filtering by station/WIP for Inspector |

---

## 5. Information Layers

### L0 — Physical (Always Visible)

```
Station topology nodes:  PRE-ASSY → AP01..AP11 → OUT
Flow direction arrows
Conveyor bar
RSO2 input branch at AP04
SSO2 input at PRE-ASSY
Occupied stations: filled, unoccupied: dashed outline
Carrier/pallet token at occupied stations
WIP token at occupied stations
```

Station node shape: vertical rectangles with ID label at top, WIP/carrier below.

### L1 — Operations (Default Visible)

```
Line state badge: STOPPED / OPERATING / READY / INDEXING
Station manufacturing status (if available from manufacturing_status)
Dwell number + simulation time
WIP count / motor count
```

### L2 — Quality (Contextual Overlay)

```
Quality result badge: PASS (green) / FAIL (red) / NG (red)
Quality HOLD indicator: red border pulse on held station
Attempt counter
Held WIP identity
Retest/Reinspect status text
```

### L3 — Context / Data (On Selection / Inspector)

```
Genealogy tree (AP04 parent→child)
Quality event timeline
Measurement values
Checklist items
Timestamps
```

### Density Rules

| Visibility | Content |
|-----------|---------|
| **Always** | Station ID, WIP ID, quality/status badge, occupancy |
| **On hover** | Station label, carrier ID, local time/dwell, held_reason |
| **On selection** | Focused context summary in Inspector |
| **Inspector** | Genealogy, measurements, checklist, tests, event history |

---

## 6. WIP vs Carrier — Visual Distinction

```
┌──── PAL-003 ────┐    ← Carrier frame (thin, #1e3a5f border)
│   MTR-0008      │    ← WIP label (bold, larger)
│   PASS #2       │    ← Quality badge
└─────────────────┘

Pre-AP04 (SSO2 WIP):
┌──── PAL-001 ────┐
│   SSO2-0003     │    ← Green tint
│   ACTIVE        │
└─────────────────┘

Post-AP04 (MTR WIP):
┌──── PAL-004 ────┐
│   MTR-0008      │    ← Amber tint
│   JOINED        │
└─────────────────┘
```

Carrier is a transport container. WIP is the production entity. Never merge into one label.

---

## 7. Station Landmark Treatment

### AP04 JOIN

```
              ┌─────────────┐
   SSO2-0003 →│  AP04 JOIN  │→ MTR-0008
   RSO2-0003 →│             │
              └─────────────┘
```

- Amber (#ffc107) station border
- RSO2 input branch from above/below
- MTR child WIP token shown post-join
- "JOIN" label at station
- Genealogy accessible via click → Inspector

### AP06 TEST

```
┌─────────────────┐
│     AP06        │   Normal: green border
│  ⏳ TESTING     │   HOLD: red border + pulse
│  MTR-0002       │   RETEST_PENDING: yellow border
│  FAIL #1        │   FAILED_FINAL: dark red
└─────────────────┘
```

States:
- PASS → green checkmark
- FAIL → red X, HOLD indicator
- RETEST_PENDING → yellow HOLD, attempt counter
- RETEST PASS → green with "#2 PASS"
- FAILED_FINAL → dark red, terminal indicator

### AP08 VISION

Same quality language as AP06 but "VISION" label. States: PASS / NG / REINSPECT_PENDING / REINSPECT PASS / FAILED_FINAL.

### AP11 FINAL QC

```
┌─────────────────┐
│     AP11        │
│  FINAL QC       │
│  MTR-0005       │
│  RELEASED  →    │   Cyan (#17a2b8) border
└─────────────────┘      arrow to LINE OUT
```

---

## 8. Semantic Navigation

| Action | Result |
|--------|--------|
| Click lane in Frame A | Select lane |
| Double-click / Open Detail | Navigate to Frame B |
| Click station in Frame B | Select station, Inspector preview |
| Click WIP/carrier | Select WIP, Inspector shows WIP context |
| Click event in strip | Select event, highlight linked station+WIP |
| ← Back | Return to Frame A (preserve overview state) |

---

## 9. Geometric Zoom / Pan (Frame B Canvas Only)

| Control | Behavior |
|---------|----------|
| `[-]` button | Zoom out (min 50%) |
| `[100%]` button | Reset to 100% |
| `[+]` button | Zoom in (max 200%) |
| `[Fit]` button | Fit full sub-line in viewport |
| Mouse wheel | Zoom around cursor |
| Drag / middle-button | Pan canvas |

**Decisions**:
- Zoom affects physical canvas only — header/controls/Inspector remain fixed
- Selected station/WIP remains highlighted during zoom
- Zoom state preserved when switching sub-lines within Frame B
- Zoom resets on return to Frame A overview
- SVG `viewBox` manipulation — no Canvas rendering

---

## 10. Typography / Readability Scale

At 1920×1080:

| Element | Size | Weight |
|---------|------|--------|
| Sub-line title | 20px | 600 |
| Station ID | 14px | 600 |
| WIP ID | 14px | 600 |
| Status / quality badge | 13px | 600 |
| Carrier ID | 11px | 400 |
| Station label (hover) | 11px | 400 |
| Event strip text | 10px | 400 |
| Timestamp / metadata | 10px | 400 |

**Rule**: No operationally important text below 11px.

At 1366×768:
- Station IDs: 12px minimum
- WIP IDs: 12px minimum
- Status badges remain readable
- Inspector collapses to sidebar icon

### Frame A Typography Follow-up Recommendation

After Frame B typography is validated, apply the same 11px minimum rule to Frame A for operational text (Sub-line ID, status badge, held station).

---

## 11. Responsive Behavior

### 1920×1080

- Full physical canvas with Inspector panel (280px)
- Event strip visible with ~6 recent events
- All controls + zoom visible

### 1366×768

- Physical canvas fills width
- Inspector collapses to icon (expandable overlay)
- Event strip shows ~3 events
- Zoom controls remain
- Station IDs remain readable at 12px
- Geometric pan acceptable if canvas overflows

---

## 12. Required Design States (I05 Acceptance)

### B1 — Normal Populated Sub-line

- Multiple WIPs at actual positions from `positions[]`
- Carrier vs WIP visually distinct
- Physical station flow with landmarks
- Readable hierarchy at 1920×1080
- All occupied stations visible

### B2 — AP06 HOLD

- ASSY-SL03 selected
- AP06 station with red border + pulse
- `RETEST_PENDING` quality badge
- `FAIL #1` attempt indicator
- MTR-xxxx WIP identity at AP06
- Other stations render normally
- Event strip shows FAIL + HOLD events

### B3 — AP04 JOIN

- AP04 station with amber border
- SSO2 parent identity shown
- RSO2 parent identity shown (from genealogy)
- MTR child WIP token at AP04
- "JOIN" label
- Genealogy accessible

### B4 — AP08 NG / REINSPECT

- AP08 station with red border
- `REINSPECT_PENDING` quality badge
- `NG #1` attempt indicator
- VISION label

### B5 — AP11 RELEASED

- AP11 station with cyan border
- `RELEASED` status
- Arrow to LINE OUT
- Motor count incremented

---

## 13. I05 Acceptance Matrix

| # | Criterion | Source |
|---|-----------|--------|
| 1 | Frame B opens from Frame A lane selection | Navigation |
| 2 | Header shows full identity: TIPA / ASSY / ASSY-SLxx | API |
| 3 | Header shows live state: line_state, dwell, sim_time | API |
| 4 | 12 station nodes rendered in physical flow | Topology |
| 5 | Occupied stations from `positions[].is_occupied` | API |
| 6 | WIP ID displayed at occupied stations | API |
| 7 | Carrier ID displayed at occupied stations | API |
| 8 | Quality badges: PASS/FAIL/NG/HOLD | API |
| 9 | AP04 JOIN: amber border, parent→child visible | API + genealogy |
| 10 | AP06 HOLD: red border, RETEST_PENDING, attempt | API |
| 11 | AP08 NG: red border, REINSPECT_PENDING | API |
| 12 | AP11 RELEASED: cyan border, LINE OUT arrow | API |
| 13 | Event strip shows recent quality events | API |
| 14 | ← Back returns to Frame A overview | Navigation |
| 15 | Zoom controls: [-][100%][+][Fit] | Canvas |
| 16 | Mouse-wheel zoom + drag pan | Canvas |
| 17 | 1920×1080: all stations visible | Responsive |
| 18 | 1366×768: stations readable, Inspector collapses | Responsive |
| 19 | Geometric zoom only affects canvas | Zoom model |
| 20 | No fake data — all from API | Truth |

---

## 14. Forbidden

- ❌ Frame B is not a zoomed Frame A
- ❌ No fake station occupancy (use `positions[]` array)
- ❌ No merged carrier + WIP labels
- ❌ No invented equipment geometry
- ❌ No global simulation time (use per-context `simulation_time_s`)
- ❌ No second conveyor for RSO2
- ❌ No MES/IIoT panels
- ❌ No Inspector implementation (Frame C is separate gate)
- ❌ No animation/motion (I07)

---

## 15. Scope

- ✅ DG04-01 design-only
- ✅ Frame B information architecture frozen
- ✅ I05 acceptance criteria defined
- ✅ No implementation
- ✅ No backend changes
- ✅ No M6-S05

---

> **DG04-01 is READY FOR SA REVIEW.**
>
> Next: SA approval → I05 Sub-line Detail implementation.
