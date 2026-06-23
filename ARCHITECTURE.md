# Architecture

Virtual Factory is an **analytics-first industrial data generation platform**. Its primary mission is to generate realistic industrial telemetry, operational events, maintenance history, fault progression, and ground-truth labels for development, validation, benchmarking, and demonstration of Industrial Analytics, Asset Health Monitoring (AHM), Predictive Maintenance (PdM), Anomaly Detection, and Digital Twin solutions.

The runtime engine executes a plant model loaded from configuration instead of embedding plant-specific behavior in code.

## Goals

- Generate realistic industrial telemetry for analytics development and IIoT testing.
- Provide ground-truth labels (operating state, fault type, severity, health index, RUL) for model validation.
- Support both industrial telemetry mode and benchmark mode with hidden labels.
- Export structured analytics datasets (Parquet/JSONL) for model training.
- Represent physical process behavior with enough fidelity for believable dynamics.
- Preserve internal ground truth for validation without exposing it as industrial telemetry.
- Support asset hierarchy modeling for complex equipment (compressor trains, pump systems).
- Support future digital twin, low-code configuration, and AI-assisted plant generation workflows.

## Core Architecture Rules

1. The simulation engine must not hard-code the plant.
2. Plant configuration must be loaded from YAML/JSON.
3. Internal equipment interaction uses physical variables and ports.
4. Sensors convert physical truth into measured industrial signals.
5. Controllers read measured signals only, not true physical states.
6. Industrial protocol output publishes measurable signals only.
7. Internal ground truth is hidden from the IIoT Platform in industrial mode.
8. Ground truth may be stored internally for debug, validation, and benchmarking.
9. The plant model is graph-based.
10. Low-code/no-code configuration and AI-assisted generation are future roadmap items.
11. Benchmark mode exports hidden ground truth for analytics validation.
12. Faults evolve over time with configurable growth rates and severity curves.
13. Operating states are explicit and exported as benchmark truth.

## Major Components

### Plant Configuration

The plant is defined in YAML/JSON. Configuration describes equipment, ports, connections, physical parameters, sensors, actuators, controllers, tags, and output policies.

The simulation engine must treat the configuration as the plant model. It must not hard-code the MVP or any future process.

### Graph Model

Equipment and control components are represented as nodes. Physical, signal, and command relationships are represented as edges.

The graph model allows the same engine to run different plants by loading different configurations.

### Equipment Models

Equipment models own their internal physical state and expose typed ports. Examples include tanks, pumps, valves, pipes, transmitters, actuators, and controllers.

Equipment interacts through ports and physical variables, not direct knowledge of other equipment internals.

### Sensors

Sensors convert physical truth into measured industrial signals. A sensor may apply range limits, units, calibration, noise, lag, drift, quantization, fault behavior, and status quality.

Controllers and protocol gateways must consume sensor outputs, not true physical states.

### Controllers

Controllers consume measured signals and produce command or output signals. The first MVP uses `LIC102` as a PID controller reading `LT102_LEVEL` and producing `LIC102_OUT`.

Controllers must not read `T102.level_true` directly.

### Actuators

Actuators convert controller outputs into equipment actions. In the first MVP, `VA101` converts `LIC102_OUT` into the physical valve state `V101.opening_actual`.

### Solver

The solver advances physical state over time. It may compute internal truth such as true flow, level, pressure, mass, energy, and degradation state.

Solver internals are not industrial telemetry. They can be stored for debug, validation, and benchmarking.

### Protocol Gateways

Protocol gateways expose industrial signals to external systems such as MQTT, OPC UA, REST, WebSocket, or file export.

In industrial mode, gateways publish measurable industrial signals only. Internal truth and solver variables must remain private and hidden from the IIoT Platform.

## MVP Runtime Flow

```text
configuration
  -> graph loader
  -> model registry
  -> simulation runtime
  -> equipment and solver update
  -> sensors
  -> controllers
  -> actuators
  -> measurable industrial signals
  -> protocol gateways
```

## Boundary Rule

The engine owns execution mechanics. Configuration owns plant structure. Equipment models own reusable behavior. Gateways own external publication.

No part of the engine should assume that the plant contains `T101`, `P101`, `V101`, `T102`, `LT102`, `LIC102`, or `VA101`.

