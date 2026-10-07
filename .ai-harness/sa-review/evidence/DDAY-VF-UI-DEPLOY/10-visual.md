# DDAY-VF-UI-DEPLOY — browser proof

Public host: `http://157.10.52.54`

## FactoriX Sim whole-factory

URL: `/factorix-sim/overview`

- Title / top bar: **FactoriX Sim / FACTORIX SIM** (no VIRTUAL FACTORY)
- Plant: Bottled Water Factory / `BW-DEMO-01`
- Run state RUNNING, simulation time advancing without browser clock
- Five accepted areas: BW-WT, BW-BP, BW-FP, BW-WH, BW-UT
- Filling & Packaging showed WARNING during the Capper scenario

Screenshot: `browser/factorix_sim_overview_fb34d36.webp`

The C01-frozen overview drilldown `href` stays `/bottled-water-demo`. That alias
serves the same FactoriX Sim factory. Direct `/factorix-sim` remains the
preferred public entry.

## Filling & Packaging 8-station line

URL: `/factorix-sim`

Stations: Blower, Rinser, Filler, Capper (`BW-FP-CAP01`), Inspection, Labeler, Case Packer, Palletizer.

LIVE chip, bottles on the conveyor, counts advancing, START/PAUSE/RESUME/STOP present
(accepted D-Day controls). PAUSE then RESUME was exercised; RESET was not used
as the D-Day path.

Screenshot: `browser/factorix_sim_line_fb34d36.webp`

## Capper abnormal scenario

Scenario `BW-CAP-DEG-01` on `BW-FP-CAP01`. Browser showed recover / fault marks
and line events (scenario phase, alarm, downtime). Header: Capper recover,
compressor fault during the same run.

Screenshot: `browser/factorix_sim_capper_fault_fb34d36.webp`

## PlantOS still distinct and live

- `/` → FactoriX IIoT login (Vite SPA). Not FactoriX Sim.
- `/health` → `{"status":"healthy","version":"0.1.0"}`
- Edge healthy; MQTT family still consumed.

Screenshots: `browser/plantos_center_login_fb34d36.webp`, `browser/plantos_health_fb34d36.webp`

## Boundary

No OEE / availability / performance / quality KPI fields in FactoriX Sim
`/factorix-sim/factory` payloads.
