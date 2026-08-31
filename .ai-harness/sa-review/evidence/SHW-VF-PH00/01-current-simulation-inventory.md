# 01 — Current Simulation Inventory

READ-ONLY audit of every simulation family present in the repo at HEAD
`240d8db5eff481f1d4d8810d275214077031e72a` (detached). All facts verified by
reading files; no stale-ROADMAP assumptions.

Legend — runtime families found: **4 inside the platform** + **2 standalone
simulators outside the platform**.

## A. Platform simulation families (under `src/virtual_factory/`)

| Field | TIPA ASSY | Continuous MVP | Compressor benchmark | Generic demo (discrete) |
|---|---|---|---|---|
| Name | `tipa_assy_demo` | `continuous_mvp_01` | `compressor_train_benchmark_01` | `generic-demo` |
| Purpose | Six-sub-line stop-and-go motor assembly demo (SSO2/RSO2 join, quality gates, MES bridge) | Default CLI demo: tank→pump→valve→tank PID level control | Analytics benchmark: 50+ tags, fault injection, asset health/PdM dataset generation | M4 discrete definition demo: 3-station line feeding an MES pipeline |
| Plant/domain | Discrete assembly (motors) | Continuous process (water transfer) | Continuous process (natural gas compression) | Discrete manufacturing (generic) |
| Runtime entrypoint | `assembly/demo_controller.py:DemoController` (+ `assembly/line_runtime.py:AssyLineRuntime`); loaded via `ui/api.py:_get_assy_controller()` env `TIPA_ASSY_CONFIG` | `core/engine_factory.create_engine` → `core/simulation_engine.SimulationEngine` (via `main.py:run_simulation`) | Same generic engine as Continuous MVP (`create_engine` defaults `continuous_process`) | `assembly/definition_io.load_definition_from_yaml` → `SimulationDefinition` → `discrete` engine + `assembly/handlers.py` |
| Plant config | `configs/plants/tipa_assy_demo.yaml` | `configs/plants/continuous_mvp_01.yaml` | `configs/plants/compressor_train_benchmark_01.yaml` | `configs/plants/generic_demo.yaml` |
| Scenario config | None in `configs/scenarios/` — `DemoScenario` enum + `SCENARIO_QUALITY_OVERRIDES` in `assembly/demo_composition.py` | `configs/scenarios/{normal_operation,demand_change,pump_stop,pump_degradation,valve_stuck}.yaml` | `configs/scenarios/compressor_benchmark_scenarios.yaml` (format mismatch — see §5) | None (definition-embedded) |
| Model registry | NOT used — topology hard-coded in `assembly/tipa.py:build_tipa_topology()` | `ModelRegistry.from_directory(configs/model_types)`: tank_v1, centrifugal_pump_v1, control_valve_v1, level/flow/pressure_transmitter_v1, pid_controller_v1, valve_actuator_v1 | Same registry: boundary_v1, compressor_train_v1, pressure/flow_transmitter_v1 | NOT used — `primitives` (source/buffer/processor/quality_gate/sink) |
| Output path/adapter | `assembly/observation_bridge.py` (M5 pipeline) + `assembly/assy_mes_bridge.py` (`MODEL_ID="tipa_assy_demo"`) | `telemetry/export.py` CSV/JSONL; `protocols/{mqtt,opcua,sparkplug}_gateway.py` | Same telemetry + `benchmark/`, `faults/`, `operating_states/`, `maintenance/`, `analytics/` | `discrete` trace + MES observation gateway (`test_m4_s04_mes.py`) |
| Tests | `test_assy_*.py`, `test_demo_*.py`, `test_quality*.py`, `test_ops0*.py`, `test_m6_int_01.py`, `test_sim_val_01_feed.py`, `test_vf_contract_finality_01.py`, `demo_assy.py` | `test_cli_*.py`, `test_minimal_*.py`, `test_pid_controller.py`, `test_scenario_*.py`, `test_runtime_*.py`, `test_api.py`, `test_telemetry_*.py`, `test_mqtt_gateway.py`, `test_sparkplug_gateway.py` | `test_compressor_*.py`, `test_benchmark.py`, `test_fault_engine.py`, `test_operating_states.py`, `test_maintenance_events.py`, `demo_analytics.py`, `demo_boundary_flow.py`, `demo_phase1.py` | `test_m4_s02_definition.py`, `test_m4_s04_mes.py` |
| Custom runtime code | Entire `src/virtual_factory/assembly/` (24 modules) | None (fully config-driven) | `equipment/compressor_train.py` model + analytics cluster | `assembly/definition_io.py`, `assembly/tipa.py`, `assembly/handlers.py` |

