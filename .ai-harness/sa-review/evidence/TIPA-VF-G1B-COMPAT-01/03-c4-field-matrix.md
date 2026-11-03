# 03 — C4 `tipa-assy-demo-v1.1` field matrix (9 message types)

VF producer: `src/virtual_factory/assembly/assy_mes_bridge.py`
(`CONTRACT_VERSION = "tipa-assy-demo-v1.1"`, 9 observed types, 666 messages,
666 unique keys).
MES consumer: `odoo/custom_addons/mes_core/services/mes_virtual_factory_adapter.py`
at MES head `2c4d01d437bf25b44adffd610350e9df6773a853`.

## Envelope / identity (all 9 types)

| Source field | Destination | Supported? | Transform | Identity / idempotency | Verdict |
|---|---|---|---|---|---|
| `message_key` | MES authoritative idempotency | Yes | required | `message_key` = authoritative key | `EXISTING_MAPPED` |
| `payload.idempotency_key` | MES validation | Yes | must equal `message_key`; mismatch rejects | idempotency | `EXISTING_MAPPED` |
| `message_type` | MES allowlist | Yes | exact 9-type allowlist; unknown rejects | dispatch | `EXISTING_MAPPED` |
| `schema_name`, `schema_version` | MES envelope | Yes | required; not used as identity | — | `EXISTING_MAPPED` |
| `payload.contract_version` | MES contract guard | Yes | `tipa-assy-demo-v1` or `v1.1`; checklist/measurement require v1.1 | fail closed | `EXISTING_MAPPED` |
| `payload.run_id` | run scope | Yes | `ASSY-SLxx:R<n>`; prefix must match `subline_id` and resolved line | run identity | `EXISTING_MAPPED` |
| `payload.subline_id` | context binding | Yes | must agree with run prefix; resolved `mes.production.line` | line identity | `EXISTING_MAPPED` |
| `payload.station_id` | workstation | Yes | composite `sub_line_id/station_id` → identity map | composite identity | `EXISTING_MAPPED` |
| `payload.wip_id` / `subject_id` | WIP scope | Yes | WIP search scoped by production + line; ambiguous/missing refuses bind | WIP identity | `EXISTING_MAPPED` |
| `payload.occurred_at` | event time | Yes | parsed to Odoo UTC; simulation seconds are not fabricated into wall clock | time provenance | `EXISTING_MAPPED` |
| `payload.observation_id` | audit only | Yes | never used for dedup | audit | `EXISTING_MAPPED` |

Code: MES `mes_virtual_factory_adapter.py:37-54,90-100,103-160,162-220,281-437`;
VF `assy_mes_bridge.py:81,97,281-291,337-358,1126-1160`.

## Message-type matrix

| C4 message type | Key source fields | MES destination / handler | Supported? | Transform / constraint | Verdict |
|---|---|---|---|---|---|
| `mes.run_status` | `line_state`, `conveyor_state`, `reason_code`, `occurred_at` | `mes.line.state.event` (`_process_run_status`) | Yes | lowercase→UPPERCASE via strict map (`running/fault/stopped/changeover`); conveyor state separate; unknown rejects | `EXISTING_MAPPED` |
| `mes.execution_event` | `event_type`, `station_id`, `wip_id`, `reason_code`, `downtime_s` | `mes.production.event`, `mes.line.out`, `mes.downtime.event` | Yes, event-type allowlist | exact dispatch: `OPERATION_COMPLETED`, `LINE_OUT`, `DOWNTIME_START/END`, `WIP_ENTERED`, `REWORK_TRIGGERED`; unknown rejects (no fallback) | `EXISTING_MAPPED` |
| `mes.issue` | `event_type` (`EXCEPTION_RAISED/RESOLVED`), `reason_code` | `mes.exception.case` (`_process_issue`) | Yes | raise→case, resolve→same correlated case; resolution without raise waits; `AP05_JAM` maps to equipment issue | `EXISTING_MAPPED` |
| `mes.quality_result` | `record_id`, `check_type`, `disposition`, `attempt_number`, `reason_code`, `is_terminal`, `terminal_state`, `proposed_quality_result/reason`, `observations` | `mes.quality.result` + `mes.quality.observation` | Yes | `PASS→passed`, `FAIL/NG→failed`; strict finality marker types; prior attempt preserved; unknown check type→`other` | `EXISTING_MAPPED` |
| `mes.genealogy_relationship` | `child_wip_id`, `parent_wip_ids[]`, `relationship_type` | `mes.genealogy.relation` | Yes | multi-parent preserved; no local parent invention | `EXISTING_MAPPED` |
| `mes.release` | `wip_id`, `release_time_s`, `event_type` | `mes.release` | Yes | evidence-only; **does not** complete MO/WO/post stock | `EXISTING_MAPPED` |
| `mes.oee_summary` | `planned_s`, `run_s`, `downtime_s`, `ideal_cycle_s`, `actual/good/reject_count`, `availability/performance/quality/oee` | `mes.oee.summary` | Yes | MES recomputes A/P/Q/OEE; declared mismatch > 1e-3 rejects | `EXISTING_MAPPED` |
| `mes.checklist_result` | `execution_id`, `attempt_number`, `status`, `required_count`, `completed_count`, `items[]` | `mes.checklist.result` | Yes, **v1.1 only** | checklist ≠ quality; v1 rejected; missing WO/template remains `unmapped` | `EXISTING_MAPPED` |
| `mes.measurement_result` | `execution_id`, `record_id`, `attempt_number`, `measurement_code`, `value`, `unit`, `lower_limit`, `upper_limit`, `in_spec`, `evidence_source` | `mes.measurement.result` + lines | Yes, **v1.1 only** | grouped by run/record/attempt; 3 points/attempt in fixture; invalid value/limits rejects | `EXISTING_MAPPED` |

## Actual observed VF C4 counts at execution

```text
mes.run_status              9
mes.execution_event        399
mes.checklist_result        49
mes.genealogy_relationship  43
mes.issue                    2
mes.quality_result          57
mes.measurement_result      96
mes.release                  5
mes.oee_summary              6
total                      666
unique message keys        666
duplicate message keys       0
sub-lines                    6
```

## Negative / rejection evidence (static)

| Check | Result |
|---|---|
| MES allowlist size is exactly the 9 observed C4 types | PASS (`03` static probe) |
| Unknown `message_type` rejected | PASS (MES `_validate_envelope`, static; MES runtime test NOT RUN) |
| `payload.idempotency_key != message_key` rejected | PASS (static; MES runtime test NOT RUN) |
| Missing/unknown contract version rejected | PASS (static) |
| v1.1-only checklist/measurement with v1 rejected | PASS (static) |
| Unknown `event_type` in `mes.execution_event` rejected (no fallback) | PASS (static) |
| C5 candidate `vf-qms-evidence-v1` not in C4 allowlist | PASS |
| `mes.instrument_calibration` not in C4 allowlist | PASS |

MES adapter/Odoo acceptance tests were **NOT RUN**: no Odoo test runtime
(`psycopg2` absent; `odoo` resolves only to the repository folder). This is
recorded as NOT RUN, not PASS.
