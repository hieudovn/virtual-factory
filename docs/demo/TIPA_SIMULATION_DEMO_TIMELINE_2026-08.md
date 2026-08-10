# TIPA Simulation Demo Timeline — August 2026

> **This document is the execution timeline for the August 2026 TIPA
> Simulation Demo only. It does not replace or modify the general
> Virtual Factory product roadmap.**

---

## 1. Purpose and Scope

This document defines the operational execution timeline, deliverables,
risks, and tracking for the short-term TIPA Assembly Line Simulation
Demo program ending with the official demo on 21-Aug-2026.

**Primary demo scope**: ASSY (Assembly Line)
**Supporting upstream**: SSO2, RSO2 (simplified)

---

## 2. Fixed Dates

| Date | Milestone |
|------|-----------|
| **09-Aug-2026** | Foundation closed, demo planning begins |
| **10-Aug-2026** | ASSY design freeze (M6-S01 baseline v0.9) |
| **17-Aug-2026** | Internal integrated demo |
| **18–20-Aug-2026** | Correction / stabilization window |
| **21-Aug-2026** | Official TIPA demo |

---

## 3. Demo Definition of Done

A viewer must be able to see a realistic simplified motor production flow:

1. SSO2-derived WIP enters ASSY
2. RSO2 semi-finished item arrives at AP04
3. AP04 creates correct assembly/genealogy
4. Motor proceeds through AP01–AP11
5. AP06 executes electrical test (PASS/FAIL)
6. At least one NG/rework/retest scenario if stable
7. AP08 visual inspection executes
8. Product is packed/final-QC'd
9. Finished product created
10. MES receives selected execution/quality/genealogy observations
11. Viewer can follow production flow visually

---

## 4. Achievements to Date

### M2 — Discrete Simulation Foundation
- **Status**: CLOSED
- Architecture: Kernel → Engine → Dispatcher Protocol → HandlerRegistry → domain runtime state
- Controller → Engine, Service → Controller
- Synchronous domain-neutral discrete engine

### M3 — Generic Discrete Manufacturing Model
- **Status**: CLOSED
- Source, Buffer, Processor, Router, Sink, QualityGate
- WIP identity/state, rework path
- TIPA v0 reference topology (NOT authoritative final design)

### M4 — Configuration / Projection / Visualization / MES Boundary
- **Status**: CLOSED
- SimulationDefinition, validation, AssemblyProjection
- SimulationScene, LayoutDefinition, NodeView, EdgeView, WipTokenView
- MESAdapter, MESInput, MESOutput, MESEvent contract boundary

### M5 — Reality Observation & Integration Foundation
- **Status**: CLOSED by SA, all merged
- Architecture: Reality → ObservationPoint → ObservationService → ObservationEnvelope → ObservationRouter → Projection → ProjectedMessage → Gateway → External Boundary
- Reverse: External context → ControlBoundary → SimulationControlBatch
- M5-S01: ObservationType, ObservationEnvelope, idempotency_key
- M5-S02: ObservationPoint, TriggerPolicy, FieldPolicy (default-deny)
- M5-S03: ObservationService, RealityInput, IdentityResolver
- M5-S04: MESProjection, IIoTProjection, ObservationRouter, ControlBoundary
- M5-S05: ObservationGatewayProtocol, MqttObsGateway, JsonlObsGateway

| Milestone | PR | Status |
|-----------|-----|--------|
| M5-AG | #14 | CLOSED / MERGED |
| M5-S01 | #15 | CLOSED / MERGED |
| M5-S02 | #16 | CLOSED / MERGED |
| M5-S03 | #17 | CLOSED / MERGED |
| M5-S04 | #18 | CLOSED / MERGED |
| M5-S05 | #19 | CLOSED / MERGED |

