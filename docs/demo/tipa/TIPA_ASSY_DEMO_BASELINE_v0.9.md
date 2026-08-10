# TIPA ASSY Demo Baseline — v0.9

> **Status**: M6-S01 freeze. Implementation-ready specification.
> **Purpose**: Authoritative demo manufacturing baseline for the 21-Aug-2026 TIPA demo.
> **NOT a claim that all TIPA process facts are confirmed.**

---

## 1. Authoritative Demo Topology

```
SSO2 simplified upstream
  → SSO2 semi-finished buffer
  → PRE-ASSY
  → AP01 / ASSY-TB1
  → AP02 / ASSY-TB2
  → AP03 / ASSY-QC1
  → AP04 / ASSY-BB1 (JOIN)
  → AP05 / ASSY-BB2
  → AP06 / ASSY-TEST1
  → AP07 / ASSY-TEST2
  → AP08 / ASSY-TEST3
  → AP09 / PACKING1
  → AP10 / PACKING2
  → AP11 / QC2
  → Finished Product

RSO2 simplified upstream
  → RSO2 semi-finished buffer
  → AP04 JOIN
```

---

## 2. Station Semantics

### PRE-ASSY
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Convert SSO2 semi-finished into initial ASSY WIP | PROVISIONAL_FOR_DEMO |
| Input | SSO2_SEMI_FINISHED | CONFIRMED_FROM_TIPA_DOCUMENT |
| Output | ASSY_STATOR_SIDE_WIP | PROVISIONAL_FOR_DEMO |
| Operation | Stator-side preparation | PROVISIONAL_FOR_DEMO |
| Next | AP01 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP01 / ASSY-TB1
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Assembly station — task block 1 | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ASSY_STATOR_SIDE_WIP | PROVISIONAL_FOR_DEMO |
| Output | ASSY_STATOR_SIDE_WIP (advanced) | PROVISIONAL_FOR_DEMO |
| Operation | Component fitting / winding prep | PROVISIONAL_FOR_DEMO |
| Next | AP02 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP02 / ASSY-TB2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Assembly station — task block 2 | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ASSY_STATOR_SIDE_WIP (from AP01) | PROVISIONAL_FOR_DEMO |
| Output | ASSY_STATOR_SIDE_WIP (advanced) | PROVISIONAL_FOR_DEMO |
| Operation | Coil insertion / winding | PROVISIONAL_FOR_DEMO |
| Next | AP03 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP03 / ASSY-QC1
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Quality check 1 — manual QC / checklist | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ASSY_STATOR_SIDE_WIP (from AP02) | PROVISIONAL_FOR_DEMO |
| Output | ASSY_STATOR_SIDE_WIP (checked) or HOLD | PROVISIONAL_FOR_DEMO |
| Operation | Checklist inspection, visual check, measurement subset | PROVISIONAL_FOR_DEMO |
| Quality | PASS → AP04; HOLD → operator review | PROVISIONAL_FOR_DEMO |
| Next (normal) | AP04 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP04 / ASSY-BB1 (JOIN)
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Join station — motor core assembly | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input A | ASSY_STATOR_SIDE_WIP (from AP03) | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input B | RSO2 semi-finished WIP | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input C | Configurable components (bearings, rotor, etc.) | PROVISIONAL_FOR_DEMO |
| Output | MOTOR_CORE_ASSEMBLY_WIP | PROVISIONAL_FOR_DEMO |
| Genealogy | Parent SSO2 WIP + Parent RSO2 WIP → Child MOTOR WIP | PROVISIONAL_FOR_DEMO |
| Next | AP05 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP05 / ASSY-BB2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Assembly station — task block post-join | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | MOTOR_CORE_ASSEMBLY_WIP | PROVISIONAL_FOR_DEMO |
| Output | MECHANICALLY_ASSEMBLED_MOTOR | PROVISIONAL_FOR_DEMO |
| Operation | Housing assembly, bolt-down, mechanical completion | PROVISIONAL_FOR_DEMO |
| Next | AP06 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP06 / ASSY-TEST1
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Electrical / functional test | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | MECHANICALLY_ASSEMBLED_MOTOR | PROVISIONAL_FOR_DEMO |
| Output | ELECTRICALLY_TESTED_MOTOR or HOLD | PROVISIONAL_FOR_DEMO |
| Tests | Resistance U-V, V-W, W-U; rotation direction; sound | PENDING_TIPA_CONFIRMATION |
| Quality | PASS → AP07; FAIL → HOLD → RETEST → PASS or HOLD | PROVISIONAL_FOR_DEMO |
| Next (normal) | AP07 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP07 / ASSY-TEST2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Additional test / measurement station | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ELECTRICALLY_TESTED_MOTOR | PROVISIONAL_FOR_DEMO |
| Output | ELECTRICALLY_TESTED_MOTOR (verified) | PROVISIONAL_FOR_DEMO |
| Next | AP08 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP08 / ASSY-TEST3
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Visual inspection station | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ELECTRICALLY_TESTED_MOTOR (from AP07) | PROVISIONAL_FOR_DEMO |
| Output | VISUALLY_ACCEPTED_MOTOR or HOLD | PROVISIONAL_FOR_DEMO |
| Quality | PASS → AP09; NG → HOLD → REINSPECT | PROVISIONAL_FOR_DEMO |
| Next (normal) | AP09 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP09 / PACKING1
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Packaging station 1 | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | VISUALLY_ACCEPTED_MOTOR | PROVISIONAL_FOR_DEMO |
| Output | BOXED_MOTOR | PROVISIONAL_FOR_DEMO |
| Next | AP10 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP10 / PACKING2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Packaging station 2 | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | BOXED_MOTOR | PROVISIONAL_FOR_DEMO |
| Output | PALLETIZED_PRODUCT | PROVISIONAL_FOR_DEMO |
| Next | AP11 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP11 / QC2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Final QC / release | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | PALLETIZED_PRODUCT | PROVISIONAL_FOR_DEMO |
| Output | RELEASED_FINISHED_GOOD or HOLD | PROVISIONAL_FOR_DEMO |
| Quality | Final inspection → release or hold | PROVISIONAL_FOR_DEMO |
| Next | Finished Goods / Exit | CONFIRMED_FROM_TIPA_DOCUMENT |

