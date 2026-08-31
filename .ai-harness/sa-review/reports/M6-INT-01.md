# M6-INT-01 — ASSY Reality Observation Bridge & MES Outbound Integration (P0)

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `M6-INT-01` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline | `83dae4fb3712091d59055b86e37f3034b2bbae8d` (authorized) |
| Head | `2380f54c099dd93f4b2f9c81b3db67ddd60a9ff9` (this gate) |
| Production code changed | **YES** (additive; no existing runtime semantics changed) |

## 2. Architecture

Virtual Factory remains the production-reality engine; MES is a downstream
consumer/projection. Implemented direction:

```text
ASSY authoritative runtime facts
        ↓
AssyObservationBridge          (NEW — assembly/observation_bridge.py)
        ↓
RealityInput                   (existing — observation/service.py)
        ↓
ObservationService             (existing)
        ↓
ObservationEnvelope            (existing)
        ↓
ObservationRouter              (existing)
        ↓
MESProjection                  (existing; +1 additive semantic type)
        ↓
ProjectedMessage               (existing)
        ↓
ObservationGateway             (existing: InMemory / Jsonl / MQTT)
```

No `AssyLineRuntime → direct MES payload` path exists. The bridge only reads
runtime truth; it never mutates simulation state.

## 3. Changed files

- `src/virtual_factory/assembly/observation_bridge.py` — NEW: observation
  points, `AssyObservationBridge`, `build_assy_observation_pipeline()`.
- `src/virtual_factory/assembly/operation_execution.py` — `OperationRegistry.
  all_operations()` (read-only enumeration of lifecycle facts).
- `src/virtual_factory/assembly/line_runtime.py` — capture `completed_at_sim_s`
  on operation completion (authoritative execution truth; 2 sites).
- `src/virtual_factory/assembly/demo_controller.py` — attach/poll bridge after
  control actions; `outbound_trace` accessor.
- `src/virtual_factory/observation/projections/mes.py` — +`"release" →
  mes.release` semantic type (additive; no existing mapping changed).
- `src/virtual_factory/ui/api.py` — attach pipeline in `_get_assy_controller`;
  `GET /assy-demo/observations` (read-only trace endpoint).
- `tests/test_m6_int_01.py` — NEW: 15 tests.

## 4. Authoritative source mapping (per P0 observation)

| P0 fact | Source | source_event_id |
|---|---|---|
| Operation completion | `OperationExecution` → `ELIGIBLE_TO_INDEX` (pure-execution stations only: PRE-ASSY, AP01-03, AP05, AP07, AP09, AP10) | `execution_id` (e.g. `EXEC-00001`) |
| AP04 genealogy | `GenealogyStore` join record | `child_wip_id` (e.g. `MTR-0001`) |
| AP06 quality (per attempt) | `QualityHistory` → `QualityRecord` | `record_id` (e.g. `QR-0001`) |
| AP08 visual quality (per attempt) | `QualityHistory` → `QualityRecord` | `record_id` |
| AP11 final-QC PASS | `QualityHistory` → `QualityRecord` (FINAL_QC, PASS) | `record_id` |
| AP11 RELEASE | `AssyWipState.lifecycle == RELEASED` | `release:<wip_id>` |

`positions[]` is NOT used to infer any completion/result/release fact.
AUTO-TIME fields are not promoted to P0 events.

## 5. source_event_id strategy & idempotency

- Every `source_event_id` is derived from a stable domain fact identity. No
  wall-clock time, random UUID, or poll count is used.
- A fact is marked projected only after at least one gateway returns
  DELIVERED; the bridge keeps a `(run_id, source_event_id)` checkpoint.
- Same fact → same `source_event_id` → delivered exactly once; a failed
  delivery is retried on the next poll (at-least-once, never duplicated).
- `run_id = <sub_line_id>:R<generation>`. Generation bumps when simulation
  time regresses (runtime reset), so a reset/new run yields fresh identities
  (`QR-0001` in run R2 ≠ `QR-0001` in run R1).

## 6. Retry attempt strategy

AP06 / AP08 retries are attempt-specific `QualityRecord`s; each attempt has a
distinct `record_id` and `attempt_number`, producing distinct observations:

```text
attempt 1 FAIL  → one quality observation
attempt 2 PASS  → a distinct quality observation
```

No overwrite of attempt 1; no new `OperationExecution` is created for retry.

