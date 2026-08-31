# 04 — TIPA ASSY Packaging Analysis

## 4.1 What TIPA ASSY is

A discrete stop-and-go assembly line demo (six sub-lines `ASSY-SL01..06`,
12 positions `PRE-ASSY`/`AP01..AP11`, SSO2+RSO2 join at AP04, quality gates
AP03/AP06/AP08/AP11), with an additive VF→MES contract bridge
(`tipa-assy-demo-v1.1`).

## 4.2 Package structure (all under `src/virtual_factory/assembly/`)

24 modules, three roles:

- **Runtime (custom, TIPA-specific):**
  `line_runtime.py` (`AssyLineRuntime`, conveyor/station/quality/operation
  execution), `station_contracts.py`, `operation_execution.py`,
  `quality_records.py`, `genealogy.py`, `sub_line_identity.py`,
  `demo_composition.py` (`AssyDemoComposition`, `DemoScenario`,
  `SCENARIO_QUALITY_OVERRIDES`), `demo_controller.py` (`DemoController`),
  `demo_snapshot.py`, `tipa.py` (`build_tipa_topology()` — hard-coded topology).
- **Output / contract bridge (project-specific):**
  `observation_bridge.py` (`AssyObservationBridge`, M6-INT-01),
  `assy_mes_bridge.py` (`AssyMesBridge`, `build_assy_mes_pipeline`,
  `CONTRACT_VERSION="tipa-assy-demo-v1.1"`).
- **Generic-discrete reuse (shared within assembly):**
  `definition_io.py` (`load_definition_from_yaml`), `handlers.py`,
  `primitives/` (used by the M4 generic demo).

## 4.3 How ASSY is selected / launched

- **Env var `TIPA_ASSY_CONFIG`** (default `configs/plants/tipa_assy_demo.yaml`),
  read by `ui/api.py:_get_assy_controller()` → `DemoController(config_path=...)`
  → `ctrl.initialize()`.
- **Docker**: `docker-compose.assy.yml` builds the root `Dockerfile`
  (`SOURCE_SHA` build arg → `VF_SOURCE_SHA`) and runs
  `virtual-factory serve --host 0.0.0.0 --port 8000` with
  `VF_ENABLE_S04B_OVERVIEW=1` and `TIPA_ASSY_CONFIG=/app/configs/plants/tipa_assy_demo.yaml`.
- **NOT reachable from `virtual-factory run`** — ASSY has its own controller
  loop (`DemoController.step/run_to_terminal`) and its own endpoint set
  `/assy-demo/*`.

## 4.4 Config loading

`assembly/line_runtime.load_assy_config_from_yaml()` — hand-rolled
`yaml.safe_load` mapping (NOT the generic Pydantic `load_plant_config`).
Top-level keys of `tipa_assy_demo.yaml`: `plant`, `conveyor`, `upstream`,
`station_durations`, `ap04`, `identity`, `simulation`, `quality`,
`auto_timing_profiles`, `production_line`.

## 4.5 Model registry usage

**None.** ASSY topology and station behavior are hard-coded in
`assembly/tipa.py` and `line_runtime.py`; `configs/model_types/*` are not
consulted. This is intentional for the demo but is the main reason ASSY cannot
be "reconfigured" like a continuous plant.

## 4.6 Output isolation (ASSY-specific)

- `assy_mes_bridge.py` stamps `plant_id="TIPA"`, `subline_id=ASSY-SLxx`,
  `run_id=ASSY-SLxx:R<n>`, `contract_version` on every projected message.
- `observation_bridge.py` routes through the shared M5 pipeline
  (`ObservationService → ObservationRouter → MESProjection → gateways`).
- ASSY output is therefore **already namespaced** by `plant_id`/`subline_id`/
  `run_id` — the one family with explicit provenance today.

## 4.7 Compatibility with workspace abstraction

- ASSY is a **working, SA-accepted discrete workspace** implemented
  project-specifically. It does not need to be moved or rewritten for SH WTP to
  be added.
- For the workspace contract, ASSY maps to:
  `workspace_id=TIPA-ASSY`, `workspace_type=discrete_assembly`,
  `plant_id=TIPA`, `runtime.engine=discrete_assembly` (a kind not yet in
  `engine_factory._SUPPORTED_KINDS`), `outputs.namespace=TIPA`.
- Adding SH WTP must **not** require ASSY changes — SH WTP should reuse the
  generic continuous engine + model registry, not the ASSY discrete stack.

## 4.8 Packaging verdict

ASSY is **self-contained and project-specific**, with the cleanest output
provenance of all families. Its only architectural tension is the hard-coded
topology (accepted for the demo) and the `/assy-demo/*` endpoints living inside
the generic `ui/api.py`. Neither blocks a workspace abstraction.
