# Graph Model

Virtual Factory uses a graph-based plant model so the engine can execute many plant configurations without hard-coded topology.

## Nodes

Nodes represent configured instances of reusable model types.

Node categories:

- equipment
- sensor
- actuator
- controller
- gateway

MVP node examples:

- `T101`: source tank
- `P101`: pump
- `V101`: control valve
- `T102`: destination tank
- `LT102`: level transmitter
- `LIC102`: PID controller
- `VA101`: valve actuator

## Edges

Edges represent relationships between compatible ports.

Edge categories:

- physical: material or energy movement
- measurement: physical truth observed by a sensor
- signal: measured signal consumed by a controller or gateway
- command: controller output consumed by an actuator
- publication: allowed signal exposed through a gateway

## MVP Physical Graph

```text
T101.out -> P101.in
P101.out -> V101.in
V101.out -> T102.in
```

## MVP Control Graph

```text
T102.level_true -> LT102.input
LT102.output -> LT102_LEVEL
LT102_LEVEL -> LIC102.process_variable
LIC102.output -> LIC102_OUT
LIC102_OUT -> VA101.command
VA101.output -> V101.opening_actual
```

The edge from `T102.level_true` to `LT102.input` is internal. It does not make `T102.level_true` publishable.

## Validation Rules

Graph validation should check:

- every edge references existing nodes and ports
- connected ports are compatible
- physical connections respect direction and medium
- controllers read measured signals
- gateways publish only allowed signals
- output profiles do not expose internal truth in industrial mode
- each industrial tag has a clear producer

## Future Direction

The graph model should support visual editing, low-code/no-code configuration, validation reports, and AI-assisted plant generation in later phases.