**Final regression**: 1067 passed, 0 failures
**Final CI**: 2/2 checks OK on head 339179e (PR #19)

---

## 5. Current Architecture Baseline

```
Reality
  ↓
ObservationPoint → ObservationService
  ↓
ObservationEnvelope
  ↓
ObservationRouter
  ├─ MESProjection → ProjectedMessage
  └─ IIoTProjection → ProjectedMessage
  ↓
ObservationGateway (MqttObsGateway / JsonlObsGateway)
  ↓
External Consumer (MES / IIoT)
```

**Reverse**:
```
External Context → ControlBoundary → SimulationControlBatch
```

**Key principle**: Virtual Factory models production reality. MES/IIoT observe
selected projections. External data models do not shape the simulation core.

---

## 6. Demo Scope

### ASSY (Primary)
- AP01–AP11 full flow
- WIP movement, station progression, process execution
- AP04 JOIN with genealogy
- AP06 electrical test
- AP08 visual inspection
- NG/rework/retest path
- Live visualization

### SSO2 (Simplified)
- Upstream semi-finished WIP production
- Feed into ASSY PRE-ASSY → AP01

### RSO2 (Simplified)
- Upstream semi-finished item production
- Feed into AP04 JOIN

### MES Integration
- Outbound: production events, quality results, genealogy to MQTT
- Inbound: production context via ControlBoundary (if ready)

### Explicitly Assumed / Mocked
| Component | Treatment |
|-----------|-----------|
| Field acquisition / Edge Layer | ASSUMED to exist |
| PLCs, sensors, barcode hardware | NOT simulated |
| Edge Agent internals | NOT simulated |
| Workstation device internals | NOT simulated |
| Production Odoo RPC | NOT implemented |

---

## 7. Design Freeze — 10 Aug

### Authoritative ASSY Topology

```
SSO2 simplified upstream
  → SSO2 semi-finished buffer
  → PRE-ASSY
  → AP01 / ASSY-TB1
  → AP02 / ASSY-TB2
  → AP03 / ASSY-QC1
  → AP04 / ASSY-BB1 (JOIN with RSO2 item + components)
  → AP05 / ASSY-BB2
  → AP06 / ASSY-TEST1 (electrical test)
  → AP07 / ASSY-TEST2
  → AP08 / ASSY-TEST3 (visual inspection)
  → AP09 / PACKING1
  → AP10 / PACKING2
  → AP11 / QC2
  → Finished Product

RSO2 simplified upstream
  → RSO2 semi-finished buffer
  → AP04 JOIN
```

### Freeze Decisions

| ID | Decision | Status |
|----|----------|--------|
| DF-01 | Station topology AP01–AP11 | DOCUMENTED (baseline v0.9) |
| DF-02 | SSO2 simplified upstream boundary | DOCUMENTED |
| DF-03 | RSO2 simplified upstream boundary | DOCUMENTED |
| DF-04 | WIP state transitions per station | DOCUMENTED |
| DF-05 | AP04 JOIN and genealogy semantics | DOCUMENTED |
| DF-06 | Quality/test/NG/rework/retest behavior | DOCUMENTED |
| DF-07 | Conveyor, pallet, buffer, carrier assumptions | DOCUMENTED |
| DF-08 | Cycle-time / timing assumptions | DOCUMENTED |
| DF-09 | MES observation points for demo | DOCUMENTED |
| DF-10 | MES payload / semantic subset | DOCUMENTED |
| DF-11 | Demo scenarios (happy path, NG, rework) | DOCUMENTED |
| DF-12 | What is REAL vs SIMULATED vs ASSUMED | DOCUMENTED |

---

## 8. Execution Timeline — 09 to 21 Aug

### 09 AUG — Foundation Closed / Demo Planning

**Status**: IN_PROGRESS (evening — inventory complete, freeze prep ready)

- [x] M2 closed
- [x] M3 closed
- [x] M4 closed
- [x] M5 closed (PR #19 merged, 1067 passed)
- [x] Integration foundation ready
- [x] Demo timeline created (this document)
- [x] Inventory remaining TIPA gaps (section 13)
- [x] Prepare ASSY design freeze (DF-01–DF-12 framework)

### 10 AUG — ASSY Design Freeze

**Objective**: Freeze all DF-01 through DF-12 decisions.

Exit: No implementation-critical ambiguity remains.

### 11–12 AUG — TIPA Runtime

**Objective**: Authoritative executable TIPA manufacturing flow.

Scope:
- Simplified SSO2 upstream
- Simplified RSO2 upstream
- ASSY AP01–AP11 topology
- WIP identities, station progression, buffers
- AP04 JOIN with genealogy
- Deterministic happy-path run

Target (end 12-Aug): One complete motor travels upstream → ASSY → finished.

### 13 AUG — Quality / Test / Rework

**Objective**: Quality stations and rework path.

- AP03 checklist/manual QC
- AP06 electrical test PASS/FAIL
- AP08 visual inspection PASS/FAIL
- AP11 packaging/final QC
- At least one NG → HOLD/REWORK/RETEST → PASS scenario

### 14 AUG — Live Visualization

**Objective**: Production state understandable visually.

- ASSY line visualization
- WIP/pallet movement, station state, buffers
- PASS/FAIL, rework/hold indication
- Reuse existing scene/UI foundations (not new framework)

### 15 AUG — MES Demo Integration

**Objective**: MES outbound observation path.

- Reality → Observation → MESProjection → MqttObsGateway → MQTT
- Selected events: operation completion, AP04 genealogy, AP06 test, AP08 visual, WIP completion
- Reverse path if ready: MES context → ControlBoundary

### 16 AUG — Full Rehearsal / Hardening

**Objective**: Run complete demo repeatedly.

- Validate happy path, NG/rework, genealogy, visualization sync
- Verify MES observations, event ordering, idempotency
- No new feature development after this point

### 17 AUG — Internal Demo

**Objective**: DEMO-CANDIDATE build.

Capture feedback. Classify:
- BLOCKER-21AUG
- HIGH
- POLISH
- POST-DEMO

### 18–20 AUG — Correction Window

Allowed: bug fixes, integration correction, timing tuning, scene polish.
Forbidden: new architecture, major refactor, new frameworks.

### 21 AUG — Official TIPA Demo

Main: ASSY line. Supporting: simplified SSO2, RSO2.

---

## 9. Work Breakdown / Task Tracker

| ID | Phase | Task | Priority | Status | Owner | Notes |
|----|-------|------|----------|--------|-------|-------|
| T-01 | 09-Aug | Create demo timeline | P0 | CLOSED | PM | This document |
| T-02 | 09-Aug | Inventory TIPA gaps | P0 | CLOSED | PM | 12 PTC items; 9 CONFIG_ONLY, 2 SMALL_LOGIC, 1 STRUCTURAL |
| T-03 | 10-Aug | M6-S01 Baseline Freeze v0.9 | P0 | IN_PROGRESS | PM | 5 docs created; awaiting SA |
| T-05 | 11-Aug | SSO2 simplified upstream | P1 | NOT_STARTED | | |
| T-06 | 11-Aug | RSO2 simplified upstream | P1 | NOT_STARTED | | |
| T-07 | 11-Aug | ASSY AP01–AP11 flow | P0 | NOT_STARTED | | |
| T-08 | 12-Aug | AP04 JOIN + genealogy | P0 | NOT_STARTED | | |
| T-09 | 12-Aug | Happy-path end-to-end | P0 | NOT_STARTED | | |
| T-10 | 13-Aug | AP03/AP06/AP08/AP11 quality | P0 | NOT_STARTED | | |
| T-11 | 13-Aug | NG/rework/retest path | P1 | NOT_STARTED | | |
| T-12 | 14-Aug | Live visualization | P0 | NOT_STARTED | | |
| T-13 | 15-Aug | MES outbound integration | P0 | NOT_STARTED | | |
| T-14 | 15-Aug | MES inbound (if ready) | P1 | NOT_STARTED | | |
| T-15 | 16-Aug | Full rehearsal | P0 | NOT_STARTED | | |
| T-16 | 17-Aug | Internal demo | P0 | NOT_STARTED | | |
| T-17 | 18–20 | Correction window | P0 | NOT_STARTED | | |
| T-18 | 21-Aug | Official TIPA demo | P0 | NOT_STARTED | | |

---

## 10. Demo Readiness Dashboard

**As of**: 09-Aug-2026

| Dimension | Weight | Rating | Notes |
|-----------|--------|--------|-------|
| Process model / runtime | 25% | 🟡 AMBER | Baseline v0.9 documented; not yet coded |
| WIP + genealogy | 15% | 🟡 AMBER | Model defined; AP04 genealogy specified |
| Quality / test / rework | 15% | 🟡 AMBER | Routing documented; provisional behavior clear |
| Visualization | 15% | 🔴 RED | Not started |
| MES integration | 15% | 🟡 AMBER | Observation matrix defined; not wired |
| Stability / regression | 10% | 🟢 GREEN | 1067 passed |
| Demo script / readiness | 5% | 🔴 RED | Not started |

**Overall Demo Readiness**: ~30% (+5% from M6-S01 baseline freeze)

> M6-S01 baseline freeze complete. All DF-01–DF-12 documented with provisional values.

---

## 11. Risks

| ID | Risk | Prob | Impact | Mitigation | Status |
|----|------|------|--------|------------|--------|
| R1 | ASSY detail not frozen by 10-Aug | Low | High | M6-S01 baseline v0.9 documented | MITIGATED |
| R2 | TIPA process gaps force late changes | Medium | High | Provisional markers, defer non-blockers | OPEN |
| R3 | AP04 join/genealogy incorrect | Medium | Critical | Explicit freeze DF-05, early test | OPEN |
| R4 | Conveyor/pallet too complex | Medium | Medium | Simplify to essential demo behavior | OPEN |
| R5 | Visualization lags runtime | Medium | Medium | Reuse existing; minimal custom UI | OPEN |
| R6 | MES semantic contract mismatch | Low | Medium | Use M5 projection; align with SA | OPEN |
| R7 | MES ingestion not available | Low | Medium | InMemory/JSONL fallback for internal demo | OPEN |
| R8 | NG/rework destabilizes happy path | Medium | High | Clean separation; conditional demo path | OPEN |
| R9 | SSO2/RSO2 fidelity expands scope | Medium | Medium | "Simplified" enforced in freeze | OPEN |
| R10 | Late architecture work threatens 17-Aug | Low | Critical | M5 is closed; no new platform | OPEN |
| R11 | Internal demo feedback exceeds correction window | Medium | High | Strict classification: BLOCKER-21AUG only | OPEN |

---

## 12. Decisions

| ID | Decision | Date |
|----|----------|------|
| D-DEMO-01 | ASSY is primary demo line | 09-Aug |
| D-DEMO-02 | SSO2 and RSO2 are simplified upstream lines | 09-Aug |
| D-DEMO-03 | Field acquisition / Edge Layer assumed to exist | 09-Aug |
| D-DEMO-04 | PLC/sensor/device simulation is post-demo | 09-Aug |
| D-DEMO-05 | MQTT is transport; REST optional | 09-Aug |
| D-DEMO-06 | UNS is addressing convention, not protocol | 09-Aug |
| D-DEMO-07 | CDM provides semantic alignment, not transport | 09-Aug |
| D-DEMO-08 | VF reality model independent from MES data model | 09-Aug |
| D-DEMO-09 | After 17-Aug, feature expansion heavily restricted | 09-Aug |

---

## 13. Open Questions / TBDs

| ID | Question | Classification | Owner |
|----|----------|---------------|-------|
| TBD-01 | Exact cycle times per station | TBD-BLOCKER | PM/SA |
| TBD-02 | AP04 component list and join sequence | TBD-BLOCKER | PM/SA |
| TBD-03 | AP06 test parameters (resistance values etc.) | TBD-NONBLOCKER | PM/SA |
| TBD-04 | AP08 defect classification detail | TBD-NONBLOCKER | PM/SA |
| TBD-05 | Conveyor model (single vs dual) | TBD-BLOCKER | PM/SA |
| TBD-06 | Pallet/carrier ID convention | PROVISIONAL | PM |
| TBD-07 | MES canonical event vocabulary subset | TBD-BLOCKER | SA |
| TBD-08 | Demo script narrative | PROVISIONAL | PM |
| TBD-09 | SSO2/RSO2 process detail | PROVISIONAL | PM/SA |
| TBD-10 | NG/rework station path (which station loops back where) | TBD-BLOCKER | PM/SA |

---

## 14. Change Log

| Date | Author | Change |
|------|--------|--------|
| 09-Aug-2026 | PM | Initial timeline created. M5 CLOSED. Demo planning begins. |
| 09-Aug-2026 | PM | SA correction: TBD-BLOCKER count fixed (5), 09-Aug→IN_PROGRESS, T-01→CLOSED. |
| 10-Aug-2026 | PM | M6-S01 baseline freeze v0.9. 5 docs created. DF-01–DF-12 documented. Readiness ~30%. |

---

## 15. Current Status Summary

**As of**: 2026-08-09 16:00 ICT

| Metric | Value |
|--------|-------|
| **Official Demo** | 21-Aug-2026 |
| **Internal Demo** | 17-Aug-2026 |
| **Days to Internal Demo** | 8 |
| **Days to Official Demo** | 12 |
| **Overall Demo Readiness** | ~30% (+5% from M6-S01) |
| **Current Critical Path** | M6-S02: TIPA runtime implementation |
| **Current Blockers** | None (all PTC items have provisional values) |
| **Next 24h Objective** | SA approval of M6-S01 → begin M6-S02 |
| **Feature Freeze Status** | V0.9 BASELINE DOCUMENTED (awaiting SA approval) |
| **Latest validated regression** | 1067 passed |
| **Latest approved/merged milestone** | M5-S05 (PR #19, head a21478c) |
| **Current main** | a21478c |
