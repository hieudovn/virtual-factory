# 07 — Workspace Isolation Test Plan

For each gate-required isolation item, the concrete, executable proof. All are
additive; none break existing demos. Tests live under `tests/test_shw_wtp_*.py`
in PH01+ (none written in PH00).

| # | Requirement | How it is tested (PH01+) |
|---|---|---|
| 1 | SHW loads independently | `virtual-factory run --config configs/workspaces/shw-wtp/plant.yaml --steps N` exits 0 and emits SHW-namespaced frames with no TIPA/compressor IDs present. Pytest: build SHW runtime from manifest alone, assert `workspace_id == "SHW-WTP"`. |
| 2 | ASSY loads independently | Existing `test_assy_demo.py` + `docker compose -f docker-compose.assy.yml up` remain green with no SHW env/config. Assert ASSY `plant_id=="TIPA"` and no `SHW` token in ASSY output. |
| 3 | No SHW canonical ID appears in an ASSY run | Run ASSY bounded demo, collect all `ProjectedMessage.payload` and `SignalValue.name`; assert `"SHW"`/`"PLANT-SHW"` absent. |
| 4 | No ASSY object/config appears in SHW | Build SHW runtime from SHW config only; assert no `AP01..AP11`, `SSO2`, `RSO2`, `ASSY-SL*` ids appear in graph/equipment/signals. |
| 5 | Scenario registries do not leak | Load SHW workspace scenarios; assert `ScenarioManager` sees only SHW scenario ids. Load ASSY/continuous scenario files separately; assert no cross-references (scenario target ids resolve within their workspace's plant). |
| 6 | Runtime state isolated | Instantiate two runtimes (SHW + continuous_mvp_01) in one process; assert `RuntimeState` / `RingBufferTelemetryStore` instances are distinct and stepping one does not mutate the other. |
| 7 | Output directories/namespaces isolated | `--csv-output`/`--jsonl-output` default per workspace under `out/<workspace_id>/`; MQTT topic prefix defaults `virtual-factory/<workspace_id>/...`; OPC UA namespace `<workspace_id>`; assert a two-workspace run writes disjoint paths and disjoint topic prefixes. |
| 8 | Test fixtures isolated | `tests/test_shw_wtp_*.py` uses `configs/workspaces/shw-wtp/` fixtures; a shared fixture conftest forbids importing `configs/plants/tipa_assy_demo.yaml` inside SHW tests. Assert by a lint/test convention check. |
| 9 | Existing ASSY regression stays green | Full `pytest tests/test_assy_*.py tests/test_ops0*.py tests/test_m6_int_01.py` green before/after SHW workspace addition. |
| 10 | Continuous/compressor scenarios remain runnable | `virtual-factory run --config configs/plants/continuous_mvp_01.yaml --scenario configs/scenarios/normal_operation.yaml` and `--config configs/plants/compressor_train_benchmark_01.yaml` both run; `test_cli_scenario.py`, `test_compressor_train.py` green. |
| 11 | Deterministic workspace resolution | **Invariant:** same workspace manifest/version + semantic contract SHA + `scenario_id` + model/dependency versions ⇒ same resolved workspace composition, absent explicitly changed dependencies. Test asserts the same pinned inputs resolve the same: plant/config references; model type bindings; scenario selection; semantic artifact references; output namespace binding; runtime engine/fidelity selection. |

## 7.1 Enforcement mechanism (frozen)

- Isolation is enforced by **`outputs.namespace` threading** across shared
  runtime-output infrastructure (runtime assembly, telemetry, observation, file
  outputs, MQTT, OPC UA, Sparkplug where applicable, tests). This REQUIRES a
  **dedicated CORE gate** (B8, frozen in C02) and MUST NOT be folded into PH01.
  No PH01 slice that depends on the threaded namespace may proceed before that
  CORE gate is authorized.
- **Deterministic composition resolution is a frozen invariant** (C03): identical
  pinned inputs — workspace manifest/version, semantic contract SHA, `scenario_id`,
  model/dependency versions — MUST resolve to the same workspace composition
  (plant/config refs, model bindings, scenario selection, semantic artifact refs,
  output namespace binding, runtime engine/fidelity), absent explicitly changed
  dependencies.
- A `test_workspace_isolation.py` gate (future) loads every registered
  workspace and asserts the 11 items above in CI (items that depend on the
  threaded namespace only run after the dedicated CORE gate).

## 7.2 PH00 deliverable scope

PH00 defines the plan only. No test is written. No runtime change threads the
namespace yet. Threading workspace identity/provenance across shared
runtime-output infrastructure requires a **dedicated CORE gate** (B8) — it is
NOT a PH01 concern and is NOT described as a “small additive” change. Any PH01
slice that depends on it must wait for the dedicated CORE gate.
