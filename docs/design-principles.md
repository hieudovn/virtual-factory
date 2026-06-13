# Design Principles

## Model-Driven First

The engine must execute plant models loaded from YAML/JSON. Plant topology, equipment instances, signal names, and controller loops belong in configuration.

The MVP must not become a special case in the engine.

## Physical Truth Is Internal

Physical truth exists so the simulation can behave realistically. It includes true level, true flow, true pressure, true mass, true energy, solver state, and degradation state.

Physical truth is not automatically an industrial signal.

## Sensors Create Industrial Reality

Industrial systems observe the plant through instruments. A measured signal may be delayed, noisy, clipped, failed, biased, or marked with poor quality.

Controllers and gateways must use measured signals. They must not bypass sensors to read truth.

## Components Communicate Through Ports

Equipment should interact through typed physical ports, signal ports, and command ports. Direct cross-component state reads should be avoided.

This keeps equipment reusable and makes graph validation possible.

## Graph-Based Configuration

Plant structure is a graph of nodes and edges. Nodes represent equipment, sensors, controllers, actuators, and gateways. Edges represent physical connections, measurement links, and command links.

Graph validation should detect missing ports, invalid connections, cycles where not allowed, and ambiguous signal ownership.

## Output Policy Is Part of the Architecture

Industrial telemetry must expose only measurable industrial signals. Internal ground truth must be hidden from the IIoT Platform in industrial mode. Debug and benchmark modes may access ground truth, but those outputs must be explicitly separated from industrial-mode outputs.

## Small MVP, Correct Boundaries

The first MVP is intentionally small. Its main purpose is to prove the architecture boundaries:

- configurable plant topology
- reusable equipment models
- measured-signal control
- industrial output isolation
- internal ground-truth storage
