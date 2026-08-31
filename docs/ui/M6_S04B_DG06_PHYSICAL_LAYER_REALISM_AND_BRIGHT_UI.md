# M6-S04B-DG06 — Physical Layer Realism + Unified VF Visual System

> **Status**: DESIGN-ONLY. Translated from SA/Designer Master Brief v1.
> **Baseline**: I06 CLOSED at `b232bdc`. I05, DG04, DG05 CLOSED.
> **Purpose**: Freeze visual direction for I09 implementation. No production code change in this gate.
> **Rule**: Design review only. I07/I08/I09/M6-S05 not authorized here.

---

## 1. Purpose

Freeze the production contract for:

`M6-S04B-I09 — Top-Down Physical Layer Realism + Unified VF Visual System`

Translate the SA/Designer master brief into a codebase-specific implementation plan with explicit file targets, risk assessment, and acceptance criteria.

---

## 2. Scope and Non-Scope

### In scope (design only)
- Visual direction for ASSY physical view
- Object taxonomy (pallet, WIP silhouettes, station archetypes)
- Right-to-left flow geometry
- Bright shell + popup strategy
- Unified VF visual tokens/primitives
- Implementation split proposal
- Codebase-fit assessment

### Out of scope
- Production implementation (I09)
- Motion/animation (I07, I09-P03)
- Backend/runtime/API changes
- MES integration

---

## 3. Design Authority Summary

**Frozen style**: Top-down Illustrated Industrial Twin

**Key decisions preserved from master brief**:

| Decision | Detail |
|----------|--------|
| Style | Top-down illustrated industrial twin |
| Theme | Bright, clean, professional shell (`#F5F7FA` page background) |
| Flow direction | **Right → Left** (SSO2/RSO2 inputs at right, LINE OUT at left) |
| Carrier base | Wooden pallet on conveyor (not floating tokens) |
| WIP taxonomy | Stator Assy, Rotor, Joined Motor, Pre-Test Motor, Tested Motor, Packed Goods |
| Station archetypes | Top-down plan-style cells with equipment icons |
| Info surface | Top-right translucent popup (replaces full-height Inspector as default) |
| Motion | Conveyor + pallet/WIP only; step-bound; no free-running animation |
| Visual system | Unified VF tokens (colors, typography, spacing, primitives) |

---

## 4. Top-Down Style Rationale

The top-down illustrated style best satisfies current constraints:

1. **2D only** — compatible with existing SVG/HTML/CSS/JS architecture
2. **Physical clarity** — conveyor, pallets, WIP, stations all visible in one frame
3. **Clean production flow** — right-to-left reading matches stakeholder plant layout
4. **Separation of concerns** — stationary assets (stations) vs moving objects (pallets/WIP) visually distinct
5. **Scalable** — same visual language extends to future VF scenarios

---

## 5. Right-to-Left Flow Rationale

**Current codebase**: Left → Right (SSO2 at x=20, PRE-ASSY at x=140, AP11 at x=1240, OUT arrow at x=1720)

**Required**: Right → Left (mirror the entire horizontal axis)

**Why**: Matches real plant layout; improves stakeholder familiarity.

**Impact on current `FB_STATION_X` array**:
```
Current: [140, 240, 340, ..., 1240]  (PRE-ASSY leftmost, AP11 rightmost)
New:     [1660, 1560, 1460, ..., 560]  (PRE-ASSY rightmost, AP11 leftmost)
```

Station order on conveyor: PRE-ASSY → AP01 → ... → AP11, but rendered right → left.

**SSO2/RSO2 input** moves to right side. **LINE OUT** moves to left side.

**AP04 RSO2 branch**: RSO2 input enters from right/top-right, joins at AP04 position.

---

## 6. Physical Layer First Principle

The physical canvas is the dominant visual layer. All information displays are secondary and on-demand.

### Layer model

| Layer | Content | Visibility |
|-------|---------|------------|
| L0 — Physical | Conveyor, pallets, WIP objects, station cells, flow arrows, branch connectors | Always visible |
| L1 — State overlay | Selection highlight, HOLD/PASS/FAIL markers, occupancy emphasis | Contextual, lightweight |
| L2 — Information | Popup card, metric pills, status chips | On-demand only |

**Rule**: Layer 2 must never visually dominate Layer 0 by default.

---

## 7. Layout Strategy

