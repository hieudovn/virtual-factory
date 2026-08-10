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
| Operation | Stator-side fitting + preparation (TB1) | PROVISIONAL_FOR_DEMO |
| Next | AP02 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP02 / ASSY-TB2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Assembly station — task block 2 | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | ASSY_STATOR_SIDE_WIP (from AP01) | PROVISIONAL_FOR_DEMO |
| Output | ASSY_STATOR_SIDE_WIP (advanced) | PROVISIONAL_FOR_DEMO |
| Operation | Terminal box wiring / connection (TB2) | PROVISIONAL_FOR_DEMO |
| Next | AP03 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP03 / ASSY-QC1
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Mechanical preparation + QC/check activities | PROVISIONAL_FOR_DEMO |
| Input | ASSY_STATOR_SIDE_WIP (from AP02) | PROVISIONAL_FOR_DEMO |
| Output | ASSY_STATOR_SIDE_WIP (prepared/checked) or HOLD | PROVISIONAL_FOR_DEMO |
| Operation | Mechanical prep, visual check, measurement subset | PROVISIONAL_FOR_DEMO |
| Quality | PASS → AP04; HOLD → operator review | PROVISIONAL_FOR_DEMO |
| Next (normal) | AP04 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP04 / ASSY-BB1 (JOIN)
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Join station — motor core assembly | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input A | ASSY_STATOR_SIDE_WIP (from AP03) | MIXED |
| Input B | RSO2 semi-finished WIP | MIXED |
| Input C | Configurable components (empty placeholder; TBD by TIPA) | PROVISIONAL_FOR_DEMO |
| Output | MOTOR_CORE_ASSEMBLY_WIP | PROVISIONAL_FOR_DEMO |
| Genealogy | Parent SSO2 WIP + Parent RSO2 WIP → Child MOTOR WIP | PROVISIONAL_FOR_DEMO |
| Next | AP05 | CONFIRMED_FROM_TIPA_DOCUMENT |

### AP05 / ASSY-BB2
| Field | Value | Status |
|-------|-------|--------|
| Purpose | Assembly station — task block post-join | CONFIRMED_FROM_TIPA_DOCUMENT |
| Input | MOTOR_CORE_ASSEMBLY_WIP | PROVISIONAL_FOR_DEMO |
| Output | MECHANICALLY_ASSEMBLED_MOTOR | PROVISIONAL_FOR_DEMO |
| Operation | Assembly + painting + measurements/runout | PROVISIONAL_FOR_DEMO |
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
| Purpose | Finishing / nameplate station | PROVISIONAL_FOR_DEMO |
| Input | ELECTRICALLY_TESTED_MOTOR | PROVISIONAL_FOR_DEMO |
| Output | FINISHED_MOTOR (with nameplate) | PROVISIONAL_FOR_DEMO |
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

## 5. Conveyor / Pallet Model (CONFIRMED: single-lane stop-and-go)

### Physical Layout

| Fact | Value | Status |
|------|-------|--------|
| Conveyor lanes | ONE lane only | CONFIRMED_FROM_PRODUCT_OWNER |
| Conveyor span | Full ASSY line (PRE-ASSY through AP11) | CONFIRMED_FROM_PRODUCT_OWNER |
| Carrier type | Wooden pallets | CONFIRMED_FROM_PRODUCT_OWNER |
| Workers / QC | Positioned on both sides of conveyor | CONFIRMED_FROM_PRODUCT_OWNER |
| Operations | Sequential along the line; one station per position | CONFIRMED_FROM_PRODUCT_OWNER |

### Movement Model

| Decision | Value | Status |
|----------|-------|--------|
| Model | Logical indexed conveyor (no physics) | DESIGN |
| Mode | STOP-AND-GO / INDEXED | CONFIRMED_FROM_PRODUCT_OWNER |
| Cycle | INDEX → STOP → OPERATE → RELEASE → INDEX → ... | CONFIRMED_FROM_PRODUCT_OWNER |
| Work constraint | All assembly/QC/test/inspection occurs during STOP only | CONFIRMED_FROM_PRODUCT_OWNER |
| Movement constraint | No station work is performed while pallet is moving | CONFIRMED_FROM_PRODUCT_OWNER |

### Carrier / Pallet Identity

| Decision | Value | Status |
|----------|-------|--------|
| Carrier type | Wooden pallet | CONFIRMED_FROM_PRODUCT_OWNER |
| Carrier per WIP | One pallet carries one WIP / motor assembly | CONFIRMED_FROM_PRODUCT_OWNER |
| Carrier association for demo | Same carrier remains associated with the WIP through ASSY | PROVISIONAL_FOR_DEMO |
| Carrier reuse | Carrier reusable after product release | PROVISIONAL_FOR_DEMO |

### Buffers & Blocking

