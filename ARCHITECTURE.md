# Architecture

Virtual Factory is a model-driven simulation system. The runtime engine executes a plant model loaded from configuration instead of embedding plant-specific behavior in code.

## Goals

- Generate realistic industrial telemetry for IIoT and control-system testing.
- Represent physical process behavior with enough fidelity for believable dynamics.
- Preserve internal ground truth for validation without exposing it as industrial telemetry.
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
