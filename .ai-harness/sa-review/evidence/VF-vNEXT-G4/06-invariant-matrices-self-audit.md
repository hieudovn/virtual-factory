# VF-vNEXT-G4 · Evidence 06 — Invariant matrices self-audit

Five matrices audited over the G4 seam. Each cell states the fail-closed behavior
and the covering test. No value is fabricated to make authorities agree.

## 1. Identity / authority matrix

Sources: graph declaration (`CompositionBinding`), participant registration
(`Coordinator.register`), port declaration (`BoundaryPort`/`PortRef`), transfer
envelope (`BoundaryTransfer`).

| Authority | absent | present-same | present-conflict |
|---|---|---|---|
| workspace_id | allowed (graph/port/transfer all anchor to one workspace) | accepted | fail closed (cross-workspace binding; transfer workspace mismatch) |
| owner scope path | N/A (every port/participant has one) | accepted | fail closed (dangling scope/port ref) |
| port id/ref | N/A | accepted | fail closed (duplicate port identity; duplicate logical binding) |
| run/context id (transfer.run_id) | allowed | carried | N/A in G4 baseline (no second run authority to contradict; not fabricated) |
| coordination boundary/time (window_id / simulation_time_s) | N/A | accepted | fail closed (backward time; time < 0; bool time) |

Tests: ports (canonical identity, workspace-root/`#`/empty, duplicate identity),
graph (dangling, duplicate edge id/logical binding, cross-workspace), transfer
(workspace mismatch), coordinator (dangling participant scope, backward time).

## 2. Port compatibility matrix

| Case | Result |
|---|---|
| out → in | valid |
| in → in | fail closed |
| out → out | fail closed |
| category same | valid |
| category different | fail closed |
| unit/descriptor both-present same | valid |
| unit/descriptor both-present different | fail closed |
| unit absent | allowed (never fabricated) |
| missing port | fail closed (registry.require) |
| duplicate port identity | fail closed |
| output fan-out | deterministic (graph.outbound) |
| input multi-producer | fail closed (implicit merge rejected) |

Tests: `test_composition_ports.py` (all direction/category/unit/descriptor/missing/
duplicate cases), `test_composition_graph.py::test_fan_out_is_deterministic`,
`test_composition_coordinator.py::test_multi_producer_input_rejected`.

## 3. Graph / order matrix

| Case | Result |
|---|---|
| declaration order permutations | identical deterministic binding order |
| registration order permutations | identical deterministic participant/commit order |
| disconnected nodes | allowed (no connectivity requirement) |
| cyclic graph | allowed (no DAG; no cycle error) |
| duplicate edge id | fail closed |
| duplicate logical binding | fail closed |
| dangling endpoint | fail closed |

Tests: `test_composition_graph.py` (deterministic order, cycles, disconnected,
duplicates, dangling), `test_composition_coordinator.py::test_deterministic_order
_independent_of_registration_order` and `test_cycle_staged_exchange_is_deterministic`.

## 4. Time / window matrix

| Case | Result |
|---|---|
| same internal cadence | completes boundary deterministically |
| different internal cadences (fixed substeps vs event cadence) | both reach the same boundary |
| already-at-boundary | no-op completes (no re-advance) |
| local time ahead of requested boundary | fail closed (no backward time) |
| backward target | fail closed |
| participant failure before another advances | window stops; no commit |
| participant failure after another advances | earlier participant stays advanced (NO rollback claimed) |

Tests: `test_different_cadences_reach_one_boundary`,
`test_already_at_boundary_is_no_op`, `test_backward_time_fails_closed`,
`test_advance_failure_stops_window_before_exchange`,
`test_failure_after_another_participant_advanced_is_not_rolled_back`.

## 5. Mutation / isolation matrix

| Case | Result |
|---|---|
| payload source mutable object changed after staging | transfer detached (unchanged) |
| consumer mutates received payload | fail closed (frozen payload) |
| undeclared state write / undeclared exchange | fail closed |
| direct runtime reference in payload (callable/object) | rejected at construction |
| container-only participant registration | fail closed |
| coordinator reach-through into domain state | impossible (only participant surface used) |
| rollback claim after failure | NOT claimed (honest; no restore) |

Tests: `test_composition_transfer.py` (detached, immutable, callable/object
rejected), `test_composition_coordinator.py` (container-only, undeclared exchange,
no-direct-mutation-via-payload, commit-failure-without-rollback).

## Self-audit conclusion

No additional defect of the same class was found beyond the two corrected during
development (multi-producer test fixture needed a second declared source; the
participant-scope resolution now wraps dangling-scope errors into
`CoordinationError`). No architecture/schema change was required; scope stays G4.
