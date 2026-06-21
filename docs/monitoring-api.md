# Monitoring API

Virtual Factory includes a minimal FastAPI monitoring API for MVP-01. It exposes publishable industrial telemetry, alarm/event signals, runtime status, and a WebSocket telemetry stream.

The API does not expose internal truth by default. Normal responses are built from publishable `SignalValue` telemetry only.

## Run Locally

Install API support:

```bash
pip install -e .[dev,api]
```

Start the API:

```bash
virtual-factory serve --port 8000
```

Open:

- `http://localhost:8000/`
- `http://localhost:8000/docs`
- `http://localhost:8000/health`
- `http://localhost:8000/status`
- `http://localhost:8000/telemetry/latest`
- `http://localhost:8000/alarms`

## Run With Docker

```bash
docker compose up --build
```

The API service is exposed at:

```text
http://localhost:8000
```

The Docker API service owns the single continuous simulation runtime. Dashboard, HTTP API, WebSocket, and MQTT publishing all read from the same `RuntimeService` instance.

## Dashboard

Open the browser dashboard:

```text
http://localhost:8000/
```

The dashboard is a professional SCADA-style UI with:

- **Left sidebar**: Navigation for Process Flow, Telemetry, Alarms, Trends,
  Data Table, PID & Control, Fault Injection, OPC/IIoT Export, and Asset Builder.
- **Top bar**: Plant name, scenario badge, simulation time, runtime status,
  connection state, and simulation controls (Start/Stop/Step/10×).
- **Process flow diagram**: Interactive SVG with equipment icons (tank, pump,
  valve, pipe, sensor, controller, actuator), live telemetry overlay, alarm
  indicator dots, and click-to-inspect property panel.
- **Bottom panel**: Tabbed views — Telemetry (KPI cards), Alarms (event grid),
  Trends (line chart), Data Table, and Settings (PID, Faults, OPC).
- **Runtime configuration**: Adjust PID parameters (Kp, Ki, Kd, setpoint) via
  sliders and number inputs; inject faults (valve stuck, pump degradation,
  sensor bias) via toggles and spinners.
- **OPC UA export settings**: Signal selector checkboxes and connection test.
- **Asset Builder**: Drag-and-drop palette with equipment icons for future
  custom plant configuration.

The dashboard first loads `/status`, `/telemetry/latest`, and `/alarms`, then
uses `/ws/telemetry` for live updates. If the WebSocket is unavailable, it
polls `/telemetry/latest` every second.

Internal truth is filtered out and is not displayed by the dashboard.
There is no authentication yet.

## Endpoints

### GET /health

Returns:

```json
{"status": "ok"}
```

### GET /status

Returns service status without internal truth:

```json
{
  "status": "running",
  "running": true,
  "plant_id": "continuous_mvp_01",
  "plant_name": "Continuous Water Transfer and Tank Level Control",
  "scenario_id": "valve_stuck",
  "initialized": true,
  "time_s": 10.0,
  "dt_s": 1.0,
  "telemetry_frames": 10,
  "mqtt_enabled": true,
  "mqtt_connected": true
}
```

### GET /telemetry/latest

Returns the latest publishable telemetry frame. If the service has not stepped yet, it runs one step first.

```json
[
  {
    "name": "LT102_LEVEL",
    "value": 2.01,
    "unit": "m",
    "category": "industrial_signal",
    "quality": "GOOD",
    "timestamp_s": 0.0,
    "source": "LT102"
  }
]
```

### GET /telemetry/history?limit=100

Returns flattened records from recent in-memory telemetry frames. No database or long-term historian is used.

### GET /alarms

Returns latest publishable alarm/event signals:

```json
[
  {
    "name": "T102_LOW_LEVEL_ALARM",
    "value": false,
    "unit": "bool",
    "category": "industrial_event",
    "quality": "GOOD",
    "timestamp_s": 0.0,
    "source": "T102_LOW_LEVEL"
  }
]
```

### POST /step

Runs one simulation step and returns the latest publishable telemetry.

### POST /run-steps?n=10

Runs `n` simulation steps and returns the latest publishable telemetry.

### POST /start

Starts the background simulation loop. If MQTT is configured for the API runtime, the loop publishes each latest publishable telemetry frame.

### POST /stop

Stops the background simulation loop.

### PATCH /api/pid/{controller_id}

Updates PID controller parameters at runtime. Accepts JSON body with any of:
`kp`, `ki`, `kd`, `setpoint`.

```json
{"kp": 1.5, "ki": 0.08, "setpoint": 3.0}
```

Returns updated parameters.

### POST /api/fault

Injects a fault into the running simulation. Accepts JSON body with `type` and `value`:

```json
{"type": "valve_stuck", "value": 30.0}
```

Set `value` to `null` to clear a fault. Supported fault types:
- `valve_stuck` — freezes valve at given opening percentage
- `pump_degradation` — reduces pump efficiency (percentage)
- `sensor_bias` — adds constant bias to sensor reading

### GET /api/opcua/status

Returns OPC UA gateway status:

```json
{"enabled": true, "endpoint": "opc.tcp://0.0.0.0:4840", "started": true}
```

### GET /api/plant-graph

Returns the plant graph structure for the SVG process flow editor.

### GET /api/model-types

Returns available model types for the asset builder palette.

## WebSocket

Connect to:

```text
ws://localhost:8000/ws/telemetry
```

The server runs one step every second and sends the latest publishable telemetry as JSON.

## Published Data Boundary

API responses are built from telemetry frames and alarm/event `SignalValue` objects:

- `industrial_signal`
- `controller_signal`
- `actuator_feedback`
- `industrial_event`

Internal truth, solver state, and debug-only physical values are not exposed by default. Debug truth endpoints are future scope and should be explicitly gated if added.
