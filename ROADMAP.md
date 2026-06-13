# Roadmap

This roadmap keeps implementation staged so the simulation core remains model-driven from the beginning.

## Phase 0: Documentation and Structure

- Create primary English development documents.
- Create Vietnamese supplementary reference documents.
- Define the MVP process, architecture rules, output policy, graph model, and balance model.
- Avoid implementing the simulation engine during this phase.

## Phase 1: MVP Continuous Process

- Load the plant from YAML/JSON.
- Represent the MVP process as a graph:
  `T101 -> P101 -> V101 -> T102`.
- Implement reusable equipment models for source tank, pump, control valve, destination tank, level transmitter, PID controller, and valve actuator.
- Simulate closed-loop level control using measured signals.
- Publish industrial-mode outputs with no internal truth leakage to the IIoT Platform.
- Store ground truth internally for debug and validation.

## Phase 2: Industrial Telemetry Interfaces

- Add protocol gateway abstractions.
- Add at least one real-time telemetry output path.
- Add signal metadata, quality, engineering units, and timestamps.
- Add output profiles for industrial mode, debug mode, and benchmark mode.

## Phase 3: Model Library Expansion

- Add reusable models for additional equipment types.
- Add common sensor and actuator behaviors.
- Add degradation and fault models.
- Add richer balance checks and validation reports.

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
