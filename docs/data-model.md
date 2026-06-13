# Data Model

This document defines the first-level data concepts for configuration and runtime state. Exact schemas should be added during implementation.

## Configuration Concepts

### Plant

A plant configuration contains metadata, nodes, edges, simulation settings, output profiles, and optional scenario definitions.

### Node

A node is a configured instance of a model type.

Example node categories:

- equipment
- sensor
- actuator
- controller
- gateway

Each node should include an `id`, `type`, parameters, ports, and optional tags.

### Edge

An edge connects two compatible ports.

Example edge categories:

- physical connection
- measurement link
- signal link
- command link
- publication link

### Port

A port is a typed interface exposed by a node. Ports may carry physical variables, measured signals, commands, or publication streams.

### Signal

A signal is an industrial value with metadata. A measured signal should include value, unit, timestamp, quality, source, and optional limits.

### Ground Truth

Ground truth is internal runtime data used for debug, validation, and benchmarking. It is not an industrial signal unless it is transformed by a sensor into a measured signal.

## MVP Nodes

The first MVP should be representable with these configured nodes:

- `T101`: source tank
- `P101`: pump
- `V101`: control valve
- `T102`: destination tank
- `LT102`: level transmitter
- `LIC102`: PID level controller
- `VA101`: valve actuator

These names belong to configuration, not engine code.

## MVP Signals

- `LT102_LEVEL`: measured level signal from `LT102`
- `LIC102_OUT`: controller output signal from `LIC102`
- `V101.opening_actual`: internal physical valve opening, affected by `VA101`
- `T102.level_true`: internal physical truth, not published in industrial mode

## Runtime State Categories

- `truth`: internal physical state and solver values
- `measured`: sensor-produced industrial signals
- `command`: controller and actuator command signals
- `published`: output signals permitted by the selected output profile
- `diagnostic`: explicit debug or benchmark values

## Schema Direction

Future schemas should validate:

- required node fields
- model type existence
- port compatibility
- unit compatibility
- graph connectivity
- controller input source rules
- output-policy compliance
