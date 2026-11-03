# TIPA-VF-G1B-COMPAT-01 — VF ↔ MES/PlantOS/QMS C1–C5 compatibility audit

**Issue:** [#129](https://github.com/hieudovn/virtual-factory/issues/129)  
**Task contract:** `.ai-harness/tasks/TIPA-VF-G1B-COMPAT-01.json`  
**Governance:** `.ai-harness/PM-EXECUTION-CONTRACT.md`  
**Design input (unmerged):** PR [#132](https://github.com/hieudovn/virtual-factory/pull/132), head `ff485d5bb50e55e91b90008465e4cc87ab7a9f22`  
**Mode:** read-only audit / test-only evidence. **No VF, MES or PlantOS production code, config or test was changed. No live MES/MQTT/PlantOS write.**

## 1. Verified heads and access

| Repository | Branch | Observed head | Access / use |
|---|---|---|---|
| `hieudovn/virtual-factory` | `main` | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` | local clone; read-only audit and tests |
| `hieudovn/MES-dev-and-demo-project` | `main` | `2c4d01d437bf25b44adffd610350e9df6773a853` | authenticated read-only shallow clone |
| `hieudovn/PlantOS` | `main` | `23126a470c0a5faff0046251bb979117b115a169` | authenticated read-only shallow clone |
| Design input | `sa/design/tipa-vf-g1-approved-baseline` | `ff485d5bb50e55e91b90008465e4cc87ab7a9f22` | PR #132, unmerged |

MES head message is `Merge PR #136: S02 release candidate - #129 + #130 + #131`.
Those are MES-side issue numbers, not VF Issue #129. The MES SHA is an observed
execution target, not a pinned future SHA.

## 2. Decision

```text
C1–C4: compatible_with_constraints (field-level EXISTING_MAPPED at observed MES head)
C5:    NEW_PLANNED — not implemented, not routable through C4
Hold:  DISCREPANCY — record-only hold can be read as an operational hold
```

This is an audit result, not G1B approval, not C5/QMS integration authorization
and not G2 authorization.

## 3. Source ownership — one authoritative writer per fact

| Contract | Authoritative producer | VF/MES/PlantOS role | Evidence |
|---|---|---|---|
| C1 raw TIPA IoT | TIPA PLC / IoT source | VF must not write live TIPA topics; MES accepts through profile validation | MES `ingest/tipa_iot/validator.py`, `source_profile.py` |
| C2 `tipa-mes-semantic-v1` | MES normalizer from accepted C1 | VF does not reconstruct C2 | MES `ingest/tipa_iot/normalizer.py:96-186` |
| C2b `tipa-cycle-evidence-v1` | MES raw order packet evidence | exact original bytes; not a C2 reverse transform | MES `ingest/tipa_iot/cycle_evidence.py:11-49` |
| C3 `tipa-mes-finished-v1` | MES append-only Finished | Finished ≠ Good ≠ QualityRelease | MES `odoo/custom_addons/mes_iot_integration/services/finished_product_service.py:8,52-105` |
| C4 `tipa-assy-demo-v1.1` | VF six-sub-line bridge | MES is consumer only | VF `src/virtual_factory/assembly/assy_mes_bridge.py:81`; MES adapter |
| C5 `vf-qms-evidence-v1` candidate | **none — planned** | must not be sent through C4 | MES allowlist; PR #132 design draft |
| PlantOS synthetic VF export | VF workspace exporter | isolated `virtual-factory/...` namespace; not PlantOS production | VF `src/virtual_factory/workspaces/plantos_export.py`; PlantOS contract docs |

## 4. Field-level matrix

The full matrix is in the evidence files; this table is the consolidated
decision view.

### C1 — raw TIPA IoT → MES accepted profile

| Source contract | Source field | Authoritative producer | Destination contract | Destination field | Supported? | Transform | Identity scope | Idempotency scope | Provenance | Verdict | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | topic `enterprise/site/area/zone/line_segment` | TIPA IoT | MES current observation | source identity | Yes | area alias, profile line check | line/machine key | delivery key | `source_system=iiot`, profile | `EXISTING_MAPPED` | `02` |
| C1 | `source_timestamp` / `timestamp` / `publish_timestamp` | TIPA IoT | MES times | source/platform/received/event time | Yes | UTC; source preferred, never publish-as-source | event time | delivery key | `event_time_source` | `EXISTING_MAPPED` | `02` |
| C1 | state/order/process/condition/energy payload fields | TIPA IoT | MES `data.*` | listed fields only | Yes | numeric/status mapping; no inverse fabrication | line/machine | fingerprint + payload hash | `source_profile` | `EXISTING_MAPPED` | `02` |
| C1 | unlisted payload fields | TIPA IoT | none | none | **No** | dropped | — | — | — | `UNAVAILABLE_PENDING_TIPA` | `02` |

### C2 / C2b / C3

| Source contract | Key fields | Destination | Supported? | Transform | Verdict |
|---|---|---|---|---|---|
| C2 `tipa-mes-semantic-v1` | `delivery_key`, `source_entity_key`, `domain`, `times.*`, `quality`, `semantic_fingerprint`, `data.*` | current observation | Yes | normalized semantic, no raw reconstruction | `EXISTING_MAPPED` |
| C2b `tipa-cycle-evidence-v1` | `packet_b64`, `cycle_evidence_only`, evidence hashes | cycle evidence ledger | Yes | exact original bytes/base64 | `EXISTING_MAPPED` |
| C3 `tipa-mes-finished-v1` | `identity_key`, `lot_serial`, `qty==1`, `line_external_code`, `source_timestamp`, `so`, `wo`, `topic`, `payload` | `mes.line.out` | Yes | evidence only; no quality assertion | `EXISTING_MAPPED` |
| C3 quality | good/reject | none | **No** | — | `UNAVAILABLE_PENDING_TIPA` |

### C4 — `tipa-assy-demo-v1.1`, 9 message types

| C4 type | Key source fields | Destination | Supported? | Constraint | Verdict |
|---|---|---|---|---|---|
| `mes.run_status` | `line_state`, `conveyor_state`, `reason_code` | `mes.line.state.event` | Yes | strict line-state map; conveyor separate | `EXISTING_MAPPED` |
| `mes.execution_event` | `event_type`, `station_id`, `wip_id`, `reason_code`, `downtime_s` | production event / line-out / downtime | Yes | exact event-type dispatch, no fallback | `EXISTING_MAPPED` |
| `mes.issue` | `EXCEPTION_RAISED/RESOLVED`, `reason_code` | `mes.exception.case` | Yes | correlated raise/resolve; `AP05_JAM` equipment issue | `EXISTING_MAPPED` |
| `mes.quality_result` | `record_id`, `check_type`, `disposition`, `attempt_number`, `is_terminal`, `terminal_state`, `observations` | `mes.quality.result/observation` | Yes | per-attempt; strict finality types | `EXISTING_MAPPED` |
| `mes.genealogy_relationship` | `child_wip_id`, `parent_wip_ids[]` | `mes.genealogy.relation` | Yes | multi-parent preserved | `EXISTING_MAPPED` |
| `mes.release` | `wip_id`, `release_time_s` | `mes.release` | Yes | evidence only; no MO/WO/stock completion | `EXISTING_MAPPED` |
| `mes.oee_summary` | planned/run/downtime/ideal cycle/counts/A-P-Q-OEE | `mes.oee.summary` | Yes | MES recomputes; mismatch >1e-3 rejects | `EXISTING_MAPPED` |
| `mes.checklist_result` | `execution_id`, attempt, counts, `items[]` | `mes.checklist.result` | Yes, v1.1 only | checklist ≠ quality | `EXISTING_MAPPED` |
| `mes.measurement_result` | `measurement_code`, `value`, `unit`, limits, `in_spec` | `mes.measurement.result` | Yes, v1.1 only | grouped per run/record/attempt; AP06 points only | `EXISTING_MAPPED` |

Envelope identity for all 9: `message_key` is the authoritative idempotency key;
`payload.idempotency_key` must equal it; `run_id` must be
`ASSY-SLxx:R<n>` and agree with `subline_id`; workstation identity is composite
`ASSY-SLxx/STATION`; WIP lookup is line/production scoped and refuses ambiguous
or cross-line binding. Evidence: MES adapter validation/dispatch blocks and VF
producer tests.

### C5 candidate

| Source contract | Fields | Destination | Supported? | Verdict |
|---|---|---|---|---|
| `vf-qms-evidence-v1` | `attempt_id`, `operation_execution_id`, `subject.wip_id`, `instrument.*`, measurement + limits, `measurement_time_utc`, `provenance` | none | **No** | `NEW_PLANNED` |
| instrument/calibration semantics | device identity, certificate revision, valid-from/to, discovery vs effective time, OOT impact | none | **No** | `UNAVAILABLE_PENDING_TIPA` |

C5 is not in the MES C4 allowlist. `mes.instrument_calibration` is not an
accepted C4 type. Sending C5 through C4 under a new name is rejected and not
authorized.

## 5. Identity crosswalk — `ASSY-SLxx` ↔ physical AA10

| VF logical | Physical machine | MES line |
|---|---|---|
| `ASSY-SL01` | `AA10-01` | `ASSY-SL01` |
| `ASSY-SL02` | `AA10-02` | `ASSY-SL02` |
| `ASSY-SL03` | `AA10-03` | `ASSY-SL03` |
| `ASSY-SL04` | `AA10-04` | `ASSY-SL04` |
| `ASSY-SL05` | `AA10-05` | `ASSY-SL05` |
| `ASSY-SL06` | `AA10-06` | `ASSY-SL06` |

Authority: MES `deploy/tipa-assy/line_masters_v1.json`, seeded into
`canonical.identity.map`. MES `ingest/config/tipa_assy_v1.yaml` owns MQTT/status
only and must not declare `mes_line`; `check_line_masters_align.py` guards that
rule. This is an observed MES identity mapping, not a guessed VF foreign key.
VF C4 carries logical `ASSY-SLxx`; `factory_run_id` is future work, not a C4
substitute.

## 6. Quality Hold observation vs EffectiveHold — DISCREPANCY

The design requires observation ≠ evaluation ≠ effective hold ≠ disposition ≠
release. The audit found a reader/writer gap:

- `record_only_service.save_observation(env, "hold", ...)` writes a
  `mes.quality.hold` row with default `status="open"` and no NCR/workflow event
  (`record_only_service.py:41-48,405-444`; `mes_quality.py:454-470`).
- The hold model has no `source_system` column; only
  `recording_request_key`/`recording_line_id` mark it
  (`mes_quality.py:504-533`).
- Readers do **not** filter record-only:
  - `mes_quality_state_service._resolve_hold` takes any `status == "open"`
    hold (`:249-262`);
  - `readiness_service.check_quality_hold` searches open holds by
    `workorder_id` (`:41-49`);
  - line monitor counts open holds by `workstation_id`
    (`line_monitor_controller.py:116-132`);
  - workorder hold checks search open holds by workorder/production
    (`mrp_workorder.py:318-356,370-373`).

**Result:** a record-only hold can be treated as an operational HOLD by derived
quality state, WO readiness (when a WO is attached), line-monitor alerts and
workorder hold checks. The writer says it must not drive the hold workflow, but
reader-side authority separation is not enforced. This is a **MES/QMS SA
correction item**, not fixed by this audit.

## 7. PlantOS synthetic publisher boundary

- VF synthetic export is workspace-isolated under `virtual-factory/...` with
  `provenance=SIMULATED_RAW`, deterministic simulated UTC and an explicit
  "not a PlantOS historian" role (`src/virtual_factory/workspaces/plantos_export.py`).
- PlantOS production UNS is `{namespace_root}/{plant_id}/...`, not
  `virtual-factory/...` (PlantOS contract spec §2, `uns`).
- MES PlantOS adapter accepts only `source_system in ("plantos_center",
  "plantos_edge")` and a `plantos-...` event-id shape; it has no separate
  synthetic marker (`mes_core/services/plantos_adapter.py`).

**Verdict:** namespace isolation is `EXISTING_MAPPED with constraint` while VF
keeps `virtual-factory/...` and never publishes into `uns/TIPA/...` or as a
PlantOS center/edge source. A formal synthetic-vs-live authority field is
`NEW_PLANNED`; current PlantOS adapter cannot distinguish a synthetic publisher
that claims `plantos_center`.

## 8. Tests and negative evidence

| Check | Result |
|---|---|
| VF C4 bridge/evidence/finality tests | **55 passed, 1 warning** |
| VF C4 smoke | 666 messages, 9 types, 666 unique keys, 6 sub-lines |
| VF duplicate-poll idempotency | PASS |
| MES static allowlist = 9 C4 types | PASS |
| C5 / `mes.instrument_calibration` not in C4 allowlist | PASS |
| Unknown C4 type / unknown execution event / idempotency mismatch / v1.1-only guard | Static PASS (MES code) |
| MES Odoo adapter/ingress/characterization tests | **NOT RUN** — no Odoo test runtime (`psycopg2` absent; `odoo` resolves only to repo folder) |
| Live MES/MQTT/PlantOS write | **NOT PERFORMED** |

The MES tests are explicitly NOT RUN, not PASS. No compatibility claim that
depends on live MES test execution is made.

## 9. Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| A01 Exact VF/MES/PlantOS heads verified | PASS | `01` |
| A02 Field-level source/destination matrix for C1–C4 | PASS | `02`, `03`, §4 |
| A03 Identity/AA10 crosswalk without guessed foreign keys | PASS | `01`, §5 |
| A04 C4 strict allowlist / negative rejection assessed | PASS (static; MES runtime NOT RUN) | `03`, `05` |
| A05 C5 marked `NEW_PLANNED`; instrument/calibration unresolved | PASS | `04` |
| A06 Hold observation vs effective hold discrepancy reported | PASS (discrepancy) | `04`, §6 |
| A07 One authoritative publisher per fact across IoT/VF | PASS | §3 |
| A08 PlantOS synthetic isolation assessed | PASS (constraint) | `04`, §7 |
| A09 No production code/config/test changed | PASS | Git diff / task gate |
| A10 No MES/PlantOS/QMS write or approval | PASS | Read-only clones; no live calls |
| A11 Exact-head PR/CI evidence | PENDING at report authoring; recorded at PR/issue comment | Task gate |

## 10. Issues / residual risk

| Type | Detail |
|---|---|
| MES runtime evidence | Odoo adapter/ingress tests NOT RUN; static allowlist/dispatch only. |
| Hold authority | Record-only hold can be operational in readers; MES/QMS SA must define and enforce separation. |
| C5 | No implementation, no wire contract, no QMS authority. |
| PlantOS | Synthetic namespace is conventional, not formally marked by the PlantOS adapter. |
| Design input | PR #132 is unmerged design input, not main. |
| Governance | No G1B approval, C5 implementation or G2 authorization is granted by this report. |
| Local environment note | A local full-suite run with a `gh` token that can see private `hieudovn/PlantOS` makes legacy `test_dday_b6_c01...` fail because it asserts PlantOS is absent. This audit did not change that test or PlantOS. Exact-head CI (no PlantOS visibility) passes; the local gate neutralises `gh` auth to match CI. |

## 11. Final status

```text
Derived status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
```

Only the exact-head task gate and PR/issue evidence may confirm this. The PM
does not self-certify COMPLETE/CLOSED, does not modify MES/PlantOS/QMS, does not
merge or deploy, and does not authorize C5 or G2.
