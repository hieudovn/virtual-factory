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
- ⬜ OPC UA gateway (future scope).
- ⬜ Sparkplug B / production-grade MQTT (future scope).

## Phase 3: Model Library Expansion

🔄 In progress — model registry and new types being added.

- ✅ Model registry loads types from YAML (`python_class` field).
- ✅ `runtime_factory.py` uses `ModelRegistry` — no hard-coded type dicts.
- 🔜 Add reusable models for additional equipment types (pipe, heat exchanger).
- 🔜 Add common sensor and actuator behaviors (done — delay, drift, stuck).
- 🔜 Add degradation and fault models.
- 🔜 Add richer balance checks and validation reports.

## Phase 4: Configuration Authoring

- Add schema validation for plant configuration.
- Add examples and templates.
- Add low-code/no-code configuration workflows.
- Add guardrails that prevent output-policy violations.

## Phase 5: AI-Assisted Plant Generation

- Generate initial plant configurations from natural language, P&ID-like descriptions, or tabular equipment lists.
- Validate generated models against schemas and graph rules.
- Require human review before running generated configurations.

## Phase 6: Digital Twin Direction

- Support calibration against real plant data.
- Support scenario replay and what-if analysis.
- Support benchmarking between simulated and observed telemetry.
