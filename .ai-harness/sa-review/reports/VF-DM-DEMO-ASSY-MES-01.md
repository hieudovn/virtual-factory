# VF-DM-DEMO-ASSY-MES-01 — TIPA ASSY Customer Demo Scenario v1

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-DM-DEMO-ASSY-MES-01` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/dm-demo-assy-mes-01` |
| Baseline (origin/main) | `17a1d9ecafb170fa94e8d01a1f12d84e79982773` |
| Contract version | `tipa-assy-demo-v1` |
| Production code changed | YES (additive only) |
| Simulation engine redesigned | NO |
| Observation pipeline core redesigned | NO |
| MQTT gateway redesigned | NO |

## 2. Objective

Deterministic, resettable single-sub-line (`ASSY-SL01`) VF→MES demo:
`SSO2+RSO2 → PRE-ASSY → AP01..AP11 → LINE_OUT`, with 4 deterministic WIPs,
independent line-state/exception/downtime/LINE_OUT/quality/genealogy events,
and a reconciled OEE summary, routed through the existing M5 pipeline
(`RealityInput → ObservationService → ObservationRouter → MESProjection →
JSONL/MQTT gateways`).

## 3. What was built

New package `src/virtual_factory/assembly/demo_assy_mes/`:

- `model.py` — domain vocabulary (`LineState`, `LineOutDisposition`, `Station`,
  `FactKind`, `DemoFact`, `ScenarioSpec`).
- `oee.py` — `OeeSummary` + `compute_oee` (A/P/Q reconciliation).
- `scenario.py` — `build_scenario_facts()` (deterministic fact script).
- `bridge.py` — `build_observation_points()`, `build_demo_pipeline()`,
  `fact_to_reality()` (DemoFact → M5 RealityInput).
- `runner.py` — `DemoRunner` (reset/start/pause/step/jam/recover, OEE, snapshot).
- `controller.py` — `DemoController` (control surface).
- `fixtures.py` — `build_fixtures()` (pure, from real messages).
- `__main__.py` — one-command end-to-end demo runner.

Additive projection change `observation/projections/mes.py`:
- `mes.oee_summary` semantic type; `LINE_OUT`/`WIP_ENTERED`/`DOWNTIME_*`
  event types → `mes.execution_event`.

Minimal control surface in `ui/api.py`:
- `POST /demo-assy-mes/{reset,start,pause,step,jam,recover}`
- `GET /demo-assy-mes/{snapshot,messages}`

## 4. The four deterministic WIPs

| WIP | Journey | LINE_OUT |
|---|---|---|
| `MTR-DEMO-001` | happy: AP04 join, AP06/AP08/AP11 PASS | GOOD |
| `MTR-DEMO-002` | AP06 FAIL a1 → rework → PASS a2 | GOOD |
| `MTR-DEMO-003` | AP05 jam → FAULT → STOPPED → recover → RUNNING | GOOD |
| `MTR-DEMO-004` | AP11 final-QC FAIL (terminal) | REJECT |

## 5. OEE reconciliation (verified)

```text
planned=1200  downtime=120  run=1080  ideal_cycle=240
actual=4  good=3  reject=1
A = 1080/1200 = 0.9
P = 240×4/1080 = 0.888889
Q = 3/4 = 0.75
OEE = 0.9 × 0.888889 × 0.75 = 0.6 (60%)
```

Computed from simulated data (LINE_OUT counts + downtime interval), not
hard-coded. `run + downtime == planned`, `good + reject == actual`.

## 6. Message contract

Every message carries: stable idempotency key, `contract_version`
(`tipa-assy-demo-v1`), `run_id` (`ASSY-SL01:R<n>`), `subline_id`, station
identity, WIP identity, `simulation_time_s`.

Emitted types (63 messages/run): `mes.run_status` ×4, `mes.issue` ×2,
`mes.execution_event` ×39, `mes.quality_result` ×13,
`mes.genealogy_relationship` ×4, `mes.oee_summary` ×1.

## 7. Tests

- `tests/test_demo_assy_mes_v1.py`: **19 passed** (topology, four WIPs,
  fault/recovery, LINE_OUT, OEE reconciliation, determinism, reset,
  idempotency, projection, JSONL serialization, control surface).
- Full suite: **1086 passed** (no failures, no regression).

## 8. Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| A01 | Deterministic repeated runs (same output/order) | PASS |
| A02 | Reset leaves no runtime state | PASS |
| A03 | No duplicate events on retry (stable keys) | PASS |
| A04 | JSONL / MQTT serialization compatible | PASS |
| A05 | OEE + counters reconcile | PASS |
| A06 | Existing VF suite no regression | PASS |
| A07 | Tests for topology, 4 units, fault/recovery, LINE_OUT, fixtures | PASS |
| A08 | Demo command / guide | PASS (`python -m virtual_factory.assembly.demo_assy_mes`) |

## 9. Evidence

`.ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-01/`:
`preflight.json`, `demo-run.jsonl` (63 real messages), `fixtures/` (9 fixture
files), `regression-full.txt`.

## 10. Changed files

- `src/virtual_factory/assembly/demo_assy_mes/` (new)
- `src/virtual_factory/observation/projections/mes.py` (additive)
- `src/virtual_factory/ui/api.py` (minimal control surface)
- `tests/test_demo_assy_mes_v1.py` (new)
- `docs/deployment/demo-assy-mes.md` (new)
- `.ai-harness/tasks/VF-DM-DEMO-ASSY-MES-01.json` (task contract)

No change to `discrete/`, observation pipeline core, or gateways.

## 11. Recommendation

```text
VF-DM-DEMO-ASSY-MES-01 — READY FOR SA REVIEW
```
