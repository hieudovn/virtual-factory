# VF-ARCH-06 · Evidence 06 — Decision F: UI / product mapping (Continuous)

## 1. Decision statement

**SH WTP maps onto the ARCH-04 Continuous experience; no frontend
implementation or final labels are required here. The legacy WTP dashboard /
nav link are NOT the target UI.**

## 2. Mapping (ARCH-04 Continuous pattern)

| ARCH-04 surface | SH WTP mapping |
|---|---|
| Platform Shell + context strip | SH-WTP Workspace → process-area Scope → equipment/instrument Object path |
| Process View | process-flow / P&ID-style graph (generic continuous capability already exists in `editor.js`) |
| Monitoring (scope-centric, 0..N views) | process overview, trend/analysis, threshold alarms, balance/quality summary |
| Context Inspector (object-centric) | equipment/instrument → Overview/State/Signals/Live Trend/Events-Alarms + Process/Control/Balance/Quality/Parameters domain tabs |
| Alarms/events/live series | ARCH-03 projections (Live Series ≠ Historian) |
| Capability/readiness presentation | capability state drives visibility honestly; no workspace-name hard-coding |
| Analysis entry points | analytics entry points (compressor-analytics precedent) — no final labels |

## 3. What is NOT the target

- `simulators/wtp/static/dashboard.html` — legacy standalone dashboard, not the
  target UI.
- The generic shell's `#nav-wtp` link to `localhost:8100` — legacy nav wiring
  to the standalone simulator, superseded by the ARCH-04 Continuous experience.

## 4. No frontend work in this gate

No component code, no CSS, no framework migration, no final labels.

**Decision F is explicit.**
