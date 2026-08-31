# I09-P02-C03R — Reference-Locked Visual Implementation — Evidence

> **Date**: 2026-08-12  
> **Baseline**: `2fbdf6e`  
> **Status**: READY FOR SA REVIEW  

## Evidence Screenshots

| # | File | Description |
|---|------|-------------|
| V1 | `V1_frame_a_overview.png` | Frame A overview: 6 sub-line cards (3 hydraulic + 3 thermal), 3×2 grid, process strips with landmarks, sidebar metrics |
| V2 | `V2_frame_b_canvas.png` | Frame B physical canvas: grid, zone boxes, conveyor, 12 stations with badges, WIP tokens on pallets, AP06 popup open |
| V3 | `V3_frame_b_clean.png` | Frame B clean view (no popup): full canvas with right→left flow, raw material RIGHT, finished goods LEFT |
| V4 | `V4_1366_viewport.png` | 1366×768 viewport: responsive layout, sidebar 140px, text ≥11px, popup constrained |
| V5 | `V5_frame_a_clean.png` | Frame A overview clean: card layout, selection highlighting, statistics |

## Visual Proofs

- ✅ Top app bar: VF logo, status strip (LIVE/STEP/TIME/SPEED), controls, right icons
- ✅ Left sidebar (156px): Line Overview metrics, Legend (7 items), utility actions
- ✅ Frame A: bright card-based layout, 3×2 grid, HYDRAULIC/THERMAL groups
- ✅ Frame B: grid background, zone boxes (RAW MATERIAL, HOLD AREA, FINISHED GOODS)
- ✅ Conveyor: dark steel body, roller segments, green product-flow arrows pointing LEFT
- ✅ SSO2 INPUT (RIGHT), OUT (LEFT), RSO2 ROTOR FEED into AP04
- ✅ 12 stations with AP badges, operation names, machine body illustrations
- ✅ AP04 = JOIN (amber accent), AP06 = TEST, AP08 = VISION, AP11 = FINAL
- ✅ WIP tokens: pallet + STATOR ASSY / MTR JOINED / PRE-TEST / TESTED MTR (blue T) / PACKED
- ✅ Floating popup (top-right): station title, tabs (Overview/Quality/History/Genealogy), summary rows
- ✅ Inspector (bottom-right): legacy data integration preserved
- ✅ Event strip (bottom-left): quality events, clickable
- ✅ Frame A ⇄ Frame B navigation: shared shell, top bar context switches
- ✅ Zoom controls in footer
- ✅ RIGHT→LEFT flow obvious (material enters RIGHT, exits LEFT)
- ✅ All station archetypes visibly distinct
- ✅ No persistent right rail
- ✅ 1366 viewport readable

## Manufacturing Semantics Preserved

- RIGHT→LEFT physical flow: raw material RIGHT, finished goods LEFT
- Full 13-station sequence: PRE-ASSY → AP01-AP11 → OUT
- AP04 = JOIN, AP06 = TEST, AP08 = VISION, AP09 = BOXING, AP10 = PACK/LABEL, AP11 = FINAL QC
- WIP states: PRE-ASSY–AP04=STATOR, AP05=JOINED, AP06=PRE-TEST, AP07-AP09=TESTED, AP10-AP11=PACKED
- TESTED MTR = blue "T" marker, NOT green checkmark
- RSO2 = ROTOR branch feed (no fabricated child MTR)

## Scope

```
Backend: NO | Runtime: NO | API: NO | Motion: NO | Popup data: YES (current truth only)
I09-P03/P04/P05: NOT STARTED | I07/I08/M6-S05: NOT STARTED
```

## Test Results

```
1248 passed (excluding pre-existing scenario switch test)
```
