# Output Policy

The output policy protects the boundary between realistic industrial telemetry and internal simulation truth.

## Industrial Mode

Industrial mode is the default external-facing mode. It may publish only measurable industrial signals.

Allowed examples:

- measured transmitter values
- controller outputs
- actuator command or feedback signals when configured as industrial signals
- equipment status signals that would exist in a real control system
- timestamps, quality codes, units, and tag metadata

Forbidden examples:

- true tank level such as `T102.level_true`
- true flow, pressure, mass, or energy values unless measured by configured instruments
- solver variables
- numerical integration state
- degradation truth
- fault truth before it is reflected through measured symptoms
- hidden balance residuals

## Debug Mode

Debug mode may expose internal values for local development. Debug outputs must be clearly labeled and must not share the same namespace as industrial tags.

## Benchmark Mode

Benchmark mode may record ground truth for model validation, controller evaluation, dataset scoring, and telemetry quality checks.

Benchmark outputs are not industrial telemetry.

## Gateway Responsibility

Protocol gateways must enforce output profiles. A gateway should publish only the signals selected by the active profile.

If a signal is not explicitly allowed, it should not be published.

## Sensor Boundary

A true physical value becomes publishable industrial telemetry only after a configured sensor converts it into a measured signal.

For the first MVP:

- `LT102_LEVEL` may be published.
- `LIC102_OUT` may be published.
- `T102.level_true` must not be published in industrial mode.
- `V101.opening_actual` should be treated as internal truth unless configured as a measurable feedback signal.

## Naming Guidance

Industrial tags should use plant-style names such as `LT102_LEVEL` or `LIC102_OUT`.

Internal values should use explicit namespaces such as `truth.T102.level`, `solver.flow.V101`, or `diagnostic.balance.T102` so they cannot be mistaken for industrial tags.
