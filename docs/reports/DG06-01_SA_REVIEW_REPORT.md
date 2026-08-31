# DG06-01 + DG06-01-C01 — SA Review Report

> **Status**: READY FOR SA REVIEW  
> **Baseline**: `b232bdc` (I06 CLOSED)  
> **Current head**: `5ca429f`  
> **Date**: 2026-08-12  

---

## 1. Executive Summary

DG06-01 translates the SA/Designer *VF Visual System Top-Down Master Design Brief v1* into a canonical repo design document at `docs/ui/M6_S04B_DG06_PHYSICAL_LAYER_REALISM_AND_BRIGHT_UI.md`. DG06-01-C01 corrects two directional/WIP-contract issues identified in SA review.

**No production code has been modified.** This is a design-only gate.

---

## 2. Gate History

| Gate | Commit | Status |
|------|--------|--------|
| DG06-01 | `5d6d42f` | Design document created (625 lines) |
| DG06-01-C01 | `5ca429f` | Directional fix + WIP evolution contract (+43/-6) |

---

## 3. Frozen Design Decisions

### 3.1 Visual Style

> **Top-down Illustrated Industrial Twin**

- 2D only — compatible with existing SVG/HTML/CSS/JS architecture
- Physical layer first, information layer secondary and on-demand
- Not a SCADA screen, not a game, not a cartoon, not a pseudo-3D render

### 3.2 Flow Direction

> **RIGHT → LEFT**

```
LEFT / DOWNSTREAM (output)                    RIGHT / UPSTREAM (input)

[OUT] ← ╔AP11╗ ← [AP10] ← [AP09] ← ╔AP08╗ ← [AP07] ← ╔AP06╗ ← [AP05] ← ╔AP04╗ ← [AP03] ← [AP02] ← [AP01] ← [PRE] ← [SSO2]
        ║FINAL║                            ║VISN║              ║TEST║              ║JOIN║
                                                                                ↑
                                                                             [RSO2]
```

- SSO2 and RSO2 inputs at RIGHT
- LINE OUT at LEFT
- All station-to-station arrows point LEFT (←)

### 3.3 Carrier — Wooden Pallet

- Light wood tone (`#C89A63`)
- Rectangular top-down silhouette with slat lines
- Consistent size family
- All WIP objects placed ON pallet, never floating

### 3.4 WIP Visual-State Evolution Contract

| Process segment | Stations | Visual token | Base color | Transition |
|----------------|----------|-------------|------------|------------|
| SSO2 → AP03 | PRE-ASSY, AP01, AP02, AP03 | **STATOR ASSY** | Teal `#2DB9C8` | Stator + pressed motor housing |
| RSO2 branch | (branch) | **ROTOR** | Amber `#E8A23A` | Rotor shaft component |
| AP04 → AP05 | AP04, AP05 | **MTR JOINED** | Blue-green `#42A58A` | After successful join |
| AP05 → AP06 | AP05 | **MTR PRE-TEST** | Blue-green `#3E8FB0` | Before electrical test |
| AP06 → AP09 | AP06, AP07, AP08, AP09 | **TESTED MTR** | Motor family + overlay | After electrical test |
| AP09 → OUT | AP09, AP10, AP11 | **PACKED GOODS** | Brown `#B68B57` | After boxing at AP09 |

**Packaging transition**: PACKED GOODS begins at AP09 (Boxing). Per repo station labels: AP09 = "Boxing", AP10 = "Closing / labeling / palletizing", AP11 = "Final QC / release".

### 3.5 Quality State Overlays

Quality outcome is always an overlay, never a change of object category:

| State | Overlay |
|-------|---------|
| PASS | Green corner badge/ring (`#2EAD5B`) |
| HOLD | Amber badge/ring (`#E5A93B`) |
| FAIL / NG | Red badge/ring (`#D84B4B`) |
| SELECTED | Blue outline (`#2F80ED`) |
| HISTORICAL | Muted gray-blue (`#7B8AA0`) |

**Critical invariant**: A TESTED MTR with FAIL is still a TESTED MTR with a red overlay — not a seventh WIP type.

### 3.6 Station Archetypes

| Station | Archetype | Equipment icon |
|---------|-----------|---------------|
| PRE-ASSY | Input / loading | Loading table, SSO2 feed indicator |
| AP01, AP02, AP05, AP07, AP09, AP10 | Assembly / manual | Workbench footprint |
| AP03 | Check station | Checklist / QC workstation |
| AP04 | **JOIN** | Central fixture, stator+rotor merge, join icon |
| AP06 | **TEST** | Test bench, meter motif, cable fixture |
| AP08 | **VISION** | Inspection booth, camera icon |
| AP11 | **FINAL** | Final check pad, QC mark, release handoff |

### 3.7 Information Surface Strategy

