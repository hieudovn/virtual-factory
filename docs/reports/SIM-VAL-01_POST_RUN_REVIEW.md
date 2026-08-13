# SIM-VAL-01 — Post-Run Review

> **Gate**: SIM-VAL-01 (mandatory audit deliverable)  
> **Baseline SHA**: `4204d4f`  
> **Updated by**: SIM-VAL-01-C01 (continuous browser runtime proof)  
> **Purpose**: Identify missing, misleading, unstable, or incomplete aspects across runtime, model, UI/UX, and observability from the actual sustained end-to-end run.  
> **PM does NOT fix findings here unless explicitly authorized.**

---

## Findings

### A. Runtime / Logic Gaps

```text
Finding ID: A-01
Category: Runtime / Logic Gaps
Observed behavior: Finite SSO2 seed (7/context) exhausts at step 17; line starves.
Evidence: BASELINE_RUN.md — 7 released then 0 WIPs, starvation_step=17.
Expected / desired behavior: Continuous production without starving.
Impact: Demo stops after ~7 motors unless feed driver used.
Root-cause hypothesis: Upstream seed is a fixed finite list; no replenishment path in composition.initialize().
Recommended action: Add bounded upstream replenishment to demo composition (DONE in C01).
Priority: P0 — RESOLVED BY C01
Proposed next gate: —
Confidence: HIGH
RESOLUTION: SIM-VAL-01-C01 added ContinuousFeedPolicy to AssyDemoComposition.
  Actual browser/API instance now sustains >10 releases without starving
  (C01 browser run: 18 created / 11 released, line still full at 12 WIPs).
```

```text
Finding ID: A-02
Category: Runtime / Logic Gaps
Observed behavior: simulation_time_s advances monotonically by 120s per dwell; line_state="stopped" appears even during productive steady-state.
Evidence: C01 browser/API trace — line_state="stopped" 45/45 records while motors continuously created/released.
Expected / desired behavior: Distinguish conveyor instantaneous state from production starvation/idle state.
Impact: "stopped" label can be misread as production stopped/starved.
Root-cause hypothesis: ConveyorState.STOPPED means "conveyor halted, stations may begin operating" (post-index instantaneous state), NOT production stopped. The snapshot is taken after each index completes, so it always shows STOPPED.
Recommended action: Document semantics; optionally add derived presentation field in a future gate.
Priority: P1 — SEMANTICS DOCUMENTED (Path A), presentation improvement deferred
Proposed next gate: I09-P04 (popup/inspector info)
Confidence: HIGH (confirmed via ConveyorState enum: INDEXING/STOPPED/OPERATING/READY_TO_INDEX)
```

```text
Finding ID: A-03 (NEW in C01)
Category: Runtime / Logic Gaps
Observed behavior: AssyDemoComposition.snapshot() returned blank sub_line_id/production_line_id/variant/plant_id.
Evidence: SIM-VAL-01 trace showed sub_line_id="" in all records.
Expected / desired behavior: Authoritative snapshot carries selected sub-line identity.
Impact: Trace identity incomplete; evidence ambiguous.
Root-cause hypothesis: composition.snapshot() called build_snapshot() without attaching ctx.identity.
Recommended action: Attach identity in composition.snapshot() (DONE in C01).
Priority: P0 — RESOLVED BY C01
Proposed next gate: —
Confidence: HIGH
RESOLUTION: SIM-VAL-01-C01 now sets plant_id, production_line_id, sub_line_id, variant in composition.snapshot(). Verified: sub_line_id="ASSY-SL01" in API and trace.
```

### B. Simulation Model Gaps

```text
Finding ID: B-01
Category: Simulation Model Gaps
Observed behavior: RSO2 is produced on-demand only when AP04 occupied and buffer==0; bounded top-up added by feed driver.
Evidence: CONT_FLOW_RESULT — RSO2 buffer=5 at end with driver.
Expected / desired behavior: A realistic RSO2 replenishment cadence/buffer capacity.
Impact: Buffer behavior is a demo simplification, not plant truth.
Root-cause hypothesis: No TIPA RSO2 replenishment model exists.
Recommended action: NEED PLANT VALIDATION / TBD
Priority: TBD
Proposed next gate: plant validation before physical realism gate
Confidence: HIGH (known simplification)
```

