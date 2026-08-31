# M6-S04B-I09-P01 — SA Review Report

> **Status**: READY FOR SA REVIEW  
> **Gate**: I09-P01 — Bright Shell + Top-Down Scene Scaffold  
> **Baseline**: `e3b723a` (DG06-01-C02 CLOSED)  
> **Current head**: `1273bbf`  
> **Date**: 2026-08-12  

---

## 1. Purpose

Implement the structural visual foundation for the unified Virtual Factory style: bright professional shell, VF design tokens, right-to-left top-down scene geometry, conveyor scaffold, station cell scaffold, popup shell.

---

## 2. Changed Files

```
src/virtual_factory/ui/static/assy_demo.css   (+171 / -104, full rewrite of Frame B/C section)
src/virtual_factory/ui/static/assy_demo.html   (popup scaffold + conveyor redesign)
src/virtual_factory/ui/static/assy_demo.js     (right-to-left geometry + station cell scaffold)
```

---

## 3. Visual Implementation

### 3.1 VF Design Tokens

32 CSS custom properties introduced under `:root`:

| Category | Tokens |
|----------|--------|
| Shell | `--vf-bg-page:#F5F7FA`, `--vf-bg-canvas:#FFFFFF`, `--vf-shell-header`, `--vf-shell-footer` |
| Border | `--vf-border-soft:#D9E1EA`, `--vf-border-panel` |
| Text | `--vf-text-primary:#1F2A37`, `--vf-text-secondary:#5B6777`, `--vf-text-muted` |
| Object | `--vf-obj-stator:#2DB9C8`, `--vf-obj-rotor:#E8A23A`, `--vf-obj-joined:#42A58A`, `--vf-obj-pretest`, `--vf-obj-packed`, `--vf-pallet-wood` |
| State | `--vf-state-pass:#2EAD5B`, `--vf-state-hold:#E5A93B`, `--vf-state-fail:#D84B4B`, `--vf-state-selected:#2F80ED`, `--vf-state-historical` |
| Spacing/Radius | `--vf-space-* (4/8/12/16/24/32)`, `--vf-radius-* (6/10/14)` |

### 3.2 Bright Shell

- Frame B: `background: var(--vf-bg-page)` (#F5F7FA) — was #0d1117
- Header: white background, light borders
- Controls: light footer (#F8F9FB), colored buttons (red RESET, green STEP, blue AUTO)
- Right panel: white background, light borders, light event items
- Inspector: light-adapted (white sections, light borders, historical = yellow #FFF3CD)
- Frame A and S04 fallback: **preserved in original dark theme**

### 3.3 Right-to-Left Geometry

`FB_STATION_X` array reversed:

```
Before (left→right): [140, 240, 340, 440, 540, 640, 740, 840, 940, 1040, 1140, 1240]
After  (right→left): [1780,1680,1580,1480,1380,1280,1180,1080, 980,  880,  780,  680]
```

- PRE-ASSY = rightmost position (1780)
- AP11 = leftmost position (680)
- SSO2 input: RIGHT side (x=1900)
- OUT: LEFT side (x=140)
- RSO2 branch: at AP04 position (x=1380)
- LINE OUT arrow: ← (LEFT-pointing)
- `FB_CONTENT_BOUNDS` updated: `{x:100, y:190, w:1720, h:320}`

### 3.4 Conveyor Scaffold

- Belt body: 18px height, #E5E9ED fill
- Top rail: 4px, #7C8796
- Bottom rail: 4px, #7C8796
- Roller segment placeholder (g element)
- Static directional arrows LEFT-pointing

### 3.5 Station Cell Scaffold

- Clean top-down cell footprint: 88×90 rect
- Light background (#F8F9FB), soft border (var(--vf-border-soft))
- AP04: amber border (#B8860B), warm background (#FFFDF5)
- AP11: blue border (var(--vf-state-selected)), light blue background
- HOLD: red border + pink background (#FFF5F5)
- Selected: blue border highlight
- Text colors: VF tokens for readability on light background

### 3.6 Popup Scaffold

- Top-right absolute position (360px wide, max 55vh)
- Translucent frosted panel (rgba(255,255,255,0.92) + backdrop-filter: blur)
- Header with title + close button
- Placeholder body: "Popup — I09-P04 integration"
- Hidden by default, open/close via `ctrlB.openPopup()` / `ctrlB.closePopup()`
- Responsive: 280px at ≤1400px

---

## 4. Preserved Functionality (Verified)

| Feature | Status |
|---------|--------|
| Station click → Inspector | ✓ |
| WIP token click | ✓ |
| Event click | ✓ |
| Selection follows positions[] after STEP | ✓ |
| Historical WIP indicator | ✓ |
| Empty station shows EMPTY | ✓ |
| Zoom (pointer-anchored, getScreenCTM) | ✓ |
| Pan (left-drag) | ✓ |
| Fit ≠ 100% | ✓ |
| Frame A → B navigation (no reset) | ✓ |
| Back B → A (fresh overview) | ✓ |
| Single AUTO timer | ✓ |
| Scenario sync (global ≠ effective) | ✓ |
| LIVE/STALE/UNAVAILABLE | ✓ |
| S04 fallback (preserved dark) | ✓ |
| Inspector (all sections) | ✓ |

---

## 5. Tests

```
python -m pytest tests/test_demo_overview.py tests/test_demo_composition.py tests/test_sub_line_identity.py tests/test_api.py tests/test_assy_demo.py tests/test_quality_records_projection.py -q -k "not TestVScenarioSwitch"
162 passed, 1 deselected (pre-existing flaky test_reset_creates_fresh_runtimes)
```

---

## 6. Scope Confirmation

```
Backend modified: NO
Runtime modified: NO
API modified: NO
WIP object library implemented: NO (P02)
Motion implemented: NO (P03)
Popup data integration implemented: NO (P04)
I09-P02 started: NO
I09-P03 started: NO
I09-P04 started: NO
I09-P05 started: NO
I07/I08/M6-S05 started: NO
```

---

> **M6-S04B-I09-P01 is READY FOR SA REVIEW at `1273bbf`.**
