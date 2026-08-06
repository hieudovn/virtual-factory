# 02 — Product Scope and TIPA Readiness

**Date:** 2026-08-05  
**Reference:** TIPA Final Assembly Line

---

## 1. First Technical Proof (M2)

**Goal:** `DiscreteSimulationEngine` skeleton executing a minimal 2-node source→sink flow using the approved kernel.

**Deliverables:**
- `DiscreteSimulationEngine` with initialize/step/shutdown lifecycle
- Event handler registry (protocol, not implementation)
- `DiscreteRuntimeState` (separate from continuous `RuntimeState`)
- Minimal integration test: source generates entity → sink consumes it
- No visualization, no TIPA configuration

**Exit:** Engine lifecycle works, event dispatch works, 2-node flow produces correct entity conservation.

---

## 2. First Visual Prototype (M4)

**Goal:** SVG renderer displaying the TIPA layout with static node positions, connected to a fake-data snapshot provider.

**Deliverables:**
- `DMRenderer` with keyed incremental SVG updates
- `DMVisualizationStore` with snapshot/delta protocol
- TIPA layout template (fixed coordinates for AP01–AP06)
- Fake-data provider for UI development
- Run controls (start, step, pause, reset)
- No real simulation engine connection yet

**Exit:** Layout renders, inspector works on click, controls send commands (to fake backend).

---

## 3. First Integrated Demo (M5)

**Goal:** Full TIPA assembly line simulation with real engine, real routing, live SVG visualization.

**Scope:**
- 6 parallel processes (AP01–AP06)
- Source input → shared buffers → workstation processing → checkpoint → output
- Line-in, line-out, hold, release
- Quality pass/fail, rework, retest
- Basic breakdown/unavailability
- Manual step + auto-run + hybrid modes
- Live SVG with entity/WIP token animation
- Inspection panel with KPI display

**Exit:** A reviewer can start a TIPA run, step through, inject a fault, see rework, and inspect any node.

---

## 4. Deferred Features

| Feature | Target Milestone |
|---------|-----------------|
| Layout editor (drag-drop topology) | M6 |
| Multi-run comparison | M6 |
| Production scheduling | M7 |
| MES/PlantOS/PIM integration | M7 |
| Authentication/authorization | M6 |
| Canvas renderer migration | M7 |
| Multi-user editing | M7 |
| Historical replay | M7 |

---

## 5. Out of Scope (Productization)

- Real-time PLC/SCADA connection
- Production database integration
- ERP/MRP integration
- Multi-tenant SaaS
- Mobile/tablet UI
- i18n/localization

---

## 6. TIPA Knowledge Readiness Matrix

### 6.1 Process Structure

| Item | Status | Notes |
|------|--------|-------|
| AP01–AP06 exist as parallel processes | **assumed** | From reference: 6 processes, parallel |
| Each process has: workstation + checkpoint | **assumed** | Generic assembly line pattern |
| Two SSO2 input sources feed shared buffers | **placeholder** | Source type, capacity unknown |
| Process times differ per AP | **placeholder** | Need actual cycle times |
| Checkpoint/test criteria | **placeholder** | Pass/fail thresholds unknown |

### 6.2 Material Flow

| Item | Status |
|------|--------|
| Line-in triggers | **placeholder** |
| Line-out destinations | **placeholder** |
| Buffer capacities | **placeholder** |
| WIP limits | **placeholder** |
| Rework routing (which AP handles rework) | **placeholder** |
| Retest after rework | **assumed** |

### 6.3 Quality and Faults

| Item | Status |
|------|--------|
| Quality check at checkpoint | **assumed** |
| Pass → output | **assumed** |
| Fail → rework loop | **assumed** |
| Breakdown types | **placeholder** |
| Repair times | **placeholder** |
| Hold/release triggers | **placeholder** |

### 6.4 Resources

| Item | Status |
|------|--------|
| Operator assignment per AP | **placeholder** |
| Operator skill levels | **unknown** |
| Tooling/equipment per AP | **placeholder** |
| Shared resources across APs | **unknown** |

### 6.5 KPIs

| Item | Status |
|------|--------|
| Throughput per AP | **assumed** |
| Cycle time | **assumed** |
| WIP count | **assumed** |
| Quality yield | **assumed** |
| Rework rate | **assumed** |
| Downtime | **assumed** |
| Specific KPI targets | **customer_confirmation_required** |

---

## 7. Summary

**Known:** 6 parallel processes (AP01–AP06), generic assembly line pattern, need for parallel visualization.

**Assumed:** Standard source→buffer→workstation→checkpoint→output flow, quality pass/fail, rework path.

**Placeholder:** Capacities, cycle times, buffer sizes, operator assignments, breakdown types.

**Unknown:** Operator skill levels, shared resources, customer KPI targets.

**Customer confirmation required:** KPI targets, specific process parameters, operator model depth.