### Primary canvas
- Logical scene: **1600×900**
- Container: fills available space, `preserveAspectRatio="xMidYMid meet"`
- Responsive to 1920×1080 and 1366×768

### Conveyor geometry
- Horizontal main conveyor spanning most of canvas width
- Conveyor y-position: centered vertically (~450 in 900-high scene)
- Width: accommodates pallet + WIP + margins
- Rails/edge guides visible

### Station placement
- Stations arranged **above and/or below** the conveyor line
- Compact spacing between stations
- AP04 (JOIN) clearly marked with RSO2 branch connector
- AP06 (TEST), AP08 (VISION), AP11 (FINAL) landmarks preserved

### Compact linear layout (Strategy A — recommended)
```
LEFT / DOWNSTREAM (output)                                    RIGHT / UPSTREAM (input)

[OUT] ← ╔AP11╗ ← [AP10] ← [AP09] ← ╔AP08╗ ← [AP07] ← ╔AP06╗ ← [AP05] ← ╔AP04╗ ← [AP03] ← [AP02] ← [AP01] ← [PRE] ← [SSO2]
        ║FINAL║                            ║VISN║              ║TEST║              ║JOIN║
                                                                                ↑
                                                                             [RSO2]
```

Flow direction: **RIGHT → LEFT**. SSO2 and RSO2 inputs enter from the RIGHT side. LINE OUT exits to the LEFT. All station-to-station arrows point LEFT (←).

---

## 8. Object Taxonomy

### 8.1 Carrier — Wooden Pallet

All WIP materials sit on wooden pallets placed on the conveyor.

**Visual**:
- Rectangular top-down pallet silhouette
- Light wood tone (`#C89A63`)
- Subtle slat lines (2-3 horizontal lines)
- Consistent size (~76×40px in scene coordinates)
- Contrast against conveyor

**Code representation**: SVG `<g>` group with `<rect>` base + slat `<line>` elements.

### 8.2 WIP Objects

Six distinct WIP states, differentiated by silhouette, base color, and short label. All placed ON the pallet, never floating.

| WIP Type | Label | Silhouette | Base Color | Code Family |
|----------|-------|------------|------------|-------------|
| Stator Assy | `STATOR` | Round housing ring, central void, thick body | Teal `#2DB9C8` | `vf-obj-stator` |
| Rotor | `ROTOR` | Narrow shaft, visible center line | Amber `#E8A23A` | `vf-obj-rotor` |
| Joined Motor | `JOINED` | Compact cylindrical body, slight endcaps | Blue-green `#42A58A` | `vf-obj-joined` |
| Pre-Test Motor | `PRE-TEST` | Similar to joined, more complete silhouette | Blue-green `#3E8FB0` | `vf-obj-pretest` |
| Tested Motor | `TESTED` | Core motor shape + PASS/FAIL status marker | Motor family + overlay | `vf-obj-tested` |
| Packed Goods | `PACKED` | Carton/box on pallet | Brown `#B68B57` | `vf-obj-packed` |

### 8.3 State Encoding Rules

**Object category** = base appearance (silhouette + base color)
**Quality state** = overlay marker (corner badge or ring)

Never use a single color to encode both category and state.

| State | Overlay |
|-------|---------|
| PASS | Green corner badge or thin ring (`#2EAD5B`) |
| HOLD | Amber badge/ring (`#E5A93B`) |
| FAIL / NG | Red badge/ring (`#D84B4B`) |
| SELECTED | Blue outline (`#2F80ED`) |
| HISTORICAL | Muted gray-blue tone (`#7B8AA0`) |

---

## 8-A. WIP Visual-State Evolution Contract

### 8-A.1 Public Post-Index Snapshot Principle

> **Frame B/I09 physical token rendering is based on the public post-index `positions[]` snapshot. A station's current occupant is shown in the manufacturing state it has when it ARRIVES at that station. Effects of that station's operation become visible only after successful dwell completion and index to the next position.**

This aligns with DG04-03 live-contract reconciliation: the public `/assy-demo/sub-line/{id}` endpoint returns the snapshot **after** step orchestration completes, which includes `index_line()` shifting all occupancy downstream.

**No transient or pre-index state may be fabricated.**

### 8-A.2 Canonical Position → Visual Token Mapping

The mapping follows the public post-index snapshot order. "Operation occurs at" describes the station where manufacturing work happens. "Visible token at" describes what the public snapshot shows at each position.