```text
Finding ID: B-02
Category: Simulation Model Gaps
Observed behavior: LINE OUT / LINE IN / REWORK are conceptual-only; no physical off-line routing.
Evidence: Frozen EXH contract; UI shows conceptual zone only.
Expected / desired behavior: Plant-faithful off-line routing (future EXH-ROUTE-01).
Impact: Exception handling is representational only.
Root-cause hypothesis: N/A — explicitly frozen.
Recommended action: List as model gap/TBD; implement in EXH-ROUTE-01 after plant validation.
Priority: TBD — Need plant validation
Proposed next gate: EXH-ROUTE-01
Confidence: HIGH (by design)
```

```text
Finding ID: B-03
Category: Simulation Model Gaps
Observed behavior: Station dwell is uniform nominal 120s; no setup/changeover, no manual timing variation.
Evidence: all dwells 120s in trace.
Expected / desired behavior: Per-station dwells reflecting real TIPA process.
Impact: Cycle realism limited.
Root-cause hypothesis: Single nominal dwell config.
Recommended action: NEED PLANT VALIDATION / TBD
Priority: TBD
Proposed next gate: plant validation
Confidence: HIGH (by design)
```

### C. UI / UX Gaps

```text
Finding ID: C-01
Category: UI / UX Gaps
Observed behavior: Following ONE WIP across stations requires clicking; steady-state 12 WIPs visually dense.
Evidence: Frame B at steady state.
Expected / desired behavior: A selected WIP is highlighted across its journey; clearer individual tracking.
Impact: Operator/demo viewer may lose individual motor in crowd.
Root-cause hypothesis: No persistent WIP highlight/path trail.
Recommended action: Add "follow selected WIP" highlight in I09-P04 popup/inspector gate.
Priority: P1 — Improve before official TIPA demo
Proposed next gate: I09-P04
Confidence: MEDIUM
```

```text
Finding ID: C-02
Category: UI / UX Gaps
Observed behavior: AP04 identity change (SSO2 → new MTR child) is not visually obvious; child just appears at AP05.
Evidence: I07-C02 direct-settle at AP04 boundary.
Expected / desired behavior: A visible JOIN moment (rotor cue + new MTR appearance) for understanding.
Impact: JOIN semantics may be missed by viewers.
Root-cause hypothesis: Direct-settle chosen for identity correctness; no JOIN visual cue beyond static rotor.
Recommended action: Add short rotor-feeder JOIN cue (I09-P05 polish) without violating identity boundary.
Priority: P2 — Post-demo / productization
Proposed next gate: I09-P05
Confidence: MEDIUM
```

```text
Finding ID: C-03
Category: UI / UX Gaps
Observed behavior: Conceptual exception area visible during normal HAPPY_PATH run may confuse viewers.
Evidence: Frame B shows OFF-LINE EXCEPTION HANDLING zone during happy path.
Expected / desired behavior: Exception zone clearly inert during normal operation.
Impact: Minor visual noise.
Root-cause hypothesis: Zone always rendered.
Recommended action: Consider de-emphasizing zone when no exception scenario active (future gate).
Priority: P2 — Post-demo
Proposed next gate: I09-P05
Confidence: LOW
```

### D. Data / Observability Gaps

```text
Finding ID: D-01
Category: Data / Observability Gaps
Observed behavior: SSO2 produced total / RSO2 consumed total not exposed in snapshot.
Evidence: ProductionSummary has sso2_buffer/rso2_buffer but no cumulative produced/consumed counters.
Expected / desired behavior: Cumulative upstream counters.
Impact: Conservation audit requires manual parent counting from genealogy.
Root-cause hypothesis: Snapshot only exposes buffer sizes.
Recommended action: Add cumulative counters to ProductionSummary (future authoritative field).
Priority: P1 — Improve before official TIPA demo
Proposed next gate: EXH-OBS-01 or SIM-VAL-02
Confidence: HIGH
```

```text
Finding ID: D-02
Category: Data / Observability Gaps
Observed behavior: WIP age / station cycle time / utilization not exposed.
Evidence: trace has simulation_time_s but no per-WIP timestamps.
Expected / desired behavior: Per-WIP age and station metrics for operators.
Impact: Cannot measure station utilization or blocking duration.
Root-cause hypothesis: Not modeled in snapshot.
Recommended action: Future authoritative fields; derive station cycle time from trace if needed.
Priority: P2 — Post-demo
Proposed next gate: EXH-OBS-01
Confidence: HIGH
```

