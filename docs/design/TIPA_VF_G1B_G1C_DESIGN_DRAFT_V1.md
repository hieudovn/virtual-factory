# G1B/G1C — TIPA MES/QMS/PlantOS Interface + UX/Scenario Design v0.2

**State: SA DESIGN DRAFT** — pending cross-SA MES/QMS/PlantOS review, physical/semantic source verification and SA/PO desktop UI acceptance.  
**Authority reference:** [#124](https://github.com/hieudovn/virtual-factory/issues/124). [#123](https://github.com/hieudovn/virtual-factory/issues/123) approves product scope, not this field-level contract. No C5 implementation exists.

## 1. Source contracts and writer authority

| Layer | Contract | Current state | Writer authority / rule |
|---|---|---|---|
| C1 | TIPA raw IoT topic/packet | REAL SOURCE, not VF-owned | Preserve true TIPA source, never route simulated packets into live raw production topics |
| C2 | `tipa-mes-semantic-v1` | MES existing normalizer | Canonical current-state observations from correct source mapping |
| C2b | `tipa-cycle-evidence-v1` | MES raw order packet evidence | Preserve original cycle packet and quality of timestamps, not reverse-transform C2 |
| C3 | `tipa-mes-finished-v1` | MES append-only Finished | Finished != Good != QualityRelease |
| C4 | `tipa-assy-demo-v1.1` | VF bridge, MES demo allowlist 9 types | Stable run/subline-scoped keys; additive changes only with MES SA approval |
| C5 | `vf-qms-evidence-v1` candidate | **NEW PLANNED, NOT SUPPORTED** | Immutable raw measurement/inspection/calibration evidence. QMS authority policy distinct. |
| PlantOS | VF synthetic observation/event export | Existing exporter patterns | Isolated synthetic source and topic/namespace; no duplicate production writer |

`C4` actual message vocabulary: `mes.execution_event`, `mes.run_status`, `mes.issue`, `mes.quality_result`, `mes.genealogy_relationship`, `mes.release`, `mes.oee_summary`, `mes.checklist_result`, `mes.measurement_result`. The existing MES allowlist rejects arbitrary new message types. Do not send C5 through C4 by naming it `mes.instrument_calibration` without joint adapter change/revision.

## 2. Identity, time, provenance — candidate shared matrix
| Concept | Identity scope | Evidence source | Constraint |
|---|---|---|---|
| physical Facility, Area, Line, Equipment | real registry effective-time revision | PDF / TIPA asset export / PIM | no inferred location from process sequence |
| VF workspace/module | workspace_id + revision | VF definition | simulation module != physical PLC |
| ASSY logical subline | `ASSY-SL01..06` within run | VF demo | separate crosswalk to raw AA10 equipment names and MES line IDs |
| Process/Operation | route/spec revision + execution id | VF runtime and source packets | operations may span modules, IDs must not be globally reused |
| WIP unit / lot / batch | run/generation-qualified surrogate | MaterialLedger/producer | `motor_no` reused across WO/lines; never global key alone |
| Material transfer | transfer id + producer/consumer ports | committed MaterialFlowLedger | event alone cannot transfer inventory |
| test attempt | stable attempt id / execution / device | source QualityRecord or instrument | append-only even after retest |
| instrument / calibration | device id + certificate/version effective time | equipment definition + calibration fixture | discovery time != effective measurement time |
| Factory event | run + generation + event ID | event ledger | deterministic identity and chronology |
| Finished evidence | source event key + scoped WO/unit | C3 or VF designated projection | not automatically quality approved |
| QMS decision | QMS policy+decision ID | explicit QMS authority | never silently inferred from observation |

All event times as UTC with offset-aware source; `simulation_tick_us` monotonic per FactoryRun; received/publication times separate; local calendar `Asia/Ho_Chi_Minh` production day 06:00→06:00 and shifts A/B/C. Cross-sink key `(source_system, source_event_id, destination, schema_version)` is proposed and must be reconciled with existing adapters in #129.

Provenance enum suggestion: `PDF_EXPLICIT`, `VF_ACCEPTED_BASELINE`, `MES_AS_BUILT`, `SA_INFERENCE`, `SYNTHETIC_ASSUMPTION`, `PENDING_TIPA`. Synthetic observations never identified as live TIPA IoT.

## 3. Quality evidence boundaries and candidate C5
- `InspectionObservation`: raw vision/checklist/rule/qualitative evidence with sample+attempt ID and source.
- `MeasurementAttempt`: immutable `attempt_id`, `operation_execution_id`, `material_ref`, `instrument_id`, `spec_revision`, measurement name, `value` + unit, applicable limits/method, `measurement_time_utc`, calibration revision as-of measurement, raw result, provenance. No decision implicit.
- `CalibrationEvidence`: instrument, certificate/model, `valid_from`, `valid_to`, `observed_or_discovered_at`, calibration status/out-of-tolerance window, reference and uncertainty when modeled. Retrospective impact algorithm filters *actual instrument use time*, process trace and affected WIP, returning candidates only.
- `QualityEvaluation`: rule/spec+revision result tied to evidence; evaluator identified.
- `EffectiveHoldDecision`, `NCR`, `Disposition`, `QualityRelease`: distinct policy/authority states; a record-only hold observation cannot be assumed active containment. MES service may query persisted `mes.quality.hold` as effective hold; MES/QMS SAs must resolve reader/writer separation before integration.
- Model QUALITY `NG/FAIL` separately from plant `FAULT/STOP/DOWNTIME`, and operation `WAITING_FOR_MATERIAL`.

**Potential C5 envelope (illustrative, not an accepted on-wire schema):**

```json
{
  "schema_version": "vf-qms-evidence-v1-draft",
  "event_id": "TIPA-P0-R1:QMS:000124",
  "factory_run_id": "TIPA-P0-R1",
  "event_type": "MEASUREMENT_RECORDED",
  "operation_execution_id": "ASSY-SL03:AP06:OE-40",
  "attempt_id": "ASSY-SL03:AP06:A-02",
  "subject": {"wip_id": "MTR-DEMO-040"},
  "instrument": {"instrument_id": "R-METER-DEMO-01", "calibration_revision": "CAL-01"},
  "measurement": {"name": "R_U-V", "value": 0.29, "unit": "ohm", "lower_limit": 0.30, "upper_limit": 0.40},
  "measurement_time_utc": "2026-10-31T03:05:00Z",
  "provenance": "SYNTHETIC_ASSUMPTION"
}
```
The numeric value and specification are synthetic only, not claimed TIPA process limits.

## 4. Desktop read models / journey design (not approved visual layouts)
1. Factory Overview: facility roster by Workshop/Area/Line, hierarchical breadcrumbs, source-backed current state, production timeline, shift performance, WIP/finished, anomalies; F0/F1 aggregate provenance displayed.
2. Area/Line: workflow/material buffers/in-out, bounded throughput, operation and equipment status, event history, line status timeline (not merely a metric trend), quality summary.
3. Equipment: component condition/signal/time trends, availability, issues, linked instrument and calibration state where modeled.
4. WIP/Motor trace: Material genealogy graph, upstream batch/stator/rotor lineage, AP04 join, testing attempts, release/Finished distinct.
5. QMS: Quality Overview → inspection/measurement attempts → calibration/device → impact candidate set → associated Motor/WO/lot; no auto-disposition.
6. Scenario Console: running FactoryRun, selective scenario injection, compare two run generations, event replay and source/provenance; standalone vs integrated explicit.

Screen-level design must use FactoriX Design System and desktop-first visual approval by SA/PO. PM must not independently claim pixel/interaction fidelity.

## 5. Scenario fixtures / oracles (design target)
| Scenario | Input/fault | Required evidence and invariants |
|---|---|---|
| SC-01 | two streams healthy, valid inputs | two-parent AP04 genealogy, equipment/WO/shift, tests, Finished separate QMS release |
| SC-02 | shaft/casting outage | RSO2 shortage, buffer drains, ASSY AP04 wait, throughput falls; zero auto-feed |
| SC-03 | varnish time/temperature excursion | suspect batch and measured evidence; no all-NG assumption |
| SC-04 | rotor imbalance corrected | original FAIL attempt and new PASS attempt preserved |
| SC-05 | AP06 first FAIL, retest PASS | R_U-V/R_V-W/R_W-U 3 per attempt, correlated instrument/spec |
| SC-06 | vision NG → reinspect | raw observation separate from disposition and line state |
| SC-07 | calibration OOT discovered later | evidence-time usage filter, candidate impacts only |
| SC-08 | duplicate, late, wrong identity, invalid input | quarantine, idempotency, no invented KPI, negative oracle |
| SC-09 | Quality Hold vs equipment fault | separate product containment from machine downtime/OEE |

G6 end-to-end mandatory SC-01/02/04/05/07; bounded target test SC-03/06/08/09. For each fixture, SA will freeze `input_manifest.json`, seed, event order, expected exact facts+counts, genealogy/accounting digest, and negative assertions before PM integrated implementation.

## 6. Cross-SA open approvals / no-go items
- MES SA signs field-by-field C4 and C1/C2/C2b/C3 mapping, including physical logical line crosswalk, distinct write owners and v1.1 extension policy.
- QMS SA signs C5 evidence contract and effective hold vs record-only semantics, calibration retrospective evaluation and Quality Release ownership.
- PlantOS SA signs synthetic topics/identity and what is purely raw observation vs projection; avoid impersonating real IoT source.
- VF SA must evaluate #126 ASSY exact clock API/replenishment seam and #129 real adapter allowlist/negative tests before Design Lock.
- PO/SA approve desktop user flows/visuals. Visual evidence cannot be certified solely by PM.
- All unknown process equipment, PDF interpretation, cycle times, temperatures, tolerance limits and BOM composition must carry explicit provenance and be replaceable configuration, not hardcoded TIPA fact.

**No code/consumer adapter is authorized until above owners approve the relevant boundary.**