| Current position in `positions[]` | Base visual token | Operation meaning | Operation that produced this state |
|---|---|---|---|
| PRE-ASSY | **STATOR ASSY** | Line entry / prep | (upstream SSO2 feed) |
| AP01 | **STATOR ASSY** | Stator-side assembly | — |
| AP02 | **STATOR ASSY** | Terminal box wiring | — |
| AP03 | **STATOR ASSY** | Mechanical prep + QC check | — |
| AP04 | **STATOR ASSY** | JOIN occurs here. MTR child created during dwell, but **child not yet visible downstream** until index. RSO2 component shown as branch feed. | — |
| AP05 | **MTR JOINED** | Assembly + painting + measurements | AP04 JOIN completed; MTR child indexed to AP05 |
| AP06 | **MTR PRE-TEST** | Electrical / functional TEST occurs here. If FAIL/HOLD/RETEST, WIP may remain at AP06 for retest. | AP05 mechanical assembly completed |
| AP07 | **TESTED MTR** | Finishing / nameplate | AP06 successful TEST completed and indexed |
| AP08 | **TESTED MTR** | Visual inspection occurs here. NG/reinspect shown as overlay only; base object unchanged. | AP06 TEST was successful (or retest passed) |
| AP09 | **TESTED MTR** | Boxing occurs here. Packaging operation begins during dwell. | AP08 passed (or reinspect passed) |
| AP10 | **PACKED GOODS** | Closing / labeling / palletizing | AP09 boxing completed |
| AP11 | **PACKED GOODS** | Final QC / release. FINAL_QC check occurs here. | AP10 packaging completed |
| OUT / released | No physical token unless `positions[]` explicitly contains one | History only otherwise | AP11 released and indexed out |

### 8-A.3 RSO2 Branch

RSO2 is a **branch component feed**, not a main-conveyor position. It is shown as:

- RSO2 input line branching into AP04 from upper or lower side
- **ROTOR** visual token at the RSO2 input point (amber `#E8A23A`, narrow shaft silhouette)
- RSO2 identity shown from genealogy (`parent_wip_ids` in `genealogy[]`) when available
- Never fabricated as main-conveyor occupancy

### 8-A.4 Manufacturing vs Visual Transition Distinctions

These distinctions are critical truthfulness rules:

| Station | Manufacturing operation | Public visual transition |
|--------|------------------------|-------------------------|
| AP04 | **JOIN** occurs here | `MTR JOINED` first visible at **AP05** after index |
| AP05 | Mechanical completion | `MTR PRE-TEST` first visible at **AP06** after index |
| AP06 | Electrical TEST | `TESTED MTR` first visible at **AP07** after successful test + index |
| AP09 | Boxing / packaging start | `PACKED GOODS` first visible at **AP10** after boxing + index |

### 8-A.5 Exception Semantics

#### AP06 FAIL / HOLD / RETEST_PENDING

While a WIP is physically held at AP06 due to FAIL/RETEST_PENDING:

- **Base visual**: `MTR PRE-TEST` (the motor has not yet been successfully tested)
- **Quality overlay**: FAIL (red badge/ring) or HOLD (amber badge/ring) from `positions[]`
- **Attempt counter**: shown from `positions[].attempt_number` and `quality_records[]`
- If retest eventually passes: WIP indexes to AP07, base visual becomes `TESTED MTR`

**Never** show a WIP held at AP06 as `TESTED MTR` just because it is at the TEST station. The test has not yet passed.

#### AP08 NG / REINSPECT_PENDING

While a WIP is held at AP08 due to NG/REINSPECT_PENDING:

- **Base visual**: `TESTED MTR` (AP06 test was successful; the motor IS tested)
- **Quality overlay**: NG (red badge/ring) or HOLD (amber badge/ring)
- Base object category does NOT change — reinspect is a quality overlay
- If reinspect passes: WIP indexes to AP09, base visual remains `TESTED MTR`

#### FAILED_FINAL

- WIP may have exhausted max attempts at AP06 or AP08
- Base visual follows the same rules as above (PRE-TEST at AP06, TESTED at AP08)
- Terminal state shown via FAIL overlay + "FAILED_FINAL" context
- Quality history in Inspector preserves all attempt records

### 8-A.6 Critical Invariants

1. **Object category ≠ quality state**: Quality outcome is always an overlay, never a change of object category. A `MTR PRE-TEST` with FAIL is still `MTR PRE-TEST` with a red overlay — not a seventh WIP type.

