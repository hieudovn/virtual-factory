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

## 7.1 Enforcement mechanism (frozen)

- Isolation is enforced by **`outputs.namespace` threading**, not by directory
  convention alone: the namespace token is propagated
  `workspace manifest → RuntimeAssembly → telemetry frame → gateway topic/prefix/URI → file path`.
- A `test_workspace_isolation.py` gate (future) loads every registered
  workspace and asserts the 10 items above in CI.

## 7.2 PH00 deliverable scope

PH00 defines the plan only. No test is written; no runtime change threads the
namespace yet (that is PH01 + a small additive telemetry/provenance change via
the core-change governance in 08).