## B. Standalone simulators (OUTSIDE the platform, not reachable from `virtual-factory` CLI)

| Field | VF-1 WTP (`simulators/wtp/`) | VF-2 PIM-native (`simulators/vf2/`) |
|---|---|---|
| Name | `wtp-sim` | `vf2-sim` |
| Purpose | Standalone WTP simulator: hard-coded 92-signal registry, 8 stage formulas | PIM-native generic simulator driven by a PIM package JSON |
| Plant/domain | Water treatment (clarification/filtration/disinfection/energy/KPI/actuator/disturbance) | Generic (PIM-driven topology/behavior) |
| Runtime entrypoint | `simulators/wtp/main.py:main` (`--contract` required, `--config`, `--scenario`, `--steps`, `--api-only`, `--csv-output`, `--opcua-endpoint`) | `simulators/vf2/main.py:main` (`--package` required, `--config`, `--scenario`, `--steps`, `--output`, `--api-server`) |
| Config | `simulators/wtp/wtp_config.yaml` | `simulators/vf2/config.yaml` (API port 8102, output `/app/out/vf2_output.csv`) |
| Model registry | `simulators/wtp/signal_registry.py` (hard-coded) + stage engines | `simulators/vf2/object_registry.py`, `package_loader.py`, `topology_engine.py`, `behavior_engine.py` |
| Output | CSV, OPC UA (`opcua_gateway.py`), API (`api_server.py`) | CSV, API (`api_server.py`) |
| Console script | NOT registered in `pyproject.toml` (run as `python -m simulators.wtp.main`) | NOT registered (run as `python -m simulators.vf2.main`) |
| Deploy | `deploy/wtp-simulator.service` | `deploy/vf2.Dockerfile` |

## C. WTP/SH contract trace

- `examples/contracts/wtp-demo-01.contract.yaml` — PlantOS Integration Contract v2
  stub: `plant.id=WTP-DEMO-01`, `type=water_treatment`, 9 `areas`
  (AREA-INT/CHEM/CLAR/FILT/DIS/CW/DIST/KPI/UTIL), empty `assets`, `signals`,
  `simulation.behaviors`, `extensions.monitoring.scenarios`.
- **`examples/song-hong-wtp/vf_consumer/` does NOT exist** — the §9 "old draft"
  is absent; the only SH/WTP artifacts are `simulators/wtp` (VF-1),
  `simulators/vf2` (VF-2), and the contract stub.
- UI integration: `ui/runtime_service.py` `"wtp_available": True`,
  `ui/static/index.html` `nav-wtp`, `ui/static/app.js` opens
  `http://localhost:8100` (VF-1 WTP API), `ui/static/editor.js` `APP.wtpMode`.

## D. Inventory conclusion

- The platform itself is **config-driven for continuous processes** and
  **code-driven for the two discrete families** (TIPA ASSY hard-coded topology,
  generic demo definition-driven).
- SH WTP today is **not a platform workspace** — it exists as two standalone
  simulators outside `src/virtual_factory`, connected only by a contract stub
  and a UI nav link. This is exactly the "duplicate mini-engine" risk the gate
  exists to prevent.
