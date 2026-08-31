# M6-S04B-I09-P02 — SA Review Report

> **Status**: READY FOR SA REVIEW  
> **Gate**: I09-P02 — Physical Station + Object Visual Library  
> **Baseline**: `1273bbf` (I09-P01 CLOSED)  
> **Current head**: `4a1f3f1`  
> **Date**: 2026-08-12  

---

## 1. Purpose

Implement the reusable physical visualization library: 6 WIP visual primitives, wooden pallet carrier, station archetypes with equipment icons, and the canonical position→visual-token mapping.

---

## 2. Changed Files

```
src/virtual_factory/ui/static/assy_demo.js   (+174 / -45)
```

No HTML/CSS changes needed — all visuals are SVG primitives rendered from JS.

---

## 3. VF SVG Primitive Library

14 reusable helpers under `VF.*` namespace:

| Helper | Type | Visual |
|--------|------|--------|
| `VF.pallet(x,y)` | Carrier | Wooden pallet (72×24px, slat lines, #C89A63) |
| `VF.statorAssy(x,y)` | WIP | Circular housing ring, central void, terminal tabs |
| `VF.rotor(x,y)` | WIP | Elongated shaft, central rotor body |
| `VF.motorJoined(x,y)` | WIP | Compact cylindrical body, endcap hints |
| `VF.motorPreTest(x,y)` | WIP | Complete motor, mounting feet, bolt details |
| `VF.motorTested(x,y)` | WIP | Motor body + green ✓ checkmark badge |
| `VF.packedGoods(x,y)` | WIP | Carton box, seam/tape lines, corner tabs |
| `VF.stateOverlay(x,y,state)` | Overlay | Red badge with ! for FAIL/HOLD |
| `VF.joinIcon(x,y)` | Icon | Crosshair circle (#B8860B) |
| `VF.testIcon(x,y)` | Icon | "T" in rectangle (blue) |
| `VF.visionIcon(x,y)` | Icon | Camera lens + body (blue) |
| `VF.finalIcon(x,y)` | Icon | Checkmark in rectangle (blue → green check) |
| `VF.hmiIcon(x,y)` | Icon | Mini terminal screen |
| `VF.stationCell(...)` | Cell | Full station cell with archetype-specific border + icon |

---

## 4. Position → Visual Token Mapping

Implemented in `VF_TOKEN`:

| Position | Token | Base color | Silhouette |
|----------|-------|------------|------------|
| PRE-ASSY | STATOR | #2DB9C8 | Circular housing |
| AP01 | STATOR | #2DB9C8 | Circular housing |
| AP02 | STATOR | #2DB9C8 | Circular housing |
| AP03 | STATOR | #2DB9C8 | Circular housing |
| AP04 | STATOR | #2DB9C8 | Circular housing |
| AP05 | JOINED | #42A58A | Compact cylinder |
| AP06 | PRETEST | #3E8FB0 | Complete motor + feet |
| AP07 | TESTED | Motor family + ✓ | Motor + test badge |
| AP08 | TESTED | Motor family + ✓ | Motor + test badge |
| AP09 | TESTED | Motor family + ✓ | Motor + test badge |
| AP10 | PACKED | #B68B57 | Carton box |
| AP11 | PACKED | #B68B57 | Carton box |

---

## 5. Station Archetypes

| Station | Archetype | Icon | Border |
|---------|-----------|------|--------|
| PRE-ASSY | INPUT | HMI terminal | Soft gray |
| AP01–03,05,07,09,10 | ASSY | (clean) | Soft gray |
| AP04 | JOIN | Crosshair circle | Amber #B8860B |
| AP06 | TEST | "T" badge | Blue |
| AP08 | VISION | Camera lens | Blue |
| AP11 | FINAL | Checkmark | Blue |

---

## 6. Truthfulness Boundaries

| Rule | Implementation |
|------|---------------|
| AP04 = STATOR on main conveyor | ✓ Prevents MTR JOINED at AP04 |
| AP05 = MTR JOINED | ✓ After AP04 index |
| AP06 = MTR PRE-TEST | ✓ Before test completion |
| AP06 FAIL/HOLD | ✓ PRE-TEST base + red overlay, never TESTED |
| AP07–09 = TESTED MTR | ✓ After AP06 pass |
| AP08 NG/reinspect | ✓ TESTED base + red overlay, never reverted |
| AP09 = TESTED MTR | ✓ Boxing not yet completed |
| AP10 = PACKED GOODS | ✓ After AP09 index |
| AP11 = PACKED GOODS | ✓ Final QC on packaged goods |
| RSO2 = ROTOR branch | ✓ ROTOR visual at branch point, not main conveyor |
| Quality = overlay | ✓ FAIL/HOLD as red badge overlay, not category change |
| `positions[]` sole truth | ✓ No fabricated occupancy |

---

## 7. Token Composition

Each occupied station renders:

```
<g class="fb-wip-token" data-wip="MTR-0003">
  VF.pallet()           — wooden pallet base
  VF.motorPreTest()     — WIP silhouette
  VF.stateOverlay()     — FAIL/HOLD if applicable
  <text> MTR-0003       — WIP ID label
  <text> PRE-TEST       — token type label
  <text> PAL-003        — carrier ID
</g>
```

---

## 8. Tests

```
python -m pytest tests/test_demo_overview.py tests/test_demo_composition.py tests/test_api.py tests/test_assy_demo.py tests/test_quality_records_projection.py -q -k "not TestVScenarioSwitch"
136 passed, 1 deselected
```

---

## 9. Scope

```
Backend modified: NO
Runtime modified: NO
API modified: NO
Motion implemented: NO (P03)
Popup data integration: NO (P04)
I09-P03 started: NO
I09-P04 started: NO
I09-P05 started: NO
I07/I08/M6-S05 started: NO
```

---

> **M6-S04B-I09-P02 is READY FOR SA REVIEW at `4a1f3f1`.**
