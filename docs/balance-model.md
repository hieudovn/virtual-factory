# Balance Model

The balance model defines how Virtual Factory treats mass, volume, and energy truth inside the simulation.

## Purpose

Balance calculations make process behavior believable and testable. They also provide validation data for debugging and benchmarking.

Balance values are internal truth unless measured by configured instruments.

## MVP Scope

The first MVP should focus on liquid volume or mass balance around the destination tank:

```text
change in T102 inventory = inflow from V101 - outflow or loss
```

If the MVP has no configured outflow from `T102`, then level rises according to inflow and tank geometry.

## Internal Truth

The solver may compute:

- true flow rate
- true tank inventory
- true tank level
- true valve restriction
- balance residuals
- numerical integration state

These values are useful for validation but are not industrial telemetry.

## Sensor Conversion

A balance-derived truth value becomes externally visible only through a sensor. For example, `T102.level_true` is converted by `LT102` into `LT102_LEVEL`.

The controller reads `LT102_LEVEL`.

## Balance Residuals

Balance residuals should be available in debug or benchmark mode to detect model defects, integration problems, or invalid configuration.

Balance residuals must not be published in industrial mode.

## Future Direction

Later phases may add:

- pressure balance
- energy balance
- multi-phase behavior
- heat transfer
- material properties
- conservation checks across plant subgraphs
