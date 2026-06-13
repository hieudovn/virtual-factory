# Virtual Factory

Virtual Factory is a physics-informed virtual plant and control lab for generating realistic industrial telemetry, testing IIoT platforms, and evolving toward digital twin simulation.

The project starts with a deliberately small continuous-process MVP, then expands through model-driven plant configuration, control logic, protocol gateways, degraded equipment behavior, and AI-assisted plant generation.

## Development Document Policy

English documents are the primary development documents. Vietnamese documents are supplementary reference documents for business and technical alignment.

When the two versions differ, the English document is authoritative for implementation.

## First MVP

The first MVP simulates a simple tank transfer process:

```text
T101 Source Tank -> P101 Pump -> V101 Control Valve -> T102 Destination Tank
```

Closed-loop level control:

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

## Core Architecture Rules

1. The simulation engine must not hard-code the plant.
2. The plant must be loaded from YAML/JSON configuration.
3. Equipment interacts internally through physical variables and ports.
4. Sensors convert physical truth into measured industrial signals.
5. Controllers must read measured signals, not true physical states.
6. Protocol gateways must publish measurable industrial signals only.
7. Internal truth, solver variables, degradation truth, and true mass or energy balance values must not be published to the IIoT Platform in industrial mode.
8. Ground truth can be stored internally for debug, validation, and benchmarking.
9. Plant configuration must be model-driven and graph-based.
10. Low-code/no-code configuration and AI-assisted plant generation are planned for later phases.

## Repository Map

- `ARCHITECTURE.md`: system boundaries, major components, and runtime flow.
- `ROADMAP.md`: staged development plan.
- `docs/design-principles.md`: project design principles and modeling rules.
- `docs/data-model.md`: configuration and runtime data concepts.
- `docs/output-policy.md`: rules for industrial telemetry versus internal ground truth.
- `docs/mvp-01-continuous-process.md`: first MVP scope.
- `docs/balance-model.md`: mass, volume, and energy balance policy.
- `docs/graph-model.md`: graph-based plant model.

## Current Development Status

Current status:

- Phase 0 documentation foundation initialized.
- Project skeleton and initial configuration are being created.
- Runtime implementation will start after config schema and graph loader are in place.
