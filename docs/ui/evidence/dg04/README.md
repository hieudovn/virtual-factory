# DG04-02 — Frame B Sub-line Detail Interactive Review Harness

## How to Open

The harness uses static JSON fixtures and must be served via a local HTTP server
(browser `fetch` of local files requires HTTP):

```bash
cd docs/ui/evidence/dg04
python -m http.server 8090
# Open http://localhost:8090/dg04_review_harness.html
```

## Files

```
dg04_review_harness.html   — Interactive Frame B prototype
fixtures/
  B1_normal.json           — Normal populated sub-line (6 WIPs, 3 genealogy)
  B2_ap06_hold.json        — AP06 HOLD (RETEST_PENDING, FAIL #1)
  B3_ap04_join.json        — AP04 JOIN focus (MTR-0008 created)
  B4_ap08_ng.json          — AP08 NG (REINSPECT_PENDING, NG #1)
  B5_ap11_released.json    — AP11 RELEASED (MTR-0010 → OUT)
README.md                  — This file
```

## Fixture-to-State Mapping

| Fixture | Sub-line | Key State |
|---------|----------|-----------|
| B1_normal | ASSY-SL01 | 6 WIPs occupied, PASS quality, normal OPERATING |
| B2_ap06_hold | ASSY-SL03 | AP06 RETEST_PENDING, FAIL #1, QUALITY HOLD |
| B3_ap04_join | ASSY-SL01 | AP04 JOIN with SSO2+RSO2→MTR genealogy |
| B4_ap08_ng | ASSY-SL02 | AP08 REINSPECT_PENDING, NG #1 |
| B5_ap11_released | ASSY-SL01 | AP11 RELEASED, MTR-0010 → OUT |

All fixtures follow the actual `AssyDemoSnapshot.to_dict()` contract.
No invented API fields.

## Review Controls

| Control | Purpose |
|---------|---------|
| State selector | Switch between B1-B5 fixtures |
| Viewport buttons | Toggle 1920×1080 / 1366×768 |
| Layer toggles | Show/hide Ops / Quality / Context layers |
| Inspector toggle | Collapse/expand right Inspector panel |
| Zoom buttons | − / 100% / + / Fit |
| Station click | Select station, Inspector populates |

## Typography Decisions

At 1920×1080:
- Station IDs: 14px bold
- WIP IDs: 12px bold inside token
- Carrier IDs: 10px muted
- Quality badges: 9px compact
- Inspector: 12px body, 13px headings

At 1366×768: SVG viewBox scaling handles density; primary IDs remain readable.

## Interactions

- **Physical canvas**: SVG-first, 12 station nodes, conveyor bar, SSO2/RSO2 input
- **Layers**: Ops (station/WIP/carrier), Quality (PASS/FAIL/HOLD badges), Context (event strip)
- **Selection**: Click station → Inspector populates from fixture data
- **Zoom**: SVG viewBox manipulation, canvas-only
- **Inspector**: WIP details, genealogy tree, quality events, DATA GAP markers

## Known DATA GAPs

| Gap | Marked |
|-----|--------|
| No per-station elapsed time | Inspector: "DATA GAP" placeholder |
| No RSO2 WIP identity at AP04 position | Genealogy records used instead |
| Measurements/Checklist detail | Inspector: "DATA GAP" placeholder |
| Quality events are flat list | Client-side filtering by station/WIP |

## 1920×1080 Review Notes

- 12 stations fit horizontally with 140px spacing
- Conveyor bar at y=340, stations at y=250
- Inspector panel 280px right side
- Review controls bar at top, production controls at bottom
- Physical canvas dominates (~65% of workspace)

## 1366×768 Review Notes

- SVG viewBox scales via preserveAspectRatio
- Station IDs remain readable at 12-14px scaled
- Inspector collapses to narrow strip (toggle to expand)
- Canvas may require internal scroll/pan at extreme zoom

## Frame A Refinement Recommendations

1. Increase Sub-line ID from 14px to 16px for better scanability
2. Increase status badge from 11px to 13px
3. Move WIP/OUT/DW counters to hover tooltip on Frame A lanes
4. Keep station topology dots at current size
5. Add a subtle variant group header divider between hydraulic and thermal sections

## Deferred to I05/I06/I07

- I05: Production Frame B implementation with live API
- I06: Production Inspector with full WIP/Station/Genealogy/Quality drill-down
- I07: Index shift, join, line-in/out animations
- M6-S05: MES integration (NOT AUTHORIZED)
