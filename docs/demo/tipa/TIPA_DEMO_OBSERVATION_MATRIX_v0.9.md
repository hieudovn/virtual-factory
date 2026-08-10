# TIPA Demo Observation Matrix — v0.9

> **Status**: M6-S01 freeze. Semantic only. No transport details.

---

## Observation Points

| Station | Reality Event | Observe? | Semantic Type | Subject | Context | Confidence |
|---------|--------------|----------|---------------|---------|---------|------------|
| PRE-ASSY | SSO2 WIP consumed | YES | execution_event | SSO2_SEMI_FINISHED | station=PRE-ASSY | PROVISIONAL |
| AP01 | Operation complete | YES | execution_event | ASSY_STATOR_SIDE_WIP | station=AP01 | PROVISIONAL |
| AP02 | Operation complete | YES | execution_event | ASSY_STATOR_SIDE_WIP | station=AP02 | PROVISIONAL |
| AP03 | QC checklist complete | YES | checklist_result | ASSY_STATOR_SIDE_WIP | station=AP03 | PROVISIONAL |
| AP03 | Measurement taken | YES | measurement | ASSY_STATOR_SIDE_WIP | station=AP03 | PROVISIONAL |
| AP04 | Join complete | YES | genealogy_relationship | MOTOR_CORE_ASSEMBLY_WIP | station=AP04, parent_ss02, parent_rso2 | PROVISIONAL |
| AP04 | Operation complete | YES | execution_event | MOTOR_CORE_ASSEMBLY_WIP | station=AP04 | PROVISIONAL |
| AP05 | Operation complete | YES | execution_event | MECHANICALLY_ASSEMBLED_MOTOR | station=AP05 | PROVISIONAL |
| AP06 | Test complete (PASS) | YES | quality_result | ELECTRICALLY_TESTED_MOTOR | station=AP06, measurements | PROVISIONAL |
| AP06 | Test complete (FAIL) | YES | quality_result + issue | ELECTRICALLY_TESTED_MOTOR | station=AP06, measurements | PROVISIONAL |
| AP06 | Measurement taken | YES | measurement | ELECTRICALLY_TESTED_MOTOR | station=AP06 | PROVISIONAL |
| AP08 | Inspection complete (PASS) | YES | quality_result | VISUALLY_ACCEPTED_MOTOR | station=AP08 | PROVISIONAL |
| AP08 | Inspection complete (NG) | YES | quality_result + issue | VISUALLY_ACCEPTED_MOTOR | station=AP08 | PROVISIONAL |
| AP11 | Release complete | YES | execution_event | RELEASED_FINISHED_GOOD | station=AP11 | PROVISIONAL |
| Any | Rework triggered | YES | issue | (subject WIP) | rework_target, rework_reason | PROVISIONAL |
| System | Run status change | YES | run_status | — | — | DESIGN |

---

## Semantic Types Used

| Type | Purpose |
|------|---------|
| `execution_event` | Operation start/completion |
| `measurement` | Quantitative measurement (resistance, dimension) |
| `checklist_result` | Manual QC checklist outcome |
| `quality_result` | PASS/FAIL/Ng inspection result |
| `genealogy_relationship` | Parent-child WIP relationship |
| `run_status` | Simulation run lifecycle |
| `issue` | Fault, rework, hold event |

---

## NOT Included (Deferred)

- Final MQTT topic names
- Exact CDM/UNS mapping
- Payload field-level schema
- Transport configuration