---

## 3. SSO2 Simplified Upstream

| Field | Value | Status |
|-------|-------|--------|
| Purpose | Produce upstream semi-finished WIP for ASSY | CONFIRMED_FROM_TIPA_DOCUMENT |
| Output | SSO2_SEMI_FINISHED (stator/shaft assembly) | PENDING_TIPA_CONFIRMATION |
| Identity | Auto-generated WIP ID; prefix `SSO2-` | PROVISIONAL_FOR_DEMO |
| Fidelity | Simplified — no thermal/hydraulic physics | PROVISIONAL_FOR_DEMO |
| Process | Shrink-fit vs press — unresolved; use configurable `sso2_operation_type` | PENDING_TIPA_CONFIRMATION |
| Release | After configured cycle time; transfer to SSO2 buffer | PROVISIONAL_FOR_DEMO |

---

## 4. RSO2 Simplified Upstream

| Field | Value | Status |
|-------|-------|--------|
| Purpose | Produce RSO2 semi-finished item for AP04 join | CONFIRMED_FROM_TIPA_DOCUMENT |
| Output | RSO2_SEMI_FINISHED (rotor assembly) | PENDING_TIPA_CONFIRMATION |
| Identity | Auto-generated WIP ID; prefix `RSO2-` | PROVISIONAL_FOR_DEMO |
| Fidelity | Simplified — no detailed machining/balancing | PROVISIONAL_FOR_DEMO |
| Process | Configurable generic operation; exact operations TBD | PENDING_TIPA_CONFIRMATION |
| Release | After configured cycle time; transfer to RSO2 buffer | PROVISIONAL_FOR_DEMO |

---

## 5. Conveyor / Pallet Model

| Decision | Value | Status |
|----------|-------|--------|
| Model | Logical indexed conveyor (no physics) | PROVISIONAL_FOR_DEMO |
| Carrier | One pallet per WIP; identity `PALLET-NNN` | PROVISIONAL_FOR_DEMO |
| Movement | Indexed station-to-station with configurable dwell | PROVISIONAL_FOR_DEMO |
| Buffers | Logical buffers at PRE-ASSY, SSO2, RSO2 inputs | PROVISIONAL_FOR_DEMO |
| Blocking | Downstream station full → upstream waits | PROVISIONAL_FOR_DEMO |
| Lane allocation | Single ASSY lane | PROVISIONAL_FOR_DEMO |
| Pallet reuse | Pallet returns after product release | PROVISIONAL_FOR_DEMO |

**Unresolved**: exact lane count, blocking rules, buffer layout → PENDING_TIPA_CONFIRMATION.

---

## 6. Timing Assumptions

| Parameter | Value | Status |
|-----------|-------|--------|
| Model | `demo_cycle_time_s` per station (configurable) | PROVISIONAL_FOR_DEMO |
| Base cycle | 2–5s demo time per station (accelerated) | PROVISIONAL_FOR_DEMO |
| End-to-end target | ~60–120s for one motor through ASSY | PROVISIONAL_FOR_DEMO |
| Acceleration | Supported via `simulation_time_s` multiplier | DESIGN |
| Real cycle times | NOT known; NOT claimed | PENDING_TIPA_CONFIRMATION |

---

## 7. Configuration Strategy

The following must be configurable (not hard-coded):

| Category | Items |
|----------|-------|
| Topology | Station list, routing edges |
| Timing | Per-station `demo_cycle_time_s` |
| Join | AP04 component list, genealogy rules |
| Quality | Thresholds, PASS/FAIL routes, rework target |
| Buffer | Capacities |
| Labels | Station names, WIP state names |
| Observation | Point enable/disable, field selection |
| Visualization | Layout positions |

---

## 8. Design Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| AP04 component list unknown | HIGH | Configurable list; default to 2–3 generic items |
| AP06 test parameters unknown | MEDIUM | Configurable test spec; demo values |
| Conveyor detail unknown | LOW | Logical model sufficient for demo |
| SSO2/RSO2 process detail unknown | LOW | Simplified generic operations |
| TIPA terminology mismatch | LOW | Simulation semantic names; map to TIPA terms later |
