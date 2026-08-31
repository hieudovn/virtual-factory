# 03 — Shared vs Workspace-Specific Classification

Classification of `src/virtual_factory` + `simulators` against the governing
rule: *engine owns execution mechanics; configuration owns plant structure;
reusable models own reusable behavior; workspace owns plant/project-specific
composition; gateways own external publication.*

Legend: **SHARED CORE** · **REUSABLE DOMAIN MODEL** · **WORKSPACE /
PROJECT-SPECIFIC** · **DEMO / FIXTURE ONLY** · **UNKNOWN / MIXED**.

## 3.1 Package classification

| Package / path | Classification | Rationale / evidence |
|---|---|---|
| `core/` (13 modules) | **SHARED CORE** | config_loader, schema, engine_factory, simulation_engine, runtime_factory, runtime_state, plant_graph, ports, time_manager, state_persistence, validators, exceptions, model_registry |
| `discrete/` (14 modules) | **SHARED CORE** | scheduler, clock, dispatcher, engine, run_service, snapshot, state, trace, handler_registry |
| `equipment/` | **REUSABLE DOMAIN MODEL** | tank, pump, valve, compressor, compressor_train, heat_exchanger, fan, pipe, separator, boundary, process_dynamics — all `configs/model_types/*`-registered |
| `balance/` | **REUSABLE DOMAIN MODEL** | mass/energy balance solvers (generic) |
| `control/` | **REUSABLE DOMAIN MODEL** | PID controller |
| `instrumentation/` | **REUSABLE DOMAIN MODEL** | level/flow/pressure transmitters, sensor quality |
| `actuation/` | **REUSABLE DOMAIN MODEL** | valve actuator |
| `sensor_quality/` | **REUSABLE DOMAIN MODEL** | sensor degradation |
| `telemetry/` | **REUSABLE DOMAIN MODEL** (transport-adjacent) | SignalValue, frames, output policy, ring buffer, export |
| `protocols/` | **REUSABLE DOMAIN MODEL** (gateway adapters) | mqtt/opcua/sparkplug gateways |
| `observation/` + `integration/` | **REUSABLE DOMAIN MODEL** (M5 pipeline) | envelope, service, router, projections, gateways |
| `faults/`, `operating_states/`, `maintenance/`, `benchmark/`, `analytics/` | **REUSABLE DOMAIN MODEL** (analytics cluster) | fault engine, state machine, event generator, benchmark manager |
| `assembly/` | **WORKSPACE / PROJECT-SPECIFIC** | TIPA ASSY (tipa.py hard-coded topology, line_runtime, demo_controller, observation_bridge, assy_mes_bridge) + generic-demo definition IO |
| `ui/` | **MIXED** | `runtime_service.py` = generic continuous API; `api.py` hosts BOTH `/runtime/*` and `/assy-demo/*` (plant-specific endpoints mixed into one FastAPI app) |
| `ai/` | **MIXED** | config generator + PID parser (tooling, not simulation runtime) |
| `scenarios/` | **WORKSPACE / PROJECT-SPECIFIC** | `scenario_loader.py`/`scenario_manager.py` are generic; `configs/scenarios/*` files are plant-specific |
| `configs/plants/*.yaml` | **WORKSPACE / PROJECT-SPECIFIC** | one file per plant |
| `configs/model_types/*.yaml` | **REUSABLE DOMAIN MODEL** | 15 generic model declarations |
| `configs/scenarios/*.yaml` | **WORKSPACE / PROJECT-SPECIFIC** | plant-coupled scenario files |
| `configs/faults/*.yaml` | **REUSABLE DOMAIN MODEL** (config) | compressor/pump fault templates |
| `simulators/wtp/` | **DEMO / FIXTURE ONLY** (legacy standalone) | VF-1 hard-coded WTP mini-engine outside the platform |
| `simulators/vf2/` | **DEMO / FIXTURE ONLY** (legacy standalone) | VF-2 PIM-native generic mini-engine outside the platform |
| `examples/contracts/` | **DEMO / FIXTURE ONLY** | contract stub |
| `tests/demo_*.py`, `tests/debug_states.py` | **DEMO / FIXTURE ONLY** | manual demos |

## 3.2 Boundary violations (FLAGGED — not fixed in PH00)

1. **Shared-core → domain coupling** — `core/simulation_engine.py` imports
   `equipment.process_dynamics`, `balance.basic_balance`,
   `balance.energy_balance`; `core/runtime_factory.py` imports
   `equipment/control/actuation/instrumentation/telemetry`. The core knows
   concrete domain packages, contrary to a strict core-domain layering.
   *Severity: LOW (currently single-engine in practice); becomes relevant if a
   second engine kind is added.*
2. **TIPA topology hard-coded in code** — `assembly/tipa.py:build_tipa_topology()`
   encodes SSO2→AP01…AP11→sink. This violates the ARCHITECTURE.md rule "engine
   must not hard-code the plant" for the continuous engine, but ASSY is a
   separate, SA-accepted discrete runtime family with its own contract. Not
   retroactively reclassified.
3. **Scenario format divergence** — `compressor_benchmark_scenarios.yaml`
   (`inject_fault`) is not loadable by `ScenarioManager._apply_action`.
   *Severity: MEDIUM for compressor benchmark scenarios (currently design-stage).*
4. **`plant.type` ignored by dispatch** — dispatch keys only on top-level
   `model_type`; `plant.type` (`discrete_assembly`, `continuous`,
   `continuous_process`) is metadata. *Severity: LOW (no mis-dispatch today),
   but it is the obvious place to add a workspace-aware discriminator.*
5. **Plant-specific endpoints inside generic API** — `ui/api.py` mixes
   `/assy-demo/*` (TIPA-specific) into the same FastAPI app as `/runtime/*`.
   *Severity: LOW; a workspace-aware router would cleanly separate these.*

## 3.3 Classification conclusion

- There **is** a genuine shared core (`core/` + `discrete/`) and a genuine
  reusable model layer (`equipment/`, `balance/`, `control/`,
  `instrumentation/`, `actuation/`, plus the observation/integration transport).
- The **workspace layer is implicit and incomplete**: plant configs +
  plant-specific packages (`assembly/`) exist, but there is no workspace
  manifest, no workspace id, and no workspace-aware dispatch/output isolation.
- The two standalone WTP simulators are the clearest **boundary violation**: a
  whole plant/domain implemented as a parallel mini-engine outside the platform.
