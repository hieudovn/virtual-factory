# 02 — Runtime Entrypoints & Selection Mechanism

## 2.1 Console scripts

`pyproject.toml` registers exactly **one** console script:

```toml
[project.scripts]
virtual-factory = "virtual_factory.main:main"
```

`simulators/wtp` (`wtp-sim`) and `simulators/vf2` (`vf2-sim`) are **not**
registered — they are invoked as `python -m simulators.wtp.main` /
`python -m simulators.vf2.main` (or via their `deploy/` systemd/Dockerfile).

## 2.2 `virtual-factory` subcommands (`src/virtual_factory/main.py:build_parser`)

| Subcommand | Selection inputs | Runtime instantiated |
|---|---|---|
| `run` | `--config` (default `configs/plants/continuous_mvp_01.yaml`), `--scenario`, `--steps`, `--dt`, `--csv-output`, `--jsonl-output`, `--mqtt-host/port/topic-prefix`, `--opcua-endpoint`, `--sparkplug` | `load_plant_config` → `load_scenario` → `core/engine_factory.create_engine` → `core/simulation_engine.SimulationEngine`; optional MQTT/OPC-UA/Sparkplug gateways |
| `serve` | `--config` (fallback `get_last_config()` from `~/.virtual_factory/state.json`), `--scenario`, `--port`, `--auto-start` | `ui.api.create_app` → `RuntimeService` (single continuous engine); `_get_assy_controller()` lazily builds the TIPA ASSY `DemoController` when `/assy-demo/*` is hit |
| `validate` | `--config` | `load_plant_config` + `core.validators.validate_with_report` |
| `generate` | `--prompt`, `--backend` | `ai.generator.generate_config` |
| `parse` | `--text` (P&ID shorthand) | `ai.pid_parser` |

## 2.3 How plant/config is selected

- **Continuous engine:** explicit `--config` flag (default `continuous_mvp_01`).
  `serve` persists the last config in `~/.virtual_factory/state.json`.
- **Dispatch discriminator:** `core/engine_factory.resolve_engine_kind(config)`
  reads a top-level `model_type` field; absent → defaults to
  `continuous_process`. `_SUPPORTED_KINDS = {"continuous_process"}`.
  **`plant.type` is metadata only — never used for dispatch.**
- **TIPA ASSY:** env var `TIPA_ASSY_CONFIG` (default
  `configs/plants/tipa_assy_demo.yaml`), read by `ui/api.py:_get_assy_controller()`.
  This path is **not** reachable from `virtual-factory run`.
- **Generic demo:** `assembly/definition_io.load_definition_from_yaml` (direct
  call, no CLI wiring).

## 2.4 How scenarios are selected

- Continuous: explicit `--scenario <path>` → `scenarios/scenario_loader.load_scenario`
  → `ScenarioConfig` (`{id, actions:[{at_s, type, target?, value?, parameters?}]}`).
- `ScenarioManager._apply_action` supports: `set_truth`, `set_parameter`
  (target `equipment.<id>.<param>`), `set_sensor_quality`, `set_sensor_bias`,
  `set_sensor_drift`, `valve_stuck`.
- **No scenario registry keyed by plant/domain** — scenario files are standalone
  and implicitly coupled to a plant's equipment IDs (`T102`, `P101`, `COMP01`).
- `configs/scenarios/compressor_benchmark_scenarios.yaml` uses a **different
  format** (wrapped `scenarios:` list + `inject_fault` action) that is NOT
  parseable by `load_scenario` — design-stage artifact, not runtime-loadable.

## 2.5 Is there a workspace concept?

**No.** No `workspace` identifier exists anywhere. Closest building blocks:

- `plant.id` (e.g. `tipa_assy_demo`, `continuous_mvp_01`,
  `compressor_train_benchmark_01`) — config metadata.
- `production_line.plant_id` / `assembly/sub_line_identity.py:72` `plant_id`
  (hard-validated to `"TIPA"`).
- `discrete/run_context.py:29` `environment` namespace (default `"demo"`).
- `observation/identity.py:51` `ExternalIdentityRef.namespace`.
- `protocols/opcua_gateway.py` `_DEFAULT_NAMESPACE="VirtualFactory"`.

None of these is threaded config → runtime → telemetry → output as a single
workspace identity.

## 2.6 Are loaders generic or plant-specific?

| Loader | Genericity |
|---|---|
| `core/config_loader.load_plant_config` | Generic (Pydantic `PlantConfig`, schema-validated) — continuous plants |
| `core/model_registry.ModelRegistry.from_directory` | Generic (15 model types, `python_class` dotted import) |
| `assembly/line_runtime.load_assy_config_from_yaml` | TIPA-specific (hand-rolled `yaml.safe_load`) |
| `assembly/definition_io.load_definition_from_yaml` | Generic-discrete-specific (hand-rolled) |

## 2.7 Coexistence / isolation (current state)

- Each runtime is a **single-process, single-config** object (`RuntimeService`
  owns exactly one continuous engine; `DiscreteRunService` at most one run).
- **No import leakage** between families is enforced by tooling — isolation is
  by convention only. Observed cross-family imports:
  - `core/simulation_engine.py` → `equipment.*`, `balance.*` (shared-core → domain).
  - `core/runtime_factory.py` → `equipment/control/actuation/instrumentation/telemetry.*`.
  - `assembly/*` → `discrete/*`, `observation/*`, `integration/*` (domain → core/transport, correct direction).
- **Outputs are not namespaced per simulation**: CSV/JSONL paths are explicit
  CLI args; MQTT topic prefix default
  `virtual-factory/demo/continuous_mvp_01`; OPC UA namespace fixed
  `VirtualFactory`; Sparkplug `edge_node_id = config.plant.id`. Two simultaneous
  runs with defaults collide.

## 2.8 Actual entrypoints summary

```text
virtual-factory run --config configs/plants/continuous_mvp_01.yaml --scenario configs/scenarios/normal_operation.yaml
virtual-factory run --config configs/plants/compressor_train_benchmark_01.yaml
virtual-factory serve --config ... --port 8000
virtual-factory validate --config ...
python -m simulators.wtp.main --contract examples/contracts/wtp-demo-01.contract.yaml --steps 60
python -m simulators.vf2.main --package path/to/package.json --steps 60
docker compose -f docker-compose.assy.yml up --build -d   # TIPA ASSY serve (port 8000)
```