2. **Pallet ≠ WIP identity**: The wooden pallet is the carrier. The WIP object is placed ON the pallet. WIP identity (`wip_id` from `positions[]`) labels the WIP, not the pallet.

3. **`positions[]` remains sole physical truth**: The visual token is determined by the WIP's position in the process flow (derived from its identity, type, and current `position_id`), NOT from genealogy or event history.

4. **No category invention**: The six categories (STATOR ASSY, ROTOR, MTR JOINED, MTR PRE-TEST, TESTED MTR, PACKED GOODS) are the complete visual taxonomy.

5. **No transient pre-index state**: The public snapshot represents post-index state. Effects of station operations become visible only after the WIP indexes to the next position. Do not render WIP in a state that the station has not yet completed.

---

Stations are stationary, rendered in top-down plan style. Each has: body footprint, type icon, AP label, connection to conveyor.

### 9.1 Input/Loading (PRE-ASSY)
- Loading table/feeder pad footprint
- SSO2 material feed indicator

### 9.2 Assembly/Manual (AP01, AP02, AP05, AP07, AP09, AP10)
- Workbench footprint
- Compact manual fixture

### 9.3 Join Station (AP04)
- Central fixture
- Stator lane + RSO2 branch merging
- Join icon or interlock visual cue
- Amber border treatment

### 9.4 Test Station (AP06)
- Test bench footprint
- Test icon / meter motif
- Cable or fixture hint

### 9.5 Vision/Inspection (AP08)
- Inspection booth or camera icon
- Small camera head/housing

### 9.6 Final QC/Release (AP11)
- Final check pad
- QC mark or clipboard icon
- Release/output handoff feel
- Cyan border treatment

### 9.7 Check Station (AP03)
- Checklist/QC workstation
- Pre-join quality checkpoint

---

## 10. Conveyor Design

**Form**: Top-down conveyor with muted steel/gray belt body, lane rails, subtle roller segmentation, directional arrow marks.

**Direction**: Right → Left (embedded arrow marks).

**Width**: Wide enough to hold wooden pallet + WIP object + state marker.

**Code**: SVG `<g>` with:
- `<rect>` belt body (wide, muted gray)
- `<rect>` edge rails (narrower, darker)
- `<path>` or repeated `<line>` for roller segmentation
- `<polygon>` arrow marks at intervals

---

## 11. Popup Strategy

### 11.1 Position
Upper-right overlay zone. Translucent white/light frosted panel.

### 11.2 Appearance
- Light frosted panel (`rgba(255,255,255,0.88)`)
- Subtle shadow
- Rounded corners (10px radius)
- 320–420px width, auto height (max ~50% viewport)
- Internal scroll when needed

### 11.3 Modes

**Overview mode** (default, no selection):
- Line state
- Step/time
- Created/released/holds
- Total WIP on line

**Station mode** (station selected):
- Station name + type
- Current occupant (WIP ID)
- Latest state/quality
- Local activity summary

**Control point mode** (AP06/AP08/AP11):
- Latest result
- Current WIP
- Latest quality state
- High-level context

### 11.4 Relationship to Inspector

The popup becomes the **default** contextual information surface. The full-height Inspector (Frame C) becomes an **expanded detail mode** accessible from the popup when deeper investigation is needed.

**Migration path**:
1. I09-P01: Add popup scaffold div + CSS
2. I09-P04: Wire popup to existing `_renderInspector` data, show summary/station modes
3. Existing Inspector sections (Quality History, Measurements, Checklist, Genealogy) accessible via "More details" affordance in popup

**Do not remove the Inspector** — it remains available as the Frame C deep-detail surface. The popup adds a lighter default interaction layer.

---

## 12. Motion Rules

### What may move
- Conveyor directional cue (subtle pulse)
- Pallet on conveyor (during valid step transition)
- WIP on pallet (moves with pallet)

### What must not move
- Station bodies
- Station equipment icons
- Conveyor structure (rails, rollers)
- Branch connectors

### Motion constraints
- Movement only along valid conveyor path, right → left
- One logical step at a time
- No skipping station logic
- No continuous free-running animation
- Motion tied to runtime step/state change

### Default motion level: **Level B — Limited transition cues**
- Subtle conveyor directional pulse
- Short shift of pallet/WIP during step transition
- Brief transfer cue between adjacent valid positions

---

