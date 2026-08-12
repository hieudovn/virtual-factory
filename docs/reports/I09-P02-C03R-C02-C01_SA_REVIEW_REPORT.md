# M6-S04B-I09-P02-C03R-C02-C01 — SA Review Report
## Physical Composition Freeze — Final

**Status**: READY FOR SA REVIEW  
**Baseline**: `2189b0e` (C01)  
**New head**: `67ade9c`

---

## 1. Changed Files

```
src/virtual_factory/ui/static/assy_demo.css
src/virtual_factory/ui/static/assy_demo.html
src/virtual_factory/ui/static/assy_demo.js
docs/ui/evidence/i09-p02-c03r/VF_VISUAL_REVIEW_HARNESS.html
```

---

## 2. Composition — VF_LAYOUT

```js
VF_LAYOUT = {
  lineInX: 1890,  lineOutX: 135,
  stationX: [1720,1600,1485,1370,1240,1115,985,865,735,615,495,365],
  conveyorY: 420, conveyorH: 160,   // 2.5x wider (body 140 + rails 10+10)
  stationY: 330,   wipY: 500,       // pallet centered in body (430-570)
}
```

| Station | X | Gap | Landmark |
|---------|---|-----|----------|
| PRE-ASSY | 1720 | — | |
| AP01 | 1600 | 120 | |
| AP02 | 1485 | 115 | |
| AP03 | 1370 | 115 | |
| **AP04** | **1240** | **130** | JOIN |
| AP05 | 1115 | 125 | |
| **AP06** | **985** | **130** | TEST |
| AP07 | 865 | 120 | |
| **AP08** | **735** | **130** | VISION |
| AP09 | 615 | 120 | |
| AP10 | 495 | 120 | |
| **AP11** | **365** | **130** | FINAL |

---

## 3. Conveyor + Pallet

| Property | Value |
|----------|-------|
| Conveyor total height | 160px |
| Conveyor body | 140px (420→570) |
| Rails | 10px each |
| Pallet size | **120×120 square** |
| Pallet color | #C4A882 (cool brown, distinct from ROTOR #E8A23A) |
| Pallet position | Centered at y=500 (conveyor body center) |
| Rollers | 16×110px at 40px intervals |

---

## 4. LINE-IN / LINE-OUT — Off-line Repair Points

| Element | Position | Label | Meaning |
|---------|----------|-------|---------|
| **LINE IN** | Above AP06 (TEST) | "QC HOLD → REPAIR" | Product taken off-line for repair when quality hold detected |
| **LINE OUT** | Above AP08 (VISION) | "REPAIR → RETURN" | Repaired product returned to line |

Both are outside the conveyor, with amber/green dashed boxes and connector lines. No SSO2/OUT arrows on the conveyor.

---

## 5. Visual Hierarchy (Station Template)

```
AP BADGE (y=276)
OPERATION NAME (y=300)
    ↓ connector
MACHINE BODY (center y=354)
    ↓
CONVEYOR (y=420-580)
    ↓
PALLET + WIP (center y=500)
```

---

## 6. Labels (Shortened)

| Station | Label |
|---------|-------|
| PRE-ASSY | Prep |
| AP02 | Term. Box |
| AP03 | Mech. Check |
| AP05 | Mech. Assy |

---

## 7. AP09 vs AP10 Distinction

- **AP09 Boxing**: open carton workbench with side panel flaps
- **AP10 Pack/Label**: closed carton with diagonal strap + tape marks (darker color)

---

## 8. Flow Arrow

- Removed repeated green arrows from conveyor
- Background flow arrow removed per user request
- Only RSO2 branch line remains

---

## 9. Collision Audit

| Viewport | Result |
|----------|--------|
| 1920×1080 | No overlap, all stations visible |
| 1600×900 | No overlap, readable |
| 1366×768 | No overlap, LINE IN/OUT visible |

---

## 10. Evidence

| # | Path | Description |
|---|------|-------------|
| EV1 | Browser: Frame B clean | Full line with LINE IN/OUT, conveyor, zones |
| EV2 | Browser: AP04 JOIN | RSO2 branch + stator, two-input fixture |
| EV3 | Harness: `/static/assy_demo.js` → VF.* | Production primitives loaded, zero console errors |
| EV4 | Harness: Object Catalog | 6 WIP categories (STATOR, ROTOR, JOINED, PRE-TEST, TESTED, PACKED) |
| EV5 | Harness: Station Catalog | 8 archetypes via production VF.stationBody() |
| EV6 | Harness: AP04 JOIN | Two-input visual with ROTOR + STATOR |

---

## 11. Deferred to P05/Later

- Robot artwork, realistic machine models
- Advanced gradients/textures
- Perfect icon pack
- Mobile/tablet responsive layout
- Motion/animation

---

## 12. Scope

```
Backend modified:    NO
Runtime modified:    NO
API modified:        NO
Motion implemented:  NO
I09-P03 started:     NO
I09-P04 started:     NO
I09-P05 started:     NO
I07/I08/M6-S05:      NOT STARTED
```

---

> **M6-S04B-I09-P02-C03R-C02-C01 is READY FOR SA REVIEW at `67ade9c`.**
> 
> URL: `http://localhost:8091/assy-demo?_=newcolor`
> 
> **STOP.**
