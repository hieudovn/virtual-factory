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

The API service runs its own simulation instance. The existing `virtual-factory` service continues publishing MQTT telemetry.

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
  "plant_id": "continuous_mvp_01",
  "plant_name": "Continuous Water Transfer and Tank Level Control",
  "scenario_id": "valve_stuck",
  "initialized": true,
  "time_s": 10.0,
  "dt_s": 1.0,
  "telemetry_frames": 10
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