```text
Finding ID: D-03
Category: Data / Observability Gaps
Observed behavior: Carrier lifecycle (create/reuse/release) not exposed.
Evidence: carrier_id present in positions but no carrier lifecycle events.
Expected / desired behavior: Carrier creation/reuse/release tracking.
Impact: Carrier reuse policy not auditable.
Root-cause hypothesis: Carrier lifecycle not projected to snapshot.
Recommended action: Future authoritative field or event stream.
Priority: P2 — Post-demo
Proposed next gate: EXH-OBS-01
Confidence: HIGH
```

### E. Test / Harness / Evidence Gaps

```text
Finding ID: E-01
Category: Test / Harness / Evidence Gaps
Observed behavior: Motion correctness verified in harness but no pytest-level unit tests for MotionEngine.detect().
Evidence: Harness Section 10 manual tests; no tests/test_motion*.py.
Expected / desired behavior: Automated regression for detector rules.
Impact: Detector regressions could slip through.
Root-cause hypothesis: MotionEngine is JS; no JS test harness in repo.
Recommended action: Add lightweight JS unit test file for detector rules in a future gate.
Priority: P2 — Post-demo
Proposed next gate: I08 hardening
Confidence: HIGH
```

```text
Finding ID: E-02
Category: Test / Harness / Evidence Gaps
Observed behavior: Browser evidence is manual screenshots; long-run stability only validated to 80 steps.
Evidence: SIM-VAL-01 80-step run.
Expected / desired behavior: Longer soak (500+ steps) for stability.
Impact: Unknown long-run drift.
Root-cause hypothesis: N/A — scope limited.
Recommended action: Extend soak test in a future gate.
Priority: P2 — Post-demo
Proposed next gate: I08 hardening
Confidence: MEDIUM
```

### F. Plant Validation / Unknowns

```text
Finding ID: F-01
Category: Plant Validation / Unknowns
Observed behavior: RSO2 replenishment cadence assumed on-demand.
Evidence: step_context on-demand produce.
Recommended action: NEED PLANT VALIDATION / TBD — actual RSO2 feeder cadence.
Priority: TBD
```

```text
Finding ID: F-02
Category: Plant Validation / Unknowns
Observed behavior: Buffer capacity, conveyor sync, carrier reuse, LINE OUT/IN take-off/return points unknown.
Evidence: All assumed in demo model.
Recommended action: NEED PLANT VALIDATION / TBD.
Priority: TBD
```

---

## Summary Tables

### Table 1 — Findings Summary

| ID | Category | Finding | Evidence | Impact | Priority | Recommended Action | Proposed Gate |
|----|----------|---------|----------|--------|----------|-------------------|---------------|
| A-01 | Runtime | Finite SSO2 seed starves at step 17 | baseline run | Demo stops after 7 motors | P0 — RESOLVED BY C01 | bounded replenishment | — |
| A-02 | Runtime | line_state="stopped" is post-index conveyor state, not production stop | C01 trace | Misleading label | P1 — documented | derived presentation field | I09-P04 |
| A-03 | Runtime | Snapshot blank sub_line_id | trace | Trace identity incomplete | P0 — RESOLVED BY C01 | attach identity | — |
| B-01 | Model | RSO2 on-demand cadence | trace | Buffer simplification | TBD | plant validation | plant validation |
| B-02 | Model | LINE OUT/IN/REWORK conceptual-only | frozen contract | Representational only | TBD | EXH-ROUTE-01 | EXH-ROUTE-01 |
| B-03 | Model | Uniform 120s dwell | trace | Cycle realism limited | TBD | plant validation | plant validation |
| C-01 | UI/UX | Hard to follow one WIP in steady state | Frame B | Individual lost | P1 | WIP follow highlight | I09-P04 |
| C-02 | UI/UX | AP04 JOIN identity not visually obvious | direct-settle | JOIN missed | P2 | JOIN visual cue | I09-P05 |
| C-03 | UI/UX | Exception zone shown during happy path | Frame B | Minor noise | P2 | de-emphasize when inert | I09-P05 |
| D-01 | Data | No cumulative SSO2/RSO2 counters | snapshot | Manual audit | P1 | add counters | EXH-OBS-01 |
| D-02 | Data | No WIP age/cycle time | snapshot | No utilization | P2 | future fields | EXH-OBS-01 |
| D-03 | Data | No carrier lifecycle | snapshot | Not auditable | P2 | future events | EXH-OBS-01 |
| E-01 | Test | No JS unit tests for detector | harness only | Regression risk | P2 | JS unit tests | I08 |
| E-02 | Test | No 500+ step soak | 80-step run | Unknown drift | P2 | soak test | I08 |
| F-01 | Plant | RSO2 cadence | assumed | risk | TBD | validate | plant |
| F-02 | Plant | buffer/carrier/LINE IN-OUT | assumed | risk | TBD | validate | plant |

