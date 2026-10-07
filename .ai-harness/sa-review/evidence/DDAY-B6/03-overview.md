# DDAY-B6 — 03. Lightweight Whole Factory Overview

Page: `GET /bottled-water-demo/overview`
State source: `GET /bottled-water-demo/factory` (same autonomous factory)

## Five accepted areas

| Area | Name | Key raw values | Abnormal source |
|---|---|---|---|
| `BW-WT` | Water Treatment | tank level, treated flow, tank volume | operating_state |
| `BW-BP` | Bottle Preparation | operating_state, preform count | operating_state |
| `BW-FP` | Filling & Packaging | total / good / reject | public Capper phase |
| `BW-UT` | Utilities | air pressure, plant power | public Compressor phase |
| `BW-WH` | Warehouse / Dispatch | inventory, receipts, dispatch | operating_state |

## Relationships

- process: `BW-WT` → `BW-FP` treated water → filler
- process: `BW-BP` → `BW-FP` prepared bottles → blower/infeed
- utility: `BW-UT` → `BW-FP` compressed air → line
- process: `BW-FP` → `BW-WH` good bottles → finished goods

## Drill-down

`BW-FP` card links to `/bottled-water-demo`, the existing detailed Filling
& Packaging UI. The F&P page has a `Whole factory` link back.

## Visuals

- [`10-visual-overview-stopped.png`](10-visual-overview-stopped.png)
- [`10-visual-overview-abnormal.png`](10-visual-overview-abnormal.png) — BW-FP `WARNING`
- [`10-visual-fp-drilldown.png`](10-visual-fp-drilldown.png) — existing F&P canvas

Chrome headless still doubles some glyphs (pre-existing capture artifact).
The five area ids, relationship chips, raw values, WARNING mark, and
drill-down target are all present.

## Non-scope held

The overview is an observer plus the existing five operator controls.
It does not invent KPI, a second hierarchy, or extra HMI workflows.
