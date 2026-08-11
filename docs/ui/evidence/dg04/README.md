# DG04-02-C01 — Frame B Sub-line Detail Interactive Review Harness

## How to Open

```bash
cd docs/ui/evidence/dg04
python -m http.server 8091
# Open http://localhost:8091/dg04_review_harness.html
```

## Files

```
dg04_review_harness.html        — Interactive Frame B prototype
fixtures/                        — Deterministic state data
  B1_normal.json                 — 6 WIPs, normal OPERATING
  B2_ap06_hold.json              — AP06 RETEST_PENDING, FAIL #1
  B3_ap04_join.json              — AP04 JOIN focus
  B4_ap08_ng.json                — AP08 REINSPECT_PENDING, NG #1
  B5_ap11_released.json          — AP11 RELEASED, MTR-0010 → OUT
DG04_B1_1920_normal.png          — Supplemental screenshot
DG04_B2_1920_ap06_hold.png       — Supplemental screenshot
DG04_B3_1920_ap04_join.png       — Supplemental screenshot
DG04_B4_1366_ap08_ng.png        — Supplemental screenshot (1366×768)
README.md                        — This file
```

## Review Harness Controls (design review only, not production)

| Control | Purpose |
|---------|---------|
| State selector | Switch between B1-B5 fixtures |
| Viewport buttons | Toggle 1920×1080 / 1366×768 |
| Layer toggles | Show/hide Ops / Quality / Context layers |
| Inspector toggle | Collapse/expand right panel |
| Zoom −/+/100%/Fit | SVG viewBox control (pointer-anchored wheel zoom, Fit to content) |
| Station click | Select station → Inspector populates |
| Wheel over canvas | Zoom around cursor (50%–200%) |
| Left-drag on canvas | Pan physical canvas |

**Production Frame B controls** (shown for layout, NOT functional in harness):
Back, Reset, Step, Auto, Pause — these are design representations of proposed production UI. They do not interact with a live simulation.

## Typography (DG04-01 Compliant)

| Element | Size | Weight |
|---------|------|--------|
| Sub-line title | 22px | 600 |
| Station ID | 15px | 600 |
| WIP ID | 14px | 600 |
| Quality badge | 12px | 600 |
| Carrier ID | 11px | 400 |
| Landmark label (JOIN/TEST/VISION/FINAL) | 11px | 600 |
| SSO2/RSO2/OUT labels | 11px | 600 |
| Event strip text | 11px | 400 |
| Inspector body | 12px | 400 |

**Rule**: No operational text below 11px. DG04-01 freeze respected.

## Zoom / Pan

- **100%**: Nominal design scale — full 1920×700 viewBox at panX=0, panY=0.
- **Fit**: Computes viewBox to enclose the physical content (SSO2 INPUT→OUT, RSO2→conveyor) within the current canvas element dimensions. Distinct from 100% — zoom level and panY vary with viewport size.
- **Wheel zoom**: Pointer-anchored — uses `getScreenCTM().inverse()` to convert client coordinates to SVG user coordinates, correctly handling `preserveAspectRatio="xMidYMid meet"` letterboxing. The SVG coordinate under the cursor remains stationary after zoom. Clamped 50%–200%. Keeps the inspected point stable.
- **Left-drag**: Drag on empty canvas area → pan. Selected station preserves selection state across zoom/pan operations.

## 1920×1080 Review

- 12 stations fit with 150px spacing, 88×90 node boxes
- Conveyor bar at y=340, SSO2/RSO2 inputs, OUT arrow
- Inspector 280px right panel
- All text meets 11px minimum

## 1366×768 Review

- SVG viewBox scales via preserveAspectRatio
- Station IDs remain readable
- Inspector collapses to narrow strip
- Canvas supports internal pan if zoomed

## Fixture Integrity

All fixtures follow `AssyDemoSnapshot.to_dict()` contract. No invented API fields. 3 DATA GAPs documented in Inspector placeholders.

## Frame A Refinement Recommendations

1. Increase Sub-line ID to 16px, status badge to 13px
2. Move WIP/OUT/DW counters to hover tooltip
3. Add variant group divider between hydraulic and thermal sections
