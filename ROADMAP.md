# Roadmap

This roadmap keeps implementation staged so the simulation core remains model-driven from the beginning.

## Phase 0: Documentation and Structure

- Create primary English development documents.
- Create Vietnamese supplementary reference documents.
- Define the MVP process, architecture rules, output policy, graph model, and balance model.
- Avoid implementing the simulation engine during this phase.

## Phase 1: MVP Continuous Process

✅ Complete — core simulation loop runs with graph-based configuration.

- ✅ Load the plant from YAML/JSON (Pydantic v2 schema with cross-reference validation).
- ✅ Represent the MVP process as a graph (`PlantGraph` with nodes and typed edges).
- ✅ Implement reusable equipment models for source tank, pump, control valve,
  destination tank, level transmitter, PID controller, and valve actuator.
- ✅ Simulate closed-loop level control using measured signals only.
- ✅ Process dynamics with quadratic pump curve, valve Cv-based flow,
  pipe resistance, and source-tank depletion.
- ✅ Publish industrial-mode outputs with no internal truth leakage.
- ✅ Store ground truth internally for debug and validation.

## Phase 2: Industrial Telemetry Interfaces

✅ Mostly complete — protocol gateway, API, and export paths are available.

- ✅ Protocol gateway abstraction (MQTT JSON publisher with reconnect logic).
- ✅ Real-time telemetry output path (MQTT + WebSocket via FastAPI).
- ✅ Signal metadata, quality, engineering units, and timestamps (`SignalValue`).
- ✅ Output profiles for industrial mode, debug mode, and benchmark mode.
- ✅ CSV and JSONL telemetry export.
- ✅ FastAPI monitoring API with dashboard UI, REST endpoints, and WebSocket stream.
- ✅ Docker / docker-compose deployment with Mosquitto MQTT broker.
- ✅ Alarm manager (high, low, bad-quality, equals, not-equals).
- ✅ Scenario manager (normal operation, valve stuck, pump stop, pump degradation,
  demand change, sensor bias).
- ✅ OPC UA gateway (TCP server with namespace, variables, background thread).
- ✅ Sparkplug B MQTT gateway (JSON payload, NBIRTH/NDEATH/NDATA lifecycle).

## Phase 3: Model Library Expansion

✅ Complete — all core equipment types implemented.

- ✅ Model registry loads types from YAML (`python_class` field).
- ✅ `runtime_factory.py` uses `ModelRegistry` — no hard-coded type dicts.
- ✅ Pipe equipment with Darcy-Weisbach pressure drop (Swamee-Jain friction).
- ✅ Common sensor and actuator behaviors (delay buffer, drift accumulator, stuck fault).
- ✅ Heat exchanger model (shell-and-tube counter-flow, LMTD method).
- ✅ Fan / blower equipment (quadratic pressure-rise curve).
- ✅ Degradation models (pump wear, valve Cv loss, pipe fouling via fault.* keys).
- ✅ Gas compressor (polytropic compression, power estimation).
- ✅ Gas-liquid separator (level dynamics, overhead/bottoms split).
- ✅ Energy balance evaluator (sensible heat, HEX transfer, outlet demand).
- ✅ Combined mass + energy balance summary in step diagnostics.

## Phase 4: Configuration Authoring

🔄 In progress — validation, templates, guardrails.

- ✅ Schema validation for plant configuration (Pydantic v2).
- ✅ `validate` CLI command with structured JSON report.
- ✅ Config templates (single_tank_transfer, heat_exchanger_loop).
- 🔜 Low-code/no-code configuration workflows.
- 🔜 Guardrails that prevent output-policy violations.

## Phase 5: AI-Assisted Plant Generation

- Generate initial plant configurations from natural language, P&ID-like descriptions, or tabular equipment lists.
- Validate generated models against schemas and graph rules.
- Require human review before running generated configurations.

## Phase 6: Digital Twin Direction

- Support calibration against real plant data.
- Support scenario replay and what-if analysis.
- Support benchmarking between simulated and observed telemetry.

## Phase 7: Professional Monitoring & Configuration UI

✅ Complete — SCADA-quality dashboard with runtime control and settings.

- ✅ Professional dashboard layout with sidebar, top bar, multi-panel design.
- ✅ SVG icon library for all equipment types (tank, pump, valve, pipe, sensor,
  controller, actuator, fan, heat exchanger, compressor, separator).
- ✅ Interactive display widgets (tank level gauge, flow bar, pressure dial,
  line chart, data table).
- ✅ Runtime configuration panel (PID tuning, setpoint adjustment, fault
  injection, equipment parameter modification).
- ✅ OPC UA / IIoT export settings UI (signal selector, endpoint config,
  namespace manager, connection test).
- ✅ Drag-and-drop asset builder (canvas, palette, port connections, property
  editor, YAML export in future).
- ✅ Dark/light theme support (sidebar toggle button).
- ✅ Mobile-responsive layout with hamburger sidebar toggle.
- ✅ Historical trending (live Canvas line chart in Trends tab).
- ✅ Data table (real-time telemetry log in Data Table tab).

