# Virtual Factory

Virtual Factory is a physics-informed virtual plant and control lab for generating realistic industrial telemetry, testing IIoT platforms, and evolving toward digital twin simulation.

The project starts with a deliberately small continuous-process MVP, then expands through model-driven plant configuration, control logic, protocol gateways, degraded equipment behavior, and AI-assisted plant generation.

## Development Document Policy

English documents are the primary development documents. Vietnamese documents are supplementary reference documents for business and technical alignment.

When the two versions differ, the English document is authoritative for implementation.

## First MVP

The first MVP simulates a simple tank transfer process:

```text
T101 Source Tank -> P101 Pump -> V101 Control Valve -> T102 Destination Tank
```

Closed-loop level control:

```text
T102.level_true
  -> LT102 Level Transmitter
  -> LT102_LEVEL measured signal
  -> LIC102 PID Controller
  -> LIC102_OUT
  -> VA101 Valve Actuator
  -> V101.opening_actual
  -> process flow
  -> T102.level_true
```

## Core Architecture Rules

1. The simulation engine must not hard-code the plant.
2. The plant must be loaded from YAML/JSON configuration.
3. Equipment interacts internally through physical variables and ports.
4. Sensors convert physical truth into measured industrial signals.
5. Controllers must read measured signals, not true physical states.
6. Protocol gateways must publish measurable industrial signals only.
7. Internal truth, solver variables, degradation truth, and true mass or energy balance values must not be published to the IIoT Platform in industrial mode.
8. Ground truth can be stored internally for debug, validation, and benchmarking.
9. Plant configuration must be model-driven and graph-based.
10. Low-code/no-code configuration and AI-assisted plant generation are planned for later phases.

## Repository Map

- `ARCHITECTURE.md`: system boundaries, major components, and runtime flow.
- `ROADMAP.md`: staged development plan.
- `docs/design-principles.md`: project design principles and modeling rules.
- `docs/data-model.md`: configuration and runtime data concepts.
- `docs/output-policy.md`: rules for industrial telemetry versus internal ground truth.
- `docs/mvp-01-continuous-process.md`: first MVP scope.
- `docs/balance-model.md`: mass, volume, and energy balance policy.
- `docs/graph-model.md`: graph-based plant model.

## Run The MVP Demo

```bash
pip install -e .[dev]
virtual-factory run --steps 30
```

Optional local telemetry export:

```bash
virtual-factory run --steps 60 --csv-output out/telemetry.csv --jsonl-output out/telemetry.jsonl
```

Exported telemetry includes publishable industrial signals only. Internal truth is not exported unless a future explicit benchmark/debug mode is added.

## Publish To MQTT

Install the optional MQTT dependency:

```bash
pip install -e .[dev,mqtt]
```

Start a broker separately, such as EMQX or Mosquitto, then run:

```bash
virtual-factory run --steps 60 --mqtt-host localhost --mqtt-port 1883
```

MQTT publishes publishable industrial telemetry only. Ground truth is not published. The current topic format is simple JSON over `{topic_prefix}/{signal_name}` and will evolve later.

## Run With Docker

```bash
docker compose up --build
```

This starts a local Mosquitto broker exposed at `localhost:1883`, runs the MVP simulation publisher, and starts the monitoring API at `http://localhost:8001`. The API still binds to port `8000` inside the container. MQTT topics use this prefix:

```text
virtual-factory/demo/continuous_mvp_01/{signal_name}
```

Use MQTT Explorer to subscribe to:

```text
virtual-factory/demo/continuous_mvp_01/#
```

CSV and JSONL outputs are written to `./out`.

Run an alternate scenario:

```bash
docker compose run --rm virtual-factory virtual-factory run --steps 60 --scenario configs/scenarios/demand_change.yaml --show-alarms
```

## Run Monitoring API

Install API support:

```bash
pip install -e .[dev,api]
```

Run locally:

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

With Docker:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8001/
http://localhost:8001/docs
```

The root URL serves a minimal MVP monitoring dashboard. The dashboard uses the JSON API and WebSocket telemetry stream, displays publishable telemetry only, and does not show internal truth. There is no authentication yet.

## Run With Scenario

```bash
virtual-factory run --steps 60 --scenario configs/scenarios/demand_change.yaml
virtual-factory run --steps 60 --scenario configs/scenarios/valve_stuck.yaml
virtual-factory run --steps 60 --scenario configs/scenarios/pump_degradation.yaml
```

Scenarios affect internal plant state or configuration parameters through explicit actions. Output remains measured publishable telemetry only.

## Alarm/Event MVP

Alarms are generated from measured industrial signals, controller signals, and actuator feedback. Alarm outputs are `industrial_event` `SignalValue` objects, so they use the same publishable telemetry path as other industrial signals.

Ground truth is not used directly for industrial alarm generation.

```bash
virtual-factory run --steps 60 --scenario configs/scenarios/valve_stuck.yaml --show-alarms
```

## Current Development Status

Current status:

- Phase 0 documentation foundation initialized.
- Python project skeleton, configuration schema, and graph loader are in place.
- MVP-01 runtime, minimal process dynamics, instrumentation metadata, and telemetry frame collection are available.
- Next step: expand protocol gateways, validation depth, and process model fidelity.