| Decision | Value | Status |
|----------|-------|--------|
| Buffers | Logical buffers at PRE-ASSY, SSO2, RSO2 inputs | PROVISIONAL_FOR_DEMO |
| Blocking (normal) | Downstream station full → upstream waits | PROVISIONAL_FOR_DEMO |
| Overrun policy | If work incomplete at nominal dwell expiry: conveyor stays stopped; cycle extended; WIP does not advance; next index only after work completes | PROVISIONAL_FOR_DEMO |

**Resolved**: single lane, stop-and-go, wooden pallets, work-during-stop.
**Unresolved**: exact overrun/blocking rule, index/movement duration, carrier reuse timing → PENDING_TIPA_CONFIRMATION.

---

## 6. Timing Model

### Conceptual Distinction

The following are separate concepts and must NOT be conflated in implementation:

| Concept | Meaning | Key |
|---------|---------|-----|
| **Line dwell time** | Duration conveyor remains stopped at each index position | `nominal_line_dwell_time_s` |
| **Station operation duration** | Time a specific station needs to complete required work | Per-station, may be ≤ or > dwell |
| **Index movement duration** | Time for conveyor to physically move pallets to next position | `index_movement_duration_s` |

### Demo Baseline Values

| Parameter | Value | Status |
|-----------|-------|--------|
| `nominal_line_dwell_time_s` | 120s | CONFIRMED_FROM_PRODUCT_OWNER |
| `index_movement_duration_s` | Configurable; demo default TBD | PROVISIONAL_FOR_DEMO |
| `station_operation_duration_s` | Configurable per station | PROVISIONAL_FOR_DEMO |
| `simulation_time_multiplier` | Supported for accelerated demo runs | DESIGN |
| Real cycle times | NOT known; NOT claimed | PENDING_TIPA_CONFIRMATION |

### Configurability

- `nominal_line_dwell_time_s` must be configurable (NOT hard-coded)
- May vary by product type, model, routing version, line-balancing state
- Future actual dwell values: TBD according to product/model/process optimization; no fixed range is currently claimed
- Station operation durations are independent of line dwell
- This separation enables future: takt analysis, bottleneck detection, line balancing, what-if simulation

### Provisional: Overrun Behavior

If station work exceeds nominal dwell:

| Decision | Value | Status |
|----------|-------|--------|
| Conveyor | Remains stopped | PROVISIONAL_FOR_DEMO |
| Line cycle | Extended until work completes | PROVISIONAL_FOR_DEMO |
| WIP | Does not advance | PROVISIONAL_FOR_DEMO |
| Next index | Only after required work completes | PROVISIONAL_FOR_DEMO |
| Isolation | Behavior behind configurable line policy | DESIGN |

**⚠️ PROVISIONAL_FOR_DEMO**: Actual TIPA overrun behavior is not confirmed.
Do not claim as confirmed TIPA behavior.

---

## 7. Configuration Strategy

The following must be configurable (not hard-coded):

| Category | Items |
|----------|-------|
| Topology | Station list, routing edges |
| Conveyor | `nominal_line_dwell_time_s`, `index_movement_duration_s`, overrun policy |
| Timing | Per-station `station_operation_duration_s`, `simulation_time_multiplier` |
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
| AP04 component list unknown | HIGH | Configurable list; empty placeholder until TIPA confirms |
| AP06 test parameters unknown | MEDIUM | Configurable test spec; demo values |
| Conveyor overrun rule unconfirmed | LOW | Provisional policy; configurable; isolated |
| SSO2/RSO2 process detail unknown | LOW | Simplified generic operations |
| TIPA terminology mismatch | LOW | Simulation semantic names; map to TIPA terms later |

---

## 9. M6-S02 Conveyor Implementation Invariants

These invariants are authoritative for the upcoming M6-S02 runtime implementation.
They must hold for all ASSY conveyor code.

| ID | Invariant |
|----|-----------|
| INV-CONV-01 | ASSY uses ONE conveyor lane |
| INV-CONV-02 | Conveyor is stop-and-go / indexed |
| INV-CONV-03 | Conveyor-bound processing occurs ONLY while conveyor is stopped |
| INV-CONV-04 | Nominal dwell is configuration-driven; current baseline `nominal_line_dwell_time_s = 120` |
| INV-CONV-05 | Line dwell and station operation duration are separate concepts |
| INV-CONV-06 | Incomplete required work prevents WIP from advancing to next index |
| INV-CONV-07 | WIP identity and pallet/carrier identity remain separate |
| INV-CONV-08 | No conveyor physics is required for the August demo |
| INV-CONV-09 | During each STOP/dwell window, all eligible occupied ASSY station positions may process their respective WIPs concurrently. The conveyor index is a LINE-LEVEL synchronization boundary, not a per-WIP sequential execution trigger. "Concurrent" describes manufacturing semantics only — it does NOT require threads, async execution, or parallel CPU execution. The deterministic synchronous simulation engine may evaluate stations sequentially within one simulation step/window provided the resulting semantics represent the same shared dwell period before the next line index. |
