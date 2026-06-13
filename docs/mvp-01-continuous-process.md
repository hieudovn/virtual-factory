# MVP 01: Continuous Process

The first MVP proves that Virtual Factory can run a configurable closed-loop process while keeping industrial telemetry separate from internal truth.

## Process

```text
T101 Source Tank -> P101 Pump -> V101 Control Valve -> T102 Destination Tank
```

## Control Loop

```text
T102.level_true
  -> LT102 Level Transmitter
  -> LT102_LEVEL measured signal
  -> LIC102 PID Controller
  -> LIC102_OUT
  -> VA101 Valve Actuator
  -> V101.opening_actual
  -> process flow
  -> T102.level_true
```

## Required Behaviors

- The plant is loaded from YAML/JSON.
- The engine does not hard-code MVP equipment names.
- Tanks maintain internal true level or volume.
- Pump and valve affect process flow through physical ports.
- `LT102` reads `T102.level_true` internally and emits `LT102_LEVEL`.
- `LIC102` reads `LT102_LEVEL`, not `T102.level_true`.
- `VA101` converts `LIC102_OUT` into `V101.opening_actual`.
- Protocol gateways publish only allowed measured industrial signals in industrial mode, with internal ground truth hidden from the IIoT Platform.
- Ground truth is retained internally for debug, validation, and benchmarking.

## Minimum Industrial Tags

- `LT102_LEVEL`
- `LIC102_OUT`

Optional industrial tags may be added only if they represent measurable or control-system-visible values.

## Internal Values

Examples of internal values:

- `T102.level_true`
- `T101.level_true`
- true process flow
- true valve opening unless configured as measured feedback
- solver state
- balance residuals

These must not be published in industrial mode.

## Success Criteria

- A configured plant can run without plant-specific engine code.
- The loop can regulate `T102` level through measured feedback.
- Output policy prevents industrial-mode ground truth leakage.
- Debug or benchmark output can compare measured signals against truth when explicitly enabled.