### Table 2 — Missing Data / Observability

| Data Item | Needed For | Currently Exposed? | Safely Derivable? | Recommended Future Source | Priority |
|-----------|-----------|-------------------|-------------------|--------------------------|----------|
| SSO2 produced total | conservation | NO | YES (from genealogy parents) | ProductionSummary counter | P1 |
| RSO2 consumed total | conservation | NO | YES (from genealogy parents) | ProductionSummary counter | P1 |
| SSO2 introduced total | throughput | NO | PARTIAL (from positions) | ProductionSummary counter | P1 |
| upstream SSO2 inventory | feed status | PARTIAL (buffer) | NO | runtime counter | P2 |
| WIP age | operator info | NO | YES (trace) | per-WIP timestamp | P2 |
| station cycle time | utilization | NO | PARTIAL (trace) | runtime metric | P2 |
| station utilization | balancing | NO | NO | runtime metric | P2 |
| blocking/starving duration | bottleneck | NO | PARTIAL | runtime metric | P2 |
| genealogy event timing | audit | YES | — | already exposed | — |
| carrier lifecycle | reuse policy | NO | NO | event stream | P2 |

### Table 3 — Demo Readiness Impact

| Finding ID | Blocks Internal Demo? | Blocks Official Demo? | Can Defer Post-Demo? | Reason |
|------------|----------------------|----------------------|----------------------|--------|
| A-01 | YES | YES | NO | line starves without feed |
| A-02 | NO | YES | NO | misleading clock |
| B-01 | NO | NO | YES | plant validation TBD |
| B-02 | NO | NO | YES | frozen by design |
| B-03 | NO | NO | YES | plant validation TBD |
| C-01 | NO | YES | NO | operator understanding |
| C-02 | NO | NO | YES | polish |
| C-03 | NO | NO | YES | polish |
| D-01 | NO | YES | NO | counters for demo |
| D-02 | NO | NO | YES | post-demo |
| D-03 | NO | NO | YES | post-demo |
| E-01 | NO | NO | YES | hardening |
| E-02 | NO | NO | YES | hardening |
| F-01 | NO | NO | YES | plant validation |
| F-02 | NO | NO | YES | plant validation |

### Table 4 — Plant Validation Questions

| Question | Why It Matters | Current Assumption | Risk If Wrong | Required Before |
|----------|---------------|-------------------|---------------|-----------------|
| RSO2 replenishment cadence | realistic feed | on-demand | feed unrealistic | physical realism gate |
| Physical buffer capacity | blocking behavior | unbounded | over/under-produce | physical realism gate |
| Conveyor synchronization | index timing | single index | timing wrong | physical realism gate |
| Carrier reuse policy | carrier lifecycle | infinite new carriers | carrier count wrong | EXH-OBS-01 |
| LINE OUT take-off point | routing | none | routing wrong | EXH-ROUTE-01 |
| LINE IN return point | routing | none | routing wrong | EXH-ROUTE-01 |
| Rework destination | exception handling | none | handling wrong | EXH-ROUTE-01 |
| Quality disposition workflow | quality | PASS/FAIL/NG only | incomplete | EXH-DOM-01 |

---

## SA Decision Input

### A. Must fix before proceeding
- **A-01**: Ship the minimal feed driver (`tools/run_assy_continuous_validation.py`) or add bounded replenishment to demo composition. (P0)

### B. Should improve before official demo
- **A-02**: Detect idle/empty state; surface non-productive time.
- **C-01**: Add "follow selected WIP" highlight.
- **D-01**: Add cumulative SSO2/RSO2 produced/consumed counters.

### C. Can defer post-demo
- C-02 (JOIN cue), C-03 (zone de-emphasis), D-02, D-03, E-01, E-02.

### D. Requires plant validation
- B-01, B-03, F-01, F-02.

### E. No change recommended
- None.

---

**PM STOPS HERE. No finding was silently fixed in this gate.**