## 7. AP04 genealogy mapping

Outbound `mes.genealogy_relationship` carries the authoritative relation:
`child_wip_id` (MTR) + `parent_wip_ids` (SSO2 + RSO2) + `component_ids` +
`relationship_type = assembly_join`. Parent/child links are read from
`GenealogyStore`, never reconstructed from WIP ID parsing.

## 8. AP11 PASS vs RELEASE separation

Two distinct facts / identities / message types:

```text
AP11 FINAL_QC PASS → mes.quality_result   (source_event_id = QR-xxxx)
AP11 RELEASE       → mes.release          (source_event_id = release:MTR-xxxx)
```

They are never collapsed into one event.

## 9. FieldPolicy (default-deny)

Each of the 5 observation points carries an explicit `FieldPolicy` allow-list.
Unknown runtime fields (e.g. `internal_secret`, `internal_truth`) are
invisible in the envelope and projected message. Test 13 verifies this.

## 10. Gateway & failure isolation

- Gateways reused: `InMemoryObsGateway`, `JsonlObsGateway` (MQTT optional).
- Gateway failure returns `DeliveryResult.FAILED` and never mutates or reverts
  simulation truth. The line keeps completing operations regardless of MES
  availability (test 10).
- Bridge reads never create timing samples (test 14).

## 11. MANUAL / AUTO equivalence

Same authoritative outcome → semantically identical outbound facts
(message_type / station / disposition / attempt). `completion_mode` is carried
as provenance only and does not change MES truth (test 9).

## 12. Test results

- New suite `tests/test_m6_int_01.py`: **15 passed**.
- Relevant regression suites (M6-INT-01 + AUTO-TIME ×3 + MANUAL-E2E-01 +
  AUTO-EQUIV-01 + M5 ×5 + OPS-04-C01 + OPS-02 schema + OPS-03 interaction):
  **452 passed**.
- Full suite: **1547 passed, 2 failed**. The 2 failures are the two
  historically known, unchanged failures acknowledged in the gate contract:
  - `TestVScenarioSwitch::test_scenario_switch_resets_state`
  - `TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`
    (reproduced identical at baseline `fe6854f` via a clean worktree).

No new failure; no new cross-module regression.

## 13. Deviations / known issues

- None introduced by this gate. The two known failures above predate this gate
  and are documented per the contract.
- `GET /assy-demo/observations` is a read-only additive endpoint (no new
  transport, no mutation).

## 14. Example outbound trace (one motor, HAPPY_PATH)

```text
mes.execution_event         EXEC-00001   OPERATION_COMPLETED  PRE-ASSY  result=DONE
mes.execution_event         EXEC-00002   OPERATION_COMPLETED  AP01      result=DONE
mes.execution_event         EXEC-00003   OPERATION_COMPLETED  AP02      result=DONE
mes.execution_event         EXEC-00004   OPERATION_COMPLETED  AP03      result=CONFIRMED
mes.genealogy_relationship  MTR-0001     AP04_JOIN            AP04      child=MTR-0001 parents=[RSO2-0001, SSO2-0001]
mes.execution_event         EXEC-00006   OPERATION_COMPLETED  AP05      result=DONE
mes.quality_result          QR-0001      QUALITY_RESULT       AP06      attempt=1 disposition=PASS
mes.execution_event         EXEC-00008   OPERATION_COMPLETED  AP07      result=DONE
mes.quality_result          QR-0002      QUALITY_RESULT       AP08      attempt=1 disposition=PASS
mes.execution_event         EXEC-00010   OPERATION_COMPLETED  AP09      result=DONE
mes.execution_event         EXEC-00011   OPERATION_COMPLETED  AP10      result=DONE
mes.quality_result          QR-0003      AP11_FINAL_QC_PASS   AP11      attempt=1 disposition=PASS
mes.release                 release:MTR-0001  AP11_RELEASE    AP11
```

Exception trace (AP06 FAIL → PASS, motor MTR-0002):

```text
mes.quality_result          QR-0002      QUALITY_RESULT  AP06  attempt=1 disposition=FAIL
mes.quality_result          QR-0003      QUALITY_RESULT  AP06  attempt=2 disposition=PASS
```

Full machine-generated traces: `.ai-harness/sa-review/evidence/M6-INT-01/`.

## 15. Recommendation

```text
M6-INT-01 READY FOR SA REVIEW
```