- **Default**: Top-right translucent popup (320–420px, frosted panel, `rgba(255,255,255,0.88)`)
- **Popup modes**: Overview (line state, counters), Station (occupant + quality), Control Point (AP06/AP08/AP11 latest result)
- **Expanded detail**: Existing Frame C Inspector accessible via "More details" from popup
- Inspector is NOT removed — popup is the lighter default layer

### 3.8 Motion Constraints

- Only conveyor + pallet + WIP may show movement
- Station bodies, equipment icons, branch connectors are stationary
- Movement tied to runtime step/state change
- One logical step at a time, right → left
- No continuous free-running animation
- Motion level: **Level B — Limited transition cues**

---

## 4. Unified VF Visual System

### 4.1 Color Tokens (excerpt)

| Token | Value | Usage |
|-------|-------|-------|
| `vf-bg-page` | `#F5F7FA` | Page background |
| `vf-bg-canvas` | `#FFFFFF` | SVG canvas |
| `vf-obj-stator` | `#2DB9C8` | Stator assy |
| `vf-obj-rotor` | `#E8A23A` | Rotor |
| `vf-obj-joined` | `#42A58A` | Joined motor |
| `vf-state-pass` | `#2EAD5B` | PASS |
| `vf-state-fail` | `#D84B4B` | FAIL/NG |
| `vf-pallet-wood` | `#C89A63` | Pallet |

### 4.2 SVG Primitive Library

21 primitives defined: `VFCanvasFrame`, `VFConveyorLane`, `VFStationCell`, `VFPallet`, `VFWipToken` variants (6), `VFStateBadge`, `VFSelectionOutline`, `VFTestBenchIcon`, `VFVisionIcon`, `VFJoinIcon`, `VFPopupCard`, etc.

### 4.3 Typography

- Font: `"Inter", "Segoe UI", system-ui, sans-serif`
- Station label: 13–14px
- Token label: 11–12px
- Minimum operational: 11px

---

## 5. Codebase-Fit Assessment

| Area | Current | Target | Effort | Risk |
|------|---------|--------|--------|------|
| Shell theme | Dark `#0d1117` | Light `#F5F7FA` | Low | CSS-only |
| Flow direction | Left→Right | Right→Left | Medium | Mirror all X coords |
| Station nodes | 88×90 text rects | Illustrated cells | High | New SVG primitives |
| WIP tokens | Text labels | Pallet + silhouettes | High | New SVG primitives |
| Conveyor | 10px bar | Rails + rollers | Medium | New SVG paths |
| Info surface | Right panel | Top-right popup | Medium | New div + CSS |
| Color system | Ad-hoc dark | Unified VF tokens | Medium | CSS variables |

**Key risk**: Right→left reversal requires systematic audit of every SVG x-coordinate. Mitigation: `FB_STATION_X` array reversed, SSO2/OUT positions swapped, arrow markers reoriented.

---

## 6. Implementation Split

| Gate | Scope | Files |
|------|-------|-------|
| **I09-P01** | Bright shell + top-down scene scaffold | `assy_demo.css`, `.html`, `.js` |
| **I09-P02** | Physical station + object library | `assy_demo.js`, `.css` |
| **I09-P03** | Controlled conveyor movement cues | `assy_demo.js`, `.css` |
| **I09-P04** | Context popup integration | `assy_demo.html`, `.js`, `.css` |
| **I09-P05** | VF style consolidation / polish | All three files |

---

## 7. What Stays the Same

- Data contracts: `positions[]`, `genealogy[]`, `quality_records[]`, `recent_quality_events[]`
- Selection model: `selectStation()`, `selectWip()`, `selectEvent()`
- Refresh persistence: WIP follows `positions[]`
- Truthfulness invariants: `positions[]` = sole physical truth
- Navigation: Frame A → B, Back, no reset
- AUTO ownership: single timer
- Zoom/pan: `getScreenCTM().inverse()`, Fit ≠ 100%
- Scenario semantics: global vs effective
- LIVE/STALE/UNAVAILABLE
- S04 fallback: preserved in original dark theme

---

## 8. Scope Confirmation

```
Production code modified: NONE
I09-P01 implementation started: NO
I07 (Motion) started: NO
I08 (Hardening) started: NO
M6-S05 (MES) started: NO
```

---

## 9. Changed Files

```
docs/ui/M6_S04B_DG06_PHYSICAL_LAYER_REALISM_AND_BRIGHT_UI.md   (5d6d42f: +625 new)
docs/ui/M6_S04B_DG06_PHYSICAL_LAYER_REALISM_AND_BRIGHT_UI.md   (5ca429f: +43/-6)
```

---

> **DG06-01 + DG06-01-C01 are READY FOR SA REVIEW at `5ca429f`.**
>
> Awaiting DG06-01 closure and I09-P01 authorization.