## Analytics Architecture

Virtual Factory's analytics architecture is layered on top of the core simulation:

```text
configuration
  -> graph loader
  -> model registry
  -> simulation runtime
  -> equipment and solver update
  -> sensors (with quality degradation)
  -> controllers
  -> actuators
  -> measurable industrial signals
  -> [telemetry mode] -> protocol gateways
  -> [benchmark mode] -> ground truth collection + protocol gateways
  -> analytics runtime (faults, states, maintenance, benchmark)
  -> benchmark package export (Parquet/JSONL)
```

### Fault Lifecycle Engine (`faults/`)

Models faults that evolve over time with:
- Configurable severity curves (linear, exponential, sigmoid, step, logarithmic)
- Growth rates controlling degradation speed
- Symptom propagation to truth variables (additive, multiplicative, replacement)
- Alarm delays modeling detection lag
- Maintenance actions with recovery profiles (instant, linear, exponential)
- Residual severity after partial repairs

### Operating State Machine (`operating_states/`)

Explicit state tracking per equipment:
- 11 defined states: Stopped, Startup, Ramp-up, Steady Running, Low Load,
  High Load, Recycle Mode, Near Surge, Shutdown, Trip, Maintenance
- Configurable state transitions with condition callbacks
- Entry/exit callbacks for state change side effects
- State history and time-in-state tracking
- State snapshots exported as benchmark truth

### Asset Hierarchy (`equipment/asset_hierarchy.py`)

Tree-structured asset model:
- Parent-child relationships for complex assemblies
- Tag aggregation across sub-components
- Metadata export for analytics
- Full hierarchical path support (e.g. `COMP_TRAIN_01.MOTOR.BEARING_DE`)

### Compressor Train (`equipment/compressor_train.py`)

Flagship analytics benchmark model:
- Phase 1: 52 tags covering compressor core, motor, bearings, lube oil,
  cooling, seal gas, anti-surge, and health
- Polytropic compression with surge margin computation
- Motor electrical and thermal modeling
- Bearing temperature and vibration modeling
- Sub-system integration (lube oil, cooling, seal gas)

### Benchmark & Ground Truth (`benchmark/`)

Hidden labels for analytics validation:
- Operating state per equipment per timestep
- Active fault types, severities, and start times
- Asset health index (1.0 = healthy, 0.0 = failed)
- Simulated remaining useful life (RUL)
- Failure probability and expected diagnosis
- Benchmark mode: labels exported alongside telemetry
- Industrial mode: labels stored but never published

### Maintenance & Events (`maintenance/`)

Structured event generation:
- Alarm events (with severity, acknowledgment)
- Operator logs and observations
- Inspection events (with findings, next inspection)
- Work orders (with priority, status, assignment)
- Failure events (with failure mode, fault ID)
- Repair actions (with parts replaced, duration)
- Downtime events (planned/unplanned, reason)
- Spare part replacements (with part numbers)

### Sensor Quality Model (`sensor_quality/`)

Enhanced sensor degradation to challenge analytics pipelines:
- Noise increase (multiplied standard deviation)
- Bias shift (constant additive offset)
- Drift (accumulating per-second increment)
- Flatline (stuck at fixed value)
- Intermittent dropout (probabilistic data loss)
- Communication loss (burst dropouts on interval)
- Calibration offset (systematic error)
- Sample rate mismatch (effective vs configured rate)

### Benchmark Package Export (`benchmark/export_utils.py`)

Standard analytics dataset outputs:
- `telemetry.parquet` — published industrial signals
- `asset_metadata.yaml` — equipment and hierarchy metadata
- `operating_states.parquet` — per-equipment state timeline
- `alarm_events.parquet` — alarm event history
- `maintenance_events.parquet` — maintenance event history
- `fault_timeline.parquet` — fault activity and severity over time
- `benchmark_labels.parquet` — hidden ground truth for validation
- `manifest.json` — dataset inventory and metadata

### Analytics Runtime (`analytics/`)

Integration layer orchestrating all analytics components:
- Fault engine step execution with symptom propagation
- Operating state machine evaluation per equipment
- Benchmark label collection per timestep
- Telemetry frame aggregation
- Fault timeline recording
- Complete simulation run orchestration
- Benchmark package assembly and export