## 13. Unified VF Visual System

### 13.1 Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `vf-bg-page` | `#F5F7FA` | Page background |
| `vf-bg-canvas` | `#FFFFFF` | SVG canvas background |
| `vf-bg-panel` | `rgba(255,255,255,0.88)` | Popup panel |
| `vf-border-soft` | `#D9E1EA` | Subtle borders |
| `vf-text-primary` | `#1F2A37` | Primary text |
| `vf-text-secondary` | `#5B6777` | Secondary text |
| `vf-conveyor` | `#AEB8C4` | Conveyor belt body |
| `vf-conveyor-edge` | `#7C8796` | Conveyor rails |
| `vf-flow-arrow` | `#5B8DEF` | Flow direction arrows |
| `vf-obj-stator` | `#2DB9C8` | Stator assy |
| `vf-obj-rotor` | `#E8A23A` | Rotor |
| `vf-obj-joined` | `#42A58A` | Joined motor |
| `vf-obj-pretest` | `#3E8FB0` | Pre-test motor |
| `vf-obj-packed` | `#B68B57` | Packed goods |
| `vf-pallet-wood` | `#C89A63` | Wooden pallet |
| `vf-state-pass` | `#2EAD5B` | PASS |
| `vf-state-hold` | `#E5A93B` | HOLD |
| `vf-state-fail` | `#D84B4B` | FAIL/NG |
| `vf-state-selected` | `#2F80ED` | Selection outline |
| `vf-state-historical` | `#7B8AA0` | Historical/muted |

### 13.2 Typography

- Font stack: `"Inter", "Segoe UI", system-ui, sans-serif`
- Page title: 20–24px
- Section title: 16–18px
- Station label: 13–14px
- Token label: 11–12px
- Small metadata: 11px minimum operational

### 13.3 Spacing (4px grid)

| Token | Value |
|-------|-------|
| `vf-space-xs` | 4px |
| `vf-space-sm` | 8px |
| `vf-space-md` | 12px |
| `vf-space-lg` | 16px |
| `vf-space-xl` | 24px |
| `vf-space-xxl` | 32px |

### 13.4 Radius

| Token | Value | Usage |
|-------|-------|-------|
| `vf-radius-sm` | 6px | Small elements |
| `vf-radius-md` | 10px | Cards, panels |
| `vf-radius-lg` | 14px | Large panels |

### 13.5 SVG Primitive Library

| Primitive | Purpose |
|-----------|---------|
| `VFCanvasFrame` | SVG canvas wrapper with background |
| `VFConveyorLane` | Main conveyor belt with rails + arrows |
| `VFConveyorArrow` | Directional arrow mark |
| `VFStationCell` | Station body footprint |
| `VFStationLabel` | AP label for station |
| `VFPallet` | Wooden pallet carrier |
| `VFWipToken` | WIP object on pallet (base) |
| `VFBranchConnector` | RSO2 branch line |
| `VFOutputZone` | LINE OUT indicator |
| `VFStatorAssyToken` | Stator assy silhouette |
| `VFRotorToken` | Rotor silhouette |
| `VFMotorJoinedToken` | Joined motor silhouette |
| `VFMotorPreTestToken` | Pre-test motor silhouette |
| `VFMotorTestedToken` | Tested motor + status marker |
| `VFPackedGoodsToken` | Packed goods carton |
| `VFStateBadge` | PASS/FAIL/HOLD overlay marker |
| `VFSelectionOutline` | Selection highlight |
| `VFTestBenchIcon` | Test station icon |
| `VFVisionIcon` | Vision camera icon |
| `VFJoinIcon` | Join/interlock icon |
| `VFPackageIcon` | Packaging icon |
| `VFPopupCard` | Top-right popup container |
| `VFMetricPill` | Numeric indicator |
| `VFStatusChip` | Status badge |

### 13.6 Code Organization

**CSS**: Organized by layer
```
assy_demo.css (or vf-visual.css):
  vf-tokens       — CSS custom properties for colors, spacing, radius
  vf-shell        — Page, header, controls, footer
  vf-scene        — SVG canvas, conveyor
  vf-station      — Station cells, labels, icons
  vf-token-object — Pallet, WIP silhouettes
  vf-popup        — Popup card, metric pills, status chips
  vf-selection    — Selection outlines, state overlays
  vf-responsive   — Media queries
```

