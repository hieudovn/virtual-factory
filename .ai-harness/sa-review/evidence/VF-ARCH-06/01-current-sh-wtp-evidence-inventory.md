# VF-ARCH-06 · Evidence 01 — Decision A: Current SH WTP evidence inventory

## 1. Scope

Repo-first inventory of every WTP-related artifact, classified per Issue #45
into six buckets:

| Bucket | Meaning |
|---|---|
| **S — reusable shared-core seam** | plant-agnostic, survives in the shared core |
| **D — SH-WTP-specific domain behavior** | water-treatment physics/process logic (future domain model, not implemented) |
| **L — standalone mini-engine / legacy path** | `simulators/wtp` / `simulators/vf2` |
| **P — semantic-binding dependency** | PIM artifact consumption contracts |
| **U — UI/projection capability** | existing generic process-flow/telemetry/alarm/trend |
| **G — implementation gap** | frozen-but-not-implemented platform piece |

## 2. Legacy WTP mini-engines (exact)

### 2.1 `simulators/wtp` — standalone WTP simulator

| Artifact | Role (verbatim docstring) |
|---|---|
| `simulation_loop.py` | "Simulation Loop — 8-stage orchestrator … Follows the exact MV→PV→KPI flow from docs/wtp-simulation-model.md" |
| `clarification_engine.py` | "Stage 3: Coagulation / Flocculation / Sedimentation" |
| `disinfection_engine.py` | "Stage 5: Chlorine Disinfection Chemistry" |
| `filtration_engine.py` | "Stage 4: Multimedia Filtration with Backwash" |
| `energy_engine.py` | "Stage 8: Pump power curves, total power, specific energy" |
| `disturbance_engine.py` | "generates values for 7 Disturbance Variables" |
| `kpi_engine.py` | "Stage 8: All 30 KPI signals including cost, quality, traceability" |
| `actuator_engine.py` | "manages 12 Manipulated Variables with realistic actuation" |
| `signal_registry.py` | "classifies all 92 signals by taxonomy role" (7 DV + 12 MV + 43 PV + 30 KPI) |
| `scenario_manager.py` | "loads, applies, and transitions between 8 WTP scenarios" |
| `opcua_gateway.py` | "OPC UA Gateway for the WTP Simulator" |
| `ingest_client.py` | "HTTP POST measurements to PlantOS with retry + buffer" |
| `api_server.py` | "FastAPI server for WTP Simulator control and monitoring" |
| `contract_parser.py` | "Reads the PlantOS Integration Contract (wtp-demo-01.contract.yaml) and extracts all 92 signal definitions…" |
| `static/dashboard.html` | standalone dashboard |

Scenarios (8): `algae_bloom`, `chemical_overdosing`, `chlorine_underdosing`,
`filter_breakthrough`, `filter_clogging_energy_impact`, `hsp_trip`,
`normal_operation`, `raw_water_contamination`.

Classification: **L** (standalone mini-engine / legacy path). Hard-coded 92
signals; own OPC UA + ingest + dashboard; separate from shared core.

### 2.2 `simulators/vf2` — PIM-package-driven simulator

| Artifact | Role |
|---|---|
| `package_loader.py` / `package_validator.py` | read + validate a PIM-generated VF-2 simulation package |
| `object_registry.py` / `signal_registry.py` | dynamic registries built from the package (negative test asserts NO hard-coded signal lists) |
| `behavior_engine.py` | "pattern-based signal generators for VF-2" |
| `topology_engine.py` | "Topology & dependency engine for VF-2" |
| `scenario_engine.py` | "activates fault scenarios with signal overrides" |
| `transform_evaluator.py` | "Safe expression evaluator for VF-2 dependent signal transforms" |
| `output/*` | CSV / memory / stdout output adapters |
| `examples/sample_pim_package.json` | PIM package example carrying **two IDs per object**: VF-local `simulation_object_id` (`VF2-REF-…`) + PIM `canonical_id` (`ASSET-REF-…`) |

Classification: **L** (standalone mini-engine) **+ P** (evidence of the
PIM-package semantic-binding pattern; not the frozen binding itself).

## 3. Shared continuous core (`src/virtual_factory`) — water-treatment-free

| Seam | Classification |
|---|---|
| `core/simulation_engine.py` ("must not hard-code a specific plant") | **S** |
| `equipment/process_dynamics.py` (tank-pump-valve-tank) | **S** (generic) |
| `equipment/compressor_train.py`, `compressor.py`, `boundary.py` | **S** (generic continuous domain models) |
| `operating_states/state_machine.py` | **S** (domain-neutral) |
| `control/pid_controller.py` | **S** |
| `balance/*` (mass/energy/medium/stream) | **S** |
| `telemetry/*`, `observation/*` | **S** |
| Any water-treatment domain logic in `src/virtual_factory` | **NONE** (grep `chlorin|clarif|filtrat|disinfect|turbid|water quality` → only English word "clarification" in `genealogy.py:7`; `water_treatment|song.?hong|SHW|WTP|coagul|backwash` → only UI nav links to the legacy simulator) |

The only WTP references in shared core are UI nav wiring:
`ui/runtime_service.py:427` (`"wtp_available": True`), `ui/static/app.js:16`
(`window.open("http://localhost:8100",…)`), `ui/static/editor.js`
(`APP.wtpMode` → `/api/wtp/plant-graph`), `ui/static/index.html:72-74`
(`#nav-wtp … 🚰 WTP Simulator`).

## 4. Config / workspace artifacts

- `configs/plants/`: `continuous_mvp_01.yaml` (tank-pump-valve-tank),
  `compressor_train_benchmark_01.yaml`, `generic_demo.yaml`, `tipa_assy_demo.yaml`.
- `configs/model_types/`: 15 model types (tank, centrifugal_pump, pipe,
  control_valve, PID, transmitters, compressor, compressor_train, separator,
  fan, heat_exchanger, boundary, valve_actuator).
- `configs/scenarios/`: compressor_benchmark, demand_change, normal_operation,
  pump_degradation, pump_stop, valve_stuck.
- `configs/workspaces/`: **does not exist** — planned location only (PH00 B9:
  target `configs/workspaces/shw-wtp/`). → **G**.

## 5. Existing continuous tests (proof of shared core)

`test_compressor_train.py`, `test_compressor_states.py`, `test_operating_states.py`,
`test_minimal_process_dynamics.py`, `test_minimal_closed_loop.py`,
`test_demand_profile.py`, `test_balance.py`, `test_pid_controller.py`,
`test_engine_boundary.py`, `demo_boundary_flow.py`, `demo_analytics.py`.

## 6. Inventory conclusion

- Shared core is water-treatment-free and reusable; SH WTP has **no** current
  domain implementation in `src/virtual_factory`.
- Both WTP mini-engines are standalone/legacy (PH00 B7: LEGACY/REFERENCE).
- The semantic-binding pattern is already evidenced by `simulators/vf2` PIM
  package (dual IDs) — a reference, not the target runtime.
- `configs/workspaces/` is a gap (planned, not implemented).

No STOP condition triggered by the inventory.
