# 05 — Continuous MVP & Compressor Benchmark Analysis

## 5.1 Continuous MVP (`continuous_mvp_01`)

- **What it is:** the default, fully config-driven continuous-process demo:
  source tank `T101` → pump `P101` → control valve `V101` → destination tank
  `T102`, PID `LIC102` level control, sensors `LT102/FT101/PT101`, actuator
  `VA101`.
- **Runtime:** `core/engine_factory.create_engine` → `core/simulation_engine.SimulationEngine`
  (the only engine kind today: `_SUPPORTED_KINDS={"continuous_process"}`).
- **Assembly:** `core/runtime_factory.build_runtime` uses
  `ModelRegistry.from_directory(configs/model_types)` to instantiate
  `equipment/sensors/controllers/actuators` by `model_type` id.
- **Models used:** tank_v1, centrifugal_pump_v1, control_valve_v1,
  level_transmitter_v1, flow_transmitter_v1, pressure_transmitter_v1,
  pid_controller_v1, valve_actuator_v1.
- **Scenarios:** 5 loadable scenario files in `configs/scenarios/`
  (normal_operation, demand_change, pump_stop, pump_degradation, valve_stuck).
- **Output:** CSV/JSONL via `telemetry/export.py`; MQTT/OPC-UA/Sparkplug via
  `protocols/`; default MQTT topic prefix
  `virtual-factory/demo/continuous_mvp_01`.
- **Test coverage:** `test_cli_demo`, `test_cli_scenario`, `test_minimal_*`,
  `test_pid_controller`, `test_scenario_*`, `test_runtime_*`, `test_api`,
  `test_telemetry_*`, `test_mqtt_gateway`, `test_sparkplug_gateway`.

## 5.2 Compressor benchmark (`compressor_train_benchmark_01`)

- **What it is:** the analytics flagship — a compressor train
  (`compressor_train_v1`) between `boundary_v1` gas source/sink, ~26
  transmitters mapped onto compressor truth, 7 alarms,
  `output_policy.mode=benchmark` (publishes `calculated` ground-truth category).
- **Runtime:** the **same generic continuous engine** — dispatch defaults to
  `continuous_process`; `plant.type: continuous` is ignored. No compressor-
  specific engine.
- **Domain models:** `equipment/compressor_train.py` (`CompressorTrain`),
  `boundary_v1`; analytics cluster `faults/`, `operating_states/`,
  `maintenance/`, `benchmark/`, `analytics/`.
- **Production default:** `deploy/virtual-factory.service` runs
  `--config /opt/virtual-factory/configs/plants/compressor_train_benchmark_01.yaml`.
- **Scenario note:** `configs/scenarios/compressor_benchmark_scenarios.yaml`
  uses a `scenarios:`-wrapped list with `inject_fault` actions — **not loadable**
  by `ScenarioManager._apply_action` (which supports only
  set_truth/set_parameter/set_sensor_quality/set_sensor_bias/set_sensor_drift/
  valve_stuck). Flagged as design-stage divergence.
- **Test coverage:** `test_compressor_train`, `test_compressor_states`,
  `test_demand_profile`, `test_benchmark`, `test_fault_engine`,
  `test_operating_states`, `test_maintenance_events`, `demo_analytics`,
  `demo_boundary_flow`, `demo_phase1`.

## 5.3 What these two prove for SH WTP

- A new continuous-process plant (like a water-treatment chain) can be added
  **purely as configuration** (`configs/plants/<id>.yaml`) **plus** reusable
  model types (`configs/model_types/*.yaml` + a `virtual_factory.equipment.*`
  class) — **no new engine**.
- The compressor benchmark proves the same engine serves **two different
  domains** (water transfer vs gas compression) purely via config + models.
- The gap: no **workspace id** distinguishes these two plants in output
  provenance (both currently rely on caller-supplied paths/prefixes).

## 5.4 Reusability assessment vs the WTP draft (gate §9)

| Draft component (§9) | Existing VF equivalent | Verdict |
|---|---|---|
| `vf_contract_loader.py` | `core/config_loader.load_plant_config` (+ Pydantic schema) | Reuse core loader; map contract→PlantConfig |
| `state_template_loader.py` | `core/runtime_state.RuntimeState` + `ModelRegistry` parameters | Reuse model parameter schema |
| `vf_object_mapper.py` | `core/runtime_factory.build_runtime` (equipment/sensors/controllers/actuators by `model_type`) | Reuse factory; mapping is config |
| `logical_models.py` | `equipment/*` model classes registered in `configs/model_types` | Reuse + add WTP-specific model types as reusable domain models |
| `scenario_runner.py` | `scenarios/scenario_manager.ScenarioManager` | Reuse (add missing action types only if SHW needs them, in a separate gate) |
| `output_adapter.py` | `telemetry/export.py` + `protocols/*` + `integration/gateways/*` | Reuse |

**Preferred outcome confirmed:** SH WTP = config + mappings + scenarios +
new reusable model types → existing shared VF runtime. No SHW-specific runtime
stack.