**JS**: SVG rendering helpers
```
assy_demo.js (additions):
  VF.renderPallet(x, y)           → SVG string
  VF.renderStatorAssy(x, y)       → SVG string
  VF.renderRotor(x, y)            → SVG string
  VF.renderJoinedMotor(x, y)      → SVG string
  VF.renderPreTestMotor(x, y)     → SVG string
  VF.renderTestedMotor(x, y, state) → SVG string
  VF.renderPackedGoods(x, y)      → SVG string
  VF.renderStationCell(x, y, id, archetype) → SVG string
  VF.renderConveyor(y, width)     → SVG string
  VF.renderPopup(data)            → HTML string
```

---

## 14. Codebase-Fit Assessment

### 14.1 What changes

| Area | Current | Target | Effort |
|------|---------|--------|--------|
| Shell theme | Dark (`#0d1117`) | Light (`#F5F7FA`) | Low — CSS-only |
| Canvas background | Dark gradient | Light solid | Low — one SVG rect change |
| Flow direction | Left→Right | Right→Left | Medium — mirror all X coords |
| Station nodes | 88×90 text rectangles | Illustrated top-down cells | High — new SVG primitives |
| WIP tokens | Text labels in rects | Pallet + illustrated silhouettes | High — new SVG primitives |
| Conveyor | 10px bar | Rails + rollers + arrows | Medium — new SVG paths |
| Info surface | Right panel 280px | Top-right popup 320-420px | Medium — new div + CSS |
| Color system | Ad-hoc dark colors | Unified VF tokens | Medium — CSS variable migration |
| Inspector | Full-height panel | Popup default + Inspector expanded | Low — refactor existing |

### 14.2 What stays the same

- Data contracts: `positions[]`, `genealogy[]`, `quality_records[]`, `recent_quality_events[]`
- Selection model: `selectStation()`, `selectWip()`, `selectEvent()`
- Refresh persistence: WIP follows `positions[]`, historical indicator for exited WIPs
- Truthfulness invariants: `positions[]` = sole physical truth
- Navigation: Frame A → B, Back, no reset
- AUTO ownership: single timer
- Zoom/pan: `getScreenCTM().inverse()`, Fit ≠ 100%
- Scenario semantics: global vs effective
- LIVE/STALE/UNAVAILABLE
- S04 fallback: preserved unchanged

### 14.3 Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Right→left reversal misses coordinates | Medium | Systematic audit: every SVG x-coordinate, arrow direction, text-anchor, marker orientation |
| WIP token illustrations too complex | Medium | Start with simplified geometric silhouettes; refine in P05 |
| Popup vs Inspector dual path confusion | Low | Popup is default; Inspector is explicit "More details" action. Clear single code path for data binding |
| Light theme breaks S04 fallback | Low | S04 fallback kept in original dark theme; only Frame A/B/C migrate |
| Performance with many SVG primitives | Low | SVG `<g>` groups scale well; no Canvas rendering needed |

---

## 15. Implementation Split

### I09-P01 — Bright Shell + Top-Down Scene Scaffold

**Scope**: CSS migration, shell color change, canvas to light, right-to-left geometry.

**Files**:
- `assy_demo.css`: Add VF token variables, migrate shell/header/controls colors
- `assy_demo.html`: Update canvas viewBox (e.g., 1600×900), mirror conveyor/arrow geometry
- `assy_demo.js`: Mirror `FB_STATION_X`, update SSO2/RSO2/OUT positions

