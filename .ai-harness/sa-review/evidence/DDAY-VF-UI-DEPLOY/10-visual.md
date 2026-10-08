# DDAY-VF-UI-DEPLOY — browser proof (evidence refresh)

Public host: `http://157.10.52.54`
Captured: 2026-10-08 against deployed executable `2a507606bd63fbc7a27ef543cbaaf54469cc631b`.

## FactoriX Sim whole-factory

URL: `/factorix-sim/overview`

- Title / top bar: **FactoriX Sim / FACTORIX SIM** (no VIRTUAL FACTORY)
- Plant: Bottled Water Factory / `BW-DEMO-01`
- Run state RUNNING, simulation time advancing (~102065 s) without a browser clock
- Five accepted areas: BW-WT, BW-BP, BW-FP, BW-WH, BW-UT
- Filling & Packaging showed RECOVERY during the Capper scenario
- Primary controls: **START / PAUSE / STOP** only. Resume and Reset stay under collapsed **Advanced**.

Screenshot: `browser/factorix_sim_overview_primary_2a50760.webp`
Advanced expanded: `browser/factorix_sim_overview_advanced_2a50760.webp`

The C01-frozen overview drilldown `href` stays `/bottled-water-demo`. That alias
serves the same FactoriX Sim factory. Direct `/factorix-sim` remains the
preferred public entry.

## Filling & Packaging 8-station line

URL: `/factorix-sim`

Stations: Blower, Rinser, Filler, Capper (`BW-FP-CAP01`), Inspection, Labeler, Case Packer, Palletizer.

LIVE chip, bottles on the conveyor, counts advancing. Primary Line control
buttons are **START / PAUSE / STOP**. Resume and Reset are not on the primary
row; they appear only after expanding **Advanced**. RESET is danger-styled and
opens `window.confirm` (`RESET returns the factory to t=0 and cannot be undone.`).
The dialog was cancelled; the factory was not reset. Classify remains on the
station popup. Advance is not on the operator skin.

Screenshots:
- primary collapsed: `browser/factorix_sim_line_primary_2a50760.webp`
- Advanced expanded: `browser/factorix_sim_line_advanced_2a50760.webp`
- RESET confirm (cancelled): `browser/factorix_sim_reset_confirm_2a50760.webp`

## Capper abnormal scenario

Scenario `BW-CAP-DEG-01` on `BW-FP-CAP01`. Header showed Capper recover /
compressor recover. Station popup for Capper remains classify-on-selection.

Screenshot: `browser/factorix_sim_capper_2a50760.webp`

## PlantOS still distinct and live

- `/` → FactoriX IIoT login (Vite SPA). Not FactoriX Sim.
- `/health` → `{"status":"healthy","version":"0.1.0"}`
- Edge healthy; MQTT family still consumed.

Screenshots: `browser/plantos_center_login_2a50760.webp`, `browser/plantos_health_2a50760.webp`

## Boundary

No OEE / availability / performance / quality KPI fields in FactoriX Sim
`/factorix-sim/factory` payloads.
