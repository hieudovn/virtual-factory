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

## Implementation Status

✅ **Mass balance is implemented and active.**

`MassBalance.evaluate()` runs every simulation step inside
`SimulationEngine.step()`, immediately after
`update_continuous_process()`.  Results are written to
`RuntimeState.diagnostics["mass_balance"]`.

### Report fields

| Field | Type | Description |
|---|---|---|
| `mass_in_kg` | float | Mass that entered the destination tank this step |
| `mass_out_kg` | float | Mass that left the destination tank this step |
| `mass_stored_before_kg` | float | Total system stored mass at step start |
| `mass_stored_after_kg` | float | Total system stored mass at step end |
| `mass_stored_delta_kg` | float | Change in stored mass this step |
| `residual_kg` | float | Imbalance = mass_in - mass_out - delta_stored |
| `residual_pct` | float | Imbalance relative to max throughput (%) |
| `balanced` | bool | True when \|residual_pct\| ≤ 0.1 % |
| `message` | str | Human-readable summary |

### Accessing results

```python
engine.step()
engine.state.diagnostics["mass_balance"]
# {"mass_in_kg": ..., "balanced": True, "message": "Mass balanced", ...}
```

### Internal truth

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