**Acceptance**:
- Page background light (#F5F7FA)
- Header/controls light-themed
- Canvas white background
- Conveyor flows right→left
- Stations rendered in right→left order
- SSO2/RSO2 inputs at right, OUT at left
- Frame A overview also migrated
- Dark theme S04 fallback preserved

### I09-P02 — Physical Station + Object Library

**Scope**: Pallet SVG, WIP token silhouettes, station archetype primitives, conveyor redesign.

**Files**:
- `assy_demo.js`: Add `VF.*` rendering helpers for pallet, WIP tokens, station cells, conveyor
- `assy_demo.css`: Add station/token-object styles
- `assy_demo.html`: Minor updates for new SVG structure

**Acceptance**:
- Wooden pallet rendered as carrier base
- 6 WIP types visually distinct (silhouette + color)
- Station cells have equipment icon hints
- AP04 JOIN has RSO2 branch visual
- AP06 has test bench icon
- AP08 has vision camera icon
- AP11 has QC/release icon
- Conveyor has rails, roller segments, direction arrows
- State overlays (PASS/FAIL/HOLD) on tokens

### I09-P03 — Controlled Conveyor Movement Cues

**Scope**: Step-bound pallet/WIP transitions, conveyor directional pulse.

**Files**:
- `assy_demo.js`: Add transition rendering between snapshot states
- `assy_demo.css`: Add transition/movement CSS

**Acceptance**:
- Pallet/WIP shifts position on STEP (right→left)
- Conveyor shows subtle directional pulse
- Movement constrained to valid conveyor path
- No movement for station bodies or equipment
- No continuous free-running animation
- Zoom/pan unaffected by movement

### I09-P04 — Context Popup Integration

**Scope**: Top-right popup card, overview/station/control-point modes.

**Files**:
- `assy_demo.html`: Add popup scaffold div
- `assy_demo.js`: Add popup rendering from existing data, wire to selection
- `assy_demo.css`: Add popup styles (frosted panel, shadow, rounded corners)

**Acceptance**:
- Popup appears top-right on station/WIP selection
- Overview mode shows line state/step/time/counters
- Station mode shows station + occupant + quality
- Control-point mode shows latest result for AP06/AP08/AP11
- "More details" opens existing Inspector sections
- Popup dismissible
- Inspector still functional for deep detail
- Right panel may reduce when popup is active

### I09-P05 — VF Visual System Consolidation

**Scope**: CSS token extraction, reusable primitives, responsive refinement, consistency.

**Files**:
- `assy_demo.css`: Organize into vf-tokens/vf-shell/vf-scene/... sections
- `assy_demo.js`: Extract reusable SVG helpers
- `assy_demo.html`: Minor cleanup

**Acceptance**:
- All VF color tokens used consistently
- Typography scale applied uniformly
- Spacing grid used throughout
- 1920×1080: all elements readable, proper proportions
- 1366×768: responsive contraction, text ≥11px
- S04 fallback still functional
- Frame A overview also migrated to bright theme
- No dark-theme remnants in production paths

---

## 16. Test / Evidence Plan

### Per-gate verification

| Gate | Visual checks | Interaction checks | Regression |
|------|--------------|-------------------|------------|
| I09-P01 | Shell color, flow direction, station order | Navigation, zoom/pan | Frame A, S04 fallback |
| I09-P02 | Pallet + WIP silhouettes, station icons, conveyor detail | Station/WIP click, Inspector | Selection, quality data |
| I09-P03 | Step transition, conveyor pulse | STEP/AUTO, zoom during movement | Data integrity |
| I09-P04 | Popup position, modes, frosted appearance | Popup open/close, "More details" → Inspector | Inspector functionality |
| I09-P05 | Token consistency, typography, responsive | All interactions | Full regression |

### Evidence format
- Running UI (primary)
- DOM/source inspection
- Screenshots supplemental
- No fabricated test data

---

## 17. Acceptance Criteria for I09 (Collective)

I09 is complete when all P01–P05 gates satisfy:

- [ ] Top-down illustrated industrial twin style visible
- [ ] Right-to-left flow correct
- [ ] Wooden pallets as carrier base
- [ ] 6 WIP types visually distinct
- [ ] Station archetypes with equipment icons
- [ ] Conveyor with rails + arrows
- [ ] Bright professional shell
- [ ] Top-right popup functional
- [ ] Popup/Inspector relationship clear
- [ ] Step-bound movement only
- [ ] State overlays correct (PASS/FAIL/HOLD/SELECTED)
- [ ] Selection + highlight preserved
- [ ] Inspector functionality preserved
- [ ] Zoom/pan preserved
- [ ] Truthfulness invariants preserved
- [ ] Frame A migrated to bright theme
- [ ] S04 fallback preserved in dark theme
- [ ] No backend/runtime/API changes
- [ ] I07/I08/M6-S05 not involved

---

## 18. Forbidden

- ❌ No production implementation in DG06-01
- ❌ No backend/runtime/API changes
- ❌ No weakening of design into generic dashboard
- ❌ No removal of Frame C Inspector
- ❌ No motion/animation implementation (I07, I09-P03 not yet authorized)
- ❌ No MES integration
- ❌ No new framework or library dependency

---

> **DG06-01 is READY FOR SA REVIEW.**
>
> Next: SA approval → I09-P01 Bright Shell + Scene Scaffold implementation.
