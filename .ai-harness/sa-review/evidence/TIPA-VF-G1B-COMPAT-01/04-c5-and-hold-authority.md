# 04 — C5 candidate, instrument/calibration gap, hold authority, PlantOS boundary

## C5 — `vf-qms-evidence-v1` candidate

**Status: `NEW_PLANNED`, not implemented, not accepted, not routable through C4.**

| Candidate field | Intended meaning | Current destination | Supported? | Verdict |
|---|---|---|---|---|
| `schema_version` | evidence envelope | none | No | `NEW_PLANNED` |
| `event_id` | run/event identity | none | No | `NEW_PLANNED` |
| `factory_run_id` | factory scope | none | No | `NEW_PLANNED` |
| `event_type` | e.g. `MEASUREMENT_RECORDED` | none | No | `NEW_PLANNED` |
| `operation_execution_id` | operation link | none | No | `NEW_PLANNED` |
| `attempt_id` | immutable attempt | none (C4 quality has attempt number, not C5 attempt ID) | No | `NEW_PLANNED` |
| `subject.wip_id` | material reference | C4 WIP only | No C5 | `NEW_PLANNED` |
| `instrument.instrument_id` | device identity | none | No | `UNAVAILABLE_PENDING_TIPA` |
| `instrument.calibration_revision` | calibration as-of measurement | none | No | `UNAVAILABLE_PENDING_TIPA` |
| `measurement.name/value/unit/lower_limit/upper_limit` | measurement evidence | C4 `mes.measurement_result` is a per-attempt fabrication of AP06 R_U-V/R_V-W/R_W-U only | Partial, not C5 | `NEW_PLANNED` |
| `measurement_time_utc` | measurement effective time | none separate from C4 event time | No | `NEW_PLANNED` |
| `provenance` | source authority | C4 `evidence_source` is `DEMO_SYNTHETIC` | Partial | `NEW_PLANNED` |

MES C4 allowlist does not contain `vf-qms-evidence-v1` or
`mes.instrument_calibration` (`mes_virtual_factory_adapter.py:37-47`). Sending a
C5 fact through C4 under a new name would be rejected and is explicitly not
authorized.

### Instrument / calibration semantics missing from current MES/QMS contracts

- No instrument identity/device registry linked to a measurement attempt.
- No calibration certificate/revision with `valid_from`/`valid_to`.
- No observation time vs discovery time separation.
- No retrospective out-of-tolerance impact filter by actual instrument use time.
- No effective `QualityRelease` separate from Finished.
These remain `UNAVAILABLE_PENDING_TIPA` / QMS SA decision, not invented.

## Quality Hold observation vs EffectiveHold authority — **DISCREPANCY**

The design draft requires: observation ≠ evaluation ≠ effective hold ≠
disposition ≠ release; a record-only hold observation cannot be assumed active
containment. The as-built code has a writer/reader gap.

| Step | As-built behaviour | Evidence |
|---|---|---|
| Record-only hold writer | `save_observation(env, "hold", ...)` creates a `mes.quality.hold` row with default `status="open"`; it deliberately creates no NCR/workflow event | `odoo/custom_addons/mes_core/services/record_only_service.py:41-48,405-444`; model default `odoo/custom_addons/mes_core/models/mes_quality.py:454-470` |
| Record-only marker | Hold has no `source_system` field; marker is `recording_request_key`/`recording_line_id`; `source_type` may be `manual` | `mes_quality.py:504-533`; `record_only_service.py:405-437` |
| Derived quality state reader | `_resolve_hold` selects **any** hold with `status == "open"`; no `source_system`/record-only filter | `odoo/custom_addons/mes_core/services/mes_quality_state_service.py:249-262` (`open_hold = quality_holds.filtered(lambda h: h.status == "open")[:1]`) |
| WO readiness reader | `check_quality_hold` searches open holds by `workorder_id`; no record-only/source filter | `odoo/custom_addons/mes_core/services/readiness_service.py:41-49` |
| Line monitor reader | Counts open holds by `workstation_id`; no record-only/source filter | `odoo/custom_addons/mes_shopfloor/controllers/line_monitor_controller.py:116-132` |
| Workorder hold reader | `_get_mes_quality_hold(statuses=("open",))` searches by workorder/production; no record-only filter | `odoo/custom_addons/mes_shopfloor/models/mrp_workorder.py:318-356,370-373` |

**Conclusion:** a record-only hold row can be treated as an operational HOLD by
`derive_quality_state`, WO readiness (when a WO is attached), line-monitor
alerts and workorder hold checks. The record-only writer says it must never
start a hold workflow, but reader-side authority separation is **not enforced**.
This is a **reader/writer discrepancy for MES/QMS SA**, not a VF defect and not
fixed here.

`mes_record_only` rows for quality/NG/measurement are distinguishable by
`source_system`; the hold model is the weak point because it lacks that column
and the readers do not use the recording marker.

## PlantOS synthetic publisher boundary

- VF's existing synthetic export uses a workspace namespace:
  `virtual-factory/{workspace_id}/...` with
  `provenance=SIMULATED_RAW`, `source_id`, simulated UTC and explicit
  "not a PlantOS historian" semantics
  (`src/virtual_factory/workspaces/plantos_export.py:1-40,150-200`).
- MES PlantOS adapter accepts `source_system in ("plantos_center",
  "plantos_edge")` and event-id format `plantos-...`; it has no synthetic-source
  marker beyond that
  (`odoo/custom_addons/mes_core/services/plantos_adapter.py:20-60`).
- PlantOS contract defines production UNS paths under
  `{namespace_root}/{plant_id}/...`, not the VF `virtual-factory/...` prefix
  (PlantOS `docs/contracts/plantos-integration-contract-spec.md` §2, `uns`).
- C4 is a REST/ProjectedMessage path, not MQTT; it does not write PlantOS.

**Verdict:** synthetic namespace isolation is **EXISTING_MAPPED with
constraint** if VF keeps the `virtual-factory/...` prefix and never publishes
into `uns/TIPA/...` or as `plantos_center/edge`. A formal synthetic-vs-live
authority field in PlantOS is `NEW_PLANNED`; current PlantOS adapter cannot
distinguish a synthetic VF publisher that claims `plantos_center`.
